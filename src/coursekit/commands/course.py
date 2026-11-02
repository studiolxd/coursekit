"""The commands of a course: creating it, its design, its status, its checks, its sign-offs and its holds."""


from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from coursekit import (
    approve,
    clientreview,
    config,
    localdesign,
    new,
    outline,
    status,
    verify,
)
from coursekit import catalog as catalogmod
from coursekit import course as coursemod
from coursekit import handoff as handoffmod
from coursekit import importer as importermod
from coursekit import init as initmod
from coursekit import media as mediamod
from coursekit import publish as publishmod
from coursekit import states as statesmod
from coursekit import theme as thememod
from coursekit import videos as videosmod
from coursekit.commands import common
from coursekit.i18n import t, tn
from coursekit.lang import format_number
from coursekit.project import Project
from coursekit.sync import load_graph, sync


def cmd_new(args: argparse.Namespace) -> int:
    project = common.project()
    folder = new.create(
        project, args.title, args.hours, code=args.code, intro=not args.no_intro, summary=not args.no_summary,
        notes=args.notes, language=args.language, approach=args.approach, design_tool=args.design_tool,
    )
    print(t("commands", "new_created", path=folder.relative_to(project.root).as_posix(), hours=args.hours))
    common.mirror(project, folder.name)
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

def _handoff_report(project: Project, code: str, stopped: str | None, course: dict | None = None) -> None:
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
    project = common.project()
    rounds = args.rounds or handoffmod.rounds_setting(project)
    log = lambda message: print(message, flush=True)  # noqa: E731
    mirror = lambda code: common.mirror(project, code)  # noqa: E731
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
    capturable = {str(a["id"]) for a in handoffmod.capturable(course)}
    if capturable and course["status"] == "delivered":  # granted after the delivery: a new version records them
        print(t("handoff", "capturable_new_version", count=len(capturable), code=course["code"], list=", ".join(sorted(capturable))))
    recordings = [a for a in handoffmod.awaiting_recordings(course) if str(a["id"]) not in capturable]
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
    project = common.project()
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
        common.mirror(project, folder.name)
        done += 1
        if args.handoff:
            try:
                handoffmod.resume(project, folder.name, rounds, log, lambda code: common.mirror(project, code))
            except handoffmod.HandoffError as exc:
                print(t("handoff", "stopped", code=folder.name, reason=exc), file=sys.stderr)
    print(t("importer", "summary", done=done, skipped=skipped))
    return 1 if blocked and not done else 0

def cmd_status(args: argparse.Namespace) -> int:
    project = common.project()
    if getattr(args, "json", False):
        data = status.detail_data(coursemod.load(project, args.code)) if args.code else status.overview_data(project)
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
        return 0
    print(status.detail(coursemod.load(project, args.code)) if args.code else status.overview(project))
    return 0

def cmd_sync(args: argparse.Namespace) -> int:
    course = coursemod.load(common.project(), args.code)
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
        common.mirror(course["_project"], course["code"])
    return 0

def cmd_design(args: argparse.Namespace) -> int:
    course = coursemod.load(common.project(), args.code)
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
        common.mirror(course["_project"], course["code"])
    return 1 if errors else 0

def cmd_outline(args: argparse.Namespace) -> int:
    course = coursemod.load(common.project(), args.code)
    try:
        print(outline.section(course, args.section) if args.section else outline.outline(course))
    except ValueError as exc:
        print(t("commands", "outline_error", error=exc), file=sys.stderr)
        return 2
    return 0

def cmd_paths(args: argparse.Namespace) -> int:
    from coursekit import paths

    project = common.project()
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

    course = coursemod.load(common.project(), args.code)
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

def _families(values: list[str] | None) -> set[str] | None:
    """The families named by --only or --ignore (repeated, or separated by commas); None when the option is not given."""
    if not values:
        return None
    names = {name.strip() for value in values for name in value.split(",") if name.strip()}
    unknown = sorted(names - set(verify.FAMILIES))
    if unknown:
        raise coursemod.RuleError(t("commands", "verify_unknown_family", names=", ".join(unknown), families=", ".join(verify.FAMILIES)))
    return names


def cmd_verify(args: argparse.Namespace) -> int:
    course = coursemod.load(common.project(), args.code)
    as_json = getattr(args, "json", False)
    problem = coursemod.approval_problem(course)
    if problem:
        if as_json:
            print(json.dumps({"code": course["code"], "error": problem}, ensure_ascii=False, indent=2))
        else:
            print(t("commands", "error_line", text=f"{course['code']}: {problem}"))
        return 1
    units = [u for u in course.get("units") or [] if args.unit is None or u["n"] == args.unit]
    if not units:
        message = t("commands", "no_units_n", n=args.unit) if args.unit else t("commands", "no_units")
        print(message, file=sys.stderr)
        return 1
    only, ignore = _families(getattr(args, "only", None)), _families(getattr(args, "ignore", None))
    filtered = only is not None or ignore is not None
    update = not args.no_update and not filtered  # a partial view must not mark a unit as verified

    def shown(finding: verify.Finding) -> bool:
        return (only is None or finding.family in only) and (ignore is None or finding.family not in ignore)

    fmt = lambda n: format_number(n, coursemod.language(course))  # noqa: E731
    failed = False
    results = []
    for unit in units:
        report = verify.verify_unit(course, unit)
        findings = [f for f in report.findings if shown(f)]
        errors = [f for f in findings if f.level == "error"]
        warnings = [f for f in findings if f.level == "warning"]
        failed = failed or bool(errors)
        notes = verify.update_status(course, unit, report) if update else []
        results.append({"n": unit["n"], "title": unit.get("title", ""), "ok": not errors, "summary": report.summary,
                        "errors": [{"family": f.family, "message": f.message} for f in errors],
                        "warnings": [{"family": f.family, "message": f.message} for f in warnings], "status": notes})
        if as_json:
            continue
        s = report.summary
        header = "verify_header_fail" if errors else "verify_header_ok"
        print("\n" + t("commands", header, code=course["code"], n=unit["n"], title=unit.get("title", "")))
        if s:
            print(t("commands", "verify_stats", words=fmt(s["words"]), min_words=fmt(s["min_words"]),
                    placeholders=s["placeholders"], types=s["placeholder_types"], formative=s["formative_questions"],
                    bank=s["bank_questions"]))
        for f in errors:
            print("  " + t("commands", "error_line", text=f"[{f.family}] {f.message}"))
        for f in warnings:
            print("  " + t("commands", "warning_line", text=f"[{f.family}] {f.message}"))
        for note in notes:
            print(f"  {note}")
    if update:
        common.mirror(course["_project"], course["code"])
    if as_json:
        print(json.dumps({"code": course["code"], "ok": not failed, "filtered": filtered, "units": results}, ensure_ascii=False,
                         indent=2, default=str))
        return 1 if failed else 0
    if len(results) > 1:
        print("\n" + t("commands", "verify_summary_title"))
        for r in results:
            print("  " + t("commands", "verify_summary_line", n=r["n"], errors=len(r["errors"]), warnings=len(r["warnings"]),
                           title=r["title"]))
    if filtered:
        print(t("commands", "verify_filtered"))
    return 1 if failed else 0


def cmd_reviewed(args: argparse.Namespace) -> int:
    course = coursemod.load(common.project(), args.code)
    statesmod.ensure_active(course)
    if (args.note or args.report) and not args.by:
        print(t("commands", "reviewed_needs_by"), file=sys.stderr)
        return 2
    print(approve.mark_reviewed(course, args.unit, args.by, args.note, args.report))
    common.mirror(course["_project"], course["code"])
    return 0

def cmd_approve(args: argparse.Namespace) -> int:
    if not args.yes and not sys.stdin.isatty():
        print(t("commands", "approve_no_terminal"), file=sys.stderr)
        return 1
    confirm = common.confirm(args.yes)
    if args.code is None:
        if args.gate != "media-style":
            print(t("commands", "approve_needs_code"), file=sys.stderr)
            return 2
        print(approve.approve_project_media_style(common.project(), confirm, do_commit=not args.no_commit))
        return 0
    course = coursemod.load(common.project(), args.code)
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
    common.mirror(course["_project"], course["code"])
    return 0

def cmd_hold(args: argparse.Namespace) -> int:
    course = coursemod.load(common.project(), args.code)
    previous = statesmod.hold(course["_dir"], args.reason)
    print(t("commands", "hold_done", code=course["code"], previous=previous))
    common.mirror(course["_project"], course["code"])
    return 0

def cmd_resume(args: argparse.Namespace) -> int:
    course = coursemod.load(common.project(), args.code)
    previous, new = statesmod.resume(course["_dir"])
    print(t("commands", "resume_done", code=course["code"], previous=previous, new=new))
    common.mirror(course["_project"], course["code"])
    return 0

def cmd_client(args: argparse.Namespace) -> int:
    course = coursemod.load(common.project(), args.code)
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
    common.mirror(course["_project"], course["code"])
    return 0

def cmd_catalog(args: argparse.Namespace) -> int:
    project = common.project()
    output = Path(args.output) if args.output else common.local_catalog(project)
    courses, units, _ = catalogmod.build(project, output, force=True)  # asked for: always written
    print(t("commands", "catalog_wrote", path=output, courses=courses, units=units))
    return 0

def cmd_publish(args: argparse.Namespace) -> int:
    project = common.project()
    if args.check:
        print("\n".join(publishmod.check(project)))
        return 0
    output = common.local_catalog(project)
    try:
        courses, units, written = catalogmod.build(project, output)
    except PermissionError as exc:
        raise publishmod.PublishError(t("publish", "cannot_replace", output=output)) from exc
    if not args.only_if_configured:
        print(t("commands", "catalog_wrote" if written else "catalog_unchanged", path=output, courses=courses, units=units))
    for line in publishmod.publish(project, args.code, args.only_if_configured):
        print(line)
    return 0
