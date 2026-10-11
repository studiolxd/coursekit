"""`coursekit paths CODE [--unit N]`: every path of the simulations of a unit, for its review.

For each unit with simulations it writes `courses/<CODE>/reviews/unit-NN-paths.md`: per simulation, a summary (scenes,
endings reached, points, time of the longest path), a flowchart (Mermaid) and the list of complete paths with their
decisions, ending, points, grade and final state. The reviewer agent reads it and the people see the branches without
playing them one by one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from coursekit import course as coursemod
from coursekit import simulation as simmod
from coursekit.i18n import t
from coursekit.verify import Report, parse_directives


@dataclass
class UnitPaths:
    n: int
    simulations: list[simmod.Simulation] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    report: Path | None = None


def unit_simulations(course: dict, unit: dict) -> UnitPaths:
    rules = coursemod.rules(course)["content"]
    result = UnitPaths(unit["n"])
    folder = coursemod.unit_dir(course["_dir"], unit["n"])
    for name in ("content.md", "assessment.md"):
        path = folder / name
        if not path.exists():
            continue
        for line, directive, body in parse_directives(path, path.read_text(encoding="utf-8").splitlines(), rules, Report()):
            if directive in (rules.get("simulation_directives") or ()):
                sim = simmod.parse(directive, body, f"{name}:{line} {directive}", line)
                sim.data.setdefault("_file", name)
                result.simulations.append(sim)
                result.errors += sim.errors
    return result


def _label(text: object, limit: int = 60) -> str:
    """A text for a Mermaid label: one line, no double quotes."""
    value = " ".join(str(text or "").split()).replace('"', "'")
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _changes(decision: dict) -> str:
    parts = [f"{var} {value:+g}" for var, value in (decision.get("effects") or {}).items()]
    parts += [f"{var} = {str(value).lower() if isinstance(value, bool) else value}" for var, value in (decision.get("set") or {}).items()]
    if decision.get("score"):
        parts.append(f"score {float(decision['score']):+g}")
    return ", ".join(parts)


def flowchart(sim: simmod.Simulation) -> str:
    """The scenes and decisions as a Mermaid flowchart."""
    scenes = sim.data.get("scenes") or {}
    ids = {sid: f"s{i}" for i, sid in enumerate(scenes)}
    lines = ["```mermaid", "flowchart TD"]
    for sid, scene in scenes.items():
        ending = scene.get("ending")
        text = f"{sid}: {_label(scene.get('text'), 40)}"
        lines.append(f'  {ids[sid]}(["{text} · {ending}"])' if ending else f'  {ids[sid]}["{text}"]')
    for sid, scene in scenes.items():
        for decision in simmod._decisions(scene):
            target = ids.get(decision.get("goto"))
            if target is None:
                continue
            label = _label(decision.get("text") or decision.get("label"), 40)
            extra = "; ".join(x for x in (f"if {decision['if']}" if decision.get("if") else "", _changes(decision)) if x)
            lines.append(f'  {ids[sid]} -->|"{label}{" · " + _label(extra, 40) if extra else ""}"| {target}')
        for step in scene.get("next") or []:
            target = ids.get(step.get("goto"))
            if target is not None:
                condition = _label(f"if {step['if']}", 40) if step.get("if") else t("paths", "otherwise")
                lines.append(f'  {ids[sid]} -.->|"{condition}"| {target}')
    lines += [f"  class {ids[sid]} {scene['ending']}" for sid, scene in scenes.items() if scene.get("ending") in simmod.ENDINGS]
    lines += ["  classDef good stroke-width:3px", "  classDef mixed stroke-dasharray:4",
              "  classDef bad stroke-width:3px,stroke-dasharray:2", "```"]
    return "\n".join(lines)


def _state(env: dict) -> str:
    return ", ".join(f"{k} = {str(v).lower() if isinstance(v, bool) else v}" for k, v in env.items())


def section(sim: simmod.Simulation, words_per_hour: float, think: float) -> str:
    scenes = sim.data.get("scenes") or {}
    out = [f"## {sim.kind} `{sim.id}` — {sim.data.get('title', '')}", ""]
    out.append(t("paths", "summary", file=sim.data.get("_file", ""), line=sim.line, scenes=len(scenes),
                 endings=", ".join(sim.reached_endings) or "-", paths=len(sim.paths),
                 more=t("paths", "truncated") if sim.truncated else "",
                 low=f"{sim.min_score:g}", high=f"{sim.max_score:g}", minutes=f"{sim.minutes(words_per_hour, think):g}",
                 scored=t("paths", "scored_yes") if sim.scored else t("paths", "scored_no"),
                 objectives=", ".join(sim.objectives) or "-"))
    out += ["", flowchart(sim), "", f"| # | {t('paths', 'col_decisions')} | {t('paths', 'col_ending')} | "
            f"{t('paths', 'col_points')} | {t('paths', 'col_grade')} | {t('paths', 'col_state')} |", "|---|---|---|---|---|---|"]
    for i, path in enumerate(sorted(sim.paths, key=lambda p: -p["score"]), 1):
        decisions = " → ".join(_label(label, 50) for _, label in path["steps"] if label is not None) or "-"
        grade = f"{simmod.grade(sim, path['score']):.0f} %" if sim.scored else "-"
        out.append(f"| {i} | {decisions} | {path['ending']} ({path['kind']}) | {path['score']:g} | {grade} | {_state(path['state'])} |")
    return "\n".join(out)


def write(course: dict, unit: dict) -> UnitPaths:
    """Write the paths report of a unit (only when it has simulations without errors)."""
    result = unit_simulations(course, unit)
    if not result.simulations or result.errors:
        return result
    rules = coursemod.rules(course)
    words_per_hour = rules["pages_per_hour"] * rules["words_per_page"]
    think = float((rules.get("decision_based") or {}).get("decision_seconds", 0))
    body = [f"# {t('paths', 'title', code=course['code'], n=unit['n'])}", "", t("paths", "intro"), ""]
    body += [section(sim, words_per_hour, think) + "\n" for sim in result.simulations]
    target = course["_dir"] / "reviews" / f"unit-{unit['n']:02d}-paths.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(body), encoding="utf-8", newline="\n")
    result.report = target
    return result
