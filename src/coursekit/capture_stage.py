"""The stages of the terminal captures: the environment a recording needs, mounted from scratch before each session.

A stage lives with the course, in `media/stages/<name>/`: its `stage.yaml` (what it is and how it is set up) and `files/`
(the project as it starts, written by the media agent with invented data). Before a session coursekit copies `files/` to
`<home>/<folder>/<name>`, runs the `setup` of the stage and the `prepare` of the resource there (not recorded), and starts the
shell in it. So every take starts clean, and it can be repeated.

    title: Recipe website with a search that ignores accents
    folder: projects        # inside the home folder (default capture.yaml › terminal.folder)
    setup:
      - git init -q && git add -A && git commit -qm "First version"
    home: real              # real: the home of the person (the settings and the session of the programs); clean: an empty one
    hide: [opencode]        # commands that are not on the PATH (a machine without the program)
    env: {}

coursekit writes down the folders it made (in its cache, outside the project) and never deletes or overwrites one that is
not its own. The shell starts with no startup files of the person (`bash --noprofile --norc`), a short prompt, the language
of the course and an invented author for git.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from coursekit import capture as capturemod
from coursekit import course as coursemod
from coursekit import lang, pii
from coursekit.i18n import t
from coursekit.util import slugify

NAME_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789-"


class StageError(Exception):
    pass


@dataclass
class Workspace:
    folder: Path  # where the shell starts
    home: Path
    env: dict[str, str]
    argv: list[str]


def stage_dir(course: dict, name: str) -> Path:
    return course["_dir"] / "media" / "stages" / name


def check_name(name: str) -> str:
    name = str(name or "").strip()
    if not name or any(c not in NAME_CHARS for c in name):
        raise StageError(t("capture", "stage_bad_name", name=name))
    return name


def load(course: dict, name: str) -> dict:
    """The `stage.yaml` of a stage of the course."""
    folder = stage_dir(course, check_name(name))
    spec_file = folder / "stage.yaml"
    if not spec_file.is_file():
        raise StageError(t("capture", "stage_missing", name=name, path=spec_file.relative_to(course["_dir"]).as_posix()))
    try:
        spec = yaml.safe_load(spec_file.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise StageError(t("capture", "stage_bad_file", name=name, error=str(exc).splitlines()[0])) from None
    if not isinstance(spec, dict):
        raise StageError(t("capture", "stage_bad_file", name=name, error="—"))
    home = str(spec.get("home") or "real")
    if home not in ("real", "clean"):
        raise StageError(t("capture", "stage_bad_home", name=name, value=home))
    return spec


def _registry(project) -> Path:
    return capturemod.base_dir(project) / "stages.json"


def _ours(project) -> set[str]:
    try:
        return set(json.loads(_registry(project).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def _remember(project, folder: Path) -> None:
    folders = _ours(project) | {str(folder)}
    path = _registry(project)
    capturemod._private_dir(path.parent)
    path.write_text(json.dumps(sorted(folders), indent=1) + "\n", encoding="utf-8")


def _clear(project, folder: Path) -> None:
    """Empties a folder coursekit made before; refuses one that exists and is not its own."""
    if folder.exists() or folder.is_symlink():
        if str(folder) not in _ours(project):
            raise StageError(t("capture", "stage_not_ours", path=folder.as_posix()))
        if folder.is_symlink() or folder.is_file():
            folder.unlink()
        else:
            shutil.rmtree(folder)


def _path_without(path_value: str, hidden: list[str], shims: Path) -> str:
    """The PATH with the hidden commands left out: a folder that has one is replaced by links to everything else in it."""
    if not hidden:
        return path_value
    shutil.rmtree(shims, ignore_errors=True)
    out = []
    for n, entry in enumerate(p for p in path_value.split(os.pathsep) if p):
        folder = Path(entry)
        if not any((folder / name).exists() for name in hidden):
            out.append(entry)
            continue
        shim = shims / f"{n:02d}-{slugify(entry)[:40]}"
        shim.mkdir(parents=True, exist_ok=True)
        for item in folder.iterdir():
            if item.name not in hidden:
                try:
                    (shim / item.name).symlink_to(item)
                except OSError:
                    continue
        out.append(str(shim))
    return os.pathsep.join(out)


def author(course: dict) -> tuple[str, str]:
    """The invented author of the commits made in a stage."""
    who = pii.people(coursemod.language(course))
    first, last = who.women[0], who.last_names[0]
    return f"{first} {last}", f"{pii._ascii(first)}.{pii._ascii(last)}@{who.email_domain}"


def environment(project, course: dict, name: str, spec: dict, home: Path) -> dict[str, str]:
    """What the shell of the stage starts with: the variables of this machine (none of coursekit or of the AI tool), the home
    of the stage, a short prompt, the language of the course, an invented git author and the PATH without what it hides."""
    env = {k: v for k, v in os.environ.items()  # the marks of the AI tool that runs coursekit, which the program would see
           if not k.startswith(("COURSEKIT_", "CLAUDECODE", "CLAUDE_CODE_")) and k != "OPENCODE"}
    who, email = author(course)
    locale = str(lang.tokens(coursemod.language(course)).get("locale") or "en_US.UTF-8")
    env.update({"HOME": str(home), "TERM": "xterm-256color", "COLORTERM": "truecolor", "LANG": locale, "LC_ALL": locale,
                "PS1": r"\W $ ", "BASH_SILENCE_DEPRECATION_WARNING": "1", "GIT_AUTHOR_NAME": who, "GIT_AUTHOR_EMAIL": email,
                "GIT_COMMITTER_NAME": who, "GIT_COMMITTER_EMAIL": email})
    if spec.get("home") == "clean":
        env.update({"GIT_CONFIG_GLOBAL": str(home / ".gitconfig"), "XDG_CONFIG_HOME": str(home / ".config"),
                    "XDG_DATA_HOME": str(home / ".local" / "share"), "XDG_CACHE_HOME": str(home / ".cache"),
                    "XDG_STATE_HOME": str(home / ".local" / "state")})
    shims = capturemod.base_dir(project) / "shims" / f"{slugify(course['code'])}-{name}"
    env["PATH"] = _path_without(env.get("PATH", ""), [str(h) for h in spec.get("hide") or []], shims)
    env.update({str(k): str(v) for k, v in (spec.get("env") or {}).items()})
    return env


def _run(command: str, folder: Path, env: dict[str, str], timeout: int) -> None:
    try:
        done = subprocess.run(["bash", "--noprofile", "--norc", "-c", command], cwd=str(folder), env=env, capture_output=True,
                              text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        raise StageError(t("capture", "stage_timeout", command=command, seconds=timeout)) from None
    if done.returncode != 0:
        last = (done.stderr.strip() or done.stdout.strip()).splitlines()[-1:] or ["—"]
        raise StageError(t("capture", "stage_failed", command=command, code=done.returncode, reason=last[0]))


def mount(project, course: dict, name: str, prepare: list[str] | None = None) -> Workspace:
    """Mounts the stage from scratch: its files in `<home>/<folder>/<name>`, its setup and the prepare of the resource."""
    cfg = capturemod.settings(project)
    terminal = dict(cfg.get("terminal") or {})
    spec = load(course, name)
    if spec.get("home") == "clean":
        home = capturemod.base_dir(project) / "homes" / f"{slugify(course['code'])}-{name}"
        shutil.rmtree(home, ignore_errors=True)
        home.mkdir(parents=True)
    else:
        home = Path.home()
    folder_name = str(spec.get("folder") or terminal.get("folder") or "projects").strip("/")
    folder = home / folder_name / name
    _clear(project, folder)
    source = stage_dir(course, name) / "files"
    if source.is_dir():
        shutil.copytree(source, folder, symlinks=True)
    else:
        folder.mkdir(parents=True)
    _remember(project, folder)
    env = environment(project, course, name, spec, home)
    timeout = int(terminal.get("setup_timeout") or 600)
    for command in [*(spec.get("setup") or []), *(prepare or [])]:
        _run(str(command), folder, env, timeout)
    return Workspace(folder, home, env, ["bash", "--noprofile", "--norc", "-i"])

