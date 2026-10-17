"""`coursekit assemble check`: the package of a unit, played in a browser before it is delivered.

Two parts. Without a browser: every file the page and its styles point to is in the package. With one (the installed
Chrome or Edge, driven by Playwright from the store workspace `html-checker`): the unit is played inside the preview page,
whose simulated LMS is as strict as a platform, and `templates/html/checker/check.mjs` reports what it saw. Here it is
compared with what the course says: no errors in the console or failed requests, axe without violations, each test
answered right gives the score it should, every path of every simulation ends where `coursekit paths` says with its
points, the adaptive blocks show the branch their condition asks for, the LMS refuses no value, the saved state fits,
and the unit resumes where it was.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from coursekit import assemble as assemblemod
from coursekit import course as coursemod
from coursekit import delivery as deliverymod
from coursekit import paths as pathsmod
from coursekit import preview, store
from coursekit import simulation as simmod
from coursekit.htmlkit.build import template_dir
from coursekit.i18n import t

Say = Callable[[str], None]

SUSPEND_LIMITS = {"1.2": 4096, "2004": 64000}
SUSPEND_WARN = 0.8  # share of the limit of suspend_data from which the check warns
AXE_ERRORS = ("critical", "serious")  # axe impacts that are errors; moderate and minor are warnings
KEYS = {
    "1.2": {"score": "cmi.core.score.raw", "status": "cmi.core.lesson_status", "success": None, "location": "cmi.core.lesson_location",
            "entry": "cmi.core.entry"},
    "2004": {"score": "cmi.score.raw", "status": "cmi.completion_status", "success": "cmi.success_status", "location": "cmi.location",
             "entry": "cmi.entry"},
}


BROWSERS = {
    "darwin": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
               "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
               "/Applications/Chromium.app/Contents/MacOS/Chromium"],
    "win32": [r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe", r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe",
              r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe", r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe",
              r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"],
}
BROWSER_COMMANDS = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "msedge")


def find_browser() -> str | None:
    """The installed Chrome, Edge or Chromium the check plays with (None when there is none)."""
    for candidate in BROWSERS.get(sys.platform, []):
        path = Path(os.path.expandvars(candidate))
        if path.is_file():
            return str(path)
    for command in BROWSER_COMMANDS:
        found = shutil.which(command)
        if found:
            return found
    return None


class CheckUnavailable(Exception):
    """The browser part cannot run here (no npm, no browser): the check of the files still holds."""


@dataclass
class CheckResult:
    unit: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    lessons: int = 0
    tests: int = 0
    simulations: int = 0
    paths: int = 0
    played: bool = False


def js_round(value: float) -> int:
    """Math.round of JavaScript (halves go up), so the expected score is the player's."""
    return math.floor(value + 0.5)


# ── without a browser ────────────────────────────────────────────────────────────────────────

REF_RE = re.compile(r"""\b(?:src|href|poster)\s*=\s*["']([^"']+)["']""", re.I)
CSS_URL_RE = re.compile(r"""url\(\s*["']?([^"')]+)["']?\s*\)""", re.I)
EXTERNAL_RE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|#|//)", re.I)


def missing_files(folder: Path) -> list[str]:
    """Files the page or its styles point to that are not in the package."""
    missing: list[str] = []

    def look(text: str, base: Path, pattern: re.Pattern) -> None:
        for ref in pattern.findall(text):
            ref = ref.strip().split("#")[0].split("?")[0]
            if not ref or EXTERNAL_RE.match(ref):
                continue
            target = (base / ref).resolve()
            if not target.is_file() and ref not in missing:
                missing.append(ref)

    index = folder / "index.html"
    if index.exists():
        look(index.read_text(encoding="utf-8"), folder, REF_RE)
    for css in folder.rglob("*.css"):
        look(css.read_text(encoding="utf-8"), css.parent, CSS_URL_RE)
    return missing


# ── the scenario: what to play ───────────────────────────────────────────────────────────────

def _walk_bricks(bricks: list[dict]):
    for brick in bricks:
        yield brick
        if brick.get("type") == "CONDITIONAL":
            yield from _walk_bricks(assemblemod.branch_bricks(brick))


def decision_steps(sim: simmod.Simulation, path: dict) -> list | None:
    """The positions of the decisions of a path among its scene's choices and hotspots (None: a scene's "continue"; for a
    task, `{"task": k}`: k things right), as the player marks them (`data-ck-decision`, `data-ck-task`); None if a step
    cannot be found."""
    scenes = sim.data.get("scenes") or {}
    env = dict(sim.data.get("state") or {})
    steps: list[int | None] = []
    for sid, label in path["steps"]:
        scene = scenes.get(sid) or {}
        if label is None:
            steps.append(None)
            continue
        if label.startswith("task:") and simmod.task_of(scene):
            k = int(label.split(":", 1)[1])
            steps.append({"task": k})
            env = {**env, str(simmod.task_of(scene)[1].get("store")): k}
            continue
        found = None
        for i, decision in enumerate(simmod._decisions(scene)):
            if str(decision.get("text") or decision.get("label")) == label and simmod.test(decision.get("if"), env):
                found = (i, decision)
                break
        if found is None:
            return None
        steps.append(found[0])
        env = simmod._apply(found[1], env)
    return steps


def sim_grade(sim: simmod.Simulation, points: float) -> int:
    """The grade the player gives a path (`grade()` of player/simulation.js)."""
    return 0 if sim.max_score <= 0 else max(0, min(100, js_round(100 * points / sim.max_score)))


def best_path(sim: simmod.Simulation) -> dict | None:
    return max(sim.paths, key=lambda p: p["score"], default=None)


@dataclass
class Scenario:
    data: dict
    sims: dict[str, simmod.Simulation]
    tests: list[dict]          # [{lesson, sims: [(id, weight, grade)]}]
    formative: list[tuple[str, float, int]]
    errors: list[str]


def scenario(course: dict, unit: dict, url: str, standard: str) -> Scenario:
    plan, plan_errors, _ = assemblemod.build_plan(course, unit)
    found = pathsmod.unit_simulations(course, unit)
    sims = {sim.id: sim for sim in found.simulations if not sim.errors}
    errors = list(plan_errors) + list(found.errors)
    where: dict[str, str] = {}
    for lesson in plan["lessons"]:
        for brick in _walk_bricks(lesson["bricks"]):
            if brick.get("type") == "SIMULATION":
                where[brick["data"].get("id")] = lesson["key"]
    steps: dict[str, list] = {}
    for sid, sim in sims.items():
        steps[sid] = []
        for n, path in enumerate(sim.paths):
            played = decision_steps(sim, path)
            if played is None:
                errors.append(t("playcheck", "path_unplayable", sim=sid, n=n + 1))
                played = []
            steps[sid].append(played)

    def best(sid: str) -> tuple[list, int]:
        sim = sims[sid]
        path = best_path(sim)
        if path is None:
            return [], 0
        return steps[sid][sim.paths.index(path)], sim_grade(sim, path["score"])

    tests, test_data = [], []
    for lesson in plan["lessons"]:
        if lesson["type"] != "evaluation":
            continue
        scored = [sid for sid, key in where.items() if key == lesson["key"] and sid in sims and sims[sid].scored]
        tests.append({"lesson": lesson["key"], "sims": [(sid, float(sims[sid].data.get("weight") or 1), best(sid)[1]) for sid in scored]})
        test_data.append({"lesson": lesson["key"], "sims": [{"id": sid, "steps": best(sid)[0]} for sid in scored]})
    formative: list[tuple[str, float, int]] = []
    if not tests:
        formative = [(sid, float(sim.data.get("weight") or 1), best(sid)[1]) for sid, sim in sims.items() if sim.scored]
    data = {
        "url": url,
        "keys": KEYS[standard],
        "tests": test_data,
        "formative": [{"id": sid, "steps": best(sid)[0]} for sid, _, _ in formative],
        "sims": [{"id": sid, "paths": steps[sid]} for sid in sims],
    }
    return Scenario(data, sims, tests, formative, errors)


# ── with a browser ───────────────────────────────────────────────────────────────────────────

def run_browser(data: dict, say: Say) -> dict:
    """Play the scenario with `checker/check.mjs` from the store workspace; raises CheckUnavailable when it cannot run."""
    node = shutil.which("node")
    if not node:
        raise CheckUnavailable(t("playcheck", "no_node"))
    template = template_dir() / "checker"
    workspace = store.ensure_workspace("html-checker", template / "package.json", say)
    if workspace is None:
        raise CheckUnavailable(t("playcheck", "no_workspace"))
    shutil.copy2(template / "check.mjs", workspace / "check.mjs")
    with tempfile.TemporaryDirectory() as tmp:
        scenario_file = Path(tmp) / "scenario.json"
        scenario_file.write_text(json.dumps(data), encoding="utf-8")
        result = subprocess.run([node, "check.mjs", str(scenario_file)], cwd=workspace, capture_output=True, text=True,
                                encoding="utf-8", check=False, timeout=900)
    try:
        observed = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        observed = {"ok": False, "error": (result.stderr or result.stdout).strip()[:500]}
    if not observed.get("ok"):
        message = str(observed.get("error") or result.stderr.strip()[:500])
        if message.startswith("no browser"):
            raise CheckUnavailable(t("playcheck", "no_browser", error=message))
        raise CheckUnavailable(t("playcheck", "run_failed", error=message))
    return observed


def adaptive_env(runs: dict, sims: dict[str, simmod.Simulation] | None = None) -> dict:
    """What the adaptive blocks read (updateAdaptive of player/simulation.js): of each simulation that ended, its variables
    and its result (grade, score, maxScore, ending, kind)."""
    env: dict = {}
    for sid, run in runs.items():
        if not run or run.get("d") != 1:
            continue
        env.update({f"{sid}.{key}": value for key, value in (run.get("e") or {}).items()})
        sim = (sims or {}).get(sid)
        ending = str(run.get("a") or "")
        score = float(run.get("s") or 0)
        maximum = sim.max_score if sim else 0
        kind = str(((sim.data.get("scenes") or {}).get(ending) or {}).get("ending") or "") if sim else ""
        env.update({f"{sid}.score": score, f"{sid}.maxScore": maximum, f"{sid}.ending": ending, f"{sid}.kind": kind,
                    f"{sid}.grade": sim_grade(sim, score) if sim else 0})
    return env


def adaptive_expected(condition: str, runs: dict, sims: dict[str, simmod.Simulation] | None = None) -> bool:
    """Whether a branch holds as updateAdaptive (player/simulation.js) decides it: only ended simulations count, and every
    variable the condition reads must be there."""
    env = adaptive_env(runs, sims)
    try:
        names = simmod.names(simmod.parse_expression(condition))
        return all(name in env for name in names) and simmod.test(condition, env)
    except simmod.ExpressionError:
        return False


def adaptive_branch(conditions: list[str], runs: dict, sims: dict[str, simmod.Simulation] | None = None) -> int:
    """The branch that should show: the first that holds, or -1 (the neutral one)."""
    return next((i for i, condition in enumerate(conditions) if adaptive_expected(condition, runs, sims)), -1)


def compare(plan: Scenario, observed: dict, standard: str, result: CheckResult) -> None:
    """Turn what the browser saw into errors and warnings."""
    err, warn = result.errors.append, result.warnings.append
    for line in dict.fromkeys(observed.get("console") or []):
        err(t("playcheck", "console", text=line))
    for line in dict.fromkeys(observed.get("failed") or []):
        err(t("playcheck", "request_failed", text=line))
    seen: set[tuple[str, str]] = set()
    for v in observed.get("axe") or []:
        if (v["id"], " ".join(v["targets"])) in seen:
            continue
        seen.add((v["id"], " ".join(v["targets"])))
        help_text = f'{v["help"]} ({v["detail"]})' if v.get("detail") else v["help"]
        line = t("playcheck", "axe", lesson=v["lesson"], rule=v["id"], impact=v.get("impact") or "?", help=help_text,
                 count=v["count"], targets=", ".join(v["targets"]))
        (err if v.get("impact") in AXE_ERRORS else warn)(line)
    result.lessons = len(observed.get("lessons") or [])

    for test, seen_test in zip(plan.tests, observed.get("tests") or [], strict=False):
        questions = seen_test["questions"]
        weights = sum(w for _, w, _ in test["sims"])
        earned = questions + sum(w * g / 100 for _, w, g in test["sims"])
        expected = js_round(100 * earned / max(1, questions + weights))
        got = seen_test.get("score")
        if got is None or got == "" or abs(float(got) - expected) > 0.5:
            err(t("playcheck", "test_score", lesson=test["lesson"], expected=expected, got=got if got not in (None, "") else "—"))
    result.tests = len(plan.tests)
    if plan.formative:
        total = sum(w for _, w, _ in plan.formative)
        expected = js_round(sum(w * g for _, w, g in plan.formative) / total)
        got = (observed.get("formative") or {}).get("score")
        if got is None or got == "" or abs(float(got) - expected) > 0.5:
            err(t("playcheck", "unit_score", expected=expected, got=got if got not in (None, "") else "—"))

    result.simulations = len(plan.sims)
    for played in observed.get("paths") or []:
        sim = plan.sims.get(played["sim"])
        if sim is None:
            continue
        n = played["n"]
        label = t("playcheck", "best_path") if n < 0 else str(n + 1)
        if played.get("missing"):
            err(t("playcheck", "path_stuck", sim=sim.id, n=label, what=played["missing"], step=(played.get("step") or 0) + 1))
            continue
        if n < 0:
            continue
        result.paths += 1
        path = sim.paths[n]
        run = played.get("run") or {}
        if run.get("d") != 1 or run.get("a") != path["ending"] or float(run.get("s") or 0) != float(path["score"]):
            err(t("playcheck", "path_differs", sim=sim.id, n=n + 1, ending=path["ending"], score=f"{path['score']:g}",
                  got_ending=run.get("a") or "—", got_score=run.get("s", "—"), done="✔" if run.get("d") == 1 else "✘"))
        for block in played.get("adaptive") or []:
            expected = adaptive_branch(block["conditions"], played.get("sims") or {}, plan.sims)
            if expected != block["shown"]:
                names = block["conditions"] + ["else"]  # index -1: the neutral branch
                err(t("playcheck", "adaptive", condition=" | ".join(block["conditions"]), sim=sim.id, n=n + 1,
                      expected=names[expected], got=names[block["shown"]]))

    for problem in {(e["code"], e.get("name") or "", (e.get("value") or "")[:80]): e for e in observed.get("lms") or []}.values():
        err(t("playcheck", "lms_refused", code=problem["code"], message=problem.get("message") or "", name=problem.get("name") or "",
              value=(problem.get("value") or "")[:80]))
    limit = SUSPEND_LIMITS[standard]
    biggest = int(observed.get("maxSuspend") or 0)
    if biggest > limit:
        err(t("playcheck", "suspend_over", size=biggest, limit=limit))
    elif biggest > SUSPEND_WARN * limit:
        warn(t("playcheck", "suspend_near", size=biggest, limit=limit))
    resume = observed.get("resume") or {}
    if resume and (resume.get("entry") != "resume" or resume.get("location") != resume.get("locationAfter")
                   or resume.get("simsBefore") != resume.get("simsAfter")):
        err(t("playcheck", "no_resume", entry=resume.get("entry") or "—", location=resume.get("location") or "—",
              after=resume.get("locationAfter") or "—"))


def check(course: dict, unit: dict, browser: str | None = None, say: Say = print) -> CheckResult:
    """Check the built unit (`assembly/html/unit-NN/`): its files always; played in a browser when one can run (if not,
    a warning says why)."""
    result = CheckResult(unit["n"])
    folder = preview.unit_dir(course, unit["n"])
    for ref in missing_files(folder):
        result.errors.append(t("playcheck", "missing_file", ref=ref))
    standard = "2004" if deliverymod.settings(course)["export"]["standard"] == "scorm_2004" else "1.2"
    server = preview.serve(course, coursemod.package_units(course) or [unit], unit["n"], port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/?unit={unit['n']}"
        plan = scenario(course, unit, url, standard)
        result.errors += plan.errors
        data = dict(plan.data)
        found = browser or find_browser()
        if found:
            data["browser"] = found
        try:
            observed = run_browser(data, say)
        except CheckUnavailable as exc:
            result.warnings.append(str(exc))
            return result
        result.played = True
        compare(plan, observed, standard, result)
    finally:
        server.shutdown()
        server.server_close()
    return result
