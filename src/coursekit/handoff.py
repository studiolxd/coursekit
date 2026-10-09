"""`coursekit handoff`: the whole production of a course by itself, from its title and hours to its delivery.

Nobody reviews anything in this mode, so it signs by itself: the design and every unit are signed as
"Coursekit Handoff" (never as a person), and each approval records `via: handoff`. The agents still cannot sign
nor run `coursekit handoff`: the signatures are given by this module, not by them. The client review is not part of it.

It drives the existing steps in order, each with the agent of its role (always headless), and decides what comes next
from the course status, so `coursekit handoff CODE` carries on wherever it stopped:

  design           the proposal (`/new-course`), its export checked and signed
  design_approved  writing, unit by unit (`coursekit write`)
  ai_review        AI review of each unit; when it is "not ready" the writer fixes and it is reviewed again
  editorial_review the sign-off of each unit
  media            theme (if the media needs it), media, assembly
  assembly         delivery

Every step is tried `rules › handoff › rounds` times; if it still fails, it stops with the reason and how to go on.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from coursekit import approve, clientreview, identity, launch
from coursekit import course as coursemod
from coursekit import media as mediamod
from coursekit import theme as thememod
from coursekit.i18n import t
from coursekit.project import Project
from coursekit.util import slugify

HANDOFF = identity.Identity("Coursekit Handoff", "handoff@coursekit.local")
VIA = "handoff"
NOT_READY = "not_ready"
# What the agents are told, on top of the headless note, so that they neither wait for nor ask a person.
AUTONOMOUS_NOTE = (
    "\n\nHANDOFF MODE: the whole process runs by itself and nobody reviews it. Nobody will sign for you or answer you: the "
    "signatures are given by coursekit. Do not tell the person to sign or to confirm anything (not even before spending "
    "credits: use only the providers and options already configured) and do not stop to ask. Decide with what you have "
    "and leave what you could not settle written down."
)
FIX_NOTE = (
    "\n\nHANDOFF MODE: the AI review of this unit found problems it could not settle (`reviews/unit-{n:02d}-ai-review.md`, "
    "Result: not ready). Fix every blocking finding in the unit, run `coursekit verify {code} --unit {n}` until it passes, "
    "and finish. Do not write the review: it is done afterwards."
)
RETRY_NOTE = "\n\nHANDOFF MODE: a previous attempt did not finish the unit ({status}). Carry on from where it was."
DESIGN_EXPORT = '{code} "Handoff mode: the proposal was not exported. Export it (Excel, matrix.json and validation.json)."'
DESIGN_FIX = (
    '{code} "Handoff mode: the design cannot be signed yet ({problem}). Fix it in slxd and export it again '
    '(Excel, matrix.json and validation.json)."'
)

Log = Callable[[str], None]
Mirror = Callable[[], None]


class HandoffError(Exception):
    pass


@dataclass
class Context:
    project: Project
    code: str
    rounds: int
    log: Log
    mirror: Mirror

    def course(self) -> dict:
        return coursemod.load(self.project, self.code)


def rounds_setting(project: Project) -> int:
    value = ((coursemod.rules(project=project).get("handoff") or {}).get("rounds")) or 2
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        raise HandoffError(t("handoff", "bad_rounds", value=value)) from None


def review_result(course_dir: Path, n: int) -> str:
    """Result of the AI review of a unit as its report says it (`<!-- result: … -->`, the last one); "unknown" if it does not."""
    report = course_dir / "reviews" / f"unit-{n:02d}-ai-review.md"
    if not report.exists():
        return "unknown"
    found = re.findall(r"<!--\s*result:\s*([a-z_]+)\s*-->", report.read_text(encoding="utf-8"))
    return found[-1] if found else "unknown"


def _snapshot(course: dict) -> tuple:
    """What a step can change: if it is the same after a step, the step achieved nothing."""
    return (course["status"], tuple(u.get("status") for u in course.get("units") or []), len(course.get("approvals") or []),
            len(course.get("history") or []))


def _agent(ctx: Context, role: str, command: str, arguments: str, name: str) -> tuple[int, Path | None]:
    agent = launch.agent_for(role)
    ctx.log(t("handoff", "agent_line", role=role, label=agent.label, command=command, arguments=arguments))
    text = launch.prompt(agent, command, arguments, True, AUTONOMOUS_NOTE)
    code, log, _ = launch.execute(ctx.project, agent, text, True, f"{ctx.code}-{name}-handoff")
    return code, log


def _where(log: Path | None, project: Project) -> str:
    return t("handoff", "see_log", path=log.relative_to(project.root).as_posix()) if log else ""


def _unit(ctx: Context, role: str, n: int, note: str = "") -> launch.UnitResult:
    agent = launch.agent_for(role)
    key = "write" if role == "writer" else "review"
    ctx.log(t("handoff", "unit_line", command=key, n=n, label=agent.label))
    result = launch.run_unit(ctx.project, ctx.code, role, n, agent, True, note=note)
    for warning in result.warnings:
        ctx.log(t("handoff", "warning_line", text=warning))
    ctx.mirror()
    return result


def _stuck(ctx: Context, key: str, log: Path | None = None, **values) -> HandoffError:
    return HandoffError(t("handoff", key, code=ctx.code, **values) + _where(log, ctx.project))


# ── stages ────────────────────────────────────────────────────────────────────────────────

def _design(ctx: Context, course: dict) -> None:
    """Proposal exported and valid, then signed."""
    if not (course["_dir"] / "design" / "matrix.json").exists():
        _, log = _agent(ctx, "design", "design-change", DESIGN_EXPORT.format(code=ctx.code), "design")
        if not (ctx.course()["_dir"] / "design" / "matrix.json").exists():
            raise _stuck(ctx, "design_not_exported", log)
    _agent(ctx, "design", "approve-design", ctx.code, "approve-design")
    problem = ""
    for attempt in range(1, ctx.rounds + 1):
        try:
            ctx.log(t("handoff", "signed_line", text=approve.approve_design(ctx.course(), lambda question: True, who=HANDOFF, via=VIA)))
            ctx.mirror()
            return
        except approve.ApprovalError as exc:
            problem = str(exc)
            if attempt < ctx.rounds:
                _agent(ctx, "design", "design-change", DESIGN_FIX.format(code=ctx.code, problem=problem.replace('"', "'")), "design-fix")
    raise _stuck(ctx, "design_not_signable", problem=problem)


def _write(ctx: Context, course: dict) -> None:
    for n in launch.units_to_do(course, "writer"):
        note, result = "", None
        for _ in range(ctx.rounds):
            result = _unit(ctx, "writer", n, note)
            if launch.done("writer", result.status):
                break
            note = RETRY_NOTE.format(status=result.status)
        if result is None or not launch.done("writer", result.status):
            raise _stuck(ctx, "unit_not_written", result.log if result else None, n=n, status=result.status if result else "-")


def _review_unit(ctx: Context, n: int) -> None:
    """Review the unit; a "not ready" result sends it back to the writer and it is reviewed again."""
    for attempt in range(1, ctx.rounds + 1):
        result = _unit(ctx, "reviewer", n)
        if not launch.done("reviewer", result.status):
            if attempt == ctx.rounds:
                raise _stuck(ctx, "unit_not_reviewed", result.log, n=n, status=result.status)
            continue
        if review_result(ctx.course()["_dir"], n) != NOT_READY:
            return
        if attempt == ctx.rounds:
            break
        ctx.log(t("handoff", "not_ready_line", n=n))
        fixed = _unit(ctx, "writer", n, FIX_NOTE.format(n=n, code=ctx.code))
        if not launch.done("writer", fixed.status):
            raise _stuck(ctx, "unit_not_written", fixed.log, n=n, status=fixed.status)
    raise _stuck(ctx, "unit_not_ready", n=n)


def _review(ctx: Context, course: dict) -> None:
    if not coursemod.ai_review_required(course):
        return
    for n in launch.units_to_do(course, "reviewer"):
        _review_unit(ctx, n)


def _sign(ctx: Context, course: dict) -> None:
    for unit in course.get("units") or []:
        current = next(u for u in ctx.course()["units"] if u["n"] == unit["n"])
        if current.get("status") != "reviewed":
            continue
        try:
            text = approve.approve_content(ctx.course(), unit["n"], lambda question: True, who=HANDOFF, via=VIA)
        except approve.ApprovalError as exc:
            raise _stuck(ctx, "unit_not_signable", n=unit["n"], problem=exc) from exc
        ctx.log(t("handoff", "signed_line", text=text))
        ctx.mirror()


def _pending_media(course: dict) -> list[dict]:
    _, _, data = mediamod.load_manifest(course["_dir"])
    return [a for a in data["assets"] if a.get("status") in ("pending", "scripted")]


def _media(ctx: Context, course: dict) -> None:
    mediamod.extract(course)
    pending = _pending_media(course)
    if pending:
        cfg = mediamod.config(course=course)
        needs_theme = any(a["type"] in (cfg.get("uses_theme") or []) for a in pending)
        if needs_theme and thememod.status(ctx.project, course).state != "derived":
            _agent(ctx, "design", "define-theme", "", "theme")
            if thememod.status(ctx.project, ctx.course()).state != "derived":
                raise _stuck(ctx, "theme_missing")
        log = None
        for _ in range(ctx.rounds):
            _, log = _agent(ctx, "media", "produce-media", ctx.code, "media")
            pending = _pending_media(ctx.course())
            if not pending:
                break
        if pending:
            raise _stuck(ctx, "media_pending", log, assets=", ".join(a["id"] for a in pending))
    ctx.mirror()
    log = None
    for _ in range(ctx.rounds):
        _, log = _agent(ctx, "assembly", "assemble", ctx.code, "assemble")
        if ctx.course()["status"] != "media":
            return
    raise _stuck(ctx, "not_assembled", log)


def _deliver(ctx: Context, course: dict) -> None:
    log = None
    for _ in range(ctx.rounds):
        _, log = _agent(ctx, "assembly", "deliver", ctx.code, "deliver")
        if ctx.course()["status"] == "delivered":
            return
    raise _stuck(ctx, "not_delivered", log)


STAGES = {
    "design": _design,
    "design_approved": _write,
    "writing": _write,
    "ai_review": _review,
    "editorial_review": _sign,
    "media": _media,
    "assembly": _deliver,
}


def proceed(ctx: Context) -> dict:
    """Run the stages from where the course is until it is delivered; returns the delivered course."""
    problem = clientreview.gate(ctx.course())
    if problem:
        raise _stuck(ctx, "client_review_required")
    while True:
        course = ctx.course()
        status = course["status"]
        if status == "delivered":
            return course
        if status in ("on_hold", "client_review"):
            raise _stuck(ctx, f"stopped_{status}")
        before = _snapshot(course)
        ctx.log(t("handoff", "stage_line", status=status))
        STAGES[status](ctx, course)
        ctx.mirror()
        if _snapshot(ctx.course()) == before:
            raise _stuck(ctx, "no_progress", status=status)


def course_code(title: str, code: str | None) -> str:
    return code.upper() if code else slugify(title).upper()


def start(project: Project, title: str, hours: float, code: str | None, flags: list[str], notes: str, rounds: int, log: Log,
          mirror: Callable[[str], None]) -> dict:
    """Create the course (the design agent proposes it) and take it to its delivery."""
    code = course_code(title, code)
    if (project.course_dir(code) / "course.yaml").exists():
        raise HandoffError(t("handoff", "course_exists", code=code))
    log(t("handoff", "start_line", code=code, who=HANDOFF.name))
    hours_text = int(hours) if float(hours).is_integer() else hours
    arguments = " ".join([f'"{title}"', str(hours_text), "--code", code, "--no-material", *flags] + ([notes] if notes else []))
    ctx = Context(project, code, rounds, log, lambda: mirror(code))
    _, session = _agent(ctx, "design", "new-course", arguments, "new-course")
    if not (project.course_dir(code) / "course.yaml").exists():
        raise _stuck(ctx, "course_not_created", session)
    return proceed(ctx)


def resume(project: Project, code: str, rounds: int, log: Log, mirror: Callable[[str], None]) -> dict:
    course = coursemod.load(project, code)
    log(t("handoff", "resume_line", code=course["code"], status=course["status"], who=HANDOFF.name))
    return proceed(Context(project, course["code"], rounds, log, lambda: mirror(course["code"])))
