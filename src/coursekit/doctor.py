"""`coursekit doctor`: what is installed and configured on this machine for the project."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from coursekit import __version__, config, identity, store
from coursekit import agents as agentsmod
from coursekit import theme as thememod
from coursekit.i18n import t
from coursekit.project import Project
from coursekit.setup import assembly_backend as setup_assembly_backend
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
    s = Section(t("doctor", "section_tools"))
    s.add(bool(url) or None, t("doctor", "mcp_server" if url else "mcp_no_url", mcp=mcp))
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
            s.add(None, t("doctor", "not_installed", name=names[tool]))
            continue
        sees = skill.exists() and command.exists()
        s.add(sees, t("doctor", "skills_commands", name=names[tool]), "coursekit agents")
        if url:
            s.add(bool(has_mcp), t("doctor", "mcp_of_tool", name=names[tool], mcp=mcp), "coursekit agents")
    for role in agentsmod.ROLES:
        tool, model = agentsmod.role(role)
        s.add(shutil.which(tool) is not None, t("doctor", "role_line", role=role, tool=tool, model=model or t("doctor", "default_model")),
              t("doctor", "role_hint", tool=tool, key=f"{role.upper()}_AGENT"))
    if agentsmod.role("writer") == agentsmod.role("reviewer"):
        s.add(None, t("doctor", "same_model"))
    return s


def collect(project: Project) -> list[Section]:
    base = Section(t("doctor", "section_base"))
    python = f"{sys.version_info[0]}.{sys.version_info[1]}"
    base.add(sys.version_info >= (3, 12), t("doctor", "coursekit_line", version=__version__, python=python))
    base.add(project.env_file.exists(), t("doctor", "env_file"), "coursekit setup")
    who = identity.current()
    label = t("doctor", "identity_with", who=who) if who else t("doctor", "identity_without")
    base.add(who is not None, label, "coursekit setup --identity")
    hooks = git("config", "--get", "core.hooksPath", cwd=project.root)
    is_repo = bool(git("rev-parse", "--show-toplevel", cwd=project.root))
    base.add(bool(hooks) if is_repo else None, t("doctor", "git_hooks" if is_repo else "not_a_repo"), "coursekit setup")
    base.add(importlib.util.find_spec("markitdown") is not None, t("doctor", "markitdown"), t("doctor", "markitdown_hint"))
    base.add(shutil.which("node") is not None, t("doctor", "node_line"), "coursekit setup --media")

    net = Section(t("doctor", "section_network"))
    cert = ca_bundle(project)
    if cert:
        net.add(bool(os.environ.get("NODE_EXTRA_CA_CERTS")), t("doctor", "ca_set", cert=cert), "coursekit setup")
    else:
        net.add(None, t("doctor", "ca_none"))

    mirror = Section(t("doctor", "section_mirror"))
    provider = str((config.project_data(project).get("mirror") or {}).get("provider") or "none")
    if provider == "none":
        mirror.add(None, t("doctor", "mirror_none"))
    else:
        folder = os.environ.get("MIRROR_DIR", "")
        mirror.add(bool(folder) and Path(folder).exists(), t("doctor", "mirror_dir", provider=provider), t("doctor", "mirror_hint"))

    if setup_assembly_backend(project) == "html":
        builders = sorted(store.workspaces_dir().glob("html-builder-*")) if store.workspaces_dir().is_dir() else []
        base.add(bool(builders) or None, t("doctor", "html_builder"), "coursekit setup")

    theme = Section(t("doctor", "section_theme"))
    found = thememod.status(project)
    theme.add(True if found.state == "derived" else None, t("doctor", f"theme_{found.state}"), t("doctor", "theme_hint"))

    media = Section(t("doctor", "section_media"))
    for tool in ("ffmpeg", "vhs", "asciinema", "piper", "stable-ts"):
        if tool == "asciinema" and os.name == "nt":
            media.add(None, t("doctor", "asciinema_windows"))
            continue
        media.add(shutil.which(tool) is not None, tool, "coursekit setup --media")
    if store.home().exists():
        media.add(None, t("doctor", "store", path=store.home().as_posix(), size=store.human(store.size(store.home()))))
    remotion_dir = project.root / "tools" / "remotion"
    if remotion_dir.exists():
        media.add((remotion_dir / "node_modules").is_dir(), t("doctor", "remotion_deps"), "coursekit setup --media")
    voice = os.environ.get("PIPER_VOICE", "")
    media.add(bool(voice) and Path(voice).exists(), "PIPER_VOICE", "coursekit setup --media")
    for key in ("ELEVENLABS_API_KEY", "AZURE_SPEECH_KEY", "GOOGLE_TTS_API_KEY", "MAGNIFIC_API_KEY"):
        media.add(bool(os.environ.get(key)) or None, t("doctor", "key_optional", key=key))
    if os.environ.get("AZURE_SPEECH_KEY") and not os.environ.get("AZURE_SPEECH_REGION"):
        media.add(False, "AZURE_SPEECH_REGION", t("doctor", "azure_region_hint"))
    return [base, tool_sections(project), net, mirror, theme, media]


def render(sections: list[Section]) -> str:
    out = []
    marks = {status: t("doctor", f"mark_{status}").ljust(7) for status in ("ok", "missing", "info")}
    for section in sections:
        out.append(section.title)
        for c in section.checks:
            out.append(f"  {marks[c.status]} {c.label}" + (f"  → {c.hint}" if c.hint else ""))
    return "\n".join(out)
