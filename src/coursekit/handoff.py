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

from coursekit import approve, clientreview, config, identity, launch, new, verify
from coursekit import assemble as assemblemod
from coursekit import course as coursemod
from coursekit import media as mediamod
from coursekit import theme as thememod
from coursekit.i18n import t
from coursekit.project import Project
from coursekit.states import derive_course_status, history_entry
from coursekit.util import edit_yaml, save_yaml, slugify

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


def theme_note(project: Project, backend: str) -> str:
    """What the design agent is told to do for the theme, from the choice made when the project was created (nobody is asked)."""
    if backend == "html":
        return (
            "\n\nTHEME (html backend): if theme/maqueta.css does not exist, write it from the brand material in theme/branding/ "
            "(and in brief/) and run `coursekit theme import theme/maqueta.css`. If there is no brand material at all, write "
            "nothing and run `coursekit theme import` without a file: the tokens are those of the base layout. Do not ask."
        )
    if thememod.source(project) == "branding":
        return (
            "\n\nTHEME (creator backend, made from the branding): create the theme in creator from the material in "
            "theme/branding/ (and in brief/) with create_theme and update_theme, link it, then get_theme and "
            "`coursekit theme import`. If theme/branding/ has no material, use the organization's default theme instead "
            "(list_themes, the one with isDefault) and say so in your summary. Do not ask."
        )
    return (
        "\n\nTHEME (creator backend, the tenant's default): use the organization's default theme. list_themes, take the one "
        "with isDefault, get_theme, save the result to .cache/theme/get_theme.json and `coursekit theme import`. Do not create "
        "or change any theme and do not ask."
    )


def _agent(ctx: Context, role: str, command: str, arguments: str, name: str, extra: str = "") -> tuple[int, Path | None, str]:
    agent = launch.agent_for(role)
    ctx.log(t("handoff", "agent_line", role=role, label=agent.label, command=command, arguments=arguments))
    text = launch.prompt(agent, command, arguments, True, AUTONOMOUS_NOTE + extra)
    code, log, summary = launch.execute(ctx.project, agent, text, True, f"{ctx.code}-{name}-handoff")
    return code, log, summary


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


def _why(ctx: Context, log: Path | None, summary: str, role: str = "") -> str:
    """The cause of an agent that did not do its job: what its session log says about creator (not authorized, not allowed) or about
    the programs it could not run, and what the agent itself said at the end (it is the one that knows when the cause is another)."""
    blocker = (launch.mcp_blocker(ctx.project, log) or launch.permission_blocker(ctx.project, log, role)) if log else None
    text = " ".join(summary.split())[:700]
    said = "\n" + t("handoff", "agent_said_line", text=text) if text else ""
    return ("\n" + t("handoff", "cause_line", text=blocker) if blocker else "") + said


def _cannot(ctx: Context, log: Path | None, role: str) -> bool:
    """The session was refused something (a server, a program) that another attempt would be refused again: do not repeat the step
    (repeating the delivery asks creator for another export each time)."""
    return bool(log and (launch.mcp_blocker(ctx.project, log) or launch.permission_blocker(ctx.project, log, role)))


def _stuck(ctx: Context, key: str, log: Path | None = None, why: str = "", **values) -> HandoffError:
    return HandoffError(t("handoff", key, code=ctx.code, **values) + _where(log, ctx.project) + why)


# ── stages ────────────────────────────────────────────────────────────────────────────────

def _propose(ctx: Context, course: dict) -> None:
    """The design proposal has to exist in slxd and be exported to design/. When the matrix was never created the design agent
    designs the course (`/new-course` works on the existing one); when it exists and only the export is missing it exports it."""
    if not (course.get("slxd") or {}).get("matrix_id"):
        hours = course["design"]["hours"]
        hours = int(hours) if float(hours).is_integer() else hours
        arguments = f'"{course["title"]}" {hours} --code {ctx.code} --no-material'
        _, log, summary = _agent(ctx, "design", "new-course", arguments, "new-course")
    else:
        _, log, summary = _agent(ctx, "design", "design-change", DESIGN_EXPORT.format(code=ctx.code), "design")
    if not (ctx.course()["_dir"] / "design" / "matrix.json").exists():
        raise _stuck(ctx, "design_not_exported", log, why=_why(ctx, log, summary))


def _design(ctx: Context, course: dict) -> None:
    """Proposal exported and valid, then signed."""
    if not (course["_dir"] / "design" / "matrix.json").exists():
        _propose(ctx, course)
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


UPLOAD_NOTE = (
    "\n\nThe course is already assembled, so every unit has its content in creator now. Produce nothing: upload each asset whose "
    "status is `produced` to the content of its unit, as the upload step of the media-production skill says (request_asset_upload "
    "or request_embed_upload, then `coursekit media upload`, then `coursekit media set` with --status uploaded and --asset-path). "
    "Do not run /assemble: the assembly agent does it next, and it is what puts the media in place of their placeholders."
)


def _not_uploaded(course: dict) -> list[dict]:
    _, _, data = mediamod.load_manifest(course["_dir"])
    return [a for a in data["assets"] if a.get("status") == "produced"]


def _refresh_media(ctx: Context, course: dict) -> None:
    """Media that is not in the course yet, or an assembly that did not finish recording. The assets marked to be produced again
    (`coursekit media redo`, after the theme changed)
    are produced. With the creator backend the produced ones are uploaded, which can only be done to the content of their unit that
    the assembly creates; then the course is assembled again so that they replace their placeholders."""
    again = bool(_pending_media(course))
    if again:
        _produce(ctx, course)
    creator = coursemod.backend(course) == "creator"
    if creator and _not_uploaded(ctx.course()):
        log = None
        for _ in range(ctx.rounds):
            _, log, summary = _agent(ctx, "media", "produce-media", ctx.code, "upload", UPLOAD_NOTE)
            if not _not_uploaded(ctx.course()) or _cannot(ctx, log, "media"):
                break
        left = _not_uploaded(ctx.course())
        if left:
            raise _stuck(ctx, "media_not_uploaded", log, why=_why(ctx, log, summary, "media"), assets=", ".join(a["id"] for a in left))
    elif not again and not (creator and _out_of_sync(ctx)):
        return
    ctx.mirror()
    for _ in range(ctx.rounds):
        _, log, summary = _agent(ctx, "assembly", "assemble", ctx.code, "assemble")
        if not creator or _in_sync(ctx) or _cannot(ctx, log, "assembly"):
            break
    if creator and not _in_sync(ctx):
        raise _stuck(ctx, "not_assembled", log, why=_why(ctx, log, summary, "assembly"))


CHECKS_NOTE = (
    "\n\nThe course is already assembled and recorded, so there is nothing to apply: `coursekit assemble diff` says `unchanged`. "
    "Do only the closing checks of the assembly skill (accessibility, text against the `.md`, snapshot, links and, when the review is "
    "already enabled, a new review version) for each unit, and then record each one with `coursekit assemble checked <CODE> --unit N`."
)


def _unchecked(ctx: Context) -> bool:
    """A unit assembled and recorded whose closing checks were not done on what is in creator now (an assembly that stopped before
    them, or one recorded by hand)."""
    course = ctx.course()
    for unit in course["units"]:
        plan, applied = assemblemod.paths(course["_dir"], unit["n"])
        if plan.exists() and applied.exists() and not assemblemod.unit_checked(course["_dir"], unit["n"]):
            return True
    return False


def _out_of_sync(ctx: Context) -> bool:
    """A unit whose last assembly recorded something different from its plan (an assembly that stopped before recording it)."""
    course = ctx.course()
    for unit in course["units"]:
        plan, applied = assemblemod.paths(course["_dir"], unit["n"])
        if plan.exists() and applied.exists() and not assemblemod.unit_in_sync(course["_dir"], unit["n"]):
            return True
    return False


def _in_sync(ctx: Context) -> bool:
    course = ctx.course()
    return all(assemblemod.unit_in_sync(course["_dir"], u["n"]) for u in course["units"])


def _produce(ctx: Context, course: dict) -> None:
    """The media agent produces the pending assets (with the theme defined first when they use it)."""
    pending = _pending_media(course)
    cfg = mediamod.config(course=course)
    needs_theme = any(a["type"] in (cfg.get("uses_theme") or []) for a in pending)
    if needs_theme and thememod.status(ctx.project, course).state != "derived":
        _agent(ctx, "design", "define-theme", "", "theme", theme_note(ctx.project, coursemod.backend(course)))
        if thememod.status(ctx.project, ctx.course()).state != "derived":
            raise _stuck(ctx, "theme_missing")
    log = None
    for _ in range(ctx.rounds):
        _, log, summary = _agent(ctx, "media", "produce-media", ctx.code, "media")
        pending = _pending_media(ctx.course())
        if not pending or _cannot(ctx, log, "media"):
            break
    if pending:
        raise _stuck(ctx, "media_pending", log, why=_why(ctx, log, summary, "media"), assets=", ".join(a["id"] for a in pending))


def _media(ctx: Context, course: dict) -> None:
    mediamod.extract(course)
    if _pending_media(course):
        _produce(ctx, course)
    ctx.mirror()
    log = None
    for _ in range(ctx.rounds):
        _, log, summary = _agent(ctx, "assembly", "assemble", ctx.code, "assemble")
        if ctx.course()["status"] != "media":
            return
        if _cannot(ctx, log, "assembly"):
            break
    raise _stuck(ctx, "not_assembled", log, why=_why(ctx, log, summary, "assembly"))


def _deliver(ctx: Context, course: dict) -> None:
    _refresh_media(ctx, course)
    log = None
    if coursemod.backend(course) == "creator" and _unchecked(ctx):
        for _ in range(ctx.rounds):
            _, log, summary = _agent(ctx, "assembly", "assemble", ctx.code, "checks", CHECKS_NOTE)
            if not _unchecked(ctx) or _cannot(ctx, log, "assembly"):
                break
        if _unchecked(ctx):
            raise _stuck(ctx, "not_checked", log, why=_why(ctx, log, summary, "assembly"))
    for _ in range(ctx.rounds):
        _, log, summary = _agent(ctx, "assembly", "deliver", ctx.code, "deliver")
        if ctx.course()["status"] == "delivered":
            return
        if _cannot(ctx, log, "assembly"):
            break
    raise _stuck(ctx, "not_delivered", log, why=_why(ctx, log, summary, "assembly"))


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
    # what the agents record by themselves (the history, the delivery) is signed by the handoff, not by whoever launched it
    launch.SESSION_ENV.update(COURSEKIT_USER_NAME=HANDOFF.name, COURSEKIT_USER_EMAIL=HANDOFF.email)
    try:
        return _run_stages(ctx)
    finally:
        launch.SESSION_ENV.clear()


def _run_stages(ctx: Context) -> dict:
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


def start(project: Project, title: str, hours: float, code: str | None, intro: bool, summary: bool, notes: str, rounds: int,
          log: Log, mirror: Callable[[str], None], pause: Callable[[Path], None] | None = None) -> dict:
    """Create the course, wait for the person to drop the reference material (`pause`), let the design agent propose it and
    take it to its delivery."""
    code = course_code(title, code)
    if (project.course_dir(code) / "course.yaml").exists():
        raise HandoffError(t("handoff", "course_exists", code=code))
    if (config.effective("delivery", project).value.get("client_review") or {}).get("required"):
        raise HandoffError(t("handoff", "client_review_required", code=code))
    log(t("handoff", "start_line", code=code, who=HANDOFF.name))
    folder = new.create(project, title, hours, code=code, intro=intro, summary=summary, notes=notes)
    log(t("commands", "new_created", path=folder.relative_to(project.root).as_posix(), hours=hours))
    mirror(code)
    if pause:
        pause(folder)
    return proceed(Context(project, code, rounds, log, lambda: mirror(code)))  # the design agent proposes the course first


def reopen(project: Project, code: str, rounds: int, log: Log, mirror: Callable[[str], None]) -> dict:
    """A delivered course goes back to the status its units imply after the content was edited (every unit is verified again:
    those that changed fall back and are reviewed, signed and assembled again) and carries on to the next version."""
    course = coursemod.load(project, code)
    if course["status"] != "delivered":
        raise HandoffError(t("handoff", "not_delivered_to_reopen", code=course["code"], status=course["status"]))
    problem = coursemod.approval_problem(course)
    if problem:
        raise HandoffError(f"{course['code']}: {problem}")
    for unit in course.get("units") or []:
        verify.update_status(course, unit, verify.verify_unit(course, unit))
    course = coursemod.load(project, code)
    status = derive_course_status(course.get("units") or [], "media")
    path = course["_dir"] / "course.yaml"
    ry, data = edit_yaml(path)
    data["status"] = status
    data.setdefault("history", []).append(history_entry(status, "Reopened for a new version", HANDOFF.name))
    save_yaml(ry, data, path)
    log(t("handoff", "reopen_line", code=course["code"], status=status, who=HANDOFF.name))
    mirror(course["code"])
    return proceed(Context(project, course["code"], rounds, log, lambda: mirror(course["code"])))


def resume(project: Project, code: str, rounds: int, log: Log, mirror: Callable[[str], None]) -> dict:
    course = coursemod.load(project, code)
    log(t("handoff", "resume_line", code=course["code"], status=course["status"], who=HANDOFF.name))
    return proceed(Context(project, course["code"], rounds, log, lambda: mirror(course["code"])))
