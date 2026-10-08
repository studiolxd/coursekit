"""Launch the agent of a role (tool and model from the .env) on a command.

Each role (design, writer, reviewer, media, assembly) runs with a tool (claude | opencode |
codex) and a model: <ROLE>_AGENT / <ROLE>_MODEL in the .env, or --agent / --model for one launch
(--agent alone uses that tool's default model). An empty model means the tool's default.

- `coursekit write CODE [N]` and `coursekit review CODE [N]` work unit by unit; without N, every
  unit still to do, in order, stopping at the first one that does not end verified (write) or
  reviewed (review). The writer is recorded in units[N].written_with and the reviewer in
  reviewed_with; a review with the writer's same tool and model warns but goes on. A review of a
  unit already reviewed is partial (only the parts changed since, from the fingerprints), unless
  --full; --parts names them by hand.
- `coursekit run COMMAND [ARGS…]` launches any other command (new-course, design-change,
  approve-design, produce-media, assemble, deliver, sync-directives…) with the agent of its role.

--headless runs the tool without its interface (claude -p, opencode run, codex exec), so another
agent or a scheduled task can launch it; the session goes to .cache/logs/.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from coursekit import agents as agentsmod
from coursekit import course as coursemod
from coursekit.fingerprint import changed_since_review
from coursekit.project import Project
from coursekit.util import edit_yaml, save_yaml

TOOLS = ("claude", "opencode", "codex")
COMMAND_ROLE = {
    "new-course": "design",
    "design-change": "design",
    "approve-design": "design",
    "course-status": "design",
    "write-unit": "writer",
    "review-unit": "reviewer",
    "approve-unit": "reviewer",
    "produce-media": "media",
    "assemble": "assembly",
    "deliver": "assembly",
    "sync-directives": "assembly",
}
TODO = {"writer": ("pending", "writing"), "reviewer": ("verified",)}
DONE = {"writer": ("verified", "reviewed", "approved"), "reviewer": ("reviewed", "approved")}
HEADLESS_NOTE = (
    "\n\nYou are running without an interface: nobody can answer you. Do not ask questions; decide "
    "with what you have, leave doubts noted (<!-- VERIFICAR: … --> or in the report) and finish with "
    "a short summary of what you did and what is pending."
)
_BASE_TOOLS = ["Read", "Edit", "Write", "Glob", "Grep", "Skill", "TodoWrite",
               "Bash(coursekit verify:*)", "Bash(coursekit brief:*)", "Bash(coursekit status:*)",
               "Bash(coursekit outline:*)", "Bash(coursekit config:*)", "Bash(git status:*)", "Bash(git diff:*)"]
CLAUDE_DENY = ["Bash(git commit:*)", "Bash(git push:*)", "Bash(coursekit approve:*)"]


class LaunchError(Exception):
    pass


@dataclass
class Agent:
    role: str
    tool: str
    model: str

    @property
    def label(self) -> str:
        return f"{self.tool} · {self.model or 'default model'}"


def agent_for(role: str, tool: str | None = None, model: str | None = None) -> Agent:
    env_tool, env_model = agentsmod.role(role)
    if tool:
        chosen, chosen_model = tool, (model or "")
    else:
        chosen, chosen_model = env_tool, (model if model is not None else env_model)
    if chosen not in TOOLS:
        raise LaunchError(f"{role.upper()}_AGENT={chosen} is not valid (use {' | '.join(TOOLS)})")
    return Agent(role, chosen, chosen_model)


def prompt(agent: Agent, command: str, arguments: str, headless: bool, extra: str = "") -> str:
    if agent.tool == "codex" or (headless and agent.tool == "opencode"):
        # Codex has no project slash commands: point it at the generated command file.
        text = (f"Follow the instructions in .coursekit/agents/commands/{command}.md with the arguments "
                f'"{arguments}". The skills are in .coursekit/agents/skills/<name>/SKILL.md.')
    else:
        text = f"/{command} {arguments}".rstrip()
    return text + extra + (HEADLESS_NOTE if headless else "")


def _exe(tool: str) -> str:
    exe = shutil.which(tool)
    if exe is None:
        raise LaunchError(f"{tool} is not installed on this machine (coursekit doctor)")
    return exe


def interactive_args(agent: Agent, text: str) -> list[str]:
    exe = _exe(agent.tool)
    if agent.tool == "opencode":
        # The TUI has no --model flag: the model goes in the generated agent (coursekit agents).
        return [exe, "--prompt", text]
    return [exe, *(["--model", agent.model] if agent.model else []), text]


def headless_args(agent: Agent, text: str, last_message: Path, mcp_name: str) -> list[str]:
    exe = _exe(agent.tool)
    with_model = ["--model", agent.model] if agent.model else []
    if agent.tool == "claude":
        allowed = [*_BASE_TOOLS]
        if agent.role == "reviewer":
            allowed.append("Bash(coursekit reviewed:*)")
        if agent.role in ("design", "media", "assembly"):
            allowed += [f"mcp__{mcp_name}", "Bash(coursekit:*)", "WebFetch"]
        return [exe, "-p", text, *with_model, "--permission-mode", "acceptEdits",
                "--allowedTools", *allowed, "--disallowedTools", *CLAUDE_DENY,
                "--output-format", "stream-json", "--verbose"]
    if agent.tool == "opencode":
        named = ["--agent", agent.role] if agent.role in ("writer", "reviewer") else []
        return [exe, "run", *named, *with_model, "--auto", "--format", "json", text]
    return [exe, "exec", *with_model, "--sandbox", "workspace-write", "--json", "-o", str(last_message), text]


def final_message(tool: str, log: Path, last_message: Path) -> str:
    """Last answer of the session, for the summary printed after a headless run."""
    if last_message.exists():
        return last_message.read_text(encoding="utf-8").strip()
    result = ""
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if tool == "claude" and event.get("type") == "result":
            result = event.get("result") or result
        elif tool == "opencode" and event.get("type") == "text":
            result = (event.get("part") or {}).get("text") or result
    return result.strip()


def execute(project: Project, agent: Agent, text: str, headless: bool, log_name: str) -> tuple[int, Path | None, str]:
    """Run the tool; returns (exit code, log path, final message)."""
    if agent.tool == "opencode":
        agentsmod.generate(project)  # the writer/reviewer agents carry the model of the .env
    if not headless:
        return subprocess.call(interactive_args(agent, text), cwd=project.root), None, ""
    logs = project.cache_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    log = logs / f"{log_name}-{stamp}.log"
    last_message = log.with_suffix(".last.txt")
    mcp_name = agentsmod.context(project)["mcp_name"]
    args = headless_args(agent, text, last_message, mcp_name)
    # A clean session even when launched from inside another agent (e.g. Claude Code).
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
    with log.open("w", encoding="utf-8") as fh:
        code = subprocess.call(args, cwd=project.root, stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env)
    return code, log, final_message(agent.tool, log, last_message)


# ── units ─────────────────────────────────────────────────────────────────────────────────

def _units(course: dict) -> list[dict]:
    return course.get("units") or []


def units_to_do(course: dict, role: str) -> list[int]:
    return [u["n"] for u in _units(course) if u.get("status", "pending") in TODO[role]]


def record(course_dir: Path, n: int, key: str, value: str) -> None:
    path = course_dir / "course.yaml"
    ry, data = edit_yaml(path)
    unit = next(u for u in data["units"] if u["n"] == n)
    if unit.get(key) != value:
        unit[key] = value
        save_yaml(ry, data, path)


def review_parts(course: dict, n: int, full: bool, given: str | None) -> list[str] | None:
    """Parts for a partial review, or None for a full one."""
    if full:
        return None
    if given:
        return [p.strip() for p in given.split(",") if p.strip()]
    unit = next(u for u in _units(course) if u["n"] == n)
    return changed_since_review(course["_dir"], unit, coursemod.tokens(course)) or None


@dataclass
class UnitResult:
    n: int
    status: str | None
    exit_code: int
    log: Path | None
    summary: str
    warnings: list[str]


def run_unit(project: Project, code: str, role: str, n: int, agent: Agent, headless: bool,
             full: bool = False, parts_given: str | None = None) -> UnitResult:
    course = coursemod.load(project, code)
    unit = next((u for u in _units(course) if u["n"] == n), None)
    if unit is None:
        raise LaunchError(f"unit {n} not found in course.yaml (is the design approved?)")
    warnings = []
    extra = ""
    if role == "reviewer":
        writer = unit.get("written_with")
        if writer is None:
            warnings.append(f"course.yaml does not say who wrote unit {n}; check it was not {agent.label}")
        elif writer == agent.label:
            warnings.append(f"unit {n} was written with {writer}, the same tool and model as this review; "
                            "another model catches more (REVIEWER_AGENT / REVIEWER_MODEL in .env)")
        record(course["_dir"], n, "reviewed_with", agent.label)
        extra = f"\n\nYou are the reviewer ({agent.label}): put that in the header of the report."
        parts = review_parts(course, n, full, parts_given)
        if parts:
            extra += (f"\n\nPARTIAL REVIEW: review only these parts, changed since the previous review: "
                      f"{', '.join(parts)}. Follow the \"Partial review\" section of the skill.")
    else:
        record(course["_dir"], n, "written_with", agent.label)
    command = "write-unit" if role == "writer" else "review-unit"
    text = prompt(agent, command, f"{course['code']} {n}", headless, extra)
    kind = "write" if role == "writer" else "review"
    exit_code, log, summary = execute(project, agent, text, headless, f"{course['code']}-u{n:02d}-{kind}")
    status = next((u.get("status") for u in _units(coursemod.load(project, code)) if u["n"] == n), None)
    return UnitResult(n, status, exit_code, log, summary, warnings)


def done(role: str, status: str | None) -> bool:
    return status in DONE[role]
