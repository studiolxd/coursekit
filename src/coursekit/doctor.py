"""`coursekit doctor`: what is installed and configured on this machine for the project."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from coursekit import __version__, config, identity
from coursekit import agents as agentsmod
from coursekit.project import Project
from coursekit.setup import ca_bundle
from coursekit.util import git


@dataclass
class Check:
    status: str  # ok | missing | info
    label: str
    hint: str = ""


@dataclass
class Section:
    title: str
    checks: list[Check] = field(default_factory=list)

    def add(self, ok: bool | None, label: str, hint: str = "") -> None:
        status = {True: "ok", False: "missing", None: "info"}[ok]
        self.checks.append(Check(status, label, hint if ok is not True else ""))


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def tool_sections(project: Project) -> Section:
    root = project.root
    values = agentsmod.context(project)
    mcp = values["mcp_name"]
    url = str(((config.project_data(project).get("platform") or {}).get("slxd") or {}).get("mcp_url") or "")
    s = Section("Agent tools")
    s.add(bool(url) or None, f"slxd MCP server '{mcp}'" + ("" if url else ": no mcp_url in project.yaml › platform.slxd"))
    checks = {
        "claude": (root / ".claude/skills/content-writing/SKILL.md", root / ".claude/commands/write-unit.md",
                   mcp in (_read_json(root / ".mcp.json").get("mcpServers") or {})),
        "opencode": (root / ".opencode/skill/content-writing/SKILL.md", root / ".opencode/command/write-unit.md",
                     mcp in (_read_json(root / "opencode.json").get("mcp") or {})),
        "codex": (root / ".coursekit/agents/skills/content-writing/SKILL.md", root / ".coursekit/agents/commands/write-unit.md",
                  (root / ".codex/config.toml").exists() and mcp in (root / ".codex/config.toml").read_text(encoding="utf-8")),
    }
    names = {"claude": "Claude Code", "opencode": "opencode", "codex": "Codex"}
    for tool, (skill, command, has_mcp) in checks.items():
        if not shutil.which(tool):
            s.add(None, f"{names[tool]}: not installed")
            continue
        sees = skill.exists() and command.exists()
        s.add(sees, f"{names[tool]}: skills and commands", "coursekit agents")
        if url:
            s.add(bool(has_mcp), f"{names[tool]}: MCP {mcp}", "coursekit agents")
    for role in agentsmod.ROLES:
        tool, model = agentsmod.role(role)
        s.add(shutil.which(tool) is not None, f"{role}: {tool} · {model or 'default model'}",
              f"install {tool} or change {role.upper()}_AGENT in .env")
    if agentsmod.role("writer") == agentsmod.role("reviewer"):
        s.add(None, "writer and reviewer use the same tool and model (another model catches more)")
    return s


def collect(project: Project) -> list[Section]:
    base = Section("Base")
    base.add(sys.version_info >= (3, 12), f"coursekit {__version__} (Python {sys.version_info[0]}.{sys.version_info[1]})")
    base.add(project.env_file.exists(), ".env", "coursekit setup")
    who = identity.current()
    base.add(who is not None, f"signing identity: {who}" if who else "signing identity", "coursekit setup --identity")
    hooks = git("config", "--get", "core.hooksPath", cwd=project.root)
    is_repo = bool(git("rev-parse", "--show-toplevel", cwd=project.root))
    base.add(bool(hooks) if is_repo else None, "git hooks" if is_repo else "not a git repository", "coursekit setup")
    base.add(importlib.util.find_spec("markitdown") is not None, "MarkItDown (coursekit brief)", "reinstall coursekit")
    base.add(shutil.which("node") is not None, "Node (web links of brief/links.md)", "coursekit setup --media")

    net = Section("Network")
    cert = ca_bundle(project)
    if cert:
        net.add(bool(os.environ.get("NODE_EXTRA_CA_CERTS")), f"corporate CA certificate: NODE_EXTRA_CA_CERTS ({cert})", "coursekit setup")
    else:
        net.add(None, "no corporate CA certificate configured or found (project.yaml › network)")

    mirror = Section("Mirror folder")
    provider = str((config.project_data(project).get("mirror") or {}).get("provider") or "none")
    if provider == "none":
        mirror.add(None, "no mirror folder (project.yaml › mirror)")
    else:
        folder = os.environ.get("MIRROR_DIR", "")
        mirror.add(bool(folder) and Path(folder).exists(), f"{provider}: MIRROR_DIR", "set it in .env (local path of the synced folder)")

    media = Section("Media (optional: coursekit setup --media)")
    for tool in ("ffmpeg", "vhs", "asciinema", "piper", "stable-ts"):
        if tool == "asciinema" and os.name == "nt":
            media.add(None, "asciinema: not available on Windows (terminal demos fall back to VHS)")
            continue
        media.add(shutil.which(tool) is not None, tool, "coursekit setup --media")
    voice = os.environ.get("PIPER_VOICE", "")
    media.add(bool(voice) and Path(voice).exists(), "PIPER_VOICE", "coursekit setup --media")
    for key in ("ELEVENLABS_API_KEY", "AZURE_SPEECH_KEY", "GOOGLE_TTS_API_KEY", "MAGNIFIC_API_KEY"):
        media.add(bool(os.environ.get(key)) or None, f"{key} (optional)")
    return [base, tool_sections(project), net, mirror, media]


def render(sections: list[Section]) -> str:
    out = []
    marks = {"ok": "ok     ", "missing": "missing", "info": "info   "}
    for section in sections:
        out.append(section.title)
        for c in section.checks:
            out.append(f"  {marks[c.status]} {c.label}" + (f"  → {c.hint}" if c.hint else ""))
    return "\n".join(out)
