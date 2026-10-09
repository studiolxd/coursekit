"""Command line entry point: `coursekit <command> [args]`."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

import yaml

from coursekit import __version__, commands, config, envfile, i18n
from coursekit import agents as agentsmod
from coursekit import init as initmod
from coursekit import setup as setupmod
from coursekit.i18n import t
from coursekit.project import PROJECT_FILE, ProjectNotFound, find_project
from coursekit.sync import DesignError


def _print_report(report: initmod.Report) -> None:
    for label, items in (
        (t("cli", "report_created"), report.created),
        (t("cli", "report_updated"), report.updated),
        (t("cli", "report_unchanged"), report.unchanged),
        (t("cli", "report_kept"), report.kept_edited),
    ):
        for item in items:
            print(f"  {label}: {item}")


def _branding_hint(answers: initmod.Answers) -> str | None:
    """Which notice about the brand material the person gets: html (a stylesheet or the base look) or a theme made from it."""
    if answers.backend == "html":
        return "html"
    return "branding" if answers.theme_source == "branding" else None


def _print_next_steps(root: Path, mcp_missing: bool = False, branding: str | None = None) -> None:
    """Invite the person to open an AI tool and create the first course."""
    here = Path.cwd().resolve()
    folder = "." if root == here else (root.relative_to(here) if root.is_relative_to(here) else root).as_posix()
    tools = ", ".join(tool if shutil.which(tool) else t("cli", "next_tool_missing", tool=tool) for tool in agentsmod.TOOLS)
    print()
    print(t("cli", "next_header"))
    print()
    print(t("cli", "next_before"))
    if mcp_missing:
        print(t("cli", "next_mcp"))
    print(t("cli", "next_brief"))
    if branding:
        print(t("cli", f"next_branding_{branding}"))
    print(t("cli", "next_config"))
    print()
    print(t("cli", "next_then"))
    if folder != ".":
        print(t("cli", "next_cd", folder=f'"{folder}"' if " " in folder else folder))
    print(t("cli", "next_open", tools=tools))
    print(t("cli", "next_command"))
    print(t("cli", "next_codex"))
    print(t("cli", "next_run"))
    print(t("cli", "next_status"))


def _pause_for_material(root: Path) -> bool:
    """Before the design starts, give the person the chance to drop the reference material in the project.

    Returns whether there is material (or the person will add it): when not, the design is told not to ask again."""
    brief = root / "brief"
    if not initmod.confirm(t("cli", "material_ask"), default=False):
        print(t("cli", "material_none"))
        return False
    print(t("cli", "material_where", sources=(brief / "sources").as_posix(), links=(brief / "links.md").as_posix(),
            notes=(brief / "notes.md").as_posix()))
    initmod.ask(t("cli", "material_wait"), "")
    return True


def _offer_first_course(root: Path) -> int:
    """Offer to create the first course now, with the tool of the design role (when it is installed)."""
    tool = agentsmod.role("design")[0]
    if not shutil.which(tool) or not initmod.confirm(t("cli", "create_ask", tool=tool)):
        return 0
    while True:
        title = initmod.ask(t("cli", "create_title"), "").replace('"', "").strip()
        if title:
            break
        print(t("cli", "create_title_bad"), file=sys.stderr)
    while True:
        text = initmod.ask(t("cli", "create_hours"), "").replace(",", ".")
        try:
            if float(text) > 0:
                break
        except ValueError:
            pass
        print(t("cli", "create_hours_bad"), file=sys.stderr)
    os.chdir(root)
    if initmod.confirm(t("cli", "handoff_ask"), default=False):
        print(t("cli", "handoff_notice"))
        return main(["handoff", title, text])  # it waits for the material itself, once the course folders exist
    has_material = _pause_for_material(root)
    return main(["run", "new-course", title, text] + ([] if has_material else ["--no-material"]))


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.folder).expanduser().resolve()
    if args.update:
        if not (root / PROJECT_FILE).exists():
            print(t("cli", "not_a_project", root=root, file=PROJECT_FILE), file=sys.stderr)
            return 1
        _print_report(initmod.update(root))
        return 0
    if (root / PROJECT_FILE).exists():
        print(t("cli", "already_a_project", root=root), file=sys.stderr)
        return 1
    interactive = sys.stdin.isatty() and not args.yes
    name = args.name or root.name
    language = args.language or "es"
    answers = initmod.Answers(name=name, content_language=language, ui_language=args.ui_language or language)
    answers.client = args.client or ""
    answers.tone = args.tone or ""
    answers.address = args.address or ""
    answers.backend = args.backend
    answers.theme_source = args.theme_source
    answers.mirror = args.mirror
    answers.mcp_url = args.mcp_url or ""
    answers.mirror_dir = args.mirror_dir or ""
    answers.mirror_url = args.mirror_url or ""
    if interactive:
        # First the language of the interface (what decides the language of everything that follows), then the one of the courses.
        answers.ui_language = initmod.ask(initmod.LANGUAGE_PROMPT, args.ui_language or args.language or "es", initmod.LANGUAGES)
        i18n.use(answers.ui_language)
        answers.content_language = initmod.ask(t("init", "content_language"), args.language or answers.ui_language, initmod.LANGUAGES)
        answers.name = initmod.ask(t("init", "name"), answers.name)
        answers.client = initmod.ask(t("init", "client"), answers.client)
        answers.tone = initmod.ask(t("init", "tone"), answers.tone)
        options = initmod.ADDRESS[answers.content_language]
        answers.address = initmod.ask(t("init", "address"), answers.address or options[0], options)
        answers.backend = initmod.ask(t("init", "backend"), answers.backend, initmod.BACKENDS, labels=initmod.BACKEND_LABELS)
        answers.mcp_url = initmod.ask_url(t("init", "mcp_url"), answers.mcp_url)  # the design is done in creator with either backend
        if answers.backend == "creator":  # with html the look is a stylesheet, not a theme of the platform
            answers.theme_source = initmod.ask(t("init", "theme_source"), answers.theme_source, initmod.THEME_SOURCES,
                                               labels=initmod.THEME_SOURCE_LABELS)
        answers.mirror = initmod.ask(t("init", "mirror"), answers.mirror, initmod.MIRRORS)
        if answers.mirror in initmod.MIRRORS_WITH_DETAILS:
            answers.mirror_dir = initmod.ask(t("init", "mirror_dir"), answers.mirror_dir).strip("\"'")
            if answers.mirror != "folder":
                answers.mirror_url = initmod.ask(t("init", "mirror_url"), answers.mirror_url)
            if answers.mirror_dir and not Path(answers.mirror_dir).expanduser().is_dir():
                print(t("init", "mirror_dir_missing", path=answers.mirror_dir))
    elif answers.address and answers.address not in initmod.ADDRESS[answers.content_language]:
        print(t("cli", "bad_address", options=initmod.ADDRESS[answers.content_language]), file=sys.stderr)
        return 1
    if answers.mcp_url and not initmod.valid_url(answers.mcp_url):
        print(t("cli", "bad_mcp_url"), file=sys.stderr)
        return 1
    if interactive or args.language or args.ui_language:  # the person chose it: it wins over the environment
        i18n.use(answers.ui_language)
    root.mkdir(parents=True, exist_ok=True)
    report = initmod.create(root, answers, git=not args.no_git)
    print(t("cli", "project_created", root=root))
    _print_report(report)
    project = find_project(root)
    setupmod.env_file(project, print)
    setupmod.set_env_value(project.env_file, "COURSEKIT_LANG", answers.ui_language, environ=False)
    if answers.mirror_dir:
        setupmod.set_env_value(project.env_file, "MIRROR_DIR", answers.mirror_dir)
        print(t("cli", "mirror_dir_saved"))
    code = setupmod.run(project, print, initmod.ask if interactive else None, initmod.confirm if interactive else None,
                        secret=initmod.ask_secret if interactive else None)
    if code != 0:
        return code
    mcp_missing = not answers.mcp_url
    _print_next_steps(root, mcp_missing, branding=_branding_hint(answers))
    if interactive and not mcp_missing:
        return _offer_first_course(root)
    return 0


def cmd_agents(args: argparse.Namespace) -> int:
    project = find_project()
    envfile.load(project.env_file)
    report = agentsmod.generate(project)
    print(t("cli", "agents_summary", written=len(report.written), unchanged=report.unchanged, removed=len(report.removed)))
    for path in report.kept:
        print(t("cli", "agents_kept", path=path))
    for path in report.configs:
        print(t("cli", "agents_updated", path=path))
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    project = find_project()
    envfile.load(project.env_file)
    course = None
    if args.course:
        course_file = project.course_dir(args.course) / "course.yaml"
        if not course_file.exists():
            print(t("cli", "course_not_found", code=args.course, file=course_file), file=sys.stderr)
            return 1
        course = yaml.safe_load(course_file.read_text(encoding="utf-8")) or {}
    names = [args.name] if args.name else list(config.NAMES)
    if args.json:
        out = {n: config.effective(n, project, course).value for n in names}
        print(json.dumps(out if not args.name else out[args.name], indent=2, ensure_ascii=False, default=str))
        return 0
    for name in names:
        layered = config.effective(name, project, course)
        if len(names) > 1:
            print(f"[{name}]")
        rows = [(k, v, o) for k, v, o in layered.flat() if not args.changed or o != "package"]
        width = max((len(k) for k, _, _ in rows), default=0)
        for key, value, origin in rows:
            shown = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
            print(f"  {key.ljust(width)}  {shown}  ({origin})")
        if len(names) > 1:
            print()
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    from coursekit import uninstall

    return uninstall.run(print, initmod.confirm if sys.stdin.isatty() else None, dry_run=args.dry_run, yes=args.yes)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coursekit",
        description=t("cli", "description"),
    )
    parser.add_argument("--version", action="version", version=f"coursekit {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.add_parser("help", help=t("cli", "help_help"))

    p = sub.add_parser("init", help=t("cli", "help_init"))
    p.add_argument("folder", nargs="?", default=".", help=t("cli", "init_folder"))
    p.add_argument("--update", action="store_true", help=t("cli", "init_update"))
    p.add_argument("--name")
    p.add_argument("--client")
    p.add_argument("--language", choices=initmod.LANGUAGES, help=t("cli", "init_language"))
    p.add_argument("--ui-language", choices=initmod.LANGUAGES, help=t("cli", "init_ui_language"))
    p.add_argument("--tone")
    p.add_argument("--address", help=t("cli", "init_address"))
    p.add_argument("--backend", choices=initmod.BACKENDS, default="creator")
    p.add_argument("--theme-source", choices=initmod.THEME_SOURCES, default="tenant_default", help=t("cli", "help_theme_source"))
    p.add_argument("--mirror", choices=initmod.MIRRORS, default="none")
    p.add_argument("--mcp-url", help=t("cli", "help_mcp_url"))
    p.add_argument("--mirror-dir", help=t("cli", "init_mirror_dir"))
    p.add_argument("--mirror-url", help=t("cli", "init_mirror_url"))
    p.add_argument("--yes", "-y", action="store_true", help=t("cli", "init_yes"))
    p.add_argument("--no-git", action="store_true", help=t("cli", "init_no_git"))
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("config", help=t("cli", "help_config"))
    p.add_argument("name", nargs="?", choices=config.NAMES, help=t("cli", "config_name"))
    p.add_argument("--course", help=t("cli", "config_course"))
    p.add_argument("--changed", action="store_true", help=t("cli", "config_changed"))
    p.add_argument("--json", action="store_true", help=t("cli", "config_json"))
    p.set_defaults(func=cmd_config)

    p = sub.add_parser("rules", help=t("cli", "help_rules"))
    p.add_argument("course", nargs="?")
    p.add_argument("--changed", action="store_true", help=t("cli", "config_changed"))
    p.set_defaults(func=lambda a: cmd_config(argparse.Namespace(name="rules", course=a.course, changed=a.changed, json=False)))

    p = sub.add_parser("agents", help=t("cli", "help_agents"))
    p.set_defaults(func=cmd_agents)

    p = sub.add_parser("uninstall", help=t("cli", "help_uninstall"))
    p.add_argument("--dry-run", action="store_true", help=t("cli", "uninstall_dry_run"))
    p.add_argument("--yes", "-y", action="store_true", help=t("cli", "uninstall_yes"))
    p.set_defaults(func=cmd_uninstall)

    commands.register(sub)
    return parser


def _language_from_env_file() -> None:
    """The `.env` of the project (if any) sets COURSEKIT_LANG before the help texts are built."""
    if os.environ.get("COURSEKIT_LANG"):
        return
    try:
        env_file = find_project().env_file
        value = envfile.parse(env_file.read_text(encoding="utf-8")).get("COURSEKIT_LANG", "")
    except (ProjectNotFound, OSError):
        return
    if value:
        os.environ["COURSEKIT_LANG"] = value


def main(argv: list[str] | None = None) -> int:
    _language_from_env_file()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in (None, "help"):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except (ProjectNotFound, DesignError, agentsmod.RenderError, *commands.ERRORS) as exc:
        print(f"coursekit: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
