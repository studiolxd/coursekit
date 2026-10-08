"""`coursekit approve`: record a human approval (sign-off) and commit it in the signer's name.

Gates:
  design   the instructional design snapshot in design/ (matrix.json and the exported Excel)
  content  one unit's content, after verification and AI review (--unit N)

The signer is the identity in the personal .env (COURSEKIT_USER_NAME / COURSEKIT_USER_EMAIL),
never the git identity. The approval is stored in course.yaml › approvals with a timestamp and a
fingerprint of what was approved, and committed with that person as author. Agents must never
run this command: the generated agent configurations deny it. A person confirms in a terminal,
or with --yes when running it from an agent chat with `!` (which runs as the person).
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
from collections.abc import Callable
from pathlib import Path

from coursekit import course as coursemod
from coursekit import identity
from coursekit.lang import format_number
from coursekit.states import history_entry, set_unit_status
from coursekit.sync import sync
from coursekit.util import edit_yaml, save_yaml, sha256_file
from coursekit.verify import verify_unit


class ApprovalError(Exception):
    pass


Confirm = Callable[[str], bool]


def signer() -> identity.Identity:
    who = identity.current()
    if who is None:
        raise ApprovalError("no signing identity: run `coursekit setup --identity` (COURSEKIT_USER_NAME / _EMAIL in .env)")
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


def approve_design(course: dict, confirm: Confirm, do_commit: bool = True) -> str:
    course_dir: Path = course["_dir"]
    design = course_dir / "design"
    matrix = design / "matrix.json"
    if not matrix.exists():
        raise ApprovalError("design/matrix.json is missing: ask the design agent to export the design first")
    validation_path = design / "validation.json"
    if validation_path.exists():
        findings = json.loads(validation_path.read_text(encoding="utf-8"))
        findings = findings.get("hallazgos", findings) if isinstance(findings, dict) else findings
        errors = [h for h in findings if h.get("severidad") == "error"]
        if errors:
            raise ApprovalError(f"the design has {len(errors)} validation errors (design/validation.json)")
    excel = sorted(design.glob("*.xlsx"))
    graph = json.loads(matrix.read_text(encoding="utf-8"))
    meta = graph.get("matrix") or {}
    check = sync(course, check_only=True)
    who = signer()
    summary = (
        f"{course['code']} — {course['title']} ({course['design']['hours']} h)\n"
        f"  slxd matrix: {meta.get('id')} · updated {meta.get('updatedAt')}\n"
        f"  units: {len(check.units)} · Excel: {excel[-1].name if excel else '(none)'}"
    )
    if not confirm(f"{summary}\nApprove this instructional design? You sign as {who}"):
        raise ApprovalError("approval cancelled")
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
    _record(course_dir, entry, "design_approved", "Instructional design approved")
    if do_commit and not commit([course_dir], f"Design approval {course['code']}", who, course_dir):
        return f"design approved by {who} (recorded, not committed)"
    return f"design approved by {who}"


def approve_content(course: dict, n: int, confirm: Confirm, do_commit: bool = True) -> str:
    problem = coursemod.approval_problem(course)
    if problem:
        raise ApprovalError(problem)
    unit = next((u for u in course.get("units") or [] if u["n"] == n), None)
    if unit is None:
        raise ApprovalError(f"unit {n} not found")
    report = verify_unit(course, unit)
    if report.errors:
        raise ApprovalError(f"unit {n} does not pass verification ({len(report.errors)} errors: coursekit verify)")
    if unit.get("status") not in ("reviewed", "approved"):
        raise ApprovalError(f"unit {n} is '{unit.get('status')}': it needs the AI review first (coursekit reviewed)")
    course_dir: Path = course["_dir"]
    review = course_dir / "reviews" / f"unit-{n:02d}-ai-review.md"
    if not review.exists():
        raise ApprovalError(f"missing AI review {review.relative_to(course_dir).as_posix()}")
    folder = coursemod.unit_dir(course_dir, n)
    files = [folder / "content.md", folder / "assessment.md"]
    who = signer()
    words = format_number(sum(s["min_words"] for s in unit.get("sections") or []), coursemod.language(course))
    if not confirm(f"Approve unit {n} — {unit['title']} (min. {words} words)? You sign as {who}"):
        raise ApprovalError("approval cancelled")
    entry = {
        "gate": "content",
        "unit": n,
        "by": str(who),
        "at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "files_sha256": {f.name: sha256_file(f) for f in files if f.exists()},
    }
    _record(course_dir, entry, None, f"Unit {n} approved")
    set_unit_status(course_dir, n, "approved", by=str(who))
    paths = [course_dir / "course.yaml", folder, review]
    if do_commit and not commit(paths, f"Content approval {course['code']} U{n}", who, course_dir):
        return f"unit {n} approved by {who} (recorded, not committed)"
    return f"unit {n} approved by {who}"


def mark_reviewed(course: dict, n: int) -> str:
    """After the AI review: the report exists and the unit still verifies. Records fingerprints."""
    from coursekit.fingerprint import record_review

    course_dir: Path = course["_dir"]
    report_path = course_dir / "reviews" / f"unit-{n:02d}-ai-review.md"
    if not report_path.exists():
        raise ApprovalError(f"missing {report_path.relative_to(course_dir).as_posix()}")
    unit = next((u for u in course.get("units") or [] if u["n"] == n), None)
    if unit is None:
        raise ApprovalError(f"unit {n} not found")
    if verify_unit(course, unit).errors:
        raise ApprovalError(f"unit {n} does not pass verification")
    old, new = set_unit_status(course_dir, n, "reviewed")
    record_review(course_dir, n, coursemod.tokens(course))
    return f"unit {n}: reviewed" + (f" · course {old} -> {new}" if old != new else "")
