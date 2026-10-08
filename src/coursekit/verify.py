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
  - the content converts for the assembly backend (when a backend check is registered).
Also moves the unit status forward when it passes and back when it no longer does.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from coursekit import config
from coursekit import course as coursemod
from coursekit.fingerprint import changed_since_review
from coursekit.lang import format_number
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

    @classmethod
    def for_tokens(cls, t: dict) -> Syntax:
        return cls(
            section=re.compile(rf"^## {re.escape(t['section'])} (\d+)\s*[—-]\s*(.+?)\s*(\*\(.*\)\*)?\s*$"),
            objective_tag=re.compile(rf"^\*\[{re.escape(t['objective'])}[^\]]*\]\*\s*$"),
            placeholder=re.compile(rf"^>\s*\*\*\[{re.escape(t['placeholder'])}\s*[—-]\s*(.+?)\]\*\*"),
            placeholder_fields=tuple(t["placeholder_fields"]),
            question_key=t["question_objective_key"],
        )


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


def check_pictographs(path: Path, text: str, allowed: str, report: Report) -> None:
    for i, line in enumerate(text.splitlines(), 1):
        found = {ch for ch in PICTOGRAPH_RE.findall(line) if ch not in allowed}
        if found:
            chars = " ".join(f"U+{ord(c):04X}" for c in sorted(found))
            report.error(f"{path.name}:{i}: emoji/pictograph not allowed ({chars})")


def parse_directives(path: Path, lines: list[str], rules: dict, report: Report, start: int = 1):
    """Yield (line_no, name, body_lines) for each directive, reporting malformed ones."""
    known = set(rules["interactive_directives"]) | set(rules["non_interactive_directives"]) | set(rules["question_directives"])
    in_code = False
    current = None
    for i, line in enumerate(lines, start):
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if current is None:
            m = DIRECTIVE_OPEN_RE.match(line)
            if m:
                name = m.group(1)
                if name not in known:
                    hint = rules.get("component_equivalents", {}).get(name)
                    report.error(f"{path.name}:{i}: unknown directive ':::{name}'" + (f" (use: {hint})" if hint else ""))
                current = (i, name, [])
        elif DIRECTIVE_CLOSE_RE.match(line):
            yield current
            current = None
        elif DIRECTIVE_OPEN_RE.match(line):
            report.error(f"{path.name}:{i}: nested directive inside ':::{current[1]}' (opened at line {current[0]})")
        else:
            current[2].append(line)
    if current is not None:
        report.error(f"{path.name}:{current[0]}: directive ':::{current[1]}' is not closed")


def check_questions(path: Path, directives, rules: dict, syntax: Syntax, report: Report) -> int:
    count = 0
    for line_no, name, body in directives:
        if name in rules["question_directives"]:
            count += 1
            if not any(b.strip().startswith(syntax.question_key) for b in body):
                report.warn(f"{path.name}:{line_no}: question without '{syntax.question_key}'")
    return count


def learner_words(lines: list[str], syntax: Syntax) -> int:
    """Learner-facing words: without comments, directive fences, objective tags and placeholders."""
    text = HTML_COMMENT_RE.sub(" ", "\n".join(lines))
    kept = []
    in_placeholder = False
    for line in text.splitlines():
        if syntax.placeholder.match(line):
            in_placeholder = True
            continue
        if in_placeholder:
            if line.startswith(">"):
                continue
            in_placeholder = False
        if DIRECTIVE_OPEN_RE.match(line) or DIRECTIVE_CLOSE_RE.match(line) or syntax.objective_tag.match(line):
            continue
        kept.append(line)
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


def analyse_section(path: Path, sec: Section, rules: dict, syntax: Syntax, report: Report) -> None:
    sec.words = learner_words(sec.lines, syntax)
    sec.directives = [name for _, name, _ in parse_directives(path, sec.lines, rules, report, sec.line + 1)]
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


def verify_unit(course: dict, unit: dict) -> Report:
    report = Report()
    language = coursemod.language(course)
    tokens = coursemod.tokens(course)
    syntax = Syntax.for_tokens(tokens)
    rules = coursemod.rules(course)["content"]
    fmt = lambda n: format_number(n, language)  # noqa: E731
    folder = coursemod.unit_dir(course["_dir"], unit["n"])
    content_path, assessment_path = folder / "content.md", folder / "assessment.md"
    if not content_path.exists():
        report.error(f"missing {content_path}")
        return report

    text = content_path.read_text(encoding="utf-8")
    check_pictographs(content_path, text, rules["allowed_symbols"], report)
    sections = split_sections(text, syntax)
    specs = unit.get("sections") or []
    found, expected = [s.n for s in sections], [s["n"] for s in specs]
    if found != expected:
        report.error(f"content.md: sections {found} do not match the design {expected}")

    by_n = {s.n: s for s in sections}
    total_words = 0
    placeholders: list[Placeholder] = []
    covered: set[str] = set()
    margin = rules.get("word_margin", 0)
    for spec in specs:
        sec = by_n.get(spec["n"])
        if sec is None:
            continue
        analyse_section(content_path, sec, rules, syntax, report)
        total_words += sec.words
        placeholders += sec.placeholders
        label = f"content.md › {tokens['section']} {spec['n']}"
        if sec.title.strip() != spec["title"].strip():
            report.warn(f"{label}: title '{sec.title}' differs from the design '{spec['title']}'")
        if sec.words < spec["min_words"]:
            report.error(f"{label}: {fmt(sec.words)} words < minimum {fmt(spec['min_words'])}")
        elif sec.words < spec["min_words"] * (1 + margin):
            report.warn(f"{label}: {fmt(sec.words)} words, below the recommended {int(margin * 100)} % margin")
        if spec["kind"] == "content":
            tags = [line for line in sec.lines if syntax.objective_tag.match(line)]
            if not tags:
                report.error(f"{label}: missing objective tag *[{tokens['objective']} UN.M — …]*")
            for tag in tags:
                covered.update(re.findall(r"U\d+\.\d+", tag))
            interactive = {d for d in sec.directives if d in rules["interactive_directives"]}
            needed = max(rules["min_interactive_per_content_section"], math.ceil(spec["hours"] * rules["interactive_per_hour"]))
            if len(interactive) < needed:
                report.error(f"{label}: {len(interactive)} distinct interactive directives < {needed}")

    if any(s["kind"] == "content" for s in specs):
        for obj in unit.get("objectives") or []:
            if obj["id"] not in covered:
                report.error(f"content.md: objective {obj['id']} is not tagged in any content section")

    for ph in placeholders:
        if ph.kind not in rules["placeholder_types"]:
            report.error(f"content.md:{ph.line}: unknown placeholder type '{ph.kind}'")
        missing = [f for f in syntax.placeholder_fields if f not in ph.fields]
        if missing:
            report.error(f"content.md:{ph.line}: placeholder missing fields: {', '.join(missing)}")
    kinds = {ph.kind for ph in placeholders}
    needed_ph = math.ceil(float(unit["hours"]) * rules["placeholders_per_hour"])
    needed_types = min(rules["min_placeholder_types"], needed_ph)
    if len(placeholders) < needed_ph:
        report.error(f"content.md: {len(placeholders)} placeholders < {needed_ph}")
    if len(kinds) < needed_types:
        report.error(f"content.md: {len(kinds)} placeholder types < {needed_types}")

    quiet = list(parse_directives(Path("content.md"), text.splitlines(), rules, Report()))
    content_questions = check_questions(content_path, quiet, rules, syntax, report)

    questions = 0
    if assessment_path.exists():
        a_text = assessment_path.read_text(encoding="utf-8")
        check_pictographs(assessment_path, a_text, rules["allowed_symbols"], report)
        directives = list(parse_directives(assessment_path, a_text.splitlines(), rules, report))
        questions = check_questions(assessment_path, directives, rules, syntax, report)
        quizzes = [a for a in (unit.get("activities") or {}).get("assessment", []) if a.get("instrument") == "cuestionario"]
        quiz_objectives = {o for a in quizzes for o in a.get("objectives") or []}
        expected_q = rules["questions_per_objective"] * len(quiz_objectives)
        if questions < expected_q:
            report.warn(
                f"assessment.md: {questions} questions in the bank, expected {expected_q} "
                f"({rules['questions_per_objective']} per objective assessed by questionnaire)"
            )
    else:
        report.error(f"missing {assessment_path.name}")

    backend = (config.project_data(course["_project"]).get("assembly") or {}).get("backend", "creator") if course.get("_project") else None
    checks = list(BACKEND_CHECKS)
    if backend == "creator":
        from coursekit.assemble import check_unit

        checks.append(check_unit)
    for check in checks:
        for err in check(course, unit):
            report.error(f"assembly: {err}")

    report.summary = {
        "words": total_words,
        "min_words": sum(s["min_words"] for s in specs),
        "placeholders": len(placeholders),
        "placeholder_types": len(kinds),
        "formative_questions": content_questions,
        "bank_questions": questions,
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
    changed = changed_since_review(course["_dir"], unit, tokens) if rank(current) >= rank("reviewed") else None
    if current == "approved" and approval:
        folder = coursemod.unit_dir(course["_dir"], unit["n"])
        now = {f.name: sha256_file(f) for f in (folder / "content.md", folder / "assessment.md") if f.exists()}
        if now != approval.get("files_sha256"):
            parts = f" ({', '.join(changed)} changed after the AI review)" if changed else ""
            notes.append(f"content changed after its approval{parts}: it must be reviewed and approved again")
            target = "writing" if report.errors else ("verified" if changed else "reviewed")
    if changed and not report.errors and rank(target) >= rank("reviewed"):
        notes.append(f"changed after the AI review: {', '.join(changed)} (coursekit review: partial review)")
        target = "verified"
    if target != current:
        old, new = set_unit_status(course["_dir"], unit["n"], target)
        notes.append(f"status: unit {current} -> {target}" + (f" · course {old} -> {new}" if old != new else ""))
        unit["status"] = target
    return notes
