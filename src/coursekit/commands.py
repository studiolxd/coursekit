"""Course commands: new, status, sync, outline, verify, reviewed, approve, brief, rules."""

from __future__ import annotations

import argparse
import sys

from coursekit import approve, envfile, new, outline, status, verify
from coursekit import brief as briefmod
from coursekit import course as coursemod
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
    print(f"created {folder.relative_to(project.root)} ({args.hours} h)")
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

    p = sub.add_parser("brief", help="convert the reference material of a course (or of the project) for the agents")
    p.add_argument("code", nargs="?", help="course code (default: the project brief/)")
    p.add_argument("--refresh", action="store_true", help="download the URLs of links.md again")
    p.set_defaults(func=cmd_brief)


ERRORS = (coursemod.CourseNotFound, approve.ApprovalError, FileExistsError)
