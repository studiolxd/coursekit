"""The style guide of the media (`theme/branding/media-style.md`, or the course's own, which wins): how the resources of the
courses must look, written from the brand. A person signs it before any visual resource is produced, and again when it changes
(rules › review › media_style): the project's guide once for every course that uses it (`coursekit approve media-style`, recorded
in project.yaml), a course's own guide in that course (`coursekit approve media-style CODE`, which also signs the project's guide
for that course alone); in handoff mode coursekit signs it."""

from __future__ import annotations

import re
from pathlib import Path

from coursekit import course as coursemod
from coursekit.util import sha256_file

NAME = "media-style.md"


def project_path(project) -> Path | None:
    """The guide of the project (theme/branding/media-style.md), None when there is none."""
    found = project.theme_dir / "branding" / NAME
    return found if found.is_file() else None


def _last(approvals: list | None, found: Path) -> dict | None:
    signed = [a for a in approvals or [] if a.get("gate") == "media_style"]
    return signed[-1] if signed and signed[-1].get("sha256") == sha256_file(found) else None


def project_approval(project) -> dict | None:
    """The last signature of the guide of the project, while it has not changed since."""
    from coursekit import config

    found = project_path(project)
    return _last(config.project_data(project).get("approvals"), found) if found else None


def path(course: dict) -> Path | None:
    """The guide in force for a course: its own, else the project's; None when there is none."""
    for base in (course["_dir"] / "theme" / "branding", course["_project"].theme_dir / "branding"):
        if (base / NAME).is_file():
            return base / NAME
    return None


NOTES = "notes.md"


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[`*_«»\"“”]", "", text)).strip().casefold().rstrip(".;:")


def notes(guide: Path) -> list[str]:
    """The indications of the person next to a guide (notes.md of the same folder): one per line, without headings, comments
    and list marks."""
    found = guide.parent / NOTES
    if not found.is_file():
        return []
    text = re.sub(r"<!--.*?-->", "", found.read_text(encoding="utf-8"), flags=re.S)
    lines = (re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", line).strip() for line in text.splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def missing_notes(guide: Path) -> list[str]:
    """The indications of notes.md that the guide does not quote: the guide lists each one, as it is, with where it applies
    (theme-definition skill), so an indication that is not there was left out when the guide was written."""
    text = _plain(guide.read_text(encoding="utf-8"))
    return [line for line in notes(guide) if _plain(line) not in text]


def required(course: dict) -> bool:
    """Whether producing a visual resource needs the guide signed: there is one, and the rule asks for it."""
    rule = str(coursemod.rules(course=course).get("review", {}).get("media_style") or "required")
    return rule != "none" and path(course) is not None


def approval(course: dict) -> dict | None:
    """The last signature of the guide in force, while it has not changed since: the course's, or, when the guide in force is
    the project's, the signature of the project."""
    found = path(course)
    if found is None:
        return None
    own = _last(course.get("approvals"), found)
    if own or found != project_path(course["_project"]):
        return own
    return project_approval(course["_project"])


def waiting(course: dict) -> bool:
    """The guide needs a signature that it does not have."""
    return required(course) and approval(course) is None
