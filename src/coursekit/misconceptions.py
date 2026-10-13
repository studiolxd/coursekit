"""The common errors of a course: `courses/<CODE>/design/misconceptions.yaml`.

What the audience gets wrong today, and why, per objective. The design agent writes it with the design and the person signs
it with the design (`coursekit approve design`). The content points at them: each distractor of a choice question ends
with the id of the error it represents (`- [ ] Reuse the strong one ‹reuse›`) and each wrong decision of a simulation
says it (`error: reuse`). `coursekit verify` checks that every error of a unit's objectives is put in front of the learner
somewhere in the unit, and that nothing points at an error the design does not list.

    U1.1:
      reuse: Reusing a strong password in several accounts, because it is strong
      year: Adding the year to the usual password to "change" it
    U1.2:
      sms: Thinking a code by SMS is as safe as an authenticator app
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from coursekit.i18n import t

FILE = Path("design") / "misconceptions.yaml"
ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
TAG_RE = re.compile(r"\s*‹([a-z][a-z0-9_]*)›\s*$")  # at the end of an option: the error it represents
OPTION_RE = re.compile(r"^\s*[-*]\s+\[( |x|X)\]\s+(.*)$")


def path(course: dict) -> Path:
    return course["_dir"] / FILE


def strip_tag(text: str) -> tuple[str, str | None]:
    """(the text without its tag, the id of the error it points at or None)."""
    m = TAG_RE.search(text)
    return (text[: m.start()], m.group(1)) if m else (text, None)


@dataclass
class Errors:
    by_id: dict[str, tuple[str, str]] = field(default_factory=dict)  # id -> (objective, text)

    def of(self, objectives: set[str]) -> list[str]:
        return [eid for eid, (objective, _) in self.by_id.items() if objective in objectives]


def load(course: dict, objectives: dict[str, int] | None = None, per_objective: int = 0) -> tuple[Errors | None, list[str]]:
    """The errors of the design and their problems. `objectives` (id -> unit) are the course's, to check each one has
    at least `per_objective` errors and that no error belongs to an objective that does not exist."""
    file = path(course)
    where = FILE.as_posix()
    if not file.exists():
        return None, [t("misconceptions", "missing", path=where, n=per_objective)] if per_objective > 0 else []
    try:
        data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return None, [f"{where}: " + t("misconceptions", "not_yaml", problem=getattr(exc, "problem", None) or exc)]
    if not isinstance(data, dict):
        return None, [f"{where}: " + t("misconceptions", "not_mapping")]
    errors, problems = Errors(), []
    for objective, entries in data.items():
        objective = str(objective)
        if objectives is not None and objective not in objectives:
            problems.append(f"{where}: " + t("misconceptions", "unknown_objective", objective=objective))
        if not isinstance(entries, dict):
            problems.append(f"{where}: " + t("misconceptions", "objective_not_mapping", objective=objective))
            continue
        for eid, text in entries.items():
            eid = str(eid)
            if not ID_RE.match(eid):
                problems.append(f"{where}: " + t("misconceptions", "bad_id", id=eid))
            elif eid in errors.by_id:
                problems.append(f"{where}: " + t("misconceptions", "duplicate", id=eid, first=errors.by_id[eid][0], second=objective))
            elif not isinstance(text, str) or not text.strip():
                problems.append(f"{where}: " + t("misconceptions", "no_text", id=eid))
            else:
                errors.by_id[eid] = (objective, text.strip())
    if objectives is not None and per_objective > 0:
        for objective in objectives:
            count = len(errors.of({objective}))
            if count < per_objective:
                problems.append(f"{where}: " + t("misconceptions", "too_few", objective=objective, count=count, n=per_objective))
    return errors, problems


@dataclass
class Uses:
    """Where a unit puts its errors in front of the learner."""
    used: dict[str, list[str]] = field(default_factory=dict)  # id -> places
    problems: list[str] = field(default_factory=list)
    untagged: list[str] = field(default_factory=list)  # places with wrong options that represent no error

    def add(self, eid: str, place: str) -> None:
        self.used.setdefault(eid, []).append(place)


def question_uses(file: str, directives, choice_directives: tuple[str, ...], uses: Uses) -> None:
    """The tags of the options of the choice questions among some directives (line, name, body)."""
    for line_no, name, body in directives:
        if name not in choice_directives:
            continue
        untagged = 0
        for line in body:
            m = OPTION_RE.match(line)
            if not m:
                continue
            _, eid = strip_tag(m.group(2))
            right = m.group(1).lower() == "x"
            if eid and right:
                uses.problems.append(t("misconceptions", "right_option_tagged", place=f"{file}:{line_no}", id=eid))
            elif eid:
                uses.add(eid, f"{file}:{line_no}")
            elif not right:
                untagged += 1
        if untagged:
            uses.untagged.append(t("misconceptions", "untagged_distractors", place=f"{file}:{line_no}", count=untagged))


def simulation_uses(sim, uses: Uses) -> None:
    """The `error` of the decisions of a simulation; a decision that loses points without one is noted."""
    untagged = 0
    for sid, scene in (sim.data.get("scenes") or {}).items():
        if not isinstance(scene, dict):
            continue
        for decision in list(scene.get("choices") or []) + list(scene.get("hotspots") or []):
            if not isinstance(decision, dict):
                continue
            eid = decision.get("error")
            if eid:
                uses.add(str(eid), f"{sim.id}.{sid}")
            elif float(decision.get("score") or 0) < 0:
                untagged += 1
    if untagged:
        uses.untagged.append(t("misconceptions", "untagged_decisions", id=sim.id, count=untagged))


def check_unit(errors: Errors, objectives: set[str], uses: Uses) -> tuple[list[str], list[str]]:
    """(errors, warnings) of a unit: unknown ids, errors of its objectives that the unit never shows, wrong options that
    represent no error."""
    problems = list(uses.problems)
    for eid, places in sorted(uses.used.items()):
        if eid not in errors.by_id:
            problems.append(t("misconceptions", "unknown_id", id=eid, places=", ".join(places)))
    for eid in errors.of(objectives):
        if eid not in uses.used:
            objective, text = errors.by_id[eid]
            problems.append(t("misconceptions", "not_shown", id=eid, objective=objective, text=text))
    return problems, list(uses.untagged)
