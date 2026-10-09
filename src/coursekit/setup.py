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
from coursekit import config, envfile, identity, store
from coursekit.i18n import t
from coursekit.project import Project
from coursekit.util import git

SHELL_MARKER = "# coursekit (TLS-inspecting proxy)"
IS_WINDOWS = os.name == "nt"
IS_MAC = sys.platform == "darwin"
BREW = ["ffmpeg", "node", "vhs", "asciinema"]
WINGET = {"ffmpeg": "Gyan.FFmpeg", "node": "OpenJS.NodeJS.LTS", "vhs": "charmbracelet.vhs"}
APT = ["ffmpeg", "nodejs", "npm", "asciinema"]
MEDIA_TOOLS = {"piper": "piper-tts", "stable-ts": "stable-ts"}  # command → package (uv tool, Python 3.12)
PIPER_VOICES = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
PIPER_DEFAULT = {"es": ("es/es_ES", "sharvard", "medium"), "en": ("en/en_GB", "alba", "medium")}

# service, its secret key, and what else it needs once the key is set
MEDIA_SERVICES = (
    ("ElevenLabs", "ELEVENLABS_API_KEY", ("ELEVENLABS_VOICE_ID",)),
    ("Azure Speech", "AZURE_SPEECH_KEY", ("AZURE_SPEECH_REGION", "AZURE_SPEECH_VOICE")),
    ("Google TTS", "GOOGLE_TTS_API_KEY", ("GOOGLE_TTS_VOICE",)),
    ("Magnific", "MAGNIFIC_API_KEY", ()),
)

Say = Callable[[str], None]
Ask = Callable[[str, str], str]


def set_env_value(path: Path, key: str, value: str, environ: bool = True) -> None:
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
    if environ:
        os.environ[key] = value


def env_file(project: Project, say: Say) -> None:
    if project.env_file.exists():
        return
    example = project.root / ".env.example"
    if example.exists():
        shutil.copyfile(example, project.env_file)
    else:
        project.env_file.write_text("", encoding="utf-8")
    say(t("setup", "env_created"))


def setup_identity(project: Project, say: Say, ask: Ask | None, name: str | None = None, email: str | None = None,
                   force: bool = False) -> identity.Identity | None:
    current = identity.current()
    if current and not force and not (name or email):
        say(t("setup", "identity_ok", who=current))
        return current
    suggestion = current or identity.suggested()
    if current and (name or email):  # changing only one of them keeps the other
        name = name or current.name
        email = email or current.email
    if not (name and email):
        if ask is None:
            if current:
                return current
            say(t("setup", "identity_no_terminal"))
            return None
        name = name or ask(t("setup", "identity_name"), suggestion.name if suggestion else "")
        email = email or ask(t("setup", "identity_email"), suggestion.email if suggestion else "")
    if not (name and email):
        say(t("setup", "identity_both"))
        return None
    set_env_value(project.env_file, "COURSEKIT_USER_NAME", name)
    set_env_value(project.env_file, "COURSEKIT_USER_EMAIL", email)
    who = identity.Identity(name, email)
    say(t("setup", "identity_saved", who=who))
    return who


def git_hooks(project: Project, say: Say) -> None:
    top = git("rev-parse", "--show-toplevel", cwd=project.root)
    if not top:
        say(t("setup", "hooks_no_repo"))
        return
    hooks = project.root / ".githooks"
    if not hooks.is_dir():
        say(t("setup", "hooks_none"))
        return
    rel = os.path.relpath(hooks, top).replace("\\", "/")
    current = git("config", "--get", "core.hooksPath", cwd=project.root)
    if current and current != rel:
        say(t("setup", "hooks_other", current=current))
        return
    if current != rel:
        subprocess.run(["git", "config", "core.hooksPath", rel], cwd=project.root, check=False)
        if IS_WINDOWS:
            subprocess.run(["git", "config", "core.autocrlf", "input"], cwd=project.root, check=False)
    say(t("setup", "hooks_ok", path=rel))


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
        done = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], check=False).returncode == 0
        if done:
            store.record("windows_env", name)
        return done
    shell = os.environ.get("SHELL", "")
    rc = Path.home() / (".bashrc" if shell.endswith("bash") else ".zshrc")
    with rc.open("a", encoding="utf-8") as fh:
        fh.write(f'\n{SHELL_MARKER}\nexport {name}="{value}"\n')
    store.record("shell_lines", {"file": str(rc), "name": name})
    return True


def network(project: Project, say: Say, confirm: Callable[[str], bool] | None) -> None:
    cert = ca_bundle(project)
    if cert is None:
        return
    os.environ.setdefault("UV_NATIVE_TLS", "1")
    if os.environ.get("NODE_EXTRA_CA_CERTS"):
        say(t("setup", "ca_ok"))
        return
    say(t("setup", "ca_found", cert=cert))
    if confirm and confirm(t("setup", "ca_question")):
        ok = persist_user_env("NODE_EXTRA_CA_CERTS", str(cert)) and persist_user_env("UV_NATIVE_TLS", "1")
        os.environ["NODE_EXTRA_CA_CERTS"] = str(cert)
        say(t("setup", "ca_set_ok" if ok else "ca_set_fail"))
    else:
        say(t("setup", "ca_manual", cert=cert))


def system_packages(say: Say) -> None:
    if IS_MAC:
        if not shutil.which("brew"):
            say(t("setup", "brew_missing"))
            return
        missing = [tool for tool in BREW if not shutil.which(tool)]
        if missing:
            if subprocess.run(["brew", "install", *missing], check=False).returncode == 0:
                store.record("system", {"manager": "brew", "packages": missing})
        say(t("setup", "ok_item", item=", ".join(BREW)))
    elif IS_WINDOWS:
        if not shutil.which("winget"):
            say(t("setup", "winget_missing", tools=", ".join(WINGET)))
            return
        for tool, package in WINGET.items():
            if shutil.which(tool):
                continue
            code = subprocess.run(["winget", "install", "--id", package, "-e", "--silent",
                                   "--accept-package-agreements", "--accept-source-agreements"], check=False).returncode
            if code == 0:
                store.record("system", {"manager": "winget", "packages": [package]})
            say(t("setup", "ok_item" if code == 0 else "warn_item", item=f"{tool} ({package})"))
        say(t("setup", "asciinema_windows"))
    else:
        missing = [p for p in APT if not shutil.which(p.replace("nodejs", "node"))]
        if missing:
            say(t("setup", "apt_hint", packages=" ".join(missing)))
        if not shutil.which("vhs"):
            say(t("setup", "vhs_hint"))


def media_tools(say: Say) -> None:
    """Piper and stable-ts as separate uv tools (Python 3.12): heavy, and only for media."""
    uv = shutil.which("uv")
    if not uv:
        say(t("setup", "uv_missing"))
        return
    for command, package in MEDIA_TOOLS.items():
        if shutil.which(command):
            say(t("setup", "ok_item", item=command))
            continue
        code = subprocess.run([uv, "tool", "install", "--python", "3.12", package], check=False).returncode
        if code == 0:
            store.record("uv_tools", package)
        say(t("setup", "ok_item" if code == 0 else "warn_item", item=package))


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
                store.record("files", str(target))
    except OSError as exc:
        say(t("setup", "piper_failed", error=exc))
        return
    if not os.environ.get("PIPER_VOICE"):
        set_env_value(project.env_file, "PIPER_VOICE", str(folder / f"{name}.onnx"))
    say(t("setup", "piper_ok", name=name))


def remotion(project: Project, say: Say) -> None:
    """Remotion workspace for videos: the sources in tools/remotion (from the package template) and its node_modules,
    installed once in the store and linked, so no project downloads Remotion and its browser again."""
    from importlib import resources

    target = project.root / "tools" / "remotion"
    if not target.exists():
        source = Path(str(resources.files("coursekit.templates.remotion")))
        shutil.copytree(source, target, ignore=shutil.ignore_patterns("__init__.py", "__pycache__"))
        say(t("setup", "remotion_workspace"))
    if not shutil.which("npm"):
        say(t("setup", "npm_missing"))
        return
    workspace = store.ensure_workspace("remotion", target / "package.json", say)
    state = store.link_node_modules(target, workspace) if workspace else "failed"
    if state == "linked":
        say(t("setup", "remotion_shared", path=workspace))
    elif state == "kept":
        say(t("setup", "remotion_kept"))
    else:  # no store or no link possible here: install in the project, as a project of its own
        code = subprocess.run([shutil.which("npm"), "install", "--silent"], cwd=target, check=False).returncode
        say(t("setup", "remotion_deps_ok" if code == 0 else "remotion_deps_fail"))


def assembly_backend(project: Project) -> str:
    return str((config.project_data(project).get("assembly") or {}).get("backend") or "creator")


def html_builder(project: Project, say: Say) -> None:
    """The builder of the html backend (the SCORM runtime and esbuild), installed once per machine in the store."""
    from importlib import resources

    package_json = Path(str(resources.files("coursekit.templates.html"))) / "package.json"
    if not shutil.which("npm"):
        say(t("setup", "npm_missing"))
        return
    workspace = store.ensure_workspace("html-builder", package_json, say)
    say(t("setup", "html_builder_ok", path=workspace) if workspace else t("setup", "html_builder_fail"))


def media_keys(project: Project, say: Say, ask: Ask, secret: Ask) -> None:
    """Ask for the optional keys of the voice and image services (Enter skips one); they go to .env."""
    say(t("setup", "keys_header"))
    saved = []
    for service, key, extras in MEDIA_SERVICES:
        if os.environ.get(key):
            say(t("setup", "key_present", key=key))
            continue
        value = secret(t("setup", "key_prompt", service=service, key=key), "")
        if not value:
            continue
        set_env_value(project.env_file, key, value)
        saved.append(key)
        for extra in extras:
            if not os.environ.get(extra):
                answer = ask(t("setup", "key_extra", key=extra), "")
                if answer:
                    set_env_value(project.env_file, extra, answer)
                    saved.append(extra)
    if saved:
        say(t("setup", "keys_saved", keys=", ".join(saved)))


def agent_roles(project: Project, say: Say, ask: Ask | None, confirm: Callable[[str], bool] | None, force: bool = False) -> None:
    """Tool and model of each role in the .env: the defaults, or the ones the person chooses.

    It runs when asked (`--roles`) or while some role has no model that we have a default for."""
    values = envfile.parse(project.env_file.read_text(encoding="utf-8")) if project.env_file.exists() else {}
    plan = {}
    for role in agentsmod.ROLES:
        key = role.upper()
        tool = values.get(f"{key}_AGENT") or agentsmod.default_tool(role)
        plan[role] = (tool, values.get(f"{key}_MODEL") or agentsmod.default_model(role, tool))
    open_roles = [r for r in agentsmod.ROLES if not values.get(f"{r.upper()}_MODEL") and plan[r][1]]
    if not (force or open_roles):
        return
    if ask and confirm:
        say(t("setup", "roles_header"))
        for role, (tool, model) in plan.items():
            say(t("setup", "roles_line", role=t("setup", f"role_{role}"), tool=tool, model=model or t("setup", "roles_default_model")))
        if not confirm(t("setup", "roles_confirm")):
            for role in agentsmod.ROLES:
                name = t("setup", f"role_{role}")
                tool, model = plan[role]
                while True:
                    tool = ask(t("setup", "role_tool", role=name, tools="/".join(agentsmod.TOOLS)), tool).lower()
                    if tool in agentsmod.TOOLS:
                        break
                    say(t("init", "choose", options=", ".join(agentsmod.TOOLS)))
                if tool != plan[role][0]:
                    model = agentsmod.default_model(role, tool)
                plan[role] = (tool, ask(t("setup", "role_model", role=name), model))
    for role, (tool, model) in plan.items():
        set_env_value(project.env_file, f"{role.upper()}_AGENT", tool)
        set_env_value(project.env_file, f"{role.upper()}_MODEL", model)
    say(t("setup", "roles_saved"))


def run(project: Project, say: Say, ask: Ask | None, confirm: Callable[[str], bool] | None, *,
        identity_only: bool = False, media: bool = False, name: str | None = None, email: str | None = None,
        secret: Ask | None = None, roles: bool = False) -> int:
    env_file(project, say)
    envfile.load(project.env_file)
    who = setup_identity(project, say, ask, name, email, force=identity_only)
    if identity_only:
        return 0 if who else 1
    network(project, say, confirm)
    git_hooks(project, say)
    agent_roles(project, say, ask, confirm, force=roles)
    report = agentsmod.generate(project)
    say(t("setup", "agents_done", count=len(report.written)))
    if not shutil.which("node"):
        say(t("setup", "node_hint"))
    if assembly_backend(project) == "html":
        html_builder(project, say)
    if not media and confirm and confirm(t("setup", "ask_media")):
        media = True
    if media:
        say(t("setup", "media_header"))
        system_packages(say)
        media_tools(say)
        piper_voice(project, say)
        remotion(project, say)
        if ask and secret:
            media_keys(project, say, ask, secret)
    from coursekit import doctor  # here: doctor imports this module

    say(doctor.render(doctor.collect(project)))
    return 0
