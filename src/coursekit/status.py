"""`coursekit status`: the state of every course, or the detail and next step of one."""

from __future__ import annotations

from coursekit import course as coursemod
from coursekit.lang import format_number
from coursekit.project import Project

NEXT_STEP = {
    "design": "review the proposal, ask for changes with /design-change and sign with `coursekit approve design {code}`",
    "design_approved": "write the units with `coursekit write {code} <N>`",
    "writing": "finish the writing (`coursekit verify {code}`) and review with `coursekit review {code} <N>`",
    "ai_review": "AI review with `coursekit review {code} <N>`",
    "editorial_review": "editorial review and sign-off of each unit with `coursekit approve content {code} --unit <N>`",
    "media": "assembly and media production",
    "assembly": "assembly",
    "client_review": "client review",
    "delivered": "delivered",
}


def overview(project: Project) -> str:
    rows = []
    for folder in project.iter_courses():
        c = coursemod.load(project, str(folder))
        approval = coursemod.design_approval(c)
        signed = f" · design signed by {approval['by'].split(' <')[0]} on {approval['at'][:10]}" if approval else ""
        rows.append(
            f"{c['code']:<24} {c['status']:<18} {c['design']['hours']} h · {len(c.get('units') or [])} units{signed}"
        )
    return "\n".join(rows) if rows else 'no courses yet: coursekit new "<title>" <hours>'


def detail(course: dict) -> str:
    fmt = lambda n: format_number(n, coursemod.language(course))  # noqa: E731
    lines = [f"{course['code']} — {course['title']} ({course['design']['hours']} h)", f"Status: {course['status']}"]
    problem = coursemod.approval_problem(course)
    approval = coursemod.design_approval(course)
    if approval and not problem:
        lines.append(f"Design: signed by {approval['by']} on {approval['at']}")
    elif approval:
        lines.append(f"Design: {problem}")
    for u in course.get("units") or []:
        words = sum(s["min_words"] for s in u.get("sections") or [])
        extra = f" · written with {u['written_with']}" if u.get("written_with") else ""
        lines.append(
            f"  U{u['n']} {u['title']} · {u['hours']} h · {len(u.get('sections') or [])} sections · "
            f"{len(u.get('objectives') or [])} objectives · min. {fmt(words)} words · {u.get('status')}{extra}"
        )
    step = NEXT_STEP.get(course["status"])
    if approval and problem:
        step = "review the design changes and sign it again with `coursekit approve design {code}`"
    if step:
        lines.append(f"Next step: {step.format(code=course['code'])}")
    return "\n".join(lines)
