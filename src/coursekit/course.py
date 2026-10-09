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


class RuleError(Exception):
    pass


def load(project: Project, code_or_path: str) -> dict:
    folder = project.course_dir(code_or_path)
    if not (folder / "course.yaml").exists():
        raise CourseNotFound(t("course", "not_found", code=code_or_path, folder=folder))
    course = load_yaml(folder / "course.yaml")
    course["_dir"] = folder
    course["_project"] = project
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
    content["component_equivalents"] = registry.get("component_equivalents") or {}
    return cfg


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
    return None
