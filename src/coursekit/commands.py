"""Course commands: new, status, sync, outline, verify, reviewed, approve, brief, rules."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from coursekit import agents as agentsmod
from coursekit import (
    approve,
    clientreview,
    config,
    directives,
    doctor,
    envfile,
    launch,
    localdesign,
    mediaaccess,
    mediacheck,
    mediatools,
    new,
    outline,
    questionbank,
    status,
    ttsbatch,
    verify,
    voices,
)
from coursekit import assemble as assemblemod
from coursekit import brief as briefmod
from coursekit import capture as capturemod
from coursekit import catalog as catalogmod
from coursekit import course as coursemod
from coursekit import delivery as deliverymod
from coursekit import handoff as handoffmod
from coursekit import importer as importermod
from coursekit import init as initmod
from coursekit import media as mediamod
from coursekit import publish as publishmod
from coursekit import research as researchmod
from coursekit import setup as setupmod
from coursekit import states as statesmod
from coursekit import theme as thememod
from coursekit import video as videomod
from coursekit import videos as videosmod
from coursekit.htmlkit.build import HtmlBuildError
from coursekit.i18n import t, tn
from coursekit.lang import format_number
from coursekit.project import Project, find_project
from coursekit.sync import load_graph, sync


def _project() -> Project:
    project = find_project()
    envfile.load(project.env_file)
    return project


def _local_catalog(project: Project) -> Path:
    return project.root / "courses" / catalogmod.file_name(project)


def _mirror(project: Project, code: str) -> None:
    """Bring the catalog of the project and the mirror folder up to date after a command that changed the course.

    The catalog in `courses/` is kept up to date, silently (and only written when its data changed). Nothing else happens when
    the project has no mirror; a catalog or a mirror that cannot be written is a warning, never a failure of the command that
    already did its work. The sessions of the agents without an interface (`COURSEKIT_MIRROR=deferred`) leave it to whoever
    started them, which does it once when the session ends instead of after every command the agent runs.
    """
    if os.environ.get("COURSEKIT_MIRROR") == "deferred":
        return
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
        notes=args.notes, language=args.language, approach=args.approach, design_tool=args.design_tool,
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


def _handoff_report(project, code: str, stopped: str | None, course: dict | None = None) -> None:
    """The decisions the design took with no one to ask, printed, and the report of the handoff; also when it stopped (once the
    course exists), so the person sees them before carrying on."""
    try:
        course = course or coursemod.load(project, code)
    except coursemod.CourseNotFound:
        return
    assumptions = handoffmod.design_assumptions(course)
    if assumptions:
        print(t("handoff", "assumptions_to_check", count=len(assumptions), path=handoffmod.NOTES.as_posix(),
                list="; ".join(assumptions)))
    report = handoffmod.write_report(course, stopped)
    if report:
        print(t("handoff", "report_written", path=report.relative_to(project.root).as_posix()))


def cmd_handoff(args: argparse.Namespace) -> int:
    project = _project()
    rounds = args.rounds or handoffmod.rounds_setting(project)
    log = lambda message: print(message, flush=True)  # noqa: E731
    mirror = lambda code: _mirror(project, code)  # noqa: E731
    starting = args.hours is not None
    if starting and args.new_version:
        print(t("commands", "handoff_new_version_options"), file=sys.stderr)
        return 2
    code = handoffmod.course_code(args.target, args.code) if starting else args.target.upper()
    pause = None if args.no_pause or not sys.stdin.isatty() else lambda folder: _pause_for_material(project, folder)
    other = starting and (project.course_dir(code) / "course.yaml").exists()  # a course this run did not start: refused, untouched
    try:
        if starting:
            course = handoffmod.start(project, args.target, args.hours, args.code, not args.no_intro, not args.no_summary, args.notes,
                                      rounds, log, mirror, pause, approach=args.approach)
        else:
            if args.no_intro or args.no_summary or args.notes or args.code or args.no_pause or args.approach:
                print(t("commands", "handoff_resume_options"), file=sys.stderr)
                return 2
            course = (handoffmod.reopen if args.new_version else handoffmod.resume)(project, args.target, rounds, log, mirror)
    except handoffmod.HandoffError as exc:
        print(t("handoff", "stopped", code=code, reason=exc), file=sys.stderr)
        if not other:
            _handoff_report(project, code, str(exc))
        return 1
    print(t("handoff", "done", code=course["code"], who=handoffmod.HANDOFF.name))
    recordings = handoffmod.awaiting_recordings(course)
    if recordings:
        items = "; ".join(f"{a['id']} ({a.get('title', '')}) → media/scripts/{a['id']}.md" for a in recordings)
        print(t("handoff", "recordings_needed", count=len(recordings), list=items))
    reviews = handoffmod.captures_to_review(course)
    if reviews:
        items = "; ".join(f"{a['id']} ({mediamod.capture_waiting(a)})" for a in reviews)
        print(t("handoff", "captures_to_review", count=len(reviews), code=course["code"], list=items))
    waiting = handoffmod.unchecked_videos(course)
    if waiting:
        names = "; ".join(f"{(v.get('channel') or {}).get('name') or '—'} · {v['url']}" for v in waiting)
        print(t("handoff", "videos_to_check", count=len(waiting), path=videosmod.REPORT, list=names))
    _handoff_report(project, code, None, course)
    print(status.detail(course))
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    project = _project()
    try:
        found = importermod.scan(Path(args.path))
        table = importermod.read_table(Path(args.hours_file)) if args.hours_file else {}
    except importermod.ImporterError as exc:
        print(t("commands", "error_line", text=exc), file=sys.stderr)
        return 1
    if not found.courses:
        print(t("importer", "no_courses", path=args.path), file=sys.stderr)
        return 1
    plan_path = Path(args.plan_file) if args.plan_file else project.root / importermod.PLAN_FILE
    plan = importermod.read_plan(plan_path)
    unmatched = importermod.resolve(found, plan, table, args.default_hours, args.hours, args.title, args.code)
    for name in found.empty:
        print(t("commands", "warning_line", text=t("importer", "empty_folder", name=name)))
    for name in unmatched:
        print(t("commands", "warning_line", text=t("importer", "table_unmatched", name=name)))
    if args.plan:
        importermod.write_plan(plan_path, found, plan)
        ready = sum(1 for c in found.courses if not c.problems)
        print(t("importer", "plan_written", path=plan_path.as_posix(), courses=len(found.courses), complete=ready))
        return 0
    done = skipped = blocked = 0
    rounds = args.rounds or handoffmod.rounds_setting(project)
    log = lambda m: print(m, flush=True)  # noqa: E731
    for item in found.courses:
        if (project.course_dir(item.code) / "course.yaml").exists():
            print(t("importer", "course_exists", folder=item.folder.name, code=item.code))
            skipped += 1
            continue
        if item.problems:
            print(t("importer", "skipped", folder=item.folder.name, reason="; ".join(item.problems)))
            skipped += 1
            blocked += 1
            continue
        folder = importermod.import_course(project, item, log)
        print(t("importer", "imported", folder=item.folder.name, code=folder.name, units=len(item.units), hours=item.hours))
        for text in item.notes:
            print(t("importer", "check_line", text=text))
        _mirror(project, folder.name)
        done += 1
        if args.handoff:
            try:
                handoffmod.resume(project, folder.name, rounds, log, lambda code: _mirror(project, code))
            except handoffmod.HandoffError as exc:
                print(t("handoff", "stopped", code=folder.name, reason=exc), file=sys.stderr)
    print(t("importer", "summary", done=done, skipped=skipped))
    return 1 if blocked and not done else 0


def cmd_videos(args: argparse.Namespace) -> int:
    project = _project()
    course = coursemod.load(project, args.code)
    statesmod.ensure_active(course)
    try:
        if args.action == "check":
            videosmod.check(course)
        else:
            if not args.url:
                print(t("videos", "need_url", action=args.action), file=sys.stderr)
                return 2
            if args.action == "propose":
                videosmod.propose(course, args.url, args.why or "", args.replaces, args.asset)
            else:
                entry = videosmod.decide(course, args.url, "approved" if args.action == "approve" else "rejected")
                print(t("videos", "decided", url=entry["url"], status=entry["status"]))
    except videosmod.VideoError as exc:
        print(t("commands", "error_line", text=exc), file=sys.stderr)
        return 1
    path = videosmod.report(course, coursemod.language(course))
    registered = videosmod.load(course["_dir"])
    counts = {s: sum(1 for v in registered if v.get("status") == s) for s in ("approved", "proposed", "pending", "rejected")}
    print(t("videos", "summary", path=path.relative_to(project.root).as_posix(), **counts))
    _mirror(project, course["code"])
    return 1 if counts["pending"] or counts["rejected"] else 0


def cmd_capture(args: argparse.Namespace) -> int:
    project = _project()
    try:
        if args.action == "serve":
            from coursekit import capture_session

            capture_session.serve(project)
            return 0
        if args.action == "profiles":
            entries = capturemod.profiles(project)
            for entry in entries:
                state = (t("capture", "no_login") if not entry["login"] else
                         t("capture", "session_since", at=entry["logged_in_at"]) if entry["logged_in_at"] else t("capture", "no_session"))
                if not entry["configured"]:
                    state += " · " + t("capture", "not_configured")
                print(t("capture", "profile_line", name=entry["name"], account=entry["account"] or "—",
                        url=entry["start_url"] or "—", state=state))
            if not entries:
                print(t("capture", "no_profiles"))
            return 0
        if not args.target:
            print(t("capture", "needs_target", action=args.action), file=sys.stderr)
            return 2
        if args.action == "login":
            print(t("capture", "login_open", name=args.target))
            meta = capturemod.login(project, args.target)
            print(t("capture", "login_done", name=args.target, at=meta["logged_in_at"]))
        elif args.action == "logout":
            done = capturemod.logout(project, args.target)
            print(t("capture", "logout_done" if done else "logout_none", name=args.target))
        elif args.action == "allow":
            if not args.mode:
                print(t("capture", "needs_mode"), file=sys.stderr)
                return 2
            course = coursemod.load(project, args.target)
            statesmod.ensure_active(course)
            grant = capturemod.allow(project, course, args.ids, args.mode, args.profile, args.window, args.minutes)
            print(t("capture", "allowed", code=grant["code"], mode=grant["mode"], what=grant["profile"] or grant["window"],
                    assets=", ".join(grant["assets"] or []) or t("capture", "every_interface_asset"),
                    until=grant["expires_at"]))
        elif args.action == "revoke":
            done = capturemod.revoke(project, args.target)
            print(t("capture", "revoked" if done else "revoke_none", code=args.target))
        else:
            if len(args.ids) != 1:
                print(t("capture", "needs_one_id", action=args.action), file=sys.stderr)
                return 2
            course = coursemod.load(project, args.target)
            asset_id = args.ids[0]
            if args.action == "redact":
                statesmod.ensure_active(course)
                result = capturemod.redact(project, course, asset_id, Path(args.file) if args.file else None)
                found = ", ".join(f"{kind} {n}" for kind, n in sorted(result["findings"].items())) or t("capture", "review_nothing")
                for warning in result["warnings"]:
                    print(t("commands", "warning_line", text=warning))
                print(t("capture", "redacted", id=asset_id, found=found, file=result["file"].relative_to(project.root).as_posix(),
                        review=result["review"].relative_to(project.root).as_posix()))
            elif args.action == "review":
                print(capturemod.review(course, asset_id).relative_to(project.root).as_posix())
            elif args.action == "replay":
                from coursekit import capture_replay

                statesmod.ensure_active(course)
                try:
                    result = capture_replay.replay(project, course["code"], asset_id)
                except capture_replay.ReplayError as exc:
                    raise capturemod.CaptureError(str(exc)) from None
                for warning in result["warnings"]:
                    print(t("commands", "warning_line", text=warning))
                made = [p.relative_to(project.root).as_posix() for p in ([result["video"]] if result["video"] else [])]
                made += [p.relative_to(project.root).as_posix() for p in result["shots"][-1:]]
                found = ", ".join(f"{kind} {n}" for kind, n in result["findings"].items()) or t("capture", "review_nothing")
                print(t("capture", "replayed", id=asset_id, files=", ".join(made), found=found,
                        review=result["review"].relative_to(project.root).as_posix()))
            else:
                state = capturemod.decide(project, course, asset_id, args.action == "approve", args.note, args.mask)
                print(t("capture", f"decided_{state['state']}", id=asset_id, code=course["code"]))
                _mirror(project, course["code"])
    except capturemod.CaptureError as exc:
        print(t("commands", "error_line", text=exc), file=sys.stderr)
        return 1
    return 0


def cmd_video(args: argparse.Namespace) -> int:
    project = _project()
    if args.code is None and args.action not in ("catalog", "gallery"):
        print(t("video", "needs_code", action=args.action), file=sys.stderr)
        return 2
    course = coursemod.load(project, args.code) if args.code else videomod.project_scope(project)
    root = project.root
    if args.action not in ("catalog", "gallery") and not args.id:
        print(t("video", "needs_id", action=args.action), file=sys.stderr)
        return 2
    try:
        if args.action == "catalog":
            print("\n".join(videomod.catalog(course)))
            return 0
        if args.action == "gallery" and args.serve:  # the live gallery, in the browser, until Ctrl+C
            code = args.code
            reload = (lambda: coursemod.load(project, code)) if code else (lambda: videomod.project_scope(project))
            return videomod.serve_gallery(videomod.live_gallery(course), args.port, not args.no_open, reload=reload)
        if args.action == "gallery":
            print(t("video", "gallery_done", path=videomod.gallery(course).relative_to(root).as_posix()))
            return 0
        if args.action == "check":
            findings = videomod.check(course, args.id)
            for f in findings:
                line = t("video", "finding", where=f.where, code=f.code, text=f.text)
                print(t("commands", "error_line" if f.level == "error" else "warning_line", text=line))
            if not findings:
                print(t("video", "check_ok", id=args.id))
            return 1 if any(f.level == "error" for f in findings) else 0
        if args.action == "new":
            path = videomod.new(course, args.id)
            print(t("video", "created", path=path.relative_to(root).as_posix()))
            return 0
        statesmod.ensure_active(course)
        if args.action == "voice":
            made = videomod.voice(course, args.id, batch=args.batch)
            print(t("video", "voice_queued_done" if args.batch else "voice_done", count=made))
        elif args.action == "preview":
            print(t("video", "preview", path=videomod.preview(course, args.id).relative_to(root).as_posix()))
        elif args.action == "export":
            done = videomod.export(course, args.id)
            print(t("video", "exported", path=done["folder"].relative_to(root).as_posix(), scenes=done["scenes"], layers=done["layers"],
                    voices=done["voices"]))
        elif args.action == "render":
            done = videomod.render(course, args.id)
            print(t("video", "rendered", path=done["video"].relative_to(root).as_posix(), seconds=f"{done['seconds']:.1f}",
                    scenes=done["scenes"]))
            _mirror(project, course["code"])
    except (videomod.VideoError, mediaaccess.AccessError, mediacheck.CheckError) as exc:
        print(t("commands", "error_line", text=exc), file=sys.stderr)
        return 1
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


def cmd_design(args: argparse.Namespace) -> int:
    course = coursemod.load(_project(), args.code)
    local = localdesign.is_local(course)
    if not local:  # designed in slxd: the review Excel, from the matrix.json and validation.json the design agent saved
        graph = load_graph(course["_dir"] / "design" / "matrix.json")
        stale = localdesign.validation_problem(course)
        if stale:  # the findings would be those of another version of the design
            print(t("commands", "error_line", text=stale), file=sys.stderr)
            return 1
        kinds = localdesign.keys(course, graph)[2]
        findings = localdesign.slxd_findings(course["_dir"] / "design" / "validation.json") + localdesign.key_findings(course, graph)
        findings = [f for f in findings if not localdesign.expected(f, kinds)]
        files = [] if args.check else [localdesign.review_excel(course)[1]]
    elif args.check:
        _, findings = localdesign.build(course)
    else:
        statesmod.ensure_active(course)
        findings, files = localdesign.export(course)
    for finding in findings:
        print(finding.line())
    errors = sum(1 for f in findings if f.severity == "error")
    print(t("design", "summary", errors=errors, warnings=len(findings) - errors) if findings else t("design", "ok"))
    if not args.check:
        print(t("design", "exported", files=", ".join(f.relative_to(course["_dir"]).as_posix() for f in files)))
        _mirror(course["_project"], course["code"])
    return 1 if errors else 0


def cmd_outline(args: argparse.Namespace) -> int:
    course = coursemod.load(_project(), args.code)
    try:
        print(outline.section(course, args.section) if args.section else outline.outline(course))
    except ValueError as exc:
        print(t("commands", "outline_error", error=exc), file=sys.stderr)
        return 2
    return 0


def cmd_paths(args: argparse.Namespace) -> int:
    from coursekit import paths

    project = _project()
    course = coursemod.load(project, args.code)
    units = [u for u in course.get("units") or [] if args.unit is None or u["n"] == args.unit]
    if not units:
        message = t("commands", "no_units_n", n=args.unit) if args.unit else t("commands", "no_units")
        print(message, file=sys.stderr)
        return 1
    failed = found = False
    for unit in units:
        result = paths.write(course, unit)
        if result.errors:
            failed = True
            print(t("paths", "unit_errors", n=unit["n"], code=course["code"]), file=sys.stderr)
            for error in result.errors:
                print(f"  {error}", file=sys.stderr)
        elif result.report:
            found = True
            print(t("paths", "unit_written", n=unit["n"], count=len(result.simulations),
                    path=result.report.relative_to(project.root).as_posix()))
    if not found and not failed:
        print(t("paths", "none", code=course["code"]))
    return 1 if failed else 0


def cmd_preview(args: argparse.Namespace) -> int:
    from coursekit import preview
    from coursekit.htmlkit import build as htmlbuild

    course = coursemod.load(_project(), args.code)
    if coursemod.backend(course) != "html":
        print(t("preview", "needs_html", code=course["code"], backend=coursemod.backend(course)), file=sys.stderr)
        return 1
    units = coursemod.package_units(course)
    if not units:
        print(t("commands", "no_units"), file=sys.stderr)
        return 1
    if args.unit is not None and not any(u["n"] == args.unit for u in units):
        print(t("commands", "unit_not_found", n=args.unit), file=sys.stderr)
        return 1
    first = args.unit if args.unit is not None else units[0]["n"]
    for unit in units:
        if (args.build and (args.unit is None or unit["n"] == args.unit)) or (unit["n"] == first and not preview.stamp(course, first)):
            print(t("preview", "building", n=unit["n"]))
            try:
                result = htmlbuild.build(course, unit, None)
            except htmlbuild.HtmlBuildError as exc:
                print(t("commands", "error_line", text=exc), file=sys.stderr)
                return 1
            for warning in result.warnings:
                print(t("commands", "warning_line", text=warning))
    return preview.run(course, units, first, args.port, not args.no_open)


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
    confirm = _confirm(args.yes)
    if args.code is None:
        if args.gate != "media-style":
            print(t("commands", "approve_needs_code"), file=sys.stderr)
            return 2
        print(approve.approve_project_media_style(_project(), confirm, do_commit=not args.no_commit))
        return 0
    course = coursemod.load(_project(), args.code)
    statesmod.ensure_active(course)
    if args.gate == "design":
        print(approve.approve_design(course, confirm, do_commit=not args.no_commit))
    elif args.gate == "style":
        print(approve.approve_style(course, confirm, do_commit=not args.no_commit))
    elif args.gate == "media-style":
        print(approve.approve_media_style(course, confirm, do_commit=not args.no_commit))
    elif args.gate == "script":
        if not args.asset:
            print(t("commands", "approve_needs_asset"), file=sys.stderr)
            return 2
        ids = list(dict.fromkeys(i.strip() for value in args.asset for i in value.split(",") if i.strip()))
        print(approve.approve_scripts(course, ids, confirm, do_commit=not args.no_commit))
    else:
        if args.unit is None:
            print(t("commands", "approve_needs_unit"), file=sys.stderr)
            return 2
        print(approve.approve_content(course, args.unit, confirm, do_commit=not args.no_commit, force=args.force))
    _mirror(course["_project"], course["code"])
    return 0


def cmd_brief_find(project: Project, args: argparse.Namespace) -> int:
    """The passages of the material (of the course and of the project) a query or a section of the design needs."""
    from coursekit import sources

    if not args.code:
        print(t("commands", "brief_find_needs_code"), file=sys.stderr)
        return 2
    course = coursemod.load(project, args.code)
    cfg = coursemod.rules(course).get("brief") or {}
    if args.section:
        found = sources.section_query(course, args.section)
        if found is None:
            print(t("commands", "brief_section_not_found", section=args.section, code=course["code"]), file=sys.stderr)
            return 1
        query, label = found
    else:
        query, label = args.find, args.find
    words = sources.stopwords(coursemod.language(course))
    files = sources.text_files(course["_dir"] / "brief", project.brief_dir)
    if not files:
        print(t("commands", "brief_find_no_text", code=course["code"]), file=sys.stderr)
        return 1
    found = sources.passages(files, int(cfg.get("passage_words") or 200), words)
    best = sources.rank(found, query, words, int(args.top or cfg.get("passages") or 8))
    print(t("commands", "brief_find_title", query=label, count=len(best), total=len(found)))
    for i, (_score, passage) in enumerate(best, 1):
        where = f"{passage.file.relative_to(project.root).as_posix()}:{passage.start}-{passage.end}"
        heading = f" · {passage.heading}" if passage.heading else ""
        print(f"\n## {i} · {where}{heading}\n\n{passage.text}")
    if not best:
        print(t("commands", "brief_find_nothing"))
    return 0


def cmd_brief(args: argparse.Namespace) -> int:
    project = _project()
    if args.find or args.section:
        return cmd_brief_find(project, args)
    log = lambda m: print(m, flush=True)  # noqa: E731
    general = project.brief_dir
    project_language = str(config.project_data(project).get("content_language") or "es")
    importing = config.effective("import", project).value
    if args.code:
        course = coursemod.load(project, args.code)
        new.ensure_brief(course["_dir"])
        new.ensure_decisions(course["_dir"])  # the courses made before it had one
        if (general / "links.md").exists() or (general / "sources").exists():
            briefmod.build(general, project.root.name, args.refresh, log=log, language=project_language, importing=importing)
        rel = "../../../brief/index.md" if (general / "index.md").exists() else None
        summary = briefmod.build(course["_dir"] / "brief", course["code"], args.refresh, general=rel, log=log,
                                 language=coursemod.language(course), importing=config.effective("import", project, course).value,
                                 forbidden=config.effective("rules", project, course).value.get("forbidden"))
        target = f"{course['code']}/brief/index.md"
    else:
        summary = briefmod.build(general, project.root.name, args.refresh, log=log, language=project_language, importing=importing)
        target = "brief/index.md"
    print(t("commands", "brief_summary", documents=summary["documents"], webs=summary["webs"], media=summary["media"], target=target))
    for source, note in summary["notes"]:
        print(t("commands", "brief_note", source=source, note=note))
    return 1 if summary["failed"] else 0


def cmd_research(args: argparse.Namespace) -> int:
    """Official sources through the search API of the `.env`; without one, the agent uses its own web search."""
    project = _project()
    course = coursemod.load(project, args.code)
    if args.status:
        for line in researchmod.status(course):
            print(line)
        return 0
    if not args.query:
        print(t("commands", "research_needs_query"), file=sys.stderr)
        return 2
    statesmod.ensure_active(course)
    try:
        found = researchmod.search(course, args.query, fact=args.fact)
    except researchmod.NoProvider as exc:
        print(exc, file=sys.stderr)
        return researchmod.NO_PROVIDER
    print(found.as_json() if args.json else researchmod.render(found, coursemod.language(course)))
    if found.warning:
        print(found.warning, file=sys.stderr)
    return 0


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
        _mirror(project, course["code"])  # the session itself did not (`COURSEKIT_MIRROR=deferred`)
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
    worked_on = None
    if args.name in launch.COMMAND_ROLE and args.name not in ("new-course", "course-status"):
        first = next((a for a in args.arguments if a.strip() and not a.startswith("-")), None)
        code = first.split()[0].strip("\"'") if first else None  # the course the command works on (all may come in one string)
        if code and (project.course_dir(code) / "course.yaml").exists():
            statesmod.ensure_active(coursemod.load(project, code))  # a course on hold does not start an agent session
            worked_on = code
    role = args.role or launch.COMMAND_ROLE.get(args.name, "design")
    agent = launch.agent_for(role, args.agent, args.model)
    # the shell took the quotes off: put them back around what has spaces, as the commands expect (`"<title>" <hours>`)
    arguments = " ".join(f'"{a}"' if any(c.isspace() for c in a) and a[0] not in "\"'" else a for a in args.arguments)
    key = "run_start_headless" if args.headless else "run_start"
    print(t("commands", key, name=args.name, arguments=arguments, role=role, label=agent.label), flush=True)
    text = launch.prompt(agent, args.name, arguments, args.headless)
    code, log, summary = launch.execute(project, agent, text, args.headless, f"{args.name}-{role}")
    if worked_on:
        _mirror(project, worked_on)  # the session itself did not (`COURSEKIT_MIRROR=deferred`)
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
    units = [u for u in coursemod.package_units(course) if args.unit is None or u["n"] == args.unit]
    if not units:
        print(t("commands", "unit_not_found", n=args.unit), file=sys.stderr)
        return 1
    failed = False
    for unit in units:
        result = htmlbuild.build(course, unit, args.version)
        for warning in result.warnings:
            print(t("commands", "warning_line", text=warning))
        print(t("htmlkit", "built", n=unit["n"], files=result.files, path=result.out_dir.relative_to(course["_project"].root).as_posix()))
        if result.package and not args.no_check and not _print_check(course, unit, args.browser):
            result.package.unlink(missing_ok=True)
            print(t("playcheck", "not_delivered"), file=sys.stderr)
            failed = True
            continue
        if result.package:
            print(t("htmlkit", "packaged", name=result.package.name, size=_size(result.package)))
        else:
            index = (result.out_dir / "index.html").relative_to(course["_project"].root).as_posix()
            print(t("htmlkit", "preview", code=course["code"], path=index))
    message = htmlbuild.mark_assembled(course)
    if message:
        print(message)
    _mirror(course["_project"], course["code"])
    return 1 if failed else 0


def _print_check(course: dict, unit: dict, browser: str | None) -> bool:
    """`assemble check` of one built unit, printed; True when it has no errors."""
    from coursekit.htmlkit import playcheck

    result = playcheck.check(course, unit, browser)
    for warning in result.warnings:
        print(t("commands", "warning_line", text=warning))
    for error in result.errors:
        print(t("commands", "error_line", text=error))
    if result.played:
        print(t("playcheck", "summary", n=unit["n"], lessons=result.lessons, tests=result.tests, simulations=result.simulations,
                paths=result.paths, errors=len(result.errors), warnings=len(result.warnings)))
    else:
        print(t("playcheck", "files_only", n=unit["n"], errors=len(result.errors), warnings=len(result.warnings)))
    return not result.errors


def cmd_assemble_check(course: dict, args: argparse.Namespace) -> int:
    from coursekit import preview
    from coursekit.htmlkit import build as htmlbuild

    if coursemod.backend(course) != "html":
        print(t("commands", "assemble_build_needs_html", code=course["code"], backend=coursemod.backend(course)), file=sys.stderr)
        return 1
    units = [u for u in coursemod.package_units(course) if args.unit is None or u["n"] == args.unit]
    if not units:
        print(t("commands", "unit_not_found", n=args.unit), file=sys.stderr)
        return 1
    ok = True
    for unit in units:
        if not preview.stamp(course, unit["n"]):
            print(t("preview", "building", n=unit["n"]))
            htmlbuild.build(course, unit, None)
        ok = _print_check(course, unit, args.browser) and ok
    return 0 if ok else 1


def _size(path: Path) -> str:
    from coursekit import store

    return store.human(path.stat().st_size)


def cmd_assemble(args: argparse.Namespace) -> int:
    import json

    course = coursemod.load(_project(), args.code)
    statesmod.ensure_active(course)
    if args.action == "build":
        return cmd_assemble_build(course, args)
    if args.action == "check":
        return cmd_assemble_check(course, args)
    if coursemod.backend(course) == "html":
        print(t("commands", "assemble_creator_only", code=course["code"], action=args.action), file=sys.stderr)
        return 1
    if args.unit is None:
        print(t("commands", "assemble_needs_unit", action=args.action), file=sys.stderr)
        return 2
    unit = coursemod.package_unit(course, args.unit)
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
    if args.action == "checked":
        print(assemblemod.record_checked(course, unit))
        _mirror(course["_project"], course["code"])
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
    if not (args.lesson and (args.lesson_id or args.keep_ids)):
        print(t("commands", "applied_needs_lesson"), file=sys.stderr)
        return 2
    ids = args.brick_ids
    if args.brick_ids_file:
        ids = Path(args.brick_ids_file).read_text(encoding="utf-8")
    replace = dict(pair.split("=", 1) for pair in re.split(r"[,\s]+", args.replace_id or "") if "=" in pair)
    print(assemblemod.record_lesson(course, unit, args.lesson, args.lesson_id, [b for b in re.split(r"[,\s]+", ids) if b],
                                    args.keep_ids, replace))
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
    if args.action == "check":
        try:
            findings, fixed = mediacheck.check(course, [args.id, *args.more] if args.id else None, args.fix)
        except mediacheck.CheckError as exc:
            print(t("commands", "error_line", text=exc), file=sys.stderr)
            return 1
        for line in fixed:
            print(line)
        for f in findings:
            print(t("commands", "warning_line", text=t("mediacheck", "line", asset=f.asset, code=f.code, text=f.text)))
        if not findings:
            print(t("mediacheck", "none"))
        return 1 if findings else 0
    if args.action in ("sheet", "transcript"):
        if not args.id:
            print(t("commands", "media_set_needs_id"), file=sys.stderr)
            return 2
        try:
            if args.action == "sheet":
                out = mediacheck.sheet(course, args.id, args.frames)
                print(t("mediacheck", "sheet", path=out.relative_to(course["_project"].root).as_posix()))
            else:
                statesmod.ensure_active(course)
                done = mediaaccess.write(course, args.id)
                root = course["_project"].root
                print(t("mediaaccess", "written", id=args.id, transcript=done["transcript"].relative_to(root).as_posix(),
                        descriptions=done["descriptions"].relative_to(root).as_posix()))
                _mirror(course["_project"], course["code"])
        except (mediacheck.CheckError, mediaaccess.AccessError) as exc:
            print(t("commands", "error_line", text=exc), file=sys.stderr)
            return 1
        return 0
    if args.action == "stock":
        if not args.id or not (args.find or args.take):
            print(t("illustrations", "stock_needs"), file=sys.stderr)
            return 2
        print("\n".join(mediamod.stock(course, args.id, find=args.find, take=args.take, color=args.color)))
        return 0
    if args.action == "embed":
        if not args.id:
            print(t("commands", "media_set_needs_id"), file=sys.stderr)
            return 2
        print(mediamod.embed(course, args.id))
        return 0
    if args.action == "narrate":
        statesmod.ensure_active(course)
        try:
            count = mediamod.narrate(course, [args.id, *args.more] if args.id else None, args.all, batch=args.batch)
        except (mediamod.MediaError, mediatools.ToolError) as exc:
            print(t("commands", "error_line", text=exc), file=sys.stderr)
            return 1
        print(t("commands", "media_narration_queued" if args.batch else "media_narrated", count=count))
        _mirror(course["_project"], course["code"])
        return 0
    if args.action in ("fit", "render"):
        if not (args.id or args.file) or (args.action == "fit" and not args.size):
            print(t("commands", "media_fit_needs"), file=sys.stderr)
            return 2
        try:
            print(mediamod.image_tool(course, args.id, args.action, args.size, args.file))
        except (mediamod.MediaError, mediatools.ToolError) as exc:
            print(t("commands", "error_line", text=exc), file=sys.stderr)
            return 1
        return 0
    if args.action == "adopt":
        statesmod.ensure_active(course)
        if not (args.id and args.file):
            print(t("commands", "media_adopt_needs"), file=sys.stderr)
            return 2
        try:
            print(mediamod.adopt(course, args.id, args.file, args.alt))
        except mediamod.MediaError as exc:
            print(t("commands", "error_line", text=exc), file=sys.stderr)
            return 1
        _mirror(course["_project"], course["code"])
        return 0
    if args.action == "optimize":
        statesmod.ensure_active(course)
        try:
            lines = mediamod.optimize(course, [args.id, *args.more] if args.id else None)
        except (mediamod.MediaError, mediatools.ToolError) as exc:
            print(t("commands", "error_line", text=exc), file=sys.stderr)
            return 1
        print("\n".join(lines) if lines else t("commands", "media_optimize_none"))
        _mirror(course["_project"], course["code"])
        return 0
    if args.action == "redo":
        statesmod.ensure_active(course)
        chosen = mediamod.redo(course, [args.id, *args.more] if args.id else None, args.all, args.clean)
        print(t("commands", "media_redo", assets=", ".join(chosen)) if chosen else t("commands", "media_redo_none"))
        _mirror(course["_project"], course["code"])
        return 0
    if args.action == "upload":
        if not (args.file and args.url and args.content_type):
            print(t("commands", "media_upload_needs"), file=sys.stderr)
            return 2
        path = Path(args.file)
        for base in (course["_dir"], course["_project"].root):
            if not path.is_absolute() and (base / path).is_file():
                path = base / path
                break
        print(mediatools.upload(path, args.url, args.content_type, args.method))
        return 0
    if not args.id:
        print(t("commands", "media_set_needs_id"), file=sys.stderr)
        return 2
    statesmod.ensure_active(course)
    values = {k: getattr(args, k) for k in ("status", "recipe", "asset_path", "file", "alt", "transcript", "subtitles_path",
                                            "made_with", "download", "download_title", "download_asset_path", "force", "depicts")}
    print(mediamod.set_asset(course, args.id, **values))
    _mirror(course["_project"], course["code"])
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    project = _project()
    print(mediatools.download(args.url, Path(args.out), project.root))
    return 0


def cmd_voice(args: argparse.Namespace) -> int:
    project = _project()
    if args.code in voices.PROVIDERS and args.provider is None:  # `voice set gemini`: the voice of the project
        args.code, args.provider = None, args.code
    course = coursemod.load(project, args.code) if args.code else None
    if args.action == "list":
        print("\n".join(voices.listing(course, project)))
        return 0
    if args.action == "unset":
        print(voices.unset_voice(course, project))
        return 0
    if not args.provider or (course is None and args.character):
        print(t("commands", "voice_set_needs"), file=sys.stderr)
        return 2
    if course is None:
        message, warning = voices.set_project_voice(project, args.provider, args.voice, args.speaker)
    else:
        message, warning = voices.set_voice(course, args.provider, args.voice, args.speaker, args.character)
    if warning:
        print(t("commands", "voice_warning", warning=warning), file=sys.stderr)
    print(message)
    return 0


def cmd_tts(args: argparse.Namespace) -> int:
    project = _project()
    course = coursemod.load(project, args.course) if args.course else None
    if args.batch:
        if course is None or args.engine or args.voice or args.speaker:
            print(t("commands", "tts_batch_needs"), file=sys.stderr)
            return 2
        mediatools.require_file(Path(args.input))
        out = Path(args.out).resolve()
        try:
            out.relative_to(project.root.resolve())
        except ValueError:
            print(t("commands", "tts_batch_outside", path=Path(args.out).as_posix()), file=sys.stderr)
            return 2
        ident = out.relative_to(project.root.resolve()).as_posix()
        added = ttsbatch.add(course, "tts", ident, Path(args.input).read_text(encoding="utf-8"), out, character=args.character)
        print(t("commands", "tts_queued" if added else "tts_already_queued", path=ident, code=course["code"]))
        return 0
    print(mediatools.tts(course, args.engine, Path(args.input), Path(args.out), args.voice, args.speaker, args.character))
    return 0


def cmd_brand(args: argparse.Namespace) -> int:
    from coursekit import brand

    project = _project()
    course = coursemod.load(project, args.code) if args.code else None
    done = brand.build(project, course, args.refresh, log=print)
    rel = done["folder"].relative_to(project.root).as_posix()
    print(t("brand", "done", path=rel, documents=done["documents"], webs=done["webs"], observed=done["observed"],
            fonts=", ".join(done["fonts"]) or "—", logos=done["logos"], icons=done["icons"], index=f"{rel}/index.md"))
    if done["missing_fonts"]:
        print(t("brand", "done_missing_fonts", families=", ".join(done["missing_fonts"])))
    return 1 if done["failed"] else 0


def cmd_tts_batch(args: argparse.Namespace) -> int:
    course = coursemod.load(_project(), args.code)
    if args.action == "list":
        print("\n".join(ttsbatch.listing(course)))
        return 0
    if args.action == "send":
        done = ttsbatch.send(course)
        print(t("ttsbatch", "sent", job=done["job"], items=done["items"], requests=done["requests"]))
        if done["left"]:
            print(t("ttsbatch", "left_for_later", count=done["left"]))
        return 0
    if args.action == "status":
        done = ttsbatch.status(course)
        if not done["state"]:
            print(t("ttsbatch", "no_job_queued", code=course["code"], count=done["queued"]))
            return 0
        stats = ", ".join(f"{k} {v}" for k, v in done["stats"].items())
        print(t("ttsbatch", "status_line", job=done["job"], state=done["state"], stats=stats or "—"))
        return 0
    done = ttsbatch.collect(course)
    if done["state"] not in ttsbatch.FINISHED:
        print(t("ttsbatch", "still_waiting", state=done["state"], count=done["waiting"]))
        return 0
    print(t("ttsbatch", "collected", done=done["done"], failed=done["failed"], state=done["state"]))
    _mirror(course["_project"], course["code"])
    return 1 if done["failed"] else 0


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
    if args.action == "questions":
        if not args.version:
            print(t("commands", "delivery_needs_version", action=args.action), file=sys.stderr)
            return 2
        print(deliverymod.add_questions(course, args.version, args.url))
        _mirror(course["_project"], course["code"])
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
        courses, units, written = catalogmod.build(project, output)
    except PermissionError as exc:
        raise publishmod.PublishError(t("publish", "cannot_replace", output=output)) from exc
    if not args.only_if_configured:
        print(t("commands", "catalog_wrote" if written else "catalog_unchanged", path=output, courses=courses, units=units))
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
    courses, units, _ = catalogmod.build(project, output, force=True)  # asked for: always written
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
    if args.action == "roles":
        tokens = thememod.load(project, course)
        for row in thememod.roles(tokens):
            origin = t("theme", f"role_from_{row['from']}", ref=row["ref"] or "")
            print(t("theme", "role_line", role=row["role"], value=row["value"], name=f" ({row['palette']})" if row["palette"] else "",
                    origin=origin))
            print(t("theme", "role_seen", use=row["use"]))
        palette = tokens.get("palette") or {}
        if palette:
            print(t("theme", "roles_palette", palette=", ".join(f"{k} {v}" for k, v in palette.items())))
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
    p.add_argument("--approach", choices=new.APPROACHES, help=t("commands", "help_new_approach"))
    p.add_argument("--design-tool", choices=new.DESIGN_TOOLS, help=t("commands", "help_new_design_tool"))
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("import", help=t("commands", "help_import"))
    p.add_argument("path", help=t("commands", "help_import_path"))
    p.add_argument("--plan", action="store_true", help=t("commands", "help_import_plan"))
    p.add_argument("--plan-file", help=t("commands", "help_import_plan_file"))
    p.add_argument("--hours-file", help=t("commands", "help_import_hours_file"))
    p.add_argument("--default-hours", type=float, help=t("commands", "help_import_default_hours"))
    p.add_argument("--hours", type=float, help=t("commands", "help_import_hours"))
    p.add_argument("--title", help=t("commands", "help_import_title"))
    p.add_argument("--code", help=t("commands", "help_new_code"))
    p.add_argument("--handoff", action="store_true", help=t("commands", "help_import_handoff"))
    p.add_argument("--rounds", type=int, help=t("commands", "help_handoff_rounds"))
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("videos", help=t("commands", "help_videos"))
    p.add_argument("action", choices=("check", "propose", "approve", "reject"))
    p.add_argument("code")
    p.add_argument("url", nargs="?")
    p.add_argument("--why", help=t("commands", "help_videos_why"))
    p.add_argument("--replaces", help=t("commands", "help_videos_replaces"))
    p.add_argument("--for", dest="asset", metavar="ASSET", help=t("commands", "help_videos_for"))
    p.set_defaults(func=cmd_videos)

    p = sub.add_parser("handoff", help=t("commands", "help_handoff"))
    p.add_argument("target", help=t("commands", "help_handoff_target"))
    p.add_argument("hours", nargs="?", type=float, help=t("commands", "help_handoff_hours"))
    p.add_argument("--code", help=t("commands", "help_new_code"))
    p.add_argument("--no-intro", action="store_true", help=t("commands", "help_new_no_intro"))
    p.add_argument("--no-summary", action="store_true", help=t("commands", "help_new_no_summary"))
    p.add_argument("--notes", default="", help=t("commands", "help_new_notes"))
    p.add_argument("--approach", choices=new.APPROACHES, help=t("commands", "help_new_approach"))
    p.add_argument("--rounds", type=int, help=t("commands", "help_handoff_rounds"))
    p.add_argument("--no-pause", action="store_true", help=t("commands", "help_handoff_no_pause"))
    p.add_argument("--new-version", action="store_true", help=t("commands", "help_handoff_new_version"))
    p.set_defaults(func=cmd_handoff)

    p = sub.add_parser("status", help=t("commands", "help_status"))
    p.add_argument("code", nargs="?")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("sync", help=t("commands", "help_sync"))
    p.add_argument("code")
    p.add_argument("--check", action="store_true", help=t("commands", "help_sync_check"))
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("design", help=t("commands", "help_design"))
    p.add_argument("code")
    p.add_argument("--check", action="store_true", help=t("commands", "help_design_check"))
    p.set_defaults(func=cmd_design)

    p = sub.add_parser("outline", help=t("commands", "help_outline"))
    p.add_argument("code")
    p.add_argument("--section", help=t("commands", "help_outline_section"))
    p.set_defaults(func=cmd_outline)

    p = sub.add_parser("paths", help=t("commands", "help_paths"))
    p.add_argument("code")
    p.add_argument("--unit", type=int, help=t("commands", "help_paths_unit"))
    p.set_defaults(func=cmd_paths)

    p = sub.add_parser("preview", help=t("commands", "help_preview"))
    p.add_argument("code")
    p.add_argument("--unit", type=int, help=t("commands", "help_preview_unit"))
    p.add_argument("--build", action="store_true", help=t("commands", "help_preview_build"))
    p.add_argument("--port", type=int, default=8765, help=t("commands", "help_preview_port"))
    p.add_argument("--no-open", action="store_true", help=t("commands", "help_preview_no_open"))
    p.set_defaults(func=cmd_preview)

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
    p.add_argument("gate", choices=("design", "content", "style", "media-style", "script"))
    p.add_argument("code", nargs="?", help=t("commands", "help_approve_code"))
    p.add_argument("--unit", type=int, help=t("commands", "help_approve_unit"))
    p.add_argument("--asset", action="append", help=t("commands", "help_approve_asset"))
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
    p.add_argument("action", choices=("plan", "diff", "applied", "checked", "link", "build", "check"),
                   help=t("commands", "help_assemble_action"))
    p.add_argument("code")
    p.add_argument("--unit", type=int, help=t("commands", "help_assemble_unit"))
    p.add_argument("--version", help=t("commands", "help_assemble_version"))
    p.add_argument("--no-check", action="store_true", help=t("commands", "help_assemble_no_check"))
    p.add_argument("--browser", help=t("commands", "help_assemble_browser"))
    p.add_argument("--lesson")
    p.add_argument("--lesson-id")
    p.add_argument("--brick-ids", default="")
    p.add_argument("--brick-ids-file", help=t("commands", "help_assemble_brick_ids_file"))
    p.add_argument("--keep-ids", action="store_true", help=t("commands", "help_assemble_keep_ids"))
    p.add_argument("--replace-id", help=t("commands", "help_assemble_replace_id"))
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
    p.add_argument("action", choices=("extract", "plan", "providers", "set", "upload", "redo", "embed", "fit", "render", "narrate",
                                      "optimize", "adopt", "check", "sheet", "transcript", "stock"))
    p.add_argument("code", nargs="?")
    p.add_argument("id", nargs="?")
    p.add_argument("more", nargs="*", help=t("commands", "help_media_more"))
    p.add_argument("--url", help=t("commands", "help_media_url"))
    p.add_argument("--content-type", help=t("commands", "help_media_content_type"))
    p.add_argument("--method", default="PUT", help=t("commands", "help_media_method"))
    for key in ("status", "recipe", "asset-path", "file", "alt", "transcript", "subtitles-path", "made-with",
                "download", "download-title", "download-asset-path"):
        p.add_argument(f"--{key}")
    p.add_argument("--depicts", choices=("interface", "concept"), help=t("commands", "help_media_depicts"))
    p.add_argument("--force", action="store_true", help=t("commands", "help_media_force"))
    p.add_argument("--all", action="store_true", help=t("commands", "help_media_all"))
    p.add_argument("--clean", action="store_true", help=t("commands", "help_media_clean"))
    p.add_argument("--size", help=t("commands", "help_media_size"))
    p.add_argument("--fix", action="store_true", help=t("commands", "help_media_fix"))
    p.add_argument("--frames", type=int, help=t("commands", "help_media_frames"))
    p.add_argument("--batch", action="store_true", help=t("commands", "help_media_batch"))
    p.add_argument("--find", help=t("commands", "help_media_find"))
    p.add_argument("--take", type=int, help=t("commands", "help_media_take"))
    p.add_argument("--color", help=t("commands", "help_media_color"))
    p.set_defaults(func=cmd_media)

    p = sub.add_parser("video", help=t("commands", "help_video"))
    p.add_argument("action", choices=("new", "check", "voice", "preview", "render", "catalog", "gallery", "export"))
    p.add_argument("code", nargs="?", help=t("commands", "help_video_code"))
    p.add_argument("id", nargs="?")
    p.add_argument("--batch", action="store_true", help=t("commands", "help_video_batch"))
    p.add_argument("--serve", action="store_true", help=t("commands", "help_video_serve"))
    p.add_argument("--port", type=int, default=8766, help=t("commands", "help_video_port"))
    p.add_argument("--no-open", action="store_true", help=t("commands", "help_video_no_open"))
    p.set_defaults(func=cmd_video)

    p = sub.add_parser("capture", help=t("commands", "help_capture"))
    p.add_argument("action", choices=("login", "logout", "profiles", "allow", "revoke", "redact", "review", "approve", "reject",
                                      "serve", "replay"))
    p.add_argument("target", nargs="?", help=t("commands", "help_capture_target"))
    p.add_argument("ids", nargs="*", help=t("commands", "help_capture_ids"))
    p.add_argument("--mode", choices=capturemod.MODES, help=t("commands", "help_capture_mode"))
    p.add_argument("--profile", help=t("commands", "help_capture_profile"))
    p.add_argument("--window", help=t("commands", "help_capture_window"))
    p.add_argument("--minutes", type=float, help=t("commands", "help_capture_minutes"))
    p.add_argument("--file", help=t("commands", "help_capture_file"))
    p.add_argument("--note", help=t("commands", "help_capture_note"))
    p.add_argument("--mask", action="append", help=t("commands", "help_capture_mask"))
    p.set_defaults(func=cmd_capture)

    p = sub.add_parser("download", help=t("commands", "help_download"))
    p.add_argument("url", help=t("commands", "help_download_url"))
    p.add_argument("--out", required=True, help=t("commands", "help_download_out"))
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("voice", help=t("commands", "help_voice"))
    p.add_argument("action", choices=("list", "set", "unset"))
    p.add_argument("code", nargs="?", help=t("commands", "help_voice_code"))
    p.add_argument("provider", nargs="?", choices=tuple(voices.PROVIDERS))
    p.add_argument("--voice")
    p.add_argument("--speaker")
    p.add_argument("--character", help=t("commands", "help_voice_character"))
    p.set_defaults(func=cmd_voice)

    p = sub.add_parser("tts", help=t("commands", "help_tts"))
    p.add_argument("--course", help=t("commands", "help_tts_course"))
    p.add_argument("--engine", choices=tuple(voices.PROVIDERS))
    p.add_argument("--in", dest="input", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--voice")
    p.add_argument("--speaker", help=t("commands", "help_tts_speaker"))
    p.add_argument("--character", help=t("commands", "help_tts_character"))
    p.add_argument("--batch", action="store_true", help=t("commands", "help_tts_batch"))
    p.set_defaults(func=cmd_tts)

    p = sub.add_parser("brand", help=t("brand", "help"))
    p.add_argument("code", nargs="?", help=t("brand", "help_code"))
    p.add_argument("--refresh", action="store_true", help=t("brand", "help_refresh"))
    p.set_defaults(func=cmd_brand)

    p = sub.add_parser("tts-batch", help=t("commands", "help_tts_batch_command"))
    p.add_argument("action", choices=("list", "send", "status", "collect"))
    p.add_argument("code")
    p.set_defaults(func=cmd_tts_batch)

    p = sub.add_parser("subtitles", help=t("commands", "help_subtitles"))
    p.add_argument("--audio", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--course", help=t("commands", "help_subtitles_course"))
    p.add_argument("--language", default="es")
    p.add_argument("--model", default="base")
    p.set_defaults(func=cmd_subtitles)

    p = sub.add_parser("delivery", help=t("commands", "help_delivery"))
    p.add_argument("action", choices=("add", "name", "check", "download", "questions"))
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
    p.add_argument("action", choices=("tokens", "check", "import", "show", "roles"), help=t("commands", "help_theme_action"))
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
    p.add_argument("--find", help=t("commands", "help_brief_find"))
    p.add_argument("--section", help=t("commands", "help_brief_section"))
    p.add_argument("--top", type=int, help=t("commands", "help_brief_top"))
    p.set_defaults(func=cmd_brief)

    p = sub.add_parser("research", help=t("commands", "help_research"))
    p.add_argument("code")
    p.add_argument("query", nargs="?", help=t("commands", "help_research_query"))
    p.add_argument("--fact", action="store_true", help=t("commands", "help_research_fact"))
    p.add_argument("--json", action="store_true", help=t("commands", "help_research_json"))
    p.add_argument("--status", action="store_true", help=t("commands", "help_research_status"))
    p.set_defaults(func=cmd_research)


ERRORS = (handoffmod.HandoffError, coursemod.CourseNotFound, coursemod.RuleError, approve.ApprovalError, FileExistsError,
          launch.LaunchError, assemblemod.AssembleError, directives.CatalogError, mediamod.MediaError, voices.VoiceError,
          mediatools.ToolError, deliverymod.DeliveryError, publishmod.PublishError, thememod.ThemeError, statesmod.StateError,
          clientreview.ClientReviewError, HtmlBuildError, localdesign.DesignError, ttsbatch.BatchError,
          researchmod.ResearchError, questionbank.BankError)
