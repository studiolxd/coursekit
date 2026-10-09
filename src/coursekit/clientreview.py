"""`coursekit client`: the review of the course by the client, optional (delivery › client_review).

The flow, for a course in `assembly`:
  send     opens a round: the course moves to `client_review` and the review links of the units are recorded
  changes  the client asked for changes: the round closes and the course goes back to `assembly`
  approve  the client approved (name and date recorded): `deliver` is allowed
  skip     delivers without the client's approval, with a reason (when the review is required)

course.yaml › client_review is the list of rounds: {round, sent_at, sent_by, to, links, outcome, ...}. The review links of
each unit (units[N].links.review) are created in the authoring platform by the assembly agent. The agents never run
this command: it records what the client decided.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from coursekit import config, identity
from coursekit.i18n import t
from coursekit.states import ensure_active, history_entry
from coursekit.util import edit_yaml, save_yaml


class ClientReviewError(Exception):
    pass


def required(course: dict) -> bool:
    cfg = config.effective("delivery", course.get("_project"), course).value
    return bool((cfg.get("client_review") or {}).get("required"))


def rounds(course: dict) -> list[dict]:
    return list(course.get("client_review") or [])


def open_round(course: dict) -> dict | None:
    last = rounds(course)[-1] if rounds(course) else None
    return last if last and last.get("outcome") is None else None


def review_links(course: dict) -> dict[str, str]:
    return {str(u["n"]): u["links"]["review"] for u in course.get("units") or [] if (u.get("links") or {}).get("review")}


def gate(course: dict) -> str | None:
    """Why the course cannot be delivered yet because of the client's review, or None."""
    if not required(course):
        return None
    last = rounds(course)[-1] if rounds(course) else None
    if last is None:
        return t("clientreview", "gate_none", code=course["code"])
    if last.get("outcome") in ("approved", "skipped"):
        return None
    if last.get("outcome") == "changes":
        return t("clientreview", "gate_changes", code=course["code"])
    return t("clientreview", "gate_waiting", code=course["code"], round=last["round"], to=last.get("to") or "-")


def _edit(course: dict):
    path: Path = course["_dir"] / "course.yaml"
    ry, data = edit_yaml(path)
    return path, ry, data


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def send(course: dict, to: str | None, where: str | None) -> str:
    ensure_active(course)
    if open_round(course):
        raise ClientReviewError(t("clientreview", "round_open", round=open_round(course)["round"]))
    if course["status"] != "assembly":
        raise ClientReviewError(t("clientreview", "send_needs_assembly", code=course["code"], status=course["status"]))
    links = {"link": where} if where else review_links(course)
    if not links:
        raise ClientReviewError(t("clientreview", "no_links"))
    who = identity.display_name()
    path, ry, data = _edit(course)
    number = len(data.get("client_review") or []) + 1
    if data.get("client_review") is None:
        data["client_review"] = []
    data["client_review"].append({"round": number, "sent_at": _now(), "sent_by": who, "to": to or "", "links": links, "outcome": None})
    data["status"] = "client_review"
    data.setdefault("history", []).append(history_entry("client_review", f"Round {number} sent" + (f" to {to}" if to else ""), who))
    save_yaml(ry, data, path)
    return t("clientreview", "sent", round=number, links="\n".join(f"  {k}: {v}" for k, v in links.items()))


def _close(course: dict, outcome: str, note: str | None, by: str | None, status: str | None) -> tuple[int, str]:
    ensure_active(course)
    current = open_round(course)
    if current is None or course["status"] != "client_review":
        raise ClientReviewError(t("clientreview", "no_open_round", code=course["code"]))
    path, ry, data = _edit(course)
    entry = data["client_review"][-1]
    entry["outcome"] = outcome
    entry["closed_at"] = _now()
    if by:
        entry["by"] = by
    if note:
        entry["note"] = note
    if status:
        data["status"] = status
    who = identity.display_name()
    detail = f"Round {entry['round']}: {outcome}" + (f" ({by})" if by else "") + (f" — {note}" if note else "")
    data.setdefault("history", []).append(history_entry(data["status"], detail, who))
    save_yaml(ry, data, path)
    return entry["round"], data["status"]


def changes(course: dict, note: str | None) -> str:
    number, _ = _close(course, "changes", note, None, "assembly")
    return t("clientreview", "changes", round=number)


def approve(course: dict, by: str, note: str | None) -> str:
    number, _ = _close(course, "approved", note, by, None)
    return t("clientreview", "approved", round=number, by=by)


def skip(course: dict, reason: str) -> str:
    ensure_active(course)
    if course["status"] not in ("assembly", "client_review"):
        raise ClientReviewError(t("clientreview", "send_needs_assembly", code=course["code"], status=course["status"]))
    if open_round(course):
        raise ClientReviewError(t("clientreview", "round_open", round=open_round(course)["round"]))
    who = identity.display_name()
    path, ry, data = _edit(course)
    if data.get("client_review") is None:
        data["client_review"] = []
    number = len(data["client_review"]) + 1
    data["client_review"].append({"round": number, "sent_at": _now(), "sent_by": who, "outcome": "skipped", "note": reason})
    data.setdefault("history", []).append(history_entry(data["status"], f"Client review skipped: {reason}", who))
    save_yaml(ry, data, path)
    return t("clientreview", "skipped", code=course["code"])

