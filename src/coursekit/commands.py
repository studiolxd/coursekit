"""Course commands: new, status, sync, outline, verify, reviewed, approve, brief, rules."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from coursekit import agents as agentsmod
from coursekit import approve, clientreview, config, directives, doctor, envfile, launch, mediatools, new, outline, status, verify, voices
from coursekit import assemble as assemblemod
from coursekit import brief as briefmod
from coursekit import catalog as catalogmod
from coursekit import course as coursemod
from coursekit import delivery as deliverymod
from coursekit import handoff as handoffmod
from coursekit import init as initmod
from coursekit import media as mediamod
from coursekit import publish as publishmod
from coursekit import setup as setupmod
from coursekit import states as statesmod
from coursekit import theme as thememod
from coursekit.htmlkit.build import HtmlBuildError
from coursekit.i18n import t, tn
from coursekit.lang import format_number
from coursekit.project import Project, find_project
from coursekit.sync import sync


def _project() -> Project:
    project = find_project()
    envfile.load(project.env_file)
    return project


def _local_catalog(project: Project) -> Path:
    return project.root / "courses" / catalogmod.file_name(project)


def _mirror(project: Project, code: str) -> None:
    """Bring the catalog of the project and the mirror folder up to date after a command that changed the course.

    The catalog in `courses/` is always written, silently. Nothing else happens when the project has no mirror; a
    catalog or a mirror that cannot be written is a warning, never a failure of the command that already did its work.
    """
    try:
        catalogmod.build(project, _local_catalog(project))
    except OSError as exc:
        print(t("commands", "catalog_not_updated", text=exc), file=sys.stderr)
    try:
        for line in publishmod.publish(project, code, only_if_configured=True):
            print(line)
    except (publishmod.PublishError, OSError) as exc:
        print(t("commands", "mirror_not_updated", text=exc), file=sys.stderr)


def cmd_new(args: argparse.Namespace) -> int:
    project = _project()
    folder = new.create(
        project, args.title, args.hours, code=args.code, intro=not args.no_intro, summary=not args.no_summary,
        notes=args.notes, language=args.language,
    )
    print(t("commands", "new_created", path=folder.relative_to(project.root).as_posix(), hours=args.hours))
    _mirror(project, folder.name)
    return 0


def _pause_for_material(project: Project, folder: Path) -> None:
    """The course folders exist: wait while the person drops the reference material, then the process goes on by itself."""
    rel = lambda path: path.relative_to(project.root).as_posix()  # noqa: E731
    brief = folder / "brief"
    print(t("commands", "handoff_pause", code=folder.name, sources=rel(brief / "sources"), links=rel(brief / "links.md"),
            notes=rel(brief / "notes.md"), general=rel(project.brief_dir)))
    if thememod.needs_branding(project):  # the look comes from brand material that is not there yet
        html = (config.project_data(project).get("assembly") or {}).get("backend") == "html"
        key = "handoff_pause_branding_html" if html else "handoff_pause_branding"
        print(t("commands", key, branding=rel(thememod.branding_dir(project))))
    initmod.ask(t("commands", "handoff_pause_wait"), "")


def cmd_handoff(args: argparse.Namespace) -> int:
    project = _project()
    rounds = args.rounds or handoffmod.rounds_setting(project)
    log = lambda message: print(message, flush=True)  # noqa: E731
    mirror = lambda code: _mirror(project, code)  # noqa: E731
    starting = args.hours is not None
    code = handoffmod.course_code(args.target, args.code) if starting else args.target.upper()
    pause = None if args.no_pause or not sys.stdin.isatty() else lambda folder: _pause_for_material(project, folder)
    try:
        if starting:
            course = handoffmod.start(project, args.target, args.hours, args.code, not args.no_intro, not args.no_summary, args.notes,
                                      rounds, log, mirror, pause)
        else:
            if args.no_intro or args.no_summary or args.notes or args.code or args.no_pause:
                print(t("commands", "handoff_resume_options"), file=sys.stderr)
                return 2
            course = handoffmod.resume(project, args.target, rounds, log, mirror)
    except handoffmod.HandoffError as exc:
        print(t("handoff", "stopped", code=code, reason=exc), file=sys.stderr)
        return 1
    print(t("handoff", "done", code=course["code"], who=handoffmod.HANDOFF.name))
    print(status.detail(course))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    project = _project()
    print(status.detail(coursemod.load(project, args.code)) if args.code else status.overview(project))
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    course = coursemod.load(_project(), args.code)
    if not args.check:
        statesmod.ensure_active(course)
    result = sync(course, check_only=args.check)
    for warning in result.warnings:
        print(t("commands", "warning_line", text=warning))
    lang = coursemod.language(course)
    words = sum(s["min_words"] for u in result.units for s in u["sections"])
    sections = sum(len(u["sections"]) for u in result.units)
    summary = "sync_summary" if args.check else "sync_summary_synced"
    print(t("commands", summary, units=tn("commands", "n_units", len(result.units)), sections=tn("commands", "n_sections", sections),
            words=format_number(words, lang)))
    for path in result.written:
        print(t("commands", "sync_written", path=path))
    if not args.check:
        _mirror(course["_project"], course["code"])
    return 0


def cmd_outline(args: argparse.Namespace) -> int:
    course = coursemod.load(_project(), args.code)
    try:
        print(outline.section(course, args.section) if args.section else outline.outline(course))
    except ValueError as exc:
        print(t("commands", "outline_error", error=exc), file=sys.stderr)
        return 2
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    course = coursemod.load(_project(), args.code)
    problem = coursemod.approval_problem(course)
    if problem:
        print(t("commands", "error_line", text=f"{course['code']}: {problem}"))
        return 1
    units = [u for u in course.get("units") or [] if args.unit is None or u["n"] == args.unit]
    if not units:
        message = t("commands", "no_units_n", n=args.unit) if args.unit else t("commands", "no_units")
        print(message, file=sys.stderr)
        return 1
    fmt = lambda n: format_number(n, coursemod.language(course))  # noqa: E731
    failed = False
    for unit in units:
        report = verify.verify_unit(course, unit)
        s = report.summary
        header = "verify_header_fail" if report.errors else "verify_header_ok"
        print("\n" + t("commands", header, code=course["code"], n=unit["n"], title=unit.get("title", "")))
        if s:
            print(t("commands", "verify_stats", words=fmt(s["words"]), min_words=fmt(s["min_words"]),
                    placeholders=s["placeholders"], types=s["placeholder_types"], formative=s["formative_questions"],
                    bank=s["bank_questions"]))
        for msg in report.errors:
            print("  " + t("commands", "error_line", text=msg))
        for msg in report.warnings:
            print("  " + t("commands", "warning_line", text=msg))
        failed = failed or bool(report.errors)
        if not args.no_update:
            for note in verify.update_status(course, unit, report):
                print(f"  {note}")
    if not args.no_update:
        _mirror(course["_project"], course["code"])
    return 1 if failed else 0


def cmd_reviewed(args: argparse.Namespace) -> int:
    course = coursemod.load(_project(), args.code)
    statesmod.ensure_active(course)
    if (args.note or args.report) and not args.by:
        print(t("commands", "reviewed_needs_by"), file=sys.stderr)
        return 2
    print(approve.mark_reviewed(course, args.unit, args.by, args.note, args.report))
    _mirror(course["_project"], course["code"])
    return 0


def _confirm(yes: bool):
    def ask(question: str) -> bool:
        print(question)
        if yes:
            print(t("commands", "confirmed_yes"))
            return True
        while True:
            answer = input(t("commands", "confirm_prompt")).strip().lower()
            if answer in ("y", "yes", "s", "si", "sí"):
                return True
            if answer in ("", "n", "no"):
                return False

    return ask


def cmd_approve(args: argparse.Namespace) -> int:
    if not args.yes and not sys.stdin.isatty():
        print(t("commands", "approve_no_terminal"), file=sys.stderr)
        return 1
    course = coursemod.load(_project(), args.code)
    statesmod.ensure_active(course)
    confirm = _confirm(args.yes)
    if args.gate == "design":
        print(approve.approve_design(course, confirm, do_commit=not args.no_commit))
    else:
        if args.unit is None:
            print(t("commands", "approve_needs_unit"), file=sys.stderr)
            return 2
        print(approve.approve_content(course, args.unit, confirm, do_commit=not args.no_commit, force=args.force))
    _mirror(course["_project"], course["code"])
    return 0


def cmd_brief(args: argparse.Namespace) -> int:
    project = _project()
    log = lambda m: print(m, flush=True)  # noqa: E731
    general = project.brief_dir
    project_language = str(config.project_data(project).get("content_language") or "es")
    if args.code:
        course = coursemod.load(project, args.code)
        new.ensure_brief(course["_dir"])
        if (general / "links.md").exists() or (general / "sources").exists():
            briefmod.build(general, project.root.name, args.refresh, log=log, language=project_language)
        rel = "../../../brief/index.md" if (general / "index.md").exists() else None
        summary = briefmod.build(course["_dir"] / "brief", course["code"], args.refresh, general=rel, log=log,
                                 language=coursemod.language(course))
        target = f"{course['code']}/brief/index.md"
    else:
        summary = briefmod.build(general, project.root.name, args.refresh, log=log, language=project_language)
        target = "brief/index.md"
    print(t("commands", "brief_summary", documents=summary["documents"], webs=summary["webs"], media=summary["media"], target=target))
    for source, note in summary["notes"]:
        print(t("commands", "brief_note", source=source, note=note))
    return 1 if summary["failed"] else 0


def _launch_report(result: launch.UnitResult, project: Project) -> None:
    for warning in result.warnings:
        print(t("commands", "launch_warning", warning=warning), file=sys.stderr)
    if result.summary:
        print(result.summary)
    if result.log:
        key = "launch_unit_log_exit" if result.exit_code else "launch_unit_log"
        print(t("commands", key, n=result.n, status=result.status, path=result.log.relative_to(project.root).as_posix(),
                code=result.exit_code))


def cmd_unit_agent(args: argparse.Namespace) -> int:
    role = "writer" if args.command == "write" else "reviewer"
    full, parts = getattr(args, "full", False), getattr(args, "parts", None)
    project = _project()
    course = coursemod.load(project, args.code)
    statesmod.ensure_active(course)
    agent = launch.agent_for(role, args.agent, args.model)
    units = [args.n] if args.n else launch.units_to_do(course, role)
    if not units:
        print(t("commands", "nothing_to_write" if role == "writer" else "nothing_to_review", code=course["code"]))
        return 0
    for n in units:
        key = "unit_start_headless" if args.headless else "unit_start"
        print(t("commands", key, command=args.command, code=course["code"], n=n, label=agent.label), flush=True)
        result = launch.run_unit(project, args.code, role, n, agent, args.headless, full, parts)
        _launch_report(result, project)
        failed = result.exit_code if not args.headless else (0 if launch.done(role, result.status) else (result.exit_code or 1))
        if failed:
            if len(units) > 1:
                print(t("commands", "stopped_at_unit", n=n), file=sys.stderr)
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
        raise launch.LaunchError(t("commands", "bad_agent", options=", ".join(launch.TOOLS)))
    if args.role and args.role not in agentsmod.ROLES:
        raise launch.LaunchError(t("commands", "bad_role", options=", ".join(agentsmod.ROLES)))


def cmd_run(args: argparse.Namespace) -> int:
    _split_run_arguments(args)
    project = _project()
    if args.name in launch.COMMAND_ROLE and args.name not in ("new-course", "course-status"):
        code = next((a for a in args.arguments if not a.startswith("-")), None)  # the course the command works on
        if code and (project.course_dir(code) / "course.yaml").exists():
            statesmod.ensure_active(coursemod.load(project, code))  # a course on hold does not start an agent session
    role = args.role or launch.COMMAND_ROLE.get(args.name, "design")
    agent = launch.agent_for(role, args.agent, args.model)
    # the shell took the quotes off: put them back around what has spaces, as the commands expect (`"<title>" <hours>`)
    arguments = " ".join(f'"{a}"' if any(c.isspace() for c in a) and a[0] not in "\"'" else a for a in args.arguments)
    key = "run_start_headless" if args.headless else "run_start"
    print(t("commands", key, name=args.name, arguments=arguments, role=role, label=agent.label), flush=True)
    text = launch.prompt(agent, args.name, arguments, args.headless)
    code, log, summary = launch.execute(project, agent, text, args.headless, f"{args.name}-{role}")
    if summary:
        print(summary)
    if log:
        print(t("commands", "run_session_exit" if code else "run_session", path=log.relative_to(project.root).as_posix(), code=code))
    return code


def cmd_roles(args: argparse.Namespace) -> int:
    _project()
    import shutil

    for role in agentsmod.ROLES:
        agent = launch.agent_for(role)
        key = "role_line" if shutil.which(agent.tool) else "role_line_missing"
        print(t("commands", key, role=role, label=agent.label))
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    project = find_project()
    tty = sys.stdin.isatty() and not args.yes
    return setupmod.run(project, print, initmod.ask if tty else None, initmod.confirm if tty else None,
                        secret=initmod.ask_secret if tty else None, roles=args.roles,
                        identity_only=args.identity, media=args.media, name=args.name, email=args.email)


def cmd_doctor(args: argparse.Namespace) -> int:
    project = _project()
    sections = doctor.collect(project)
    print(doctor.render(sections))
    return 0


def cmd_assemble_build(course: dict, args: argparse.Namespace) -> int:
    from coursekit.htmlkit import build as htmlbuild

    if coursemod.backend(course) != "html":
        print(t("commands", "assemble_build_needs_html", code=course["code"], backend=coursemod.backend(course)), file=sys.stderr)
        return 1
    units = [u for u in course.get("units") or [] if args.unit is None or u["n"] == args.unit]
    if not units:
        print(t("commands", "unit_not_found", n=args.unit), file=sys.stderr)
        return 1
    for unit in units:
        result = htmlbuild.build(course, unit, args.version)
        for warning in result.warnings:
            print(t("commands", "warning_line", text=warning))
        print(t("htmlkit", "built", n=unit["n"], files=result.files, path=result.out_dir.relative_to(course["_project"].root).as_posix()))
        if result.package:
            print(t("htmlkit", "packaged", name=result.package.name, size=_size(result.package)))
        else:
            print(t("htmlkit", "preview", path=(result.out_dir / "index.html").relative_to(course["_project"].root).as_posix()))
    message = htmlbuild.mark_assembled(course)
    if message:
        print(message)
    _mirror(course["_project"], course["code"])
    return 0


def _size(path: Path) -> str:
    from coursekit import store

    return store.human(path.stat().st_size)


def cmd_assemble(args: argparse.Namespace) -> int:
    import json

    course = coursemod.load(_project(), args.code)
    statesmod.ensure_active(course)
    if args.action == "build":
        return cmd_assemble_build(course, args)
    if coursemod.backend(course) == "html":
        print(t("commands", "assemble_creator_only", code=course["code"], action=args.action), file=sys.stderr)
        return 1
    if args.unit is None:
        print(t("commands", "assemble_needs_unit", action=args.action), file=sys.stderr)
        return 2
    unit = next((u for u in course.get("units") or [] if u["n"] == args.unit), None)
    if unit is None:
        print(t("commands", "unit_not_found", n=args.unit), file=sys.stderr)
        return 1
    if args.action == "plan":
        plan, errors, warnings, counts = assemblemod.write_plan(course, unit)
        for w in warnings:
            print(t("commands", "warning_line", text=w))
        for e in errors:
            print(t("commands", "error_line", text=e))
        if plan is None:
            return 1
        print(t("commands", "assemble_plan", path=f"assembly/unit-{args.unit:02d}.plan.json", lessons=len(plan["lessons"]),
                bricks=sum(counts.values()), detail=", ".join(f"{k} {v}" for k, v in counts.items())))
        return 0
    if args.action == "diff":
        print(json.dumps(assemblemod.diff(course, unit), indent=1, ensure_ascii=False))
        return 0
    if args.action == "link":
        if not (args.content_id or args.preview or args.review):
            print(t("commands", "link_needs_content_id"), file=sys.stderr)
            return 2
        print(assemblemod.link(course, unit, args.content_id, args.preview, args.review))
        _mirror(course["_project"], course["code"])
        return 0
    if args.content:
        print(assemblemod.record_content_title(course, unit))
        _mirror(course["_project"], course["code"])
        return 0
    if not (args.lesson and args.lesson_id):
        print(t("commands", "applied_needs_lesson"), file=sys.stderr)
        return 2
    print(assemblemod.record_lesson(course, unit, args.lesson, args.lesson_id, [b for b in args.brick_ids.split(",") if b]))
    _mirror(course["_project"], course["code"])
    return 0


def cmd_directives(args: argparse.Namespace) -> int:
    project = _project()
    registry = config.effective("directives", project).value
    new_lines, removed, total = directives.check(registry, Path(args.file))
    for line in [*new_lines, *removed]:
        print(line)
    if not new_lines and not removed:
        print(t("commands", "directives_ok", total=total))
        return 0
    return 1


def cmd_media(args: argparse.Namespace) -> int:
    project = _project()
    if args.action == "providers":
        print("\n".join(mediamod.providers(project)))
        return 0
    if not args.code:
        print(t("commands", "action_needs_course"), file=sys.stderr)
        return 2
    course = coursemod.load(project, args.code)
    if args.action == "extract":
        counts = mediamod.extract(course)
        print(t("commands", "media_manifest", total=sum(counts.values()), detail=", ".join(f"{k} {v}" for k, v in counts.items())))
        return 0
    if args.action == "plan":
        warnings, lines = mediamod.plan(course)
        for w in warnings:
            print(t("commands", "warning_line", text=w))
        print("\n".join(lines) if lines else t("commands", "media_nothing"))
        return 0
    if not args.id:
        print(t("commands", "media_set_needs_id"), file=sys.stderr)
        return 2
    statesmod.ensure_active(course)
    values = {k: getattr(args, k) for k in ("status", "recipe", "asset_path", "file", "alt", "transcript", "subtitles_path",
                                            "made_with", "download", "download_title", "download_asset_path", "force")}
    print(mediamod.set_asset(course, args.id, **values))
    _mirror(course["_project"], course["code"])
    return 0


def cmd_voice(args: argparse.Namespace) -> int:
    project = _project()
    course = coursemod.load(project, args.code) if args.code else None
    if args.action == "list":
        print("\n".join(voices.listing(course)))
        return 0
    if not (course and args.provider):
        print(t("commands", "voice_set_needs"), file=sys.stderr)
        return 2
    message, warning = voices.set_voice(course, args.provider, args.voice, args.speaker)
    if warning:
        print(t("commands", "voice_warning", warning=warning), file=sys.stderr)
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
    print(t("commands", "subtitles_wrote", path=args.out))
    return 0


def cmd_delivery(args: argparse.Namespace) -> int:
    course = coursemod.load(_project(), args.code)
    if args.action == "check":
        warning = deliverymod.check_ready(course)
        print(warning or t("commands", "delivery_ready", code=course["code"]))
        return 0
    if args.unit is None or not args.version:
        print(t("commands", "delivery_needs_unit_version", action=args.action), file=sys.stderr)
        return 2
    if args.action == "name":
        deliverymod.check_ready(course)
        print(deliverymod.expected_name(course, args.unit, args.version))
        return 0
    if args.action == "download":
        if not args.url:
            print(t("commands", "delivery_download_needs_url"), file=sys.stderr)
            return 2
        print(deliverymod.download(course, args.unit, args.version, args.url))
        return 0
    if not args.file:
        print(t("commands", "delivery_add_needs_file"), file=sys.stderr)
        return 2
    print(deliverymod.add(course, args.unit, args.version, args.file, args.job, args.snapshot))
    _mirror(course["_project"], course["code"])
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    project = _project()
    if args.check:
        print("\n".join(publishmod.check(project)))
        return 0
    output = _local_catalog(project)
    try:
        courses, units = catalogmod.build(project, output)
    except PermissionError as exc:
        raise publishmod.PublishError(t("publish", "cannot_replace", output=output)) from exc
    if not args.only_if_configured:
        print(t("commands", "catalog_wrote", path=output, courses=courses, units=units))
    for line in publishmod.publish(project, args.code, args.only_if_configured):
        print(line)
    return 0


def cmd_hold(args: argparse.Namespace) -> int:
    course = coursemod.load(_project(), args.code)
    previous = statesmod.hold(course["_dir"], args.reason)
    print(t("commands", "hold_done", code=course["code"], previous=previous))
    _mirror(course["_project"], course["code"])
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    course = coursemod.load(_project(), args.code)
    previous, new = statesmod.resume(course["_dir"])
    print(t("commands", "resume_done", code=course["code"], previous=previous, new=new))
    _mirror(course["_project"], course["code"])
    return 0


def cmd_client(args: argparse.Namespace) -> int:
    course = coursemod.load(_project(), args.code)
    if args.action == "send":
        print(clientreview.send(course, args.to, args.where))
    elif args.action == "changes":
        print(clientreview.changes(course, args.note))
    elif args.action == "approve":
        if not args.by:
            print(t("clientreview", "needs_by"), file=sys.stderr)
            return 2
        print(clientreview.approve(course, args.by, args.note))
    else:
        if not args.reason:
            print(t("clientreview", "needs_reason"), file=sys.stderr)
            return 2
        print(clientreview.skip(course, args.reason))
    _mirror(course["_project"], course["code"])
    return 0


def cmd_catalog(args: argparse.Namespace) -> int:
    project = _project()
    output = Path(args.output) if args.output else _local_catalog(project)
    courses, units = catalogmod.build(project, output)
    print(t("commands", "catalog_wrote", path=output, courses=courses, units=units))
    return 0


def _print_contrast(tokens: dict) -> bool:
    results = thememod.check(tokens)
    for ok, line in results:
        print(t("commands", "theme_check_ok" if ok else "theme_check_fail", line=line))
    return all(ok for ok, _ in results)


def cmd_theme(args: argparse.Namespace) -> int:
    project = _project()
    if args.action == "show" and args.file and not args.course:
        args.course = args.file  # `theme show PWD` is `theme show --course PWD`
    course = coursemod.load(project, args.course) if args.course else None
    rel = lambda path: path.relative_to(project.root).as_posix()  # noqa: E731
    if args.action == "tokens":
        print(t("commands", "theme_wrote", path=rel(thememod.write_css(project, course))))
        return 0
    if args.action == "import":
        project_backend = (config.project_data(project).get("assembly") or {}).get("backend") or "creator"
        backend = coursemod.backend(course) if course else project_backend
        if not args.file and backend != "html":
            print(t("commands", "theme_import_needs_file"), file=sys.stderr)
            return 2
        path, tokens = thememod.import_creator(project, course, Path(args.file) if args.file else None)
        origin = tokens["origin"]
        if origin["source"] == "css":
            print(t("commands", "theme_imported_css", path=rel(path), file=origin["file"]))
        else:
            print(t("commands", "theme_imported", path=rel(path), name=origin.get("name") or "-", theme_id=origin.get("theme_id") or "-"))
        for note in origin["notes"]:
            print(t("commands", "warning_line", text=note))
        if not _print_contrast(tokens):
            print(t("commands", "theme_contrast_hint_css" if origin["source"] == "css" else "theme_contrast_hint"))
        return 0
    if args.action == "show":
        found = thememod.status(project, course)
        print(t("commands", "theme_scope_course" if found.scope == "course" else "theme_scope_project", path=rel(found.path)))
        if found.state == "missing":
            print(t("commands", "theme_missing", path=rel(found.path)))
        elif found.state == "manual":
            print(t("commands", "theme_manual"))
        elif found.origin.get("source") == "css":
            o = found.origin
            print(t("commands", "theme_origin_css", file=o.get("file") or "-", digest=o.get("sha256") or "-",
                    date=str(o.get("imported_at") or "")[:10]))
        else:
            o = found.origin
            print(t("commands", "theme_origin", name=o.get("name") or "-", theme_id=o.get("theme_id") or "-",
                    version=o.get("version") or "-", date=str(o.get("imported_at") or "")[:10]))
        return 0
    return 0 if _print_contrast(thememod.load(project, course)) else 1


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("new", help=t("commands", "help_new"))
    p.add_argument("title")
    p.add_argument("hours", type=float)
    p.add_argument("--code", help=t("commands", "help_new_code"))
    p.add_argument("--language", help=t("commands", "help_new_language"))
    p.add_argument("--no-intro", action="store_true", help=t("commands", "help_new_no_intro"))
    p.add_argument("--no-summary", action="store_true", help=t("commands", "help_new_no_summary"))
    p.add_argument("--notes", default="", help=t("commands", "help_new_notes"))
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("handoff", help=t("commands", "help_handoff"))
    p.add_argument("target", help=t("commands", "help_handoff_target"))
    p.add_argument("hours", nargs="?", type=float, help=t("commands", "help_handoff_hours"))
    p.add_argument("--code", help=t("commands", "help_new_code"))
    p.add_argument("--no-intro", action="store_true", help=t("commands", "help_new_no_intro"))
    p.add_argument("--no-summary", action="store_true", help=t("commands", "help_new_no_summary"))
    p.add_argument("--notes", default="", help=t("commands", "help_new_notes"))
    p.add_argument("--rounds", type=int, help=t("commands", "help_handoff_rounds"))
    p.add_argument("--no-pause", action="store_true", help=t("commands", "help_handoff_no_pause"))
    p.set_defaults(func=cmd_handoff)

    p = sub.add_parser("status", help=t("commands", "help_status"))
    p.add_argument("code", nargs="?")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("sync", help=t("commands", "help_sync"))
    p.add_argument("code")
    p.add_argument("--check", action="store_true", help=t("commands", "help_sync_check"))
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("outline", help=t("commands", "help_outline"))
    p.add_argument("code")
    p.add_argument("--section", help=t("commands", "help_outline_section"))
    p.set_defaults(func=cmd_outline)

    p = sub.add_parser("verify", help=t("commands", "help_verify"))
    p.add_argument("code")
    p.add_argument("--unit", type=int)
    p.add_argument("--no-update", action="store_true", help=t("commands", "help_verify_no_update"))
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("reviewed", help=t("commands", "help_reviewed"))
    p.add_argument("code")
    p.add_argument("unit", type=int)
    p.add_argument("--by", help=t("commands", "help_reviewed_by"))
    p.add_argument("--note", help=t("commands", "help_reviewed_note"))
    p.add_argument("--report", help=t("commands", "help_reviewed_report"))
    p.set_defaults(func=cmd_reviewed)

    p = sub.add_parser("approve", help=t("commands", "help_approve"))
    p.add_argument("gate", choices=("design", "content"))
    p.add_argument("code")
    p.add_argument("--unit", type=int, help=t("commands", "help_approve_unit"))
    p.add_argument("--yes", action="store_true", help=t("commands", "help_approve_yes"))
    p.add_argument("--no-commit", action="store_true", help=t("commands", "help_approve_no_commit"))
    p.add_argument("--force", action="store_true", help=t("commands", "help_approve_force"))
    p.set_defaults(func=cmd_approve)

    for name, help_text in (("write", t("commands", "help_write")), ("review", t("commands", "help_review"))):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("code")
        p.add_argument("n", type=int, nargs="?", help=t("commands", "help_unit_n"))
        p.add_argument("--headless", action="store_true", help=t("commands", "help_headless"))
        if name == "review":
            p.add_argument("--full", action="store_true", help=t("commands", "help_full"))
            p.add_argument("--parts", help=t("commands", "help_parts"))
        p.add_argument("--agent", choices=launch.TOOLS, help=t("commands", "help_agent_launch"))
        p.add_argument("--model", help=t("commands", "help_model_launch"))
        p.set_defaults(func=cmd_unit_agent)

    p = sub.add_parser("run", help=t("commands", "help_run"))
    p.add_argument("name", help=t("commands", "help_run_name"))
    p.add_argument("arguments", nargs=argparse.REMAINDER)
    p.add_argument("--role", choices=agentsmod.ROLES, help=t("commands", "help_run_role"))
    p.add_argument("--headless", action="store_true")
    p.add_argument("--agent", choices=launch.TOOLS)
    p.add_argument("--model")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("assemble", help=t("commands", "help_assemble"))
    p.add_argument("action", choices=("plan", "diff", "applied", "link", "build"), help=t("commands", "help_assemble_action"))
    p.add_argument("code")
    p.add_argument("--unit", type=int, help=t("commands", "help_assemble_unit"))
    p.add_argument("--version", help=t("commands", "help_assemble_version"))
    p.add_argument("--lesson")
    p.add_argument("--lesson-id")
    p.add_argument("--brick-ids", default="")
    p.add_argument("--content", action="store_true", help=t("commands", "help_assemble_content"))
    p.add_argument("--content-id")
    p.add_argument("--preview", help=t("commands", "help_assemble_preview"))
    p.add_argument("--review", help=t("commands", "help_assemble_review"))
    p.set_defaults(func=cmd_assemble)

    p = sub.add_parser("directives", help=t("commands", "help_directives"))
    p.add_argument("action", choices=("check",))
    p.add_argument("file", help=t("commands", "help_directives_file"))
    p.set_defaults(func=cmd_directives)

    p = sub.add_parser("media", help=t("commands", "help_media"))
    p.add_argument("action", choices=("extract", "plan", "providers", "set"))
    p.add_argument("code", nargs="?")
    p.add_argument("id", nargs="?")
    for key in ("status", "recipe", "asset-path", "file", "alt", "transcript", "subtitles-path", "made-with",
                "download", "download-title", "download-asset-path"):
        p.add_argument(f"--{key}")
    p.add_argument("--force", action="store_true", help=t("commands", "help_media_force"))
    p.set_defaults(func=cmd_media)

    p = sub.add_parser("voice", help=t("commands", "help_voice"))
    p.add_argument("action", choices=("list", "set"))
    p.add_argument("code", nargs="?")
    p.add_argument("provider", nargs="?", choices=tuple(voices.PROVIDERS))
    p.add_argument("--voice")
    p.add_argument("--speaker")
    p.set_defaults(func=cmd_voice)

    p = sub.add_parser("tts", help=t("commands", "help_tts"))
    p.add_argument("--course", help=t("commands", "help_tts_course"))
    p.add_argument("--engine", choices=tuple(voices.PROVIDERS))
    p.add_argument("--in", dest="input", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--voice")
    p.add_argument("--speaker", help=t("commands", "help_tts_speaker"))
    p.set_defaults(func=cmd_tts)

    p = sub.add_parser("subtitles", help=t("commands", "help_subtitles"))
    p.add_argument("--audio", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--course", help=t("commands", "help_subtitles_course"))
    p.add_argument("--language", default="es")
    p.add_argument("--model", default="base")
    p.set_defaults(func=cmd_subtitles)

    p = sub.add_parser("delivery", help=t("commands", "help_delivery"))
    p.add_argument("action", choices=("add", "name", "check", "download"))
    p.add_argument("code")
    p.add_argument("--unit", type=int)
    p.add_argument("--url", help=t("commands", "help_delivery_url"))
    p.add_argument("--version")
    p.add_argument("--file")
    p.add_argument("--job")
    p.add_argument("--snapshot")
    p.set_defaults(func=cmd_delivery)

    p = sub.add_parser("hold", help=t("commands", "help_hold"))
    p.add_argument("code")
    p.add_argument("--reason", required=True, help=t("commands", "help_hold_reason"))
    p.set_defaults(func=cmd_hold)

    p = sub.add_parser("resume", help=t("commands", "help_resume"))
    p.add_argument("code")
    p.set_defaults(func=cmd_resume)

    p = sub.add_parser("client", help=t("commands", "help_client"))
    p.add_argument("code")
    p.add_argument("action", choices=("send", "changes", "approve", "skip"), help=t("commands", "help_client_action"))
    p.add_argument("--to", help=t("commands", "help_client_to"))
    p.add_argument("--where", help=t("commands", "help_client_where"))
    p.add_argument("--by", help=t("commands", "help_client_by"))
    p.add_argument("--note", help=t("commands", "help_client_note"))
    p.add_argument("--reason", help=t("commands", "help_client_reason"))
    p.set_defaults(func=cmd_client)

    p = sub.add_parser("publish", help=t("commands", "help_publish"))
    p.add_argument("code", nargs="?")
    p.add_argument("--check", action="store_true", help=t("commands", "help_publish_check"))
    p.add_argument("--only-if-configured", action="store_true", help=t("commands", "help_publish_only"))
    p.set_defaults(func=cmd_publish)

    p = sub.add_parser("catalog", help=t("commands", "help_catalog"))
    p.add_argument("--output")
    p.set_defaults(func=cmd_catalog)

    p = sub.add_parser("theme", help=t("commands", "help_theme"))
    p.add_argument("action", choices=("tokens", "check", "import", "show"), help=t("commands", "help_theme_action"))
    p.add_argument("file", nargs="?", help=t("commands", "help_theme_file"))
    p.add_argument("--course", help=t("commands", "help_theme_course"))
    p.set_defaults(func=cmd_theme)

    p = sub.add_parser("setup", help=t("setup", "help_setup"))
    p.add_argument("--identity", action="store_true", help=t("setup", "help_identity"))
    p.add_argument("--media", action="store_true", help=t("setup", "help_media"))
    p.add_argument("--roles", action="store_true", help=t("setup", "help_roles"))
    p.add_argument("--name", help=t("setup", "help_name"))
    p.add_argument("--email", help=t("setup", "help_email"))
    p.add_argument("--yes", "-y", action="store_true", help=t("setup", "help_yes"))
    p.set_defaults(func=cmd_setup)

    p = sub.add_parser("doctor", help=t("commands", "help_doctor"))
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("roles", help=t("commands", "help_roles"))
    p.set_defaults(func=cmd_roles)

    p = sub.add_parser("brief", help=t("commands", "help_brief"))
    p.add_argument("code", nargs="?", help=t("commands", "help_brief_code"))
    p.add_argument("--refresh", action="store_true", help=t("commands", "help_brief_refresh"))
    p.set_defaults(func=cmd_brief)


ERRORS = (handoffmod.HandoffError, coursemod.CourseNotFound, coursemod.RuleError, approve.ApprovalError, FileExistsError,
          launch.LaunchError, assemblemod.AssembleError, directives.CatalogError, mediamod.MediaError, voices.VoiceError,
          mediatools.ToolError, deliverymod.DeliveryError, publishmod.PublishError, thememod.ThemeError, statesmod.StateError,
          clientreview.ClientReviewError, HtmlBuildError)
