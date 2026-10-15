"""`coursekit verify`: check a course's content against the production rules.

Per unit (content.md + assessment.md):
  - the instructional design is approved and unchanged since the approval;
  - sections present and in design order (course.yaml › units › sections);
  - minimum words per section, from its hours (learner-facing text only);
  - objective tag in every content section; every unit objective covered;
  - distinct interactive directives per content section, by hours;
  - multimedia placeholders per unit hour: count, distinct types, required fields;
  - directives well formed (known name, closed, not nested); questions carry an objective;
  - no emojis or pictographs outside the allowed symbols;
  - simulations (:::scenario, :::conversation): their YAML, every path (no dead ends, every scene reachable, endings with
    debriefing), unique ids in the course; adaptive blocks (:::if / :::else) read variables of earlier simulations;
  - decision-based courses (design.approach): every content section opens with a simulation, has the minimum of them, and every
    objective of the unit is practised in one; the simulation time counts towards the hours of the section;
  - the content converts for the assembly backend (when a backend check is registered).
Also moves the unit status forward when it passes and back when it no longer does.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import yaml

from coursekit import config
from coursekit import course as coursemod
from coursekit import importer as importermod
from coursekit import misconceptions as misconmod
from coursekit import readability as readmod
from coursekit import simulation as simmod
from coursekit import story as storymod
from coursekit import videos as videosmod
from coursekit.fingerprint import changed_since_review
from coursekit.i18n import t
from coursekit.lang import format_number
from coursekit.states import now as timestamp
from coursekit.states import rank, set_unit_status
from coursekit.util import sha256_file

DIRECTIVE_OPEN_RE = re.compile(r"^:::([a-z][a-z-]*)\s*$")
DIRECTIVE_CLOSE_RE = re.compile(r"^:::\s*$")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
PICTOGRAPH_RE = re.compile("[\U0001f000-\U0001faff\U0001f1e6-\U0001f1ff⌀-⏿☀-➿⬀-⯿️‍]")

# Extra checks registered by the assembly backends: (course, unit) -> list of error messages.
BACKEND_CHECKS: list[Callable[[dict, dict], list[str]]] = []


@dataclass
class Syntax:
    """Content-format patterns for one language."""

    section: re.Pattern
    objective_tag: re.Pattern
    placeholder: re.Pattern
    placeholder_fields: tuple[str, ...]
    question_key: str
    media_types: dict[str, str]  # how each resource type is written in the language -> its id
    activity: re.Pattern  # the heading of an assessment activity (a test)

    @classmethod
    def for_tokens(cls, tokens: dict) -> Syntax:
        return cls(
            section=re.compile(rf"^## {re.escape(tokens['section'])} (\d+)\s*[—-]\s*(.+?)\s*(\*\(.*\)\*)?\s*$"),
            objective_tag=re.compile(rf"^\*\[{re.escape(tokens['objective'])}[^\]]*\]\*\s*$"),
            placeholder=re.compile(rf"^>\s*\*\*\[{re.escape(tokens['placeholder'])}\s*[—-]\s*(.+?)\]\*\*"),
            placeholder_fields=tuple(tokens["placeholder_fields"]),
            question_key=tokens["question_objective_key"],
            media_types={written.casefold(): type_id for type_id, written in tokens["media_types"].items()},
            activity=re.compile(rf"^## {re.escape(tokens['assessment_activity'])}\s+[\d.]+\s*[—-]"),
        )

    def media_type(self, written: str) -> str | None:
        return self.media_types.get(written.strip().casefold())


@dataclass
class Placeholder:
    kind: str
    line: int
    fields: set[str] = field(default_factory=set)


@dataclass
class Section:
    n: int
    title: str
    line: int
    lines: list[str] = field(default_factory=list)
    directives: list[str] = field(default_factory=list)
    placeholders: list[Placeholder] = field(default_factory=list)
    simulations: list[simmod.Simulation] = field(default_factory=list)
    words: int = 0


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


URL = re.compile(r"https?://[^\s)>\]\"']+|(?<![\w/.])www\.[^\s)>\]\"']+", re.I)


def check_forbidden(label: str, lines: list[str], forbidden: dict, report: Report, videos: dict | None = None) -> None:
    """`rules › forbidden`: addresses of sites and words or phrases that must not appear in the content. A video on a forbidden
    site is let through when `coursekit videos` registered it as approved (its channel is official) or proposed (the agent
    found it official and a person has yet to check it: a warning)."""
    hosts = [str(h).strip().lower().lstrip(".") for h in forbidden.get("hosts") or [] if str(h).strip()]
    terms = [str(w).strip() for w in forbidden.get("terms") or [] if str(w).strip()]
    for number, line in enumerate(lines, 1):
        for url in URL.findall(line) if hosts else []:
            host = (urlparse(url if "://" in url else f"http://{url}").hostname or "").lower()
            if any(host == h or host.endswith(f".{h}") for h in hosts):
                entry = (videos or {}).get(videosmod.key(url))
                status = entry.get("status") if entry else None
                if status == "approved":
                    continue
                if status == "proposed":
                    report.warn(t("verify", "video_proposed", label=label, line=number, host=host))
                elif status == "rejected":
                    report.error(t("verify", "video_rejected", label=label, line=number, host=host))
                else:
                    report.error(t("verify", "forbidden_host", label=label, line=number, host=host))
        for term in terms:
            if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", line, re.I):
                report.error(t("verify", "forbidden_term", label=label, line=number, term=term))


def check_pictographs(path: Path, text: str, allowed: str, report: Report) -> None:
    for i, line in enumerate(text.splitlines(), 1):
        found = {ch for ch in PICTOGRAPH_RE.findall(line) if ch not in allowed}
        if found:
            chars = " ".join(f"U+{ord(c):04X}" for c in sorted(found))
            report.error(t("verify", "pictograph", file=path.name, line=i, chars=chars))


def parse_directives(path: Path, lines: list[str], rules: dict, report: Report, start: int = 1):
    """Yield (line_no, name, body_lines) for each directive, reporting malformed ones."""
    known = (set(rules["interactive_directives"]) | set(rules["non_interactive_directives"]) | set(rules["question_directives"])
             | set(rules.get("simulation_directives") or ()))
    in_code = False
    current = None
    for i, line in enumerate(lines, start):
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if current is None:
            if simmod.IF_RE.match(line.strip()) or simmod.ELIF_RE.match(line.strip()) or simmod.ELSE_RE.match(line.strip()):
                continue  # the fences of an adaptive block (scan_conditionals checks them)
            m = DIRECTIVE_OPEN_RE.match(line)
            if m:
                name = m.group(1)
                if name not in known:
                    hint = rules.get("component_equivalents", {}).get(name)
                    if hint:
                        report.error(t("verify", "unknown_directive_hint", file=path.name, line=i, name=name, hint=hint))
                    else:
                        report.error(t("verify", "unknown_directive", file=path.name, line=i, name=name))
                current = (i, name, [])
        elif DIRECTIVE_CLOSE_RE.match(line):
            yield current
            current = None
        elif DIRECTIVE_OPEN_RE.match(line):
            report.error(t("verify", "nested_directive", file=path.name, line=i, outer=current[1], opened=current[0]))
        else:
            current[2].append(line)
    if current is not None:
        report.error(t("verify", "directive_not_closed", file=path.name, line=current[0], name=current[1]))


def check_questions(path: Path, directives, rules: dict, syntax: Syntax, report: Report) -> int:
    count = 0
    for line_no, name, body in directives:
        if name in rules["question_directives"]:
            count += 1
            if not any(b.strip().startswith(syntax.question_key) for b in body):
                report.warn(t("verify", "question_without_objective", file=path.name, line=line_no, key=syntax.question_key))
    return count


def learner_words(lines: list[str], syntax: Syntax, skip: tuple[str, ...] = ()) -> int:
    """Learner-facing words: without comments, directive fences, objective tags and placeholders, nor the body of the
    directives in `skip` (simulations: their time is counted apart) nor the `:::if` branch of adaptive blocks (the `:::else`
    branch, which every learner may see, is counted)."""
    text = HTML_COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), "\n".join(lines))
    hidden = simmod.adaptive_lines(text.splitlines())
    kept = []
    in_placeholder = False
    skipping = False
    for n, line in enumerate(text.splitlines(), 1):
        if skipping:
            skipping = not DIRECTIVE_CLOSE_RE.match(line)
            continue
        m = DIRECTIVE_OPEN_RE.match(line)
        if m and m.group(1) in skip:
            skipping = True
            continue
        if n in hidden:
            continue
        if syntax.placeholder.match(line):
            in_placeholder = True
            continue
        if in_placeholder:
            if line.startswith(">"):
                continue
            in_placeholder = False
        if DIRECTIVE_OPEN_RE.match(line) or DIRECTIVE_CLOSE_RE.match(line) or syntax.objective_tag.match(line):
            continue
        kept.append(misconmod.strip_tag(line)[0] if misconmod.OPTION_RE.match(line) else line)
    return len(" ".join(kept).split())


def split_sections(text: str, syntax: Syntax) -> list[Section]:
    sections: list[Section] = []
    for i, line in enumerate(text.splitlines(), 1):
        m = syntax.section.match(line)
        if m:
            sections.append(Section(n=int(m.group(1)), title=m.group(2), line=i))
        elif sections:
            sections[-1].lines.append(line)
    return sections


def parse_simulations(path: Path, directives, rules: dict, report: Report, passing: float = 50) -> list[simmod.Simulation]:
    """Read and check the simulations among some directives; their problems go to the report (`passing`: the pass mark the
    scored ones are checked against)."""
    found = []
    for line_no, name, body in directives:
        if name in (rules.get("simulation_directives") or ()):
            sim = simmod.parse(name, body, f"{path.name}:{line_no} {name}", line_no)
            if sim.id:
                sim_label = f"{path.name}:{line_no} {name} '{sim.id}'"
                sim.errors = [e.replace(f"{path.name}:{line_no} {name}:", f"{sim_label}:", 1) for e in sim.errors]
            for e in sim.errors:
                report.error(e)
            for w in sim.warnings:
                report.warn(w)
            if not sim.errors:
                problems, notes = simmod.grading_problems(sim, passing)
                for e in problems:
                    report.error(f"{path.name}:{line_no}: {e}")
                for w in notes:
                    report.warn(f"{path.name}:{line_no}: {w}")
            found.append(sim)
    return found


def analyse_section(path: Path, sec: Section, rules: dict, syntax: Syntax, report: Report) -> None:
    simulations = tuple(rules.get("simulation_directives") or ())
    sec.words = learner_words(sec.lines, syntax, simulations)
    directives = list(parse_directives(path, sec.lines, rules, report, sec.line + 1))
    sec.directives = [name for _, name, _ in directives]
    sec.simulations = parse_simulations(path, directives, rules, report)
    current = None
    for i, line in enumerate(sec.lines, sec.line + 1):
        m = syntax.placeholder.match(line)
        if m:
            current = Placeholder(kind=m.group(1).strip(), line=i)
            sec.placeholders.append(current)
            continue
        if current is not None:
            if not line.startswith(">"):
                current = None
                continue
            for f in syntax.placeholder_fields:
                if re.match(rf"^>\s*\*\*{re.escape(f)}:\*\*", line):
                    current.fields.add(f)


def course_simulations(course: dict, rules: dict) -> list[tuple[int, str, int, str, set[str], bool]]:
    """Every simulation of the course, read without checking it: (unit, file, line, id, what an adaptive block can read of
    it: its variables and the fields of its result, scored)."""
    found = []
    for other in course.get("units") or []:
        folder = coursemod.unit_dir(course["_dir"], other["n"])
        for name in ("content.md", "assessment.md"):
            path = folder / name
            if not path.exists():
                continue
            for line_no, directive, body in parse_directives(path, path.read_text(encoding="utf-8").splitlines(), rules, Report()):
                if directive not in (rules.get("simulation_directives") or ()):
                    continue
                try:
                    data = yaml.safe_load("\n".join(body))
                except yaml.YAMLError:
                    continue
                if isinstance(data, dict) and data.get("id"):
                    state = data.get("state") if isinstance(data.get("state"), dict) else {}
                    found.append((other["n"], name, line_no, str(data["id"]), simmod.variable_types(state),
                                  data.get("scored") is True))
    return found


def check_readability(course: dict, label: str, lines: list[str], report: Report) -> None:
    """Warnings when the prose of a section is harder than its audience can take (rules › readability)."""
    cfg = coursemod.rules(course).get("readability") or {}
    audience = str(cfg.get("audience") or "general")
    long_words = int((cfg.get("long_sentence_words") or {}).get(audience) or 0)
    if not long_words:
        return
    # the three audiences of the defaults have a name in each language; a project's own one is shown as it is written
    name = t("verify", f"audience_{audience}") if audience in ("basic", "general", "specialist") else audience
    language = coursemod.language(course)
    m = readmod.measure(lines, language, long_words)
    if m.sentences < int(cfg.get("min_sentences") or 0):
        return
    minimum = (cfg.get("min_index") or {}).get(audience)
    if m.index is not None and minimum is not None and m.index < float(minimum):
        report.warn(t("verify", "hard_to_read", label=label, index=round(m.index), name=m.index_name, minimum=minimum,
                      audience=name, average=round(m.average)))
    share = len(m.long) / m.sentences
    if share > float(cfg.get("long_share_max") or 1):
        report.warn(t("verify", "long_sentences", label=label, count=len(m.long), total=m.sentences, words=long_words,
                      audience=name, example=readmod.start(m.long[0])))


CHOICE_BRICKS = ("SINGLE_CHOICE", "MULTI_SELECT", "TRIVIAL")


def check_misconceptions(course: dict, unit: dict, files: list[tuple[str, list]], sims: list, report: Report) -> None:
    """The common errors of the unit's objectives (design/misconceptions.yaml) are in front of the learner: in a distractor
    of a choice question (`‹id›`) or in a decision of a simulation (`error: id`)."""
    per_objective = int((coursemod.rules(course).get("misconceptions") or {}).get("per_objective") or 0)
    errors, _ = misconmod.load(course)
    if errors is None:
        if per_objective > 0:
            report.warn(t("misconceptions", "no_file"))
        return
    registry = config.effective("directives", course.get("_project"), course).value.get("directives") or {}
    choice = tuple(name for name, d in registry.items() if (d or {}).get("brick") in CHOICE_BRICKS)
    uses = misconmod.Uses()
    for name, directives in files:
        misconmod.question_uses(name, directives, choice, uses)
    for sim in sims:
        misconmod.simulation_uses(sim, uses)
    objectives = {str(o.get("id")) for o in unit.get("objectives") or [] if isinstance(o, dict)}
    problems, notes = misconmod.check_unit(errors, objectives, uses)
    for problem in problems:
        report.error(problem)
    for note in notes:
        report.warn(note)


ADAPTIVE_LIMITS = {"branches": 10, "condition": 500, "simulations": 8}  # creator's limits for one block


def check_adaptive(path: Path, lines: list[str], unit_n: int, sims: list, report: Report) -> int:
    """The `:::if` blocks of a file: well formed, with `:::else`, reading variables (or the result: grade, score, maxScore,
    ending, kind) of simulations that come before in the same unit (each unit is its own package, with its own saved
    state: it cannot read what was decided in another), within creator's limits; never in a test."""
    blocks, problems = simmod.scan_conditionals(lines)
    for line, key in problems:
        report.error(f"{path.name}:{line}: " + t("simulation", key))
    for block in blocks:
        where = f"{path.name}:{block.line}: "
        if path.name == "assessment.md":
            report.error(where + t("simulation", "if_in_test"))
        if len(block.branches) > ADAPTIVE_LIMITS["branches"]:
            report.error(where + t("simulation", "if_too_many_branches", count=len(block.branches), limit=ADAPTIVE_LIMITS["branches"]))
        end = block.end_line or block.line
        inside = [(sid, scored) for n, name, line, sid, _, scored in sims if n == unit_n and name == path.name and block.line < line < end]
        for sid, scored in inside:
            if scored:
                report.error(where + t("simulation", "if_scored_inside", id=sid))
        earlier = {f"{sid}.{var}" for n, name, line, sid, variables, _ in sims for var in variables
                   if (n == unit_n and name == path.name and line < block.line)
                   or (n == unit_n and name == "content.md" and path.name == "assessment.md")}
        elsewhere = {f"{sid}.{var}": n for n, name, line, sid, variables, _ in sims for var in variables if n != unit_n}
        inner = {f"{sid}.{var}" for n, name, line, sid, variables, _ in sims for var in variables
                 if (sid, False) in inside or (sid, True) in inside}
        types = {f"{sid}.{var}": kind for n, name, line, sid, variables, _ in sims for var, kind in variables.items()
                 if f"{sid}.{var}" in earlier}
        read: set[str] = set()
        for line_no, condition in block.branches:
            here = f"{path.name}:{line_no}: "
            if len(condition) > ADAPTIVE_LIMITS["condition"]:
                report.error(here + t("simulation", "if_too_long", count=len(condition), limit=ADAPTIVE_LIMITS["condition"]))
            try:
                node = simmod.parse_expression(condition)
            except simmod.ExpressionError as exc:
                report.error(f"{here}{exc}")
                continue
            for name in sorted(simmod.names(node)):
                read.add(name.split(".", 1)[0])
                if name in earlier:
                    continue
                if name in inner:
                    report.error(here + t("simulation", "if_reads_inside", condition=condition, name=name))
                elif name in elsewhere:
                    report.error(here + t("simulation", "if_other_unit", condition=condition, name=name, n=elsewhere[name]))
                else:
                    report.error(here + t("simulation", "if_unknown_simulation", condition=condition, name=name))
            try:  # creator checks the types before evaluating: a condition that mixes them never holds
                kind = simmod.check_types(node, types)
                if kind not in ("bool", "?"):
                    raise simmod.ExpressionError(t("simulation", "expr_not_boolean", got=kind))
            except simmod.ExpressionError as exc:
                report.error(f"{here}{exc}")
        if len(read) > ADAPTIVE_LIMITS["simulations"]:
            report.error(where + t("simulation", "if_too_many_simulations", count=len(read), limit=ADAPTIVE_LIMITS["simulations"]))
    return len(blocks)


def in_dialog(lines: list[str], line_no: int) -> bool:
    """The line (1-based) is inside a :::dialog directive."""
    inside = False
    for n, line in enumerate(lines, 1):
        stripped = line.strip()
        if n == line_no:
            return inside
        if stripped == ":::dialog":
            inside = True
        elif stripped == ":::":
            inside = False
    return False


def opens_with_simulation(sec: Section, simulations: tuple[str, ...]) -> bool:
    """The first thing of a section, after headings and comments, is a simulation."""
    text = HTML_COMMENT_RE.sub(" ", "\n".join(sec.lines))
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "---":
            continue
        m = DIRECTIVE_OPEN_RE.match(stripped)
        return bool(m and m.group(1) in simulations)
    return False


def verify_unit(course: dict, unit: dict) -> Report:
    report = Report()
    if course.get("_project"):  # the skins of the project, checked (and joined to the built-in ones) before the simulations
        for problem in simmod.use_project_skins(course["_project"].root):
            report.error(problem)
    language = coursemod.language(course)
    tokens = coursemod.tokens(course)
    syntax = Syntax.for_tokens(tokens)
    all_rules = coursemod.rules(course)
    rules = all_rules["content"]
    decision = all_rules.get("decision_based") or {}
    decision_based = (course.get("design") or {}).get("approach") == "decision-based"
    imported = (course.get("design") or {}).get("origin") == "import"
    shortfall = report.warn if imported else report.error  # an imported course keeps its content: it is told, not blocked
    simulations = tuple(rules.get("simulation_directives") or ())
    fmt = lambda n: format_number(n, language)  # noqa: E731
    folder = coursemod.unit_dir(course["_dir"], unit["n"])
    content_path, assessment_path = folder / "content.md", folder / "assessment.md"
    if not content_path.exists():
        report.error(t("verify", "file_missing", path=content_path))
        return report

    text = content_path.read_text(encoding="utf-8")
    check_pictographs(content_path, text, rules["allowed_symbols"], report)
    forbidden = all_rules.get("forbidden") or {}
    registry = videosmod.by_key(course["_dir"])
    check_forbidden(content_path.name, text.splitlines(), forbidden, report, registry)
    sections = split_sections(text, syntax)
    specs = unit.get("sections") or []
    found, expected = [s.n for s in sections], [s["n"] for s in specs]
    if found != expected:
        report.error(t("verify", "sections_mismatch", found=found, expected=expected))

    by_n = {s.n: s for s in sections}
    total_words = 0
    placeholders: list[Placeholder] = []
    covered: set[str] = set()
    margin = rules.get("word_margin", 0)
    words_per_hour = all_rules["pages_per_hour"] * all_rules["words_per_page"]
    think = float(decision.get("decision_seconds", 0))
    sim_words = lambda sims: sum(sim.time_words(words_per_hour, think) for sim in sims)  # noqa: E731
    assessment_sims: list[simmod.Simulation] = []
    if assessment_path.exists():  # their time belongs to the activities section of the unit
        quiet_lines = assessment_path.read_text(encoding="utf-8").splitlines()
        assessment_sims = parse_simulations(assessment_path, parse_directives(assessment_path, quiet_lines, rules, Report()), rules,
                                            Report())
    activities = next((s["n"] for s in specs if s["kind"] == "activities"), None)
    if assessment_sims and activities is None:
        report.error(t("verify", "assessment_simulations_without_section", minutes=fmt(round(
            60 * sim_words(assessment_sims) / words_per_hour, 1))))
    unit_sims: list[simmod.Simulation] = []
    practised: set[str] = set()
    closing = next((s["n"] for s in specs if s["kind"] == "summary"), specs[-1]["n"] if specs else None)
    min_total = 0
    for spec in specs:
        sec = by_n.get(spec["n"])
        if sec is None:
            min_total += spec["min_words"]
            continue
        analyse_section(content_path, sec, rules, syntax, report)
        total_words += sec.words
        placeholders += sec.placeholders
        unit_sims += sec.simulations
        for sim in sec.simulations:
            practised.update(sim.objectives)
        label = f"content.md › {tokens['section']} {spec['n']}"
        minimum = spec["min_words"]
        played = sim_words(sec.simulations)
        if spec["n"] == activities:
            played += sim_words(assessment_sims)
        for sim in sec.simulations + (assessment_sims if spec["n"] == activities else []):
            if sim.time_words(words_per_hour, think) > minimum:
                report.error(t("verify", "simulation_longer_than_section", label=label, id=sim.id,
                               minutes=fmt(sim.minutes(words_per_hour, think)), hours=fmt(spec["hours"])))
        sec.words += played  # a simulation takes the time of what is read in it, like the rest of the section
        total_words += played
        min_total += minimum
        if sec.title.strip() != spec["title"].strip():
            report.warn(t("verify", "title_differs", label=label, title=sec.title, design=spec["title"]))
        check_readability(course, label, sec.lines, report)
        needed_reflections = int(rules.get("reflections_per_unit") or 0)
        if spec["n"] == closing and sec.directives.count("reflection") < needed_reflections:
            report.warn(t("verify", "no_reflection", label=label, n=needed_reflections))
        if decision_based and spec["kind"] == "content":
            if not opens_with_simulation(sec, simulations):
                report.error(t("verify", "section_not_opening_with_simulation", label=label))
            needed_sims = int(decision.get("min_simulations_per_content_section") or 0)
            if len(sec.simulations) < needed_sims:
                report.error(t("verify", "few_simulations", label=label, count=len(sec.simulations), needed=needed_sims))
        if sec.words < minimum:
            shortfall(t("verify", "words_below_minimum", label=label, words=fmt(sec.words), minimum=fmt(minimum)))
        elif sec.words < minimum * (1 + margin):
            report.warn(t("verify", "words_below_margin", label=label, words=fmt(sec.words), margin=int(margin * 100)))
        elif rules.get("word_margin_max") is not None and sec.words > minimum * (1 + float(rules["word_margin_max"])):
            report.warn(t("verify", "words_above_margin", label=label, words=fmt(sec.words), minimum=fmt(minimum),
                          margin=round(float(rules["word_margin_max"]) * 100)))
        if spec["kind"] == "content":
            tags = [line for line in sec.lines if syntax.objective_tag.match(line)]
            if not tags:
                report.error(t("verify", "missing_objective_tag", label=label, objective=tokens["objective"]))
            for tag in tags:
                covered.update(re.findall(r"U\d+\.\d+", tag))
            interactive = {d for d in sec.directives if d in rules["interactive_directives"] or d in simulations}
            needed = max(rules["min_interactive_per_content_section"], math.ceil(spec["hours"] * rules["interactive_per_hour"]))
            if len(interactive) < needed:
                shortfall(t("verify", "few_interactive", label=label, count=len(interactive), needed=needed))

    if any(s["kind"] == "content" for s in specs):
        for obj in unit.get("objectives") or []:
            if obj["id"] not in covered:
                report.error(t("verify", "objective_not_tagged", id=obj["id"]))
            if decision_based and obj["id"] not in practised:
                report.error(t("verify", "objective_not_practised", id=obj["id"]))

    allowed = ", ".join(tokens["media_types"][i] for i in rules["placeholder_types"] if i in tokens["media_types"])
    for ph in placeholders:
        if syntax.media_type(ph.kind) not in rules["placeholder_types"]:
            report.error(t("verify", "unknown_placeholder_type", line=ph.line, kind=ph.kind, allowed=allowed))
        missing = [f for f in syntax.placeholder_fields if f not in ph.fields]
        if missing:
            report.error(t("verify", "placeholder_missing_fields", line=ph.line, fields=", ".join(missing)))
    kinds = {syntax.media_type(ph.kind) or ph.kind for ph in placeholders}
    needed_ph = math.ceil(float(unit["hours"]) * rules["placeholders_per_hour"])
    needed_types = min(rules["min_placeholder_types"], needed_ph)
    if len(placeholders) < needed_ph:
        shortfall(t("verify", "few_placeholders", count=len(placeholders), needed=needed_ph))
    if len(kinds) < needed_types:
        shortfall(t("verify", "few_placeholder_types", count=len(kinds), needed=needed_types))

    quiet = list(parse_directives(Path("content.md"), text.splitlines(), rules, Report()))
    content_questions = check_questions(content_path, quiet, rules, syntax, report)
    sims = course_simulations(course, rules)
    adaptive = check_adaptive(content_path, text.splitlines(), unit["n"], sims, report)

    questions = 0
    assessment_directives: list = []
    if assessment_path.exists():
        a_text = assessment_path.read_text(encoding="utf-8")
        check_pictographs(assessment_path, a_text, rules["allowed_symbols"], report)
        check_forbidden(assessment_path.name, a_text.splitlines(), forbidden, report, registry)
        directives = list(parse_directives(assessment_path, a_text.splitlines(), rules, report))
        assessment_directives = directives
        questions = check_questions(assessment_path, directives, rules, syntax, report)
        passing = float(((course.get("design") or {}).get("grading") or {}).get("passing_score") or 50)
        # with a test, the grade is the test's: a scored simulation of the content does not count (in any backend)
        if any(syntax.activity.match(line) for line in a_text.splitlines()):
            for sim in unit_sims:
                if sim.scored:
                    report.warn(t("verify", "scored_outside_test", id=sim.id))
        unit_sims += parse_simulations(assessment_path, directives, rules, report, passing)
        adaptive += check_adaptive(assessment_path, a_text.splitlines(), unit["n"], sims, report)
        quizzes = [a for a in (unit.get("activities") or {}).get("assessment", []) if a.get("instrument") == "cuestionario"]
        quiz_objectives = {o for a in quizzes for o in a.get("objectives") or []}
        expected_q = rules["questions_per_objective"] * len(quiz_objectives)
        if questions < expected_q:
            report.warn(
                t("verify", "few_questions", questions=questions, expected=expected_q, per_objective=rules["questions_per_objective"])
            )
    else:
        report.error(t("verify", "file_missing", path=assessment_path.name))

    places = {}
    for n, name, line, sid, _, _ in sims:
        places.setdefault(sid, []).append(f"{t('verify', 'unit_word')} {n} {name}:{line}")
    for sid in sorted({sim.id for sim in unit_sims if sim.id}):
        if len(places.get(sid, [])) > 1:
            report.error(t("verify", "duplicate_simulation", id=sid, places=", ".join(places[sid])))
    check_misconceptions(course, unit, [(content_path.name, quiet), (assessment_path.name, assessment_directives)], unit_sims, report)
    if decision_based and unit_sims:
        bible, problems = storymod.load(course)
        for problem in problems:
            report.error(problem)
        if bible is not None:
            cast = storymod.character_names(bible)
            for sim in unit_sims:
                people = [("character", sim.data.get("character"))] if sim.data.get("character") else []
                for sid, scene in (sim.data.get("scenes") or {}).items():
                    people += [(f"scenes.{sid}.characters", p.get("name")) for p in (scene or {}).get("characters") or []
                               if isinstance(p, dict)]
                for place, name in people:
                    if name and str(name).strip().casefold() not in cast:
                        report.error(f"{sim.id}: " + t("story", "unknown_character", place=place, name=name))
            for line_no, line in enumerate(text.splitlines(), 1):
                m = re.match(r"^\*\*(.+?):\*\*", line.strip())
                if m and in_dialog(text.splitlines(), line_no) and not storymod.is_learner(course, m.group(1)) \
                        and storymod.canonical(course, m.group(1)) is None:
                    report.error(f"content.md:{line_no}: " + t("story", "unknown_speaker", name=m.group(1),
                                                                 learner=coursemod.tokens(course).get("learner", "")))
    backend = coursemod.backend(course) if course.get("_project") else None
    checks = list(BACKEND_CHECKS)
    if backend == "creator":
        from coursekit.assemble import check_unit

        checks.append(check_unit)
    elif backend == "html":
        from coursekit.htmlkit.build import check_unit as check_html_unit

        checks.append(check_html_unit)
    for check in checks:
        for err in check(course, unit):
            report.error(t("verify", "assembly_error", error=err))

    if imported:  # the text is the client's: it is reused, not written again
        package = importermod.source_words(course["_dir"], unit["n"])
        growth = float(rules.get("import_max_growth") or 0)
        written = sum(sec.words for sec in sections)
        if package and growth and written > package * growth:
            report.error(t("verify", "unit_inflated", unit=unit["n"], words=fmt(written), package=fmt(package), times=growth))
        elif package and written < package * 0.5:
            report.warn(t("verify", "unit_trimmed", unit=unit["n"], words=fmt(written), package=fmt(package)))
    if imported and min_total:
        if total_words < min_total:
            report.warn(t("verify", "unit_short", unit=unit["n"], words=fmt(total_words), minimum=fmt(min_total), hours=fmt(unit["hours"])))
        elif rules.get("word_margin_max") is not None and total_words > min_total * (1 + float(rules["word_margin_max"])):
            report.warn(t("verify", "unit_long", unit=unit["n"], words=fmt(total_words), minimum=fmt(min_total), hours=fmt(unit["hours"])))
    report.summary = {
        "words": total_words,
        "min_words": min_total,
        "placeholders": len(placeholders),
        "placeholder_types": len(kinds),
        "formative_questions": content_questions,
        "bank_questions": questions,
        "simulations": len(unit_sims),
    }
    return report


def update_status(course: dict, unit: dict, report: Report) -> list[str]:
    """Move the unit forward when it passes, and back when its content changed or broke."""
    notes: list[str] = []
    current = unit.get("status") or "pending"
    target = current
    if not report.errors:
        if rank(current) < rank("verified"):
            target = "verified"
    elif rank(current) >= rank("verified"):
        target = "writing"  # verified content no longer passes
    elif current == "pending" and report.summary.get("words"):
        target = "writing"
    approval = next(
        (a for a in reversed(course.get("approvals") or []) if a.get("gate") == "content" and a.get("unit") == unit["n"]),
        None,
    )
    tokens = coursemod.tokens(course)
    ai_review = coursemod.ai_review_required(course)
    changed = changed_since_review(course["_dir"], unit, tokens) if ai_review and rank(current) >= rank("reviewed") else None
    if current == "approved" and approval:
        folder = coursemod.unit_dir(course["_dir"], unit["n"])
        now = {f.name: sha256_file(f) for f in (folder / "content.md", folder / "assessment.md") if f.exists()}
        if now != approval.get("files_sha256"):
            if changed:
                notes.append(t("verify", "changed_after_approval_parts", parts=", ".join(changed)))
            else:
                notes.append(t("verify", "changed_after_approval"))
            target = "writing" if report.errors else ("verified" if changed else "reviewed")
    if changed and not report.errors and rank(target) >= rank("reviewed"):
        notes.append(t("verify", "changed_after_review", parts=", ".join(changed)))
        target = "verified"
    review = None
    if not ai_review and not report.errors and rank(target) < rank("reviewed"):
        target, review = "reviewed", {"kind": "skipped", "at": timestamp()}  # no AI review in this project: verified is reviewed
        notes.append(t("verify", "review_skipped"))
    if target != current:
        old, new = set_unit_status(course["_dir"], unit["n"], target, review=review)
        if old != new:
            notes.append(t("verify", "status_change_course", current=current, target=target, old=old, new=new))
        else:
            notes.append(t("verify", "status_change", current=current, target=target))
        unit["status"] = target
    return notes
