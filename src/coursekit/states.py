"""Unit and course state transitions.

Unit status moves forward with the work and backwards when content changes:
    pending -> writing -> verified -> reviewed -> approved
While the course is being written, its status is derived from its units:
    any unit started            -> writing
    every unit verified         -> ai_review
    every unit reviewed         -> editorial_review
    every unit approved         -> media
Every course status change is appended to course.yaml › history.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from coursekit import identity
from coursekit.util import edit_yaml, save_yaml

UNIT_ORDER = ["pending", "writing", "verified", "reviewed", "approved"]
WRITING_PHASE = ("design_approved", "writing", "ai_review", "editorial_review", "media")


def rank(status: str | None) -> int:
    return UNIT_ORDER.index(status) if status in UNIT_ORDER else 0


def derive_course_status(units: list, current: str) -> str:
    """Course status implied by its units; statuses outside the writing phase are kept."""
    if current not in WRITING_PHASE or not units:
        return current
    ranks = [rank(u.get("status")) for u in units]
    if min(ranks) >= rank("approved"):
        return "media"
    if min(ranks) >= rank("reviewed"):
        return "editorial_review"
    if min(ranks) >= rank("verified"):
        return "ai_review"
    if max(ranks) >= rank("writing"):
        return "writing"
    return "design_approved"


def history_entry(status: str, note: str, by: str | None = None) -> dict:
    return {"date": dt.date.today().isoformat(), "status": status, "by": by or identity.display_name(), "note": note}


def set_unit_status(course_dir: Path, n: int, status: str, note: str | None = None, by: str | None = None) -> tuple[str, str]:
    """Set one unit's status and re-derive the course status. Returns (old, new) course status."""
    path = course_dir / "course.yaml"
    ry, data = edit_yaml(path)
    units = data.get("units") or []
    unit = next((u for u in units if u["n"] == n), None)
    if unit is None:
        raise KeyError(f"unit {n} not found")
    changed = unit.get("status") != status
    unit["status"] = status
    old = data["status"]
    new = derive_course_status(units, old)
    data["status"] = new
    if old != new or note:
        data.setdefault("history", []).append(history_entry(new, note or f"Unit {n}: {status}", by))
    if changed or old != new or note:
        save_yaml(ry, data, path)
    return old, new
