"""`coursekit status`: the state of every course, or the detail and next step of one."""

from __future__ import annotations

from coursekit import course as coursemod
from coursekit.i18n import t, tn
from coursekit.lang import format_number
from coursekit.project import Project

# Course status -> key of the next-step text in the catalog.
NEXT_STEP = {
    status: f"next_{status}"
    for status in (
        "design", "design_approved", "writing", "ai_review", "editorial_review", "media", "assembly", "client_review", "delivered",
        "on_hold",
    )
}


def overview(project: Project) -> str:
    rows = []
    for folder in project.iter_courses():
        c = coursemod.load(project, str(folder))
        approval = coursemod.design_approval(c)
        row = {
            "code": f"{c['code']:<24}", "status": f"{c['status']:<18}", "hours": c["design"]["hours"],
            "units": tn("status", "units", len(c.get("units") or [])),
        }
        if approval:
            rows.append(t("status", "overview_row_signed", by=approval["by"].split(" <")[0], date=approval["at"][:10], **row))
        else:
            rows.append(t("status", "overview_row", **row))
    return "\n".join(rows) if rows else t("status", "no_courses")


def detail(course: dict) -> str:
    fmt = lambda n: format_number(n, coursemod.language(course))  # noqa: E731
    lines = [f"{course['code']} — {course['title']} ({course['design']['hours']} h)", t("status", "state_line", status=course["status"]),
             t("status", "backend_line", backend=coursemod.backend(course))]
    problem = coursemod.approval_problem(course)
    approval = coursemod.design_approval(course)
    if approval and not problem:
        lines.append(t("status", "design_signed", by=approval["by"], at=approval["at"]))
    elif approval:
        lines.append(t("status", "design_problem", problem=problem))
    for u in course.get("units") or []:
        words = sum(s["min_words"] for s in u.get("sections") or [])
        lines.append(
            t("status", "unit_line_written_with" if u.get("written_with") else "unit_line",
              n=u["n"], title=u["title"], hours=u["hours"], sections=len(u.get("sections") or []),
              objectives=len(u.get("objectives") or []), words=fmt(words), status=u.get("status"), tool=u.get("written_with"))
        )
    if course["status"] == "on_hold":
        hold = course.get("hold") or {}
        lines.append(t("status", "hold_line", since=str(hold.get("at") or "")[:10], by=hold.get("by") or "-",
                       reason=hold.get("reason") or "-", previous=hold.get("previous") or "-"))
    last = (course.get("client_review") or [None])[-1]
    if last:
        lines.append(t("status", "client_round_line", round=last["round"], outcome=t("status", f"outcome_{last.get('outcome') or 'open'}"),
                       to=f" · {last['to']}" if last.get("to") else ""))
    key = NEXT_STEP.get(course["status"])
    if course["status"] == "client_review" and last and last.get("outcome") in ("approved", "skipped"):
        key = "next_client_review_closed"
    if approval and problem:
        key = "next_design_changed"
    if key:
        lines.append(t("status", "next_step_line", step=t("status", key, code=course["code"])))
    return "\n".join(lines)
