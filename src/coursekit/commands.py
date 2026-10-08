"""Course commands: new, status, sync, outline, verify, reviewed, approve, brief, rules."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from coursekit import agents as agentsmod
from coursekit import approve, config, directives, doctor, envfile, launch, mediatools, new, outline, status, verify, voices
from coursekit import assemble as assemblemod
from coursekit import brief as briefmod
from coursekit import course as coursemod
from coursekit import media as mediamod
from coursekit import setup as setupmod
from coursekit.lang import format_number
from coursekit.project import Project, find_project
from coursekit.sync import sync


def _project() -> Project:
    project = find_project()
    envfile.load(project.env_file)
    return project


def cmd_new(args: argparse.Namespace) -> int:
    project = _project()
    folder = new.create(
        project, args.title, args.hours, code=args.code, intro=not args.no_intro, summary=not args.no_summary,
        notes=args.notes, language=args.language,
    )
    print(f"created {folder.relative_to(project.root).as_posix()} ({args.hours} h)")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    project = _project()
    print(status.detail(coursemod.load(project, args.code)) if args.code else status.overview(project))
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    course = coursemod.load(_project(), args.code)
    result = sync(course, check_only=args.check)
    for warning in result.warnings:
        print(f"WARNING {warning}")
    lang = coursemod.language(course)
    words = sum(s["min_words"] for u in result.units for s in u["sections"])
    sections = sum(len(u["sections"]) for u in result.units)
    print(f"{len(result.units)} units, {sections} sections, {format_number(words, lang)} minimum words"
          + ("" if args.check else " · synced into course.yaml"))
    for path in result.written:
        print(f"  written: {path}")
    return 0


def cmd_outline(args: argparse.Namespace) -> int:
    course = coursemod.load(_project(), args.code)
    try:
        print(outline.section(course, args.section) if args.section else outline.outline(course))
    except ValueError as exc:
        print(f"coursekit: {exc}", file=sys.stderr)
        return 2
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    course = coursemod.load(_project(), args.code)
    problem = coursemod.approval_problem(course)
    if problem:
        print(f"ERROR   {course['code']}: {problem}")
        return 1
    units = [u for u in course.get("units") or [] if args.unit is None or u["n"] == args.unit]
    if not units:
        print(f"coursekit: no units in course.yaml{f' with n={args.unit}' if args.unit else ''}", file=sys.stderr)
        return 1
    fmt = lambda n: format_number(n, coursemod.language(course))  # noqa: E731
    failed = False
    for unit in units:
        report = verify.verify_unit(course, unit)
        s = report.summary
        print(f"\n[{'FAIL' if report.errors else 'OK'}] {course['code']} · U{unit['n']} — {unit.get('title', '')}")
        if s:
            print(f"  words {fmt(s['words'])}/{fmt(s['min_words'])} · placeholders {s['placeholders']} "
                  f"({s['placeholder_types']} types) · formative questions {s['formative_questions']} · "
                  f"bank questions {s['bank_questions']}")
        for msg in report.errors:
            print(f"  ERROR   {msg}")
        for msg in report.warnings:
            print(f"  WARNING {msg}")
        failed = failed or bool(report.errors)
        if not args.no_update:
            for note in verify.update_status(course, unit, report):
                print(f"  {note}")
    return 1 if failed else 0


def cmd_reviewed(args: argparse.Namespace) -> int:
    course = coursemod.load(_project(), args.code)
    print(approve.mark_reviewed(course, args.unit))
    return 0


def _confirm(yes: bool):
    def ask(question: str) -> bool:
        print(question)
        if yes:
            print("→ confirmed with --yes")
            return True
        while True:
            answer = input("[y/N] ").strip().lower()
            if answer in ("y", "yes", "s", "si", "sí"):
                return True
            if answer in ("", "n", "no"):
                return False

    return ask


def cmd_approve(args: argparse.Namespace) -> int:
    if not args.yes and not sys.stdin.isatty():
        print("coursekit: no interactive terminal. Sign in your own terminal, or from the agent chat with\n"
              "  `! coursekit approve … --yes` (the `!` runs it as you, not as the agent)", file=sys.stderr)
        return 1
    course = coursemod.load(_project(), args.code)
    confirm = _confirm(args.yes)
    if args.gate == "design":
        print(approve.approve_design(course, confirm, do_commit=not args.no_commit))
    else:
        if args.unit is None:
            print("coursekit: content approvals need --unit N", file=sys.stderr)
            return 2
        print(approve.approve_content(course, args.unit, confirm, do_commit=not args.no_commit))
    return 0


def cmd_brief(args: argparse.Namespace) -> int:
    project = _project()
    log = lambda m: print(m, flush=True)  # noqa: E731
    general = project.brief_dir
    if args.code:
        course = coursemod.load(project, args.code)
        new.ensure_brief(course["_dir"])
        if (general / "links.md").exists() or (general / "sources").exists():
            briefmod.build(general, project.root.name, args.refresh, log=log)
        rel = "../../../brief/index.md" if (general / "index.md").exists() else None
        summary = briefmod.build(course["_dir"] / "brief", course["code"], args.refresh, general=rel, log=log)
        target = f"{course['code']}/brief/index.md"
    else:
        summary = briefmod.build(general, project.root.name, args.refresh, log=log)
        target = "brief/index.md"
    print(f"brief: {summary['documents']} documents, {summary['webs']} webs, {summary['media']} images/audio/video → {target}")
    for source, note in summary["notes"]:
        print(f"  warning: {source}: {note}")
    return 1 if summary["failed"] else 0


def _launch_report(result: launch.UnitResult, project: Project) -> None:
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if result.summary:
        print(result.summary)
    if result.log:
        print(f"unit {result.n}: {result.status} · session in {result.log.relative_to(project.root).as_posix()}"
              + (f" · exit {result.exit_code}" if result.exit_code else ""))


def cmd_unit_agent(args: argparse.Namespace) -> int:
    role = "writer" if args.command == "write" else "reviewer"
    if role == "writer" and (args.full or args.parts):
        print("coursekit: --full and --parts are for review", file=sys.stderr)
        return 2
    project = _project()
    course = coursemod.load(project, args.code)
    agent = launch.agent_for(role, args.agent, args.model)
    units = [args.n] if args.n else launch.units_to_do(course, role)
    if not units:
        print(f"nothing to {args.command} in {course['code']}")
        return 0
    for n in units:
        print(f"{args.command} {course['code']} · unit {n} with {agent.label}" + (" (headless)" if args.headless else ""),
              flush=True)
        result = launch.run_unit(project, args.code, role, n, agent, args.headless, args.full, args.parts)
        _launch_report(result, project)
        failed = result.exit_code if not args.headless else (0 if launch.done(role, result.status) else (result.exit_code or 1))
        if failed:
            if len(units) > 1:
                print(f"stopped at unit {n}: fix it and launch the command again", file=sys.stderr)
            return failed
    return 0


RUN_FLAGS = {"--headless": False, "--agent": True, "--model": True, "--role": True}


def _split_run_arguments(args: argparse.Namespace) -> None:
    """coursekit's own options may come after the command name: take them out of its arguments."""
    rest, items = [], list(args.arguments)
    while items:
        item = items.pop(0)
        if item in RUN_FLAGS:
            if RUN_FLAGS[item]:
                setattr(args, item[2:], items.pop(0) if items else None)
            else:
                args.headless = True
        else:
            rest.append(item)
    args.arguments = rest
    if args.agent and args.agent not in launch.TOOLS:
        raise launch.LaunchError(f"--agent must be one of {', '.join(launch.TOOLS)}")
    if args.role and args.role not in agentsmod.ROLES:
        raise launch.LaunchError(f"--role must be one of {', '.join(agentsmod.ROLES)}")


def cmd_run(args: argparse.Namespace) -> int:
    _split_run_arguments(args)
    project = _project()
    role = args.role or launch.COMMAND_ROLE.get(args.name, "design")
    agent = launch.agent_for(role, args.agent, args.model)
    arguments = " ".join(args.arguments)
    print(f"/{args.name} {arguments} with the {role} agent ({agent.label})" + (" (headless)" if args.headless else ""), flush=True)
    text = launch.prompt(agent, args.name, arguments, args.headless)
    code, log, summary = launch.execute(project, agent, text, args.headless, f"{args.name}-{role}")
    if summary:
        print(summary)
    if log:
        print(f"session in {log.relative_to(project.root).as_posix()}" + (f" · exit {code}" if code else ""))
    return code


def cmd_roles(args: argparse.Namespace) -> int:
    _project()
    import shutil

    for role in agentsmod.ROLES:
        agent = launch.agent_for(role)
        missing = "" if shutil.which(agent.tool) else "  (not installed)"
        print(f"{role:<9} {agent.label}{missing}")
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    project = find_project()
    tty = sys.stdin.isatty() and not args.yes

    def ask(question: str, default: str) -> str:
        shown = f" ({default})" if default else ""
        return input(f"{question}{shown}: ").strip() or default

    def confirm(question: str) -> bool:
        return input(f"{question} [Y/n] ").strip().lower() in ("", "y", "yes", "s", "si", "sí")

    return setupmod.run(project, print, ask if tty else None, confirm if tty else None,
                        identity_only=args.identity, media=args.media, name=args.name, email=args.email)


def cmd_doctor(args: argparse.Namespace) -> int:
    project = _project()
    sections = doctor.collect(project)
    print(doctor.render(sections))
    return 0


def cmd_assemble(args: argparse.Namespace) -> int:
    import json

    course = coursemod.load(_project(), args.code)
    unit = next((u for u in course.get("units") or [] if u["n"] == args.unit), None)
    if unit is None:
        print(f"coursekit: unit {args.unit} not found", file=sys.stderr)
        return 1
    if args.action == "plan":
        plan, errors, warnings, counts = assemblemod.write_plan(course, unit)
        for w in warnings:
            print(f"WARNING {w}")
        for e in errors:
            print(f"ERROR   {e}")
        if plan is None:
            return 1
        print(f"plan assembly/unit-{args.unit:02d}.plan.json: {len(plan['lessons'])} lessons, {sum(counts.values())} bricks "
              f"({', '.join(f'{k} {v}' for k, v in counts.items())})")
        return 0
    if args.action == "diff":
        print(json.dumps(assemblemod.diff(course, unit), indent=1, ensure_ascii=False))
        return 0
    if args.action == "link":
        if not args.content_id:
            print("coursekit: link needs --content-id", file=sys.stderr)
            return 2
        print(assemblemod.link(course, unit, args.content_id))
        return 0
    if args.content:
        print(assemblemod.record_content_title(course, unit))
        return 0
    if not (args.lesson and args.lesson_id):
        print("coursekit: applied needs --lesson and --lesson-id (or --content)", file=sys.stderr)
        return 2
    print(assemblemod.record_lesson(course, unit, args.lesson, args.lesson_id, [b for b in args.brick_ids.split(",") if b]))
    return 0


def cmd_directives(args: argparse.Namespace) -> int:
    project = _project()
    registry = config.effective("directives", project).value
    new_lines, removed, total = directives.check(registry, Path(args.file))
    for line in [*new_lines, *removed]:
        print(line)
    if not new_lines and not removed:
        print(f"ok: the directive registry matches creator ({total} bricks)")
        return 0
    return 1


def cmd_media(args: argparse.Namespace) -> int:
    project = _project()
    if args.action == "providers":
        print("\n".join(mediamod.providers(project)))
        return 0
    if not args.code:
        print("coursekit: this action needs a course code", file=sys.stderr)
        return 2
    course = coursemod.load(project, args.code)
    if args.action == "extract":
        counts = mediamod.extract(course)
        print(f"manifest: {sum(counts.values())} assets ({', '.join(f'{k} {v}' for k, v in counts.items())})")
        return 0
    if args.action == "plan":
        warnings, lines = mediamod.plan(course)
        for w in warnings:
            print(f"WARNING {w}")
        print("\n".join(lines) if lines else "nothing to produce")
        return 0
    if not args.id:
        print("coursekit: set needs an asset id", file=sys.stderr)
        return 2
    values = {k: getattr(args, k) for k in ("status", "recipe", "asset_path", "file", "alt", "transcript", "subtitles_path",
                                            "made_with", "download", "download_title", "download_asset_path")}
    print(mediamod.set_asset(course, args.id, **values))
    return 0


def cmd_voice(args: argparse.Namespace) -> int:
    project = _project()
    course = coursemod.load(project, args.code) if args.code else None
    if args.action == "list":
        print("\n".join(voices.listing(course)))
        return 0
    if not (course and args.provider):
        print("coursekit: voice set needs CODE and PROVIDER", file=sys.stderr)
        return 2
    message, warning = voices.set_voice(course, args.provider, args.voice, args.speaker)
    if warning:
        print(f"warning: {warning}", file=sys.stderr)
    print(message)
    return 0


def cmd_tts(args: argparse.Namespace) -> int:
    project = _project()
    course = coursemod.load(project, args.course) if args.course else None
    print(mediatools.tts(course, args.engine, Path(args.input), Path(args.out), args.voice, args.speaker))
    return 0


def cmd_subtitles(args: argparse.Namespace) -> int:
    project = _project()
    language = coursemod.language(coursemod.load(project, args.course)) if args.course else args.language
    mediatools.subtitles(Path(args.audio), Path(args.text), Path(args.out), args.model, language)
    print(f"wrote {args.out}")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("new", help="create a course from its title and hours")
    p.add_argument("title")
    p.add_argument("hours", type=float)
    p.add_argument("--code", help="course code (default: from the title)")
    p.add_argument("--language", help="course language (default: project.yaml › content_language)")
    p.add_argument("--no-intro", action="store_true", help="units without the opening introduction section")
    p.add_argument("--no-summary", action="store_true", help="units without the closing summary section")
    p.add_argument("--notes", default="", help="extra instructions for the instructional design")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("status", help="state of every course, or the detail and next step of one")
    p.add_argument("code", nargs="?")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("sync", help="write units and sections from the approved design (design/matrix.json)")
    p.add_argument("code")
    p.add_argument("--check", action="store_true", help="only report what would be synced")
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("outline", help="compact map of a course, or the text of one section")
    p.add_argument("code")
    p.add_argument("--section", help="U.S: print only that section's text")
    p.set_defaults(func=cmd_outline)

    p = sub.add_parser("verify", help="check the content against the production rules")
    p.add_argument("code")
    p.add_argument("--unit", type=int)
    p.add_argument("--no-update", action="store_true", help="do not update unit and course status")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("reviewed", help="mark a unit as AI-reviewed (used by the review agent)")
    p.add_argument("code")
    p.add_argument("unit", type=int)
    p.set_defaults(func=cmd_reviewed)

    p = sub.add_parser("approve", help="sign off the design or a unit (people only, never an agent)")
    p.add_argument("gate", choices=("design", "content"))
    p.add_argument("code")
    p.add_argument("--unit", type=int, help="unit number (content gate)")
    p.add_argument("--yes", action="store_true", help="confirm without a prompt (for `!` in an agent chat)")
    p.add_argument("--no-commit", action="store_true", help="record the approval without committing")
    p.set_defaults(func=cmd_approve)

    for name, help_text in (("write", "write units with the writer agent (WRITER_AGENT / WRITER_MODEL)"),
                            ("review", "AI review of units with the reviewer agent (REVIEWER_AGENT / REVIEWER_MODEL)")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("code")
        p.add_argument("n", type=int, nargs="?", help="unit number (default: every unit still to do)")
        p.add_argument("--headless", action="store_true", help="run without the tool's interface (logs in .cache/logs/)")
        p.add_argument("--full", action="store_true", help="review: the whole unit, even if it was reviewed before")
        p.add_argument("--parts", help='review: only these parts, e.g. "section 4, activity 1.2"')
        p.add_argument("--agent", choices=launch.TOOLS, help="tool for this launch (overrides .env)")
        p.add_argument("--model", help="model for this launch (overrides .env)")
        p.set_defaults(func=cmd_unit_agent)

    p = sub.add_parser("run", help="launch a command (/new-course, /assemble…) with the agent of its role")
    p.add_argument("name", help="command name, e.g. new-course, design-change, assemble, deliver")
    p.add_argument("arguments", nargs=argparse.REMAINDER)
    p.add_argument("--role", choices=agentsmod.ROLES, help="role whose agent runs it (default: from the command)")
    p.add_argument("--headless", action="store_true")
    p.add_argument("--agent", choices=launch.TOOLS)
    p.add_argument("--model")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("assemble", help="plan, diff and record the assembly of a unit in creator")
    p.add_argument("action", choices=("plan", "diff", "applied", "link"))
    p.add_argument("code")
    p.add_argument("--unit", type=int, required=True)
    p.add_argument("--lesson")
    p.add_argument("--lesson-id")
    p.add_argument("--brick-ids", default="")
    p.add_argument("--content", action="store_true", help="applied: record the content title as renamed")
    p.add_argument("--content-id")
    p.set_defaults(func=cmd_assemble)

    p = sub.add_parser("directives", help="compare the directive registry with the creator catalog")
    p.add_argument("action", choices=("check",))
    p.add_argument("file", help="JSON saved from list_brick_types")
    p.set_defaults(func=cmd_directives)

    p = sub.add_parser("media", help="media manifest of a course and how to produce each asset")
    p.add_argument("action", choices=("extract", "plan", "providers", "set"))
    p.add_argument("code", nargs="?")
    p.add_argument("id", nargs="?")
    for key in ("status", "recipe", "asset-path", "file", "alt", "transcript", "subtitles-path", "made-with",
                "download", "download-title", "download-asset-path"):
        p.add_argument(f"--{key}")
    p.set_defaults(func=cmd_media)

    p = sub.add_parser("voice", help="voice providers available here, and the one voice of a course")
    p.add_argument("action", choices=("list", "set"))
    p.add_argument("code", nargs="?")
    p.add_argument("provider", nargs="?", choices=tuple(voices.PROVIDERS))
    p.add_argument("--voice")
    p.add_argument("--speaker")
    p.set_defaults(func=cmd_voice)

    p = sub.add_parser("tts", help="voice-over of a script with the course voice")
    p.add_argument("--course", help="use the voice of this course (course.yaml › media.voice)")
    p.add_argument("--engine", choices=tuple(voices.PROVIDERS))
    p.add_argument("--in", dest="input", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--voice")
    p.add_argument("--speaker", help="speaker of multi-speaker Piper voices")
    p.set_defaults(func=cmd_tts)

    p = sub.add_parser("subtitles", help="captions (VTT) aligning a script with its audio")
    p.add_argument("--audio", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--course", help="the course language")
    p.add_argument("--language", default="es")
    p.add_argument("--model", default="base")
    p.set_defaults(func=cmd_subtitles)

    p = sub.add_parser("setup", help="prepare this machine for the project (identity, .env, hooks, agents, network)")
    p.add_argument("--identity", action="store_true", help="only set or change the signing identity")
    p.add_argument("--media", action="store_true", help="also install the media production tools")
    p.add_argument("--name", help="signing name (without asking)")
    p.add_argument("--email", help="signing email (without asking)")
    p.add_argument("--yes", "-y", action="store_true", help="do not ask")
    p.set_defaults(func=cmd_setup)

    p = sub.add_parser("doctor", help="what is installed and configured here for the project")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("roles", help="tool and model of each role")
    p.set_defaults(func=cmd_roles)

    p = sub.add_parser("brief", help="convert the reference material of a course (or of the project) for the agents")
    p.add_argument("code", nargs="?", help="course code (default: the project brief/)")
    p.add_argument("--refresh", action="store_true", help="download the URLs of links.md again")
    p.set_defaults(func=cmd_brief)


ERRORS = (coursemod.CourseNotFound, approve.ApprovalError, FileExistsError, launch.LaunchError,
          assemblemod.AssembleError, directives.CatalogError, mediamod.MediaError, voices.VoiceError, mediatools.ToolError)
