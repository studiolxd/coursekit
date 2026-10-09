"""`coursekit approve`: record a human approval (sign-off) and commit it in the signer's name.

Gates:
  design   the instructional design snapshot in design/ (matrix.json and the exported Excel)
  content  one unit's content, after verification and AI review (--unit N)

The signer is the identity in the personal .env (COURSEKIT_USER_NAME / COURSEKIT_USER_EMAIL),
never the git identity. The approval is stored in course.yaml › approvals with a timestamp and a
fingerprint of what was approved, and committed with that person as author. Agents must never
run this command: the generated agent configurations deny it. A person confirms in a terminal,
or with --yes when running it from an agent chat with `!` (which runs as the person).

Handoff mode (`coursekit handoff`) signs by itself with its own identity: it passes `who` and `via="handoff"`, and
the approval records `via`, so a delegated signature is never mistaken for a person's.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
from collections.abc import Callable
from pathlib import Path

from coursekit import course as coursemod
from coursekit import identity
from coursekit.fingerprint import changed_since_review
from coursekit.i18n import t
from coursekit.lang import format_number
from coursekit.states import history_entry, now, set_unit_status
from coursekit.sync import sync
from coursekit.util import edit_yaml, save_yaml, sha256_file
from coursekit.verify import verify_unit


class ApprovalError(Exception):
    pass


Confirm = Callable[[str], bool]


def signer() -> identity.Identity:
    who = identity.current()
    if who is None:
        raise ApprovalError(t("approve", "no_identity"))
    return who


def _record(course_dir: Path, entry: dict, status: str | None, note: str) -> None:
    path = course_dir / "course.yaml"
    ry, data = edit_yaml(path)
    if data.get("approvals") is None:
        data["approvals"] = []
    data["approvals"].append(entry)
    if status:
        data["status"] = status
    data.setdefault("history", []).append(history_entry(data["status"], note, entry["by"]))
    save_yaml(ry, data, path)


def commit(paths: list[Path], message: str, who: identity.Identity, cwd: Path) -> bool:
    """Commit only `paths`, with the signer as author."""
    names = [str(p) for p in paths]
    add = subprocess.run(["git", "add", "--", *names], cwd=cwd)
    if add.returncode:
        return False
    result = subprocess.run(["git", "commit", "-q", "--author", str(who), "-m", message, "--", *names], cwd=cwd)
    return result.returncode == 0


def approve_design(course: dict, confirm: Confirm, do_commit: bool = True, who: identity.Identity | None = None,
                   via: str | None = None) -> str:
    course_dir: Path = course["_dir"]
    design = course_dir / "design"
    matrix = design / "matrix.json"
    if not matrix.exists():
        raise ApprovalError(t("approve", "matrix_missing"))
    validation_path = design / "validation.json"
    if validation_path.exists():
        findings = json.loads(validation_path.read_text(encoding="utf-8"))
        findings = findings.get("hallazgos", findings) if isinstance(findings, dict) else findings
        errors = [h for h in findings if h.get("severidad") == "error"]
        if errors:
            raise ApprovalError(t("approve", "design_errors", count=len(errors)))
    excel = sorted(design.glob("*.xlsx"))
    graph = json.loads(matrix.read_text(encoding="utf-8"))
    meta = graph.get("matrix") or {}
    check = sync(course, check_only=True)
    who = who or signer()
    summary = t(
        "approve", "design_summary",
        code=course["code"], title=course["title"], hours=course["design"]["hours"],
        matrix_id=meta.get("id"), updated=meta.get("updatedAt"),
        units=len(check.units), excel=excel[-1].name if excel else t("approve", "excel_none"),
    )
    if not confirm(t("approve", "design_confirm", summary=summary, who=who)):
        raise ApprovalError(t("approve", "cancelled"))
    sync(course)
    entry = {
        "gate": "design",
        "by": str(who),
        "at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "matrix_id": meta.get("id"),
        "matrix_updated_at": meta.get("updatedAt"),
        "snapshot_sha256": sha256_file(matrix),
        "excel": excel[-1].name if excel else None,
    }
    if via:
        entry["via"] = via
    _record(course_dir, entry, "design_approved", "Instructional design approved")
    if do_commit and not commit([course_dir], f"Design approval {course['code']}", who, course_dir):
        return t("approve", "design_approved_uncommitted", who=who)
    return t("approve", "design_approved", who=who)


def approve_content(course: dict, n: int, confirm: Confirm, do_commit: bool = True, force: bool = False,
                    who: identity.Identity | None = None, via: str | None = None) -> str:
    problem = coursemod.approval_problem(course)
    if problem:
        raise ApprovalError(problem)
    unit = next((u for u in course.get("units") or [] if u["n"] == n), None)
    if unit is None:
        raise ApprovalError(t("approve", "unit_not_found", n=n))
    report = verify_unit(course, unit)
    if report.errors:
        raise ApprovalError(t("approve", "unit_fails_verification_errors", n=n, count=len(report.errors)))
    ai_required = coursemod.ai_review_required(course)
    kind = (unit.get("review") or {}).get("kind")
    if unit.get("status") not in ("reviewed", "approved") + (() if ai_required else ("verified",)):
        raise ApprovalError(t("approve", "needs_review", n=n, status=unit.get("status")))
    course_dir: Path = course["_dir"]
    review = course_dir / "reviews" / f"unit-{n:02d}-ai-review.md"
    # The AI report is needed unless a person recorded their own review of the unit or the project skips the AI review.
    if ai_required and kind != "human" and not review.exists():
        raise ApprovalError(t("approve", "review_missing", path=review.relative_to(course_dir).as_posix()))
    changed = changed_since_review(course_dir, unit, coursemod.tokens(course)) if ai_required or kind == "human" else None
    if changed and not force:
        raise ApprovalError(t("approve", "changed_since_review", n=n, parts=", ".join(changed)))
    folder = coursemod.unit_dir(course_dir, n)
    files = [folder / "content.md", folder / "assessment.md"]
    who = who or signer()
    words = format_number(sum(s["min_words"] for s in unit.get("sections") or []), coursemod.language(course))
    if not confirm(t("approve", "content_confirm", n=n, title=unit["title"], words=words, who=who)):
        raise ApprovalError(t("approve", "cancelled"))
    entry = {
        "gate": "content",
        "unit": n,
        "by": str(who),
        "at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "files_sha256": {f.name: sha256_file(f) for f in files if f.exists()},
    }
    if via:
        entry["via"] = via
    _record(course_dir, entry, None, f"Unit {n} approved")
    set_unit_status(course_dir, n, "approved", by=str(who))
    own_report = (unit.get("review") or {}).get("report")
    reports = [review] + ([course_dir / own_report] if own_report else [])
    paths = [course_dir / "course.yaml", folder, *(p for p in reports if p.exists())]
    if do_commit and not commit(paths, f"Content approval {course['code']} U{n}", who, course_dir):
        return t("approve", "unit_approved_uncommitted", n=n, who=who)
    return t("approve", "unit_approved", n=n, who=who)


def mark_reviewed(course: dict, n: int, by: str | None = None, note: str | None = None, report: str | None = None) -> str:
    """The unit is reviewed: by the AI (its report exists) or, with `by`, by a person. Records fingerprints."""
    from coursekit.fingerprint import record_review

    course_dir: Path = course["_dir"]
    unit = next((u for u in course.get("units") or [] if u["n"] == n), None)
    if unit is None:
        raise ApprovalError(t("approve", "unit_not_found", n=n))
    info = {"kind": "ai", "at": now()}
    if by is None:
        report_path = course_dir / "reviews" / f"unit-{n:02d}-ai-review.md"
        if not report_path.exists():
            raise ApprovalError(t("approve", "file_missing", path=report_path.relative_to(course_dir).as_posix()))
    else:
        info = {"kind": "human", "by": by, "at": info["at"]}
        if note:
            info["note"] = note
        if report:
            path = Path(report)
            path = path if path.is_absolute() or path.exists() else course_dir / path
            if not path.is_file():
                raise ApprovalError(t("approve", "report_not_found", path=report))
            try:
                info["report"] = path.resolve().relative_to(course_dir.resolve()).as_posix()
            except ValueError:
                raise ApprovalError(t("approve", "report_outside", path=report, course=course["code"])) from None
    if verify_unit(course, unit).errors:
        raise ApprovalError(t("approve", "unit_fails_verification", n=n))
    detail = t("approve", "reviewed_by_note", n=n, by=by) if by else None
    old, new = set_unit_status(course_dir, n, "reviewed", note=detail, by=by, review=info)
    record_review(course_dir, n, coursemod.tokens(course))
    key = "reviewed_human" if by else "reviewed"
    if old != new:
        return t("approve", key + "_course", n=n, old=old, new=new, by=by)
    return t("approve", key, n=n, by=by)
