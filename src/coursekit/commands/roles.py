"""The commands that launch the agents of each role, and the ones of the machine (setup, doctor)."""


from __future__ import annotations

import argparse
import sys

from coursekit import agents as agentsmod
from coursekit import course as coursemod
from coursekit import (
    doctor,
    launch,
)
from coursekit import init as initmod
from coursekit import setup as setupmod
from coursekit import states as statesmod
from coursekit.commands import common
from coursekit.i18n import t
from coursekit.project import Project, find_project


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
    project = common.project()
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
        common.mirror(project, course["code"])  # the session itself did not (`COURSEKIT_MIRROR=deferred`)
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
    project = common.project()
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
        common.mirror(project, worked_on)  # the session itself did not (`COURSEKIT_MIRROR=deferred`)
    if summary:
        print(summary)
    if log:
        print(t("commands", "run_session_exit" if code else "run_session", path=log.relative_to(project.root).as_posix(), code=code))
    return code

def cmd_roles(args: argparse.Namespace) -> int:
    common.project()
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
    project = common.project()
    sections = doctor.collect(project)
    print(doctor.render(sections))
    return 0
