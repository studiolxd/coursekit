"""Command line entry point: `coursekit <command> [args]`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from coursekit import __version__, config, envfile
from coursekit import init as initmod
from coursekit.project import PROJECT_FILE, ProjectNotFound, find_project


def _print_report(report: initmod.Report) -> None:
    for label, items in (
        ("created", report.created),
        ("updated", report.updated),
        ("unchanged", report.unchanged),
        ("kept (edited by hand, not updated)", report.kept_edited),
    ):
        for item in items:
            print(f"  {label}: {item}")


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.folder).expanduser().resolve()
    if args.update:
        if not (root / PROJECT_FILE).exists():
            print(f"coursekit: {root} is not a coursekit project (no {PROJECT_FILE})", file=sys.stderr)
            return 1
        _print_report(initmod.update(root))
        return 0
    if (root / PROJECT_FILE).exists():
        print(f"coursekit: {root} is already a project; use `coursekit init --update`", file=sys.stderr)
        return 1
    interactive = sys.stdin.isatty() and not args.yes
    name = args.name or root.name
    language = args.language
    answers = initmod.Answers(name=name, content_language=language, ui_language=args.ui_language or language)
    answers.client = args.client or ""
    answers.tone = args.tone or ""
    answers.address = args.address or ""
    answers.backend = args.backend
    answers.mirror = args.mirror
    if interactive:
        answers.name = initmod.ask("Project name", answers.name)
        answers.client = initmod.ask("Client", answers.client)
        answers.content_language = initmod.ask("Course language", answers.content_language, initmod.LANGUAGES)
        answers.ui_language = initmod.ask("Language for people", answers.content_language, initmod.LANGUAGES)
        answers.tone = initmod.ask("Tone", answers.tone)
        options = initmod.ADDRESS[answers.content_language]
        answers.address = initmod.ask("Address", answers.address or options[0], options)
        answers.backend = initmod.ask("Assembly backend", answers.backend, initmod.BACKENDS)
        answers.mirror = initmod.ask("Mirror folder", answers.mirror, initmod.MIRRORS)
    elif answers.address and answers.address not in initmod.ADDRESS[answers.content_language]:
        print(f"coursekit: --address must be one of {initmod.ADDRESS[answers.content_language]}", file=sys.stderr)
        return 1
    root.mkdir(parents=True, exist_ok=True)
    report = initmod.create(root, answers, git=not args.no_git)
    print(f"coursekit project created in {root}")
    _print_report(report)
    print("next: copy .env.example to .env and run `coursekit setup`")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    project = find_project()
    envfile.load(project.env_file)
    course = None
    if args.course:
        course_file = project.course_dir(args.course) / "course.yaml"
        if not course_file.exists():
            print(f"coursekit: course {args.course} not found ({course_file})", file=sys.stderr)
            return 1
        course = yaml.safe_load(course_file.read_text(encoding="utf-8")) or {}
    names = [args.name] if args.name else list(config.NAMES)
    if args.json:
        out = {n: config.effective(n, project, course).value for n in names}
        print(json.dumps(out if not args.name else out[args.name], indent=2, ensure_ascii=False))
        return 0
    for name in names:
        layered = config.effective(name, project, course)
        if len(names) > 1:
            print(f"[{name}]")
        rows = [(k, v, o) for k, v, o in layered.flat() if not args.changed or o != "package"]
        width = max((len(k) for k, _, _ in rows), default=0)
        for key, value, origin in rows:
            shown = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            print(f"  {key.ljust(width)}  {shown}  ({origin})")
        if len(names) > 1:
            print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coursekit",
        description="AI-assisted e-learning course production.",
    )
    parser.add_argument("--version", action="version", version=f"coursekit {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.add_parser("help", help="show this help")

    p = sub.add_parser("init", help="create a project, or refresh the files coursekit generated in it")
    p.add_argument("folder", nargs="?", default=".", help="project folder (default: current folder)")
    p.add_argument("--update", action="store_true", help="refresh generated files of an existing project")
    p.add_argument("--name")
    p.add_argument("--client")
    p.add_argument("--language", choices=initmod.LANGUAGES, default="es", help="course language")
    p.add_argument("--ui-language", choices=initmod.LANGUAGES, help="language for people (default: course language)")
    p.add_argument("--tone")
    p.add_argument("--address", help="tu | usted (es), you (en)")
    p.add_argument("--backend", choices=initmod.BACKENDS, default="creator")
    p.add_argument("--mirror", choices=initmod.MIRRORS, default="none")
    p.add_argument("--yes", "-y", action="store_true", help="do not ask; use the options and defaults")
    p.add_argument("--no-git", action="store_true", help="do not run git init")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("config", help="show the effective configuration and where each value is set")
    p.add_argument("name", nargs="?", choices=config.NAMES, help="one configuration (default: all)")
    p.add_argument("--course", help="include the overrides of this course (code or folder)")
    p.add_argument("--changed", action="store_true", help="only values that differ from the package defaults")
    p.add_argument("--json", action="store_true", help="print the merged values as JSON")
    p.set_defaults(func=cmd_config)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in (None, "help"):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except ProjectNotFound as exc:
        print(f"coursekit: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
