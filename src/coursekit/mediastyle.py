"""The style guide of the media (`theme/branding/media-style.md`, or the course's own, which wins): how the resources of the
courses must look, written from the brand. A person signs it (`coursekit approve media-style CODE`) before any visual resource
is produced, and again when it changes (rules › review › media_style); in handoff mode coursekit signs it."""

from __future__ import annotations

from pathlib import Path

from coursekit import course as coursemod
from coursekit.util import sha256_file

NAME = "media-style.md"


def path(course: dict) -> Path | None:
    """The guide in force for a course: its own, else the project's; None when there is none."""
    for base in (course["_dir"] / "theme" / "branding", course["_project"].theme_dir / "branding"):
        if (base / NAME).is_file():
            return base / NAME
    return None


def required(course: dict) -> bool:
    """Whether producing a visual resource needs the guide signed: there is one, and the rule asks for it."""
    rule = str(coursemod.rules(course=course).get("review", {}).get("media_style") or "required")
    return rule != "none" and path(course) is not None


def approval(course: dict) -> dict | None:
    """The last signature of the guide in force, while it has not changed since."""
    found = path(course)
    if found is None:
        return None
    signed = [a for a in course.get("approvals") or [] if a.get("gate") == "media_style"]
    if not signed:
        return None
    last = signed[-1]
    return last if last.get("sha256") == sha256_file(found) else None


def waiting(course: dict) -> bool:
    """The guide needs a signature that it does not have."""
    return required(course) and approval(course) is None
