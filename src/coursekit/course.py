"""A course: its course.yaml, folders, effective rules and design approval."""

from __future__ import annotations

import math
from pathlib import Path

from coursekit import config, lang
from coursekit.i18n import t
from coursekit.project import Project
from coursekit.util import load_yaml, sha256_file

# Course statuses, in order. Labels for people come from the messages catalog (phase 3).
STATUSES = (
    "design",
    "design_approved",
    "writing",
    "ai_review",
    "editorial_review",
    "media",
    "assembly",
    "client_review",
    "delivered",
    "on_hold",
)
SECTION_KINDS = ("intro", "content", "activities", "summary")


class CourseNotFound(Exception):
    pass


UPDATE_MODES = ("off", "propose", "apply")


def update_mode(rules: dict) -> str:
    """`rules › update › mode`, as one of `off`, `propose`, `apply`. An unquoted `off` or `no` in a YAML file is the boolean false:
    it means off, as a missing value does."""
    value = (rules.get("update") or {}).get("mode")
    if value is None or value is False:
        return "off"
    mode = str(value).strip().lower()
    if mode in ("no", "false"):
        return "off"
    if mode not in UPDATE_MODES:
        raise RuleError(t("course", "bad_update_mode", value=value, valid=", ".join(UPDATE_MODES)))
    return mode


class RuleError(Exception):
    pass


INCLUSIVE_MODES = ("none", "neutral", "split", "slash")


def inclusive_language(rules: dict) -> str:
    """`rules › inclusive_language`: how the texts name people (`none`, `neutral`, `split` or `slash`)."""
    mode = str(rules.get("inclusive_language") or "neutral").strip().lower()
    if mode not in INCLUSIVE_MODES:
        raise RuleError(t("course", "bad_inclusive", value=mode, valid=", ".join(INCLUSIVE_MODES)))
    return mode


def load(project: Project, code_or_path: str) -> dict:
    folder = project.course_dir(code_or_path)
    if not (folder / "course.yaml").exists():
        raise CourseNotFound(t("course", "not_found", code=code_or_path, folder=folder))
    course = load_yaml(folder / "course.yaml")
    course["_dir"] = folder
    course["_project"] = project
    from coursekit import simulation as simmod  # the skins of the project join the built-in ones

    simmod.use_project_skins(project.root)
    return course


def backend(course: dict) -> str:
    """Where the course is assembled: `creator` or `html` (course.yaml › assembly › backend, else the project's)."""
    own = (course.get("assembly") or {}).get("backend")
    project = course.get("_project")
    return str(own or ((config.project_data(project).get("assembly") or {}).get("backend") if project else None) or "creator")


def language(course: dict) -> str:
    project = course.get("_project")
    fallback = config.project_data(project).get("content_language", "es") if project else "es"
    return str(course.get("language") or fallback).split("-")[0]


AUDIENCE_KEYS = ("who", "context", "knowledge", "level", "learning")


def audience(course: dict) -> dict[str, str]:
    """Who the course is for: `project.yaml › audience`, changed by the course (`course.yaml › design`: `audience` as text, the
    `who`, or as a mapping of the same keys; `level`; `prerequisites`, the `knowledge`)."""
    project = course.get("_project")
    own = config.project_data(project).get("audience") if project else None
    found = {k: str((own or {}).get(k) or "").strip() for k in AUDIENCE_KEYS} if isinstance(own, dict) else dict.fromkeys(AUDIENCE_KEYS, "")
    design = course.get("design") or {}
    given = design.get("audience")
    if isinstance(given, dict):
        found.update({k: str(v).strip() for k, v in given.items() if k in AUDIENCE_KEYS and str(v or "").strip()})
    elif str(given or "").strip():
        found["who"] = str(given).strip()
    for key, name in (("level", "level"), ("prerequisites", "knowledge")):
        if str(design.get(key) or "").strip():
            found[name] = str(design[key]).strip()
    return found


def ai_review_required(course: dict) -> bool:
    """rules › review › ai: `required` (default) or `skip`; any other value is a mistake worth reporting."""
    value = str(((config.effective("rules", course.get("_project"), course).value.get("review") or {}).get("ai")) or "required")
    if value not in ("required", "skip"):
        raise RuleError(t("course", "bad_review_ai", value=value))
    return value == "required"


def tokens(course: dict) -> dict:
    return lang.tokens(language(course))


def rules(course: dict | None = None, project: Project | None = None) -> dict:
    """Effective production rules, with the directive lists derived from the directives registry."""
    project = project or (course or {}).get("_project")
    cfg = config.effective("rules", project, course).value
    registry = config.effective("directives", project, course).value
    directives = registry.get("directives") or {}

    def by_role(role: str) -> list[str]:
        return [name for name, d in directives.items() if d.get("role") == role]

    content = cfg.setdefault("content", {})
    content["interactive_directives"] = by_role("interactive")
    content["question_directives"] = by_role("question")
    content["non_interactive_directives"] = by_role("static")
    content["simulation_directives"] = by_role("simulation")
    content["component_equivalents"] = registry.get("component_equivalents") or {}
    return cfg


ASSESSMENT_PLACEMENTS = ("unit", "separate")
BANK_QUESTIONS = {  # the question directives each question-bank format can take
    "aiken": ("single-choice",),
    "gift": ("single-choice", "multi-select", "true-false", "match", "sorting-groups", "short-answer", "fill-in-the-blank"),
    "moodle-xml": ("single-choice", "multi-select", "true-false", "match", "sorting-groups", "short-answer", "fill-in-the-blank",
                   "sorting"),  # sorting as the core «ordering» type of Moodle 4.4 or later
    "qti": ("single-choice", "multi-select", "true-false", "match", "sorting-groups", "short-answer", "fill-in-the-blank",
            "sorting"),  # exported by creator only (create_export question_bank)
}
CREATOR_BANK = {"gift": "gift", "moodle-xml": "moodle_xml", "qti": "qti"}  # format → questionBankFormat of create_export


def bank_questions(fmt: str, backend_name: str = "") -> tuple[str, ...]:
    """The question directives a question-bank format takes (the same whether coursekit writes the bank or creator exports it)."""
    return BANK_QUESTIONS[fmt]
ASSESSMENT_FORMATS = ("platform", *BANK_QUESTIONS)


def assessment_delivery(course: dict) -> tuple[str, str]:
    """(placement, format) of the tests: `delivery › assessment`, the course's over the project's."""
    cfg = (config.effective("delivery", course.get("_project"), course).value.get("assessment") or {})
    placement = str(cfg.get("placement") or "unit").strip().lower()
    fmt = str(cfg.get("format") or "platform").strip().lower()
    if placement not in ASSESSMENT_PLACEMENTS:
        raise RuleError(t("course", "bad_assessment", key="placement", value=placement, valid=", ".join(ASSESSMENT_PLACEMENTS)))
    if fmt not in ASSESSMENT_FORMATS:
        raise RuleError(t("course", "bad_assessment", key="format", value=fmt, valid=", ".join(ASSESSMENT_FORMATS)))
    if fmt == "qti" and backend(course) != "creator":
        raise RuleError(t("course", "qti_needs_creator"))
    return placement, fmt


def assessment_unit(course: dict) -> dict | None:
    """The package of the tests when they go apart (`placement: separate`): one more unit to assemble and deliver, after the
    others, with no content of its own. Its lessons are the assessment activities of every unit (built by the plan from their
    assessment.md); what is recorded of it lives in `course.yaml › assessment_unit`. None when the tests stay in their units or no
    unit has one."""
    placement, fmt = assessment_delivery(course)
    if placement != "separate":
        return None
    units = course.get("units") or []
    activities = [dict(a, unit=u["n"]) for u in units for a in (u.get("activities") or {}).get("assessment") or []]
    if not activities or (fmt != "platform" and not tests_with_simulations(course)):
        return None  # with a question-bank format only the scored simulations of the tests stay in a package
    own = course.get("assessment_unit") or {}
    return {"n": max(u["n"] for u in units) + 1, "kind": "assessment", "title": tokens(course)["assessment_unit_title"],
            "hours": 0, "sections": [], "objectives": [o for u in units for o in u.get("objectives") or []],
            "activities": {"learning": [], "assessment": activities}, "sources": [u["n"] for u in units],
            "content_id": own.get("content_id"), "links": own.get("links") or {},
            "status": "approved" if all(u.get("status") == "approved" for u in units) else "pending"}


def bank_unit(course: dict) -> dict | None:
    """With the creator backend and a question-bank format creator exports (gift, moodle-xml, qti; aiken is written by coursekit),
    the questions of the tests go in a creator content of their own,
    which is not delivered as a package: creator exports it as the bank (`create_export` question_bank). One more unit to
    assemble, after the units and the package of the tests; what is recorded of it lives in `course.yaml › bank_unit`."""
    fmt = assessment_delivery(course)[1]
    units = course.get("units") or []
    if fmt not in CREATOR_BANK or backend(course) != "creator" or not any((u.get("activities") or {}).get("assessment") for u in units):
        return None
    tests = assessment_unit(course)
    own = course.get("bank_unit") or {}
    return {"n": (tests or {"n": max(u["n"] for u in units)})["n"] + 1, "kind": "bank", "title": tokens(course)["question_bank_title"],
            "hours": 0, "sections": [], "objectives": [o for u in units for o in u.get("objectives") or []],
            "activities": {"learning": [], "assessment": [dict(a, unit=u["n"]) for u in units
                                                          for a in (u.get("activities") or {}).get("assessment") or []]},
            "sources": [u["n"] for u in units], "content_id": own.get("content_id"), "links": own.get("links") or {},
            "status": "approved" if all(u.get("status") == "approved" for u in units) else "pending"}


def tests_with_simulations(course: dict) -> bool:
    """Some assessment.md of the course has a simulation (what stays in a package with a question-bank format)."""
    names = tuple(rules(course)["content"].get("simulation_directives") or ())
    for u in course.get("units") or []:
        path = unit_dir(course["_dir"], u["n"]) / "assessment.md"
        if path.exists() and any(line.strip() in {f":::{n}" for n in names} for line in path.read_text(encoding="utf-8").splitlines()):
            return True
    return False


def package_units(course: dict) -> list[dict]:
    """The units that become a package (assembly and delivery): the units of the design and, when the tests go apart, theirs."""
    return list(course.get("units") or []) + [u for u in (assessment_unit(course), bank_unit(course)) if u]


def package_unit(course: dict, n: int | None) -> dict | None:
    return next((u for u in package_units(course) if u["n"] == n), None)


def min_words(hours: float, cfg: dict) -> int:
    """Minimum learner-facing words for a number of hours. Pages round up, never down."""
    return math.ceil(float(hours) * cfg["pages_per_hour"]) * cfg["words_per_page"]


def unit_dir(course_dir: Path, n: int) -> Path:
    return course_dir / "content" / f"unit-{n:02d}"


def design_approval(course: dict) -> dict | None:
    approvals = [a for a in course.get("approvals") or [] if a.get("gate") == "design"]
    return approvals[-1] if approvals else None


def approval_problem(course: dict) -> str | None:
    """Why the design is not (or no longer) approved; None when it is."""
    approval = design_approval(course)
    if approval is None:
        return t("course", "design_not_approved", code=course.get("code"))
    matrix = course["_dir"] / "design" / "matrix.json"
    if not matrix.exists():
        return t("course", "matrix_missing")
    if sha256_file(matrix) != approval.get("snapshot_sha256"):
        return t("course", "matrix_changed")
    from coursekit import localdesign  # imports this module

    problem = localdesign.export_problem(course)
    if problem:
        return problem
    if approval.get("story_sha256"):
        story = course["_dir"] / "design" / "story.md"
        if not story.exists() or sha256_file(story) != approval["story_sha256"]:
            return t("course", "story_changed")
    if approval.get("misconceptions_sha256"):
        errors = course["_dir"] / "design" / "misconceptions.yaml"
        if not errors.exists() or sha256_file(errors) != approval["misconceptions_sha256"]:
            return t("course", "misconceptions_changed")
    return None
