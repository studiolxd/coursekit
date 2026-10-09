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
from coursekit.i18n import t
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


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def history_entry(status: str, note: str, by: str | None = None) -> dict:
    return {"date": dt.date.today().isoformat(), "status": status, "by": by or identity.display_name(), "note": note}


def set_unit_status(course_dir: Path, n: int, status: str, note: str | None = None, by: str | None = None,
                    review: dict | None = None) -> tuple[str, str]:
    """Set one unit's status and re-derive the course status. Returns (old, new) course status.

    `review` records how the unit was reviewed ({kind: ai|human|skipped, ...}); it is dropped when the unit falls
    back below `reviewed`.
    """
    path = course_dir / "course.yaml"
    ry, data = edit_yaml(path)
    units = data.get("units") or []
    unit = next((u for u in units if u["n"] == n), None)
    if unit is None:
        raise KeyError(t("states", "unit_not_found", n=n))
    changed = unit.get("status") != status or review is not None
    unit["status"] = status
    if review is not None:
        unit["review"] = review
    elif rank(status) < rank("reviewed") and "review" in unit:
        del unit["review"]
        changed = True
    old = data["status"]
    new = derive_course_status(units, old)
    data["status"] = new
    if old != new or note:
        data.setdefault("history", []).append(history_entry(new, note or f"Unit {n}: {status}", by))
    if changed or old != new or note:
        save_yaml(ry, data, path)
    return old, new


class StateError(Exception):
    pass


def ensure_active(course: dict) -> None:
    """Work on a course that is on hold is refused until `coursekit resume`."""
    if course.get("status") == "on_hold":
        hold_info = course.get("hold") or {}
        raise StateError(t("states", "on_hold", code=course["code"], since=str(hold_info.get("at") or "")[:10],
                           reason=hold_info.get("reason") or "-", previous=hold_info.get("previous") or "-"))


def hold(course_dir: Path, reason: str, by: str | None = None) -> str:
    """Put the course on hold, remembering where it was. Returns the previous status."""
    path = course_dir / "course.yaml"
    ry, data = edit_yaml(path)
    if data["status"] == "on_hold":
        raise StateError(t("states", "already_on_hold", code=data["code"]))
    previous = str(data["status"])
    who = by or identity.display_name()
    data["hold"] = {"previous": previous, "reason": reason, "by": who, "at": dt.datetime.now().astimezone().isoformat(timespec="seconds")}
    data["status"] = "on_hold"
    data.setdefault("history", []).append(history_entry("on_hold", reason, who))
    save_yaml(ry, data, path)
    return previous


def resume(course_dir: Path, by: str | None = None) -> tuple[str, str]:
    """Back to the status the course had (re-derived from its units while it is being written). Returns (previous, new)."""
    path = course_dir / "course.yaml"
    ry, data = edit_yaml(path)
    if data["status"] != "on_hold":
        raise StateError(t("states", "not_on_hold", code=data["code"], status=data["status"]))
    previous = str((data.get("hold") or {}).get("previous") or "design")
    new = derive_course_status(data.get("units") or [], previous)
    data["status"] = new
    data.pop("hold", None)
    data.setdefault("history", []).append(history_entry(new, f"Resumed (on hold since {previous})", by))
    save_yaml(ry, data, path)
    return previous, new
