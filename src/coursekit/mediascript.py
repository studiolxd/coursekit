"""The script of a resource (the brief of a screen recording, the montage of a video), approved by a person before it is made.

The narration of a recording or of a video is text the learner will hear, and it is not part of the content of the units that
the editorial review reads: a person approves it, with the steps, before anything is captured or voiced
(`coursekit approve script CODE --asset ID`, `rules › review › scripts: required`). What is signed is a fingerprint of
`media/scripts/<id>.md` (without its `capture` block: the exact steps a capture session writes there) and of
`media/scripts/<id>.video.yaml`; a change to either asks for the approval again. A session of the handoff signs it by itself,
as the handoff signs every gate.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from coursekit import course as coursemod
from coursekit import identity
from coursekit.i18n import t

BLOCK_RE = re.compile(r"^```capture[ \t]*\n.*?^```[ \t]*$", re.M | re.S)


class ScriptError(Exception):
    pass


def files(course: dict, asset_id: str) -> list[Path]:
    folder = course["_dir"] / "media" / "scripts"
    return [p for p in (folder / f"{asset_id}.md", folder / f"{asset_id}.video.yaml") if p.exists()]


def fingerprint(course: dict, asset_id: str) -> str | None:
    """What is approved: the brief without its capture block, and the montage; None when the resource has no script."""
    found = files(course, asset_id)
    if not found:
        return None
    digest = hashlib.sha256()
    for path in found:
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".md":
            text = BLOCK_RE.sub("", text)
        digest.update(path.name.encode("utf-8") + b"\0" + re.sub(r"\s+", " ", text).strip().encode("utf-8") + b"\0")
    return digest.hexdigest()[:16]


def approval(course: dict, asset_id: str) -> dict | None:
    return next((a for a in reversed(course.get("approvals") or []) if a.get("gate") == "script" and a.get("asset") == asset_id), None)


def state(course: dict, asset_id: str) -> str:
    """approved | changed (it was approved, then it changed) | pending (never approved) | none (no script yet)."""
    current = fingerprint(course, asset_id)
    if current is None:
        return "none"
    signed = approval(course, asset_id)
    if signed is None:
        return "pending"
    return "approved" if signed.get("fingerprint") == current else "changed"


def required(course: dict) -> bool:
    return str(coursemod.rules(course=course).get("review", {}).get("scripts") or "required") != "none"


def _in_handoff() -> bool:
    from coursekit.handoff import HANDOFF

    who = identity.current()
    return who is not None and who.name == HANDOFF.name and who.email == HANDOFF.email


def require(course: dict, asset_id: str) -> None:
    """Raises ScriptError unless the script of the resource is approved as it is now (or approval is not required)."""
    if not required(course):
        return
    current = state(course, asset_id)
    if current == "approved":
        return
    if current == "none":
        raise ScriptError(t("mediascript", "no_script", id=asset_id, path=f"media/scripts/{asset_id}.md"))
    if _in_handoff():  # nobody reviews the handoff: it signs, as it signs every gate
        from coursekit import approve
        from coursekit.handoff import HANDOFF, VIA

        approve.approve_script(course, asset_id, lambda question: True, do_commit=False, who=HANDOFF, via=VIA)
        return
    raise ScriptError(t("mediascript", current, id=asset_id, code=course["code"]))


def ready(course: dict, asset_id: str) -> None:
    """Before a resource is captured or voiced: no official video stands in for it, and its script is approved."""
    from coursekit import videos

    official = videos.standing_in(course, asset_id)
    if official:
        raise ScriptError(t("videos", f"stands_in_{official['status']}", id=asset_id, url=official["url"], code=course["code"]))
    require(course, asset_id)
