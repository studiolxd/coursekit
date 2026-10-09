"""`coursekit new`: create a course from its title and duration.

Units, sections, objectives and hours are NOT created here: the design agent proposes them in
the instructional design and `coursekit sync` writes them after approval.
"""

from __future__ import annotations

import datetime as dt
import json
from importlib import resources
from pathlib import Path

from coursekit import config, course, identity
from coursekit.i18n import t
from coursekit.project import Project
from coursekit.util import render, slugify

COURSE_FOLDERS = ("brief/sources", "design", "content", "media", "reviews")


def _template(*parts: str) -> str:
    package = "coursekit.templates." + ".".join(parts[:-1])
    return resources.files(package).joinpath(parts[-1]).read_text(encoding="utf-8")


def ensure_brief(course_dir: Path) -> list[str]:
    """Create brief/sources, links.md and notes.md of a course if missing."""
    brief = course_dir / "brief"
    (brief / "sources").mkdir(parents=True, exist_ok=True)
    (brief / "sources" / ".gitkeep").touch()
    created = []
    for name in ("links.md", "notes.md"):
        if not (brief / name).exists():
            (brief / name).write_text(_template("brief", name), encoding="utf-8", newline="\n")
            created.append(name)
    return created


def create(
    project: Project,
    title: str,
    hours: float,
    code: str | None = None,
    intro: bool = True,
    summary: bool = True,
    notes: str = "",
    language: str | None = None,
) -> Path:
    code = code.upper() if code else slugify(title).upper()
    course_dir = project.courses_dir / code
    if course_dir.exists():
        raise FileExistsError(t("new", "already_exists", path=course_dir))
    data = config.project_data(project)
    cfg = course.rules(project=project)
    defaults = cfg.get("defaults") or {}
    grading = defaults.get("grading") or {}
    q = lambda v: json.dumps(v, ensure_ascii=False)  # noqa: E731 — YAML-safe scalar
    hours_value = int(hours) if float(hours).is_integer() else hours
    who = identity.current() or identity.suggested()
    text = render(
        _template("course", "course.yaml"),
        code=q(code),
        title=q(title),
        client=q(data.get("client") or ""),
        language=language or data.get("content_language") or "es",
        hours=hours_value,
        structure=defaults.get("structure", "sin_modulos"),
        intro=str(bool(defaults.get("intro_section", True)) and intro).lower(),
        summary=str(bool(defaults.get("summary_section", True)) and summary).lower(),
        tone=q(data.get("tone") or ""),
        notes=q(notes),
        unit_tests_weight=grading.get("unit_tests_weight", 60),
        final_test_weight=grading.get("final_test_weight", 40),
        passing_score=grading.get("passing_score", 50),
        attempts=grading.get("attempts", 2),
        today=dt.date.today().isoformat(),
        author=q(who.name if who else "unknown"),
    )
    for sub in COURSE_FOLDERS:
        (course_dir / sub).mkdir(parents=True, exist_ok=True)
    (course_dir / "course.yaml").write_text(text, encoding="utf-8", newline="\n")
    ensure_brief(course_dir)
    (course_dir / "media" / "manifest.yaml").write_text(
        "# Generated from the content placeholders.\nassets: []\n", encoding="utf-8", newline="\n"
    )
    return course_dir
