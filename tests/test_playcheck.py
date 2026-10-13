"""`coursekit assemble check`: the files of a built package, the scenario it is played with, and how what the browser saw
becomes errors. The browser itself never runs in the tests (its part is replaced); the simulated LMS and the interactions
of the player run with node when it is installed."""

import json
import shutil
import subprocess
from importlib import resources
from pathlib import Path

import pytest

from coursekit import simulation as simmod
from coursekit.cli import main
from coursekit.htmlkit import playcheck
from tests.test_decision_based import SCENARIO
from tests.test_html_backend import html_course  # noqa: F401 - the fixture


def call_sim():
    sim = simmod.parse("scenario", SCENARIO.splitlines()[1:-1], "x")
    assert not sim.errors
    return sim


# ── without a browser ────────────────────────────────────────────────────────────────────────


def test_missing_files_are_found_in_the_page_and_its_styles(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "media").mkdir()
    (tmp_path / "media" / "here.png").write_bytes(b"x")
    (tmp_path / "index.html").write_text(
        '<img src="media/here.png"><img src="media/gone.png"><a href="https://example.com/x">x</a><a href="#top">t</a>'
        '<link href="assets/styles.css"><audio src="media/a.mp3?v=1"></audio>', encoding="utf-8")
    (tmp_path / "assets" / "styles.css").write_text("a { background: url('../media/here.png') } b { background: url(../media/no.svg) }",
                                                     encoding="utf-8")
    assert playcheck.missing_files(tmp_path) == ["media/gone.png", "media/a.mp3", "../media/no.svg"]


def test_every_path_becomes_the_positions_the_player_marks():
    sim = call_sim()
    steps = {tuple(playcheck.decision_steps(sim, path)) for path in sim.paths}
    # choices 0-2, the hotspot is the fourth decision (3) and its scene goes on with "continue" (None)
    assert steps == {(0,), (1,), (2,), (3, None)}


def test_js_round_and_the_grade_of_a_path_are_the_players():
    sim = call_sim()
    assert playcheck.js_round(2.5) == 3 and playcheck.js_round(-0.5) == 0
    assert playcheck.sim_grade(sim, 1) == 50 and playcheck.sim_grade(sim, -2) == 0 and playcheck.sim_grade(sim, 2) == 100
    assert playcheck.best_path(sim)["score"] == 2


def test_the_adaptive_branch_needs_ended_simulations():
    ended = {"call": {"a": "leak", "e": {"risk": 3}, "s": -2, "d": 1}}
    assert playcheck.adaptive_expected("call.risk >= 3", ended)
    assert not playcheck.adaptive_expected("call.risk >= 3", {"call": {**ended["call"], "d": 0}})
    assert not playcheck.adaptive_expected("other.x > 1", ended)
    assert not playcheck.adaptive_expected("call.risk >=", ended)


# ── what the browser saw ─────────────────────────────────────────────────────────────────────


def scenario_of(sim):
    return playcheck.Scenario({}, {"call": sim}, [{"lesson": "U1-E1.1", "sims": [("call", 1.0, 100)]}], [], [])


def good_observation(sim):
    paths = []
    for n, path in enumerate(sim.paths):
        run = {"a": path["ending"], "e": path["state"], "s": path["score"], "d": 1}
        shown = path["state"].get("risk", 0) >= 3
        paths.append({"sim": "call", "n": n, "missing": None, "run": run, "sims": {"call": run},
                      "adaptive": [{"condition": "call.risk >= 3", "shown": shown}]})
    return {"ok": True, "console": [], "failed": [], "axe": [], "lessons": [{"key": "U1-S1"}, {"key": "U1-E1.1"}],
            "tests": [{"lesson": "U1-E1.1", "questions": 2, "score": "100"}], "paths": paths, "lms": [], "maxSuspend": 300,
            "resume": {"entry": "resume", "location": "U1-S1", "locationAfter": "U1-S1", "simsBefore": {}, "simsAfter": {}}}


def test_a_package_that_plays_as_the_course_says_has_no_errors():
    sim = call_sim()
    result = playcheck.CheckResult(1)
    playcheck.compare(scenario_of(sim), good_observation(sim), "1.2", result)
    assert result.errors == [] and result.warnings == []
    assert (result.lessons, result.tests, result.simulations, result.paths) == (2, 1, 1, 4)


def test_every_difference_is_an_error():
    sim = call_sim()
    seen = good_observation(sim)
    seen["console"] = ["boom", "boom"]
    seen["failed"] = ["http://x/media/a.png (404)"]
    seen["axe"] = [{"lesson": "U1-S1", "id": "color-contrast", "impact": "serious", "help": "Contrast", "detail": "2:1",
                    "targets": [".a"], "count": 1},
                   {"lesson": "U1-S1", "id": "region", "impact": "moderate", "help": "Regions", "targets": ["p"], "count": 1}]
    seen["tests"][0]["score"] = "80"
    seen["paths"][0]["run"] = {**seen["paths"][0]["run"], "a": "safe"}
    seen["paths"][1]["adaptive"][0]["shown"] = not seen["paths"][1]["adaptive"][0]["shown"]
    seen["paths"].append({"sim": "call", "n": 2, "missing": "decision 1", "step": 0})
    seen["lms"] = [{"code": 405, "name": "cmi.interactions.0.result", "value": "incorrect", "message": "Incorrect data type"}] * 2
    seen["maxSuspend"] = 5000
    seen["resume"]["entry"] = "ab-initio"
    result = playcheck.CheckResult(1)
    playcheck.compare(scenario_of(sim), seen, "1.2", result)
    text = "\n".join(result.errors)
    assert text.count("boom") == 1 and "media/a.png (404)" in text
    assert "color-contrast (serious): Contrast (2:1)" in text and result.warnings == [result.warnings[0]] and "region" in result.warnings[0]
    assert "should give 100 and the SCORM gets 80" in text
    assert "path 1: should end at" in text and "ends at safe" in text
    assert "block ':::if call.risk >= 3' after path 2" in text
    assert "path 3: at step 1 there is no decision 1" in text
    assert text.count("cmi.interactions.0.result = incorrect (error 405") == 1
    assert "reaches 5000 characters and the standard admits 4096" in text
    assert "does not resume" in text


def test_a_saved_state_near_its_limit_is_a_warning():
    sim = call_sim()
    seen = good_observation(sim)
    seen["maxSuspend"] = 3500
    result = playcheck.CheckResult(1)
    playcheck.compare(scenario_of(sim), seen, "1.2", result)
    assert result.errors == [] and "3500 of the 4096" in result.warnings[0]
    result = playcheck.CheckResult(1)
    playcheck.compare(scenario_of(sim), seen, "2004", result)
    assert result.warnings == []


def test_the_expected_score_weighs_questions_and_simulations():
    sim = call_sim()
    plan = playcheck.Scenario({}, {"call": sim}, [{"lesson": "U1-E1.1", "sims": [("call", 2.0, 50)]}], [], [])
    seen = good_observation(sim)
    seen["tests"][0].update(questions=3, score="80")  # (3 + 2·0.5) / (3 + 2) = 80
    result = playcheck.CheckResult(1)
    playcheck.compare(plan, seen, "1.2", result)
    assert result.errors == []
    plan = playcheck.Scenario({}, {"call": sim}, [], [("call", 1.0, 50), ("call", 3.0, 100)], [])
    seen = {**good_observation(sim), "tests": [], "formative": {"score": "88"}}  # (50 + 300) / 4 = 87.5 → 88
    result = playcheck.CheckResult(1)
    playcheck.compare(plan, seen, "1.2", result)
    assert result.errors == []


# ── the command ──────────────────────────────────────────────────────────────────────────────


def test_without_a_browser_only_the_files_are_checked(html_course, monkeypatch, capsys):  # noqa: F811
    def unavailable(data, say):
        assert data["url"].startswith("http://127.0.0.1:") and data["url"].endswith("/?unit=1")
        assert data["keys"]["score"] == "cmi.core.score.raw" and data["tests"][0]["lesson"] == "U1-E1.1"
        raise playcheck.CheckUnavailable("the unit was not played: no browser")

    monkeypatch.setattr(playcheck, "run_browser", unavailable)
    assert main(["assemble", "check", "PWD", "--unit", "1"]) == 0
    out = capsys.readouterr().out
    assert "building unit 1" in out and "WARNING" in out and "no browser" in out
    assert "unit 1: only the files checked — 0 error(s), 1 warning(s)" in out


def test_build_with_a_version_does_not_write_a_package_that_fails_the_check(html_course, monkeypatch, capsys):  # noqa: F811
    calls = []

    def failing(course, unit, browser=None, say=print):
        calls.append(browser)
        return playcheck.CheckResult(unit["n"], errors=["U1-S1: accessibility, broken"], played=True)

    monkeypatch.setattr(playcheck, "check", failing)
    zip_path = html_course / "delivery" / "PWD-U01-v1.0-scorm12.zip"
    assert main(["assemble", "build", "PWD", "--unit", "1", "--version", "1.0", "--browser", "/opt/chrome"]) == 1
    captured = capsys.readouterr()
    assert "ERROR" in captured.out and "broken" in captured.out and "the package is not written" in captured.err
    assert calls == ["/opt/chrome"] and not zip_path.exists()
    assert main(["assemble", "build", "PWD", "--unit", "1", "--version", "1.0", "--no-check"]) == 0
    assert zip_path.exists() and len(calls) == 1


# ── the JavaScript, with node ────────────────────────────────────────────────────────────────


def run_node(tmp_path, files: dict[str, str], script: str):
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    base = Path(str(resources.files("coursekit.templates.html")))
    for target, source in files.items():
        shutil.copy(base / source, tmp_path / target)
    (tmp_path / "run.mjs").write_text(script, encoding="utf-8")
    out = subprocess.run([node, "run.mjs"], cwd=tmp_path, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def test_interactions_are_written_as_each_standard_admits(tmp_path):
    out = run_node(tmp_path, {"interactions.mjs": "player/interactions.js"}, """
import { conform } from './interactions.mjs';
const q = { id: 'U1-E1.1-b1', type: 'choice', choices: [0, 2], result: 'incorrect', weighting: 1 };
const sim = { id: 'call-1', type: 'choice', choice: 27, description: 'Le llamo yo', result: 'incorrect', weighting: 2 };
console.log(JSON.stringify([conform(q, '1.2'), conform(q, '2004'), conform(sim, '1.2'), conform({ ...sim, result: 'wrong' }, '2004')]));
""")
    assert out[0] == {"id": "U1-E1.1-b1", "type": "choice", "learnerResponse": "a,c", "result": "wrong", "weighting": 1}
    assert out[1]["learnerResponse"] == "a[,]c" and out[1]["result"] == "incorrect"
    assert out[2]["learnerResponse"] == "1" and out[2]["description"] == "Le llamo yo" and "choice" not in out[2]
    assert out[3]["result"] == "incorrect"


def test_the_simulated_lms_is_as_strict_as_a_platform(tmp_path):
    out = run_node(tmp_path, {"lms.mjs": "lms.js"}, """
import { check, choiceProblem, createLms } from './lms.mjs';
const cases = [
  ['1.2', 'cmi.interactions.0.result', 'incorrect'], ['1.2', 'cmi.interactions.0.result', 'wrong'],
  ['2004', 'cmi.interactions.0.result', 'incorrect'], ['1.2', 'cmi.core.lesson_status', 'done'],
  ['1.2', 'cmi.core.score.raw', '101'], ['2004', 'cmi.score.raw', '101'], ['1.2', 'cmi.suspend_data', 'x'.repeat(4097)],
  ['1.2', 'cmi.core.session_time', '00:00:08.27'], ['2004', 'cmi.session_time', 'PT8.27S'], ['2004', 'cmi.session_time', '8s'],
  ['1.2', 'cmi.interactions.0.id', 'has space'], ['1.2', 'cmi.core.student_id', 'x'], ['1.2', 'cmi.interactions.0.description', 'd'],
];
const memory = { data: null, load() { return this.data && JSON.parse(this.data); }, save(d) { this.data = JSON.stringify(d); } };
let lms = createLms('1.2', memory);
const api = lms.api12;
const flow = [api.LMSSetValue('cmi.core.lesson_location', 'x'), api.LMSGetLastError(), api.LMSInitialize(''),
  api.LMSGetValue('cmi.core.entry'), api.LMSSetValue('cmi.interactions.0.type', 'choice'),
  api.LMSSetValue('cmi.interactions.0.student_response', 'Le llamo yo'), api.LMSGetLastError(),
  api.LMSSetValue('cmi.interactions.0.student_response', 'a,c'), api.LMSGetValue('cmi.interactions._count'),
  api.LMSSetValue('cmi.core.lesson_location', 'U1-S2'), api.LMSSetValue('cmi.core.exit', 'suspend'), api.LMSFinish(''),
  api.LMSFinish(''), lms.errors.length];
lms = createLms('1.2', memory);
const again = [lms.api12.LMSInitialize(''), lms.api12.LMSGetValue('cmi.core.entry'), lms.api12.LMSGetValue('cmi.core.lesson_location'),
  lms.api12.LMSSetValue('cmi.core.exit', ''), lms.api12.LMSFinish('')];
lms = createLms('1.2', memory);
const fresh = [lms.api12.LMSInitialize(''), lms.api12.LMSGetValue('cmi.core.entry'), lms.api12.LMSGetValue('cmi.core.lesson_location')];
console.log(JSON.stringify({ codes: cases.map(([s, n, v]) => check(s, n, v)),
  choice: [choiceProblem('1.2', 'a,c'), choiceProblem('1.2', 'ac'), choiceProblem('2004', 'a[,]c'), choiceProblem('2004', 'Le llamo')],
  flow, again, fresh }));
""")
    assert out["codes"] == [405, 0, 0, 405, 405, 0, 405, 0, 0, 406, 405, 403, 401]
    assert out["choice"] == [False, True, False, True]
    assert out["flow"] == ["false", "301", "true", "ab-initio", "true", "false", "405", "true", "1", "true", "true", "true", "false", 3]
    assert out["again"] == ["true", "resume", "U1-S2", "true", "true"]
    assert out["fresh"] == ["true", "ab-initio", ""]  # after a normal exit, a new attempt from scratch
