"""`coursekit setup`: prepare this machine for a project (repeatable).

- identity: name and email that sign approvals (COURSEKIT_USER_NAME / _EMAIL in .env), asked the
  first time with the git identity as the suggestion; `--identity` changes it;
- .env from .env.example when missing;
- git hooks of the project (.githooks: refresh the agents after every pull and checkout);
- skills, commands and agent settings (`coursekit agents`);
- network: the CA certificates of project.yaml › network (TLS-inspecting proxies) for the Node
  tools (Claude Code, opencode, npm) and uv;
- `--media`: system tools for media production and the local draft voice.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path

from coursekit import agents as agentsmod
from coursekit import config, envfile, identity
from coursekit.project import Project
from coursekit.util import git

IS_WINDOWS = os.name == "nt"
IS_MAC = sys.platform == "darwin"
BREW = ["ffmpeg", "node", "vhs", "asciinema"]
WINGET = {"ffmpeg": "Gyan.FFmpeg", "node": "OpenJS.NodeJS.LTS", "vhs": "charmbracelet.vhs"}
APT = ["ffmpeg", "nodejs", "npm", "asciinema"]
MEDIA_TOOLS = {"piper": "piper-tts", "stable-ts": "stable-ts"}  # command → package (uv tool, Python 3.12)
PIPER_VOICES = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
PIPER_DEFAULT = {"es": ("es/es_ES", "sharvard", "medium"), "en": ("en/en_GB", "alba", "medium")}

Say = Callable[[str], None]
Ask = Callable[[str, str], str]


def set_env_value(path: Path, key: str, value: str) -> None:
    """Set KEY=value in a .env file, keeping the rest (and its comments) as it is."""
    quoted = f'"{value}"' if any(c in value for c in " #'") else value
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}=") or line.strip().startswith(f"export {key}="):
            lines[i] = f"{key}={quoted}"
            break
    else:
        lines.append(f"{key}={quoted}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    os.environ[key] = value


def env_file(project: Project, say: Say) -> None:
    if project.env_file.exists():
        return
    example = project.root / ".env.example"
    if example.exists():
        shutil.copyfile(example, project.env_file)
    else:
        project.env_file.write_text("", encoding="utf-8")
    say("ok: created .env (personal, never committed)")


def setup_identity(project: Project, say: Say, ask: Ask | None, name: str | None = None, email: str | None = None,
                   force: bool = False) -> identity.Identity | None:
    current = identity.current()
    if current and not force and not (name or email):
        say(f"ok: you sign as {current}")
        return current
    suggestion = current or identity.suggested()
    if not (name and email):
        if ask is None:
            if current:
                return current
            say("missing: identity to sign approvals; run `coursekit setup --identity` in a terminal "
                "(or --name and --email)")
            return None
        name = name or ask("Your name (signs approvals)", suggestion.name if suggestion else "")
        email = email or ask("Your email", suggestion.email if suggestion else "")
    if not (name and email):
        say("missing: name and email are both needed to sign")
        return None
    set_env_value(project.env_file, "COURSEKIT_USER_NAME", name)
    set_env_value(project.env_file, "COURSEKIT_USER_EMAIL", email)
    who = identity.Identity(name, email)
    say(f"ok: you sign as {who} (saved in .env)")
    return who


def git_hooks(project: Project, say: Say) -> None:
    top = git("rev-parse", "--show-toplevel", cwd=project.root)
    if not top:
        say("info: not a git repository: no hooks")
        return
    hooks = project.root / ".githooks"
    if not hooks.is_dir():
        say("info: no .githooks/ in the project (coursekit init --update creates it)")
        return
    rel = os.path.relpath(hooks, top).replace("\\", "/")
    current = git("config", "--get", "core.hooksPath", cwd=project.root)
    if current and current != rel:
        say(f"warning: core.hooksPath is already '{current}'; not changing it")
        return
    if current != rel:
        subprocess.run(["git", "config", "core.hooksPath", rel], cwd=project.root, check=False)
        if IS_WINDOWS:
            subprocess.run(["git", "config", "core.autocrlf", "input"], cwd=project.root, check=False)
    say(f"ok: git hooks enabled ({rel})")


def ca_bundle(project: Project) -> Path | None:
    """The first configured CA certificate that exists on this machine."""
    network = config.project_data(project).get("network") or {}
    for raw in network.get("ca_bundles") or []:
        path = Path(os.path.expandvars(str(raw))).expanduser()
        if path.exists():
            return path
    return None


def persist_user_env(name: str, value: str) -> bool:
    """Persist an environment variable for the user (registry on Windows, shell rc elsewhere)."""
    if IS_WINDOWS:
        safe = value.replace("'", "''")
        cmd = f"[Environment]::SetEnvironmentVariable('{name}', '{safe}', 'User')"
        return subprocess.run(["powershell", "-NoProfile", "-Command", cmd], check=False).returncode == 0
    shell = os.environ.get("SHELL", "")
    rc = Path.home() / (".bashrc" if shell.endswith("bash") else ".zshrc")
    with rc.open("a", encoding="utf-8") as fh:
        fh.write(f'\n# coursekit (TLS-inspecting proxy)\nexport {name}="{value}"\n')
    return True


def network(project: Project, say: Say, confirm: Callable[[str], bool] | None) -> None:
    cert = ca_bundle(project)
    if cert is None:
        return
    os.environ.setdefault("UV_NATIVE_TLS", "1")
    if os.environ.get("NODE_EXTRA_CA_CERTS"):
        say("ok: corporate CA certificate configured (NODE_EXTRA_CA_CERTS)")
        return
    say(f"info: corporate CA certificate found ({cert}): Claude Code, opencode and npm need NODE_EXTRA_CA_CERTS")
    if confirm and confirm("Set NODE_EXTRA_CA_CERTS (and UV_NATIVE_TLS=1) for your user?"):
        ok = persist_user_env("NODE_EXTRA_CA_CERTS", str(cert)) and persist_user_env("UV_NATIVE_TLS", "1")
        os.environ["NODE_EXTRA_CA_CERTS"] = str(cert)
        say("ok: set; open new terminals and restart the agent tools" if ok else "warning: could not set it; do it by hand")
    else:
        say(f'info: set it yourself: NODE_EXTRA_CA_CERTS="{cert}" and UV_NATIVE_TLS=1')


def system_packages(say: Say) -> None:
    if IS_MAC:
        if not shutil.which("brew"):
            say("warning: Homebrew not found (https://brew.sh); then repeat coursekit setup --media")
            return
        missing = [t for t in BREW if not shutil.which(t)]
        if missing:
            subprocess.run(["brew", "install", *missing], check=False)
        say("ok: " + ", ".join(BREW))
    elif IS_WINDOWS:
        if not shutil.which("winget"):
            say("warning: winget not found (App Installer); install by hand: " + ", ".join(WINGET))
            return
        for tool, package in WINGET.items():
            if shutil.which(tool):
                continue
            code = subprocess.run(["winget", "install", "--id", package, "-e", "--silent",
                                   "--accept-package-agreements", "--accept-source-agreements"], check=False).returncode
            say(f"{'ok' if code == 0 else 'warning'}: {tool} ({package})")
        say("info: asciinema has no Windows build (terminal demos fall back to VHS)")
    else:
        missing = [p for p in APT if not shutil.which(p.replace("nodejs", "node"))]
        if missing:
            say("info: install with your package manager, e.g.: sudo apt install " + " ".join(missing))
        if not shutil.which("vhs"):
            say("info: install vhs: https://github.com/charmbracelet/vhs")


def media_tools(say: Say) -> None:
    """Piper and stable-ts as separate uv tools (Python 3.12): heavy, and only for media."""
    uv = shutil.which("uv")
    if not uv:
        say("warning: uv not found (https://docs.astral.sh/uv/); media tools not installed")
        return
    for command, package in MEDIA_TOOLS.items():
        if shutil.which(command):
            say(f"ok: {command}")
            continue
        code = subprocess.run([uv, "tool", "install", "--python", "3.12", package], check=False).returncode
        say(f"{'ok' if code == 0 else 'warning'}: {package}")


def voices_dir() -> Path:
    if IS_WINDOWS:
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "piper"
    return Path.home() / ".local" / "share" / "piper"


def piper_voice(project: Project, say: Say) -> None:
    language = str(config.project_data(project).get("content_language") or "es")
    folder_url, speaker, quality = PIPER_DEFAULT.get(language, PIPER_DEFAULT["es"])
    folder = voices_dir()
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{folder_url.split('/')[-1]}-{speaker}-{quality}"
    try:
        for suffix in (".onnx", ".onnx.json"):
            target = folder / f"{name}{suffix}"
            if not target.exists():
                urllib.request.urlretrieve(f"{PIPER_VOICES}/{folder_url}/{speaker}/{quality}/{name}{suffix}", target)
    except OSError as exc:
        say(f"warning: could not download the Piper voice ({exc})")
        return
    if not os.environ.get("PIPER_VOICE"):
        set_env_value(project.env_file, "PIPER_VOICE", str(folder / f"{name}.onnx"))
    say(f"ok: Piper draft voice {name}")


def run(project: Project, say: Say, ask: Ask | None, confirm: Callable[[str], bool] | None, *,
        identity_only: bool = False, media: bool = False, name: str | None = None, email: str | None = None) -> int:
    env_file(project, say)
    envfile.load(project.env_file)
    who = setup_identity(project, say, ask, name, email, force=identity_only)
    if identity_only:
        return 0 if who else 1
    network(project, say, confirm)
    git_hooks(project, say)
    report = agentsmod.generate(project)
    say(f"ok: skills, commands and agent settings ({len(report.written)} updated)")
    if not shutil.which("node"):
        say("info: Node downloads the web links of brief/links.md (coursekit setup --media installs it)")
    if media:
        say("== media tools")
        system_packages(say)
        media_tools(say)
        piper_voice(project, say)
    say("done: run `coursekit doctor` to check everything")
    return 0
