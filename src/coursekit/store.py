"""The per-machine store of coursekit: what is installed once for every project, and the record of what `setup` installed.

Where: `COURSEKIT_HOME`, else the user's data folder (`~/Library/Application Support/coursekit` on macOS,
`$XDG_DATA_HOME/coursekit` or `~/.local/share/coursekit` on Linux, `%LOCALAPPDATA%\\coursekit` on Windows).

- `workspaces/<name>-<hash>/`: a Node workspace (the Remotion one, the HTML builder) installed once with `npm install`.
  The hash is that of its `package.json` (and lock file): projects with the same dependencies share the install, and a
  project that adds its own dependencies gets another. A project keeps its sources and a `node_modules` link to it
  (a symbolic link, a junction on Windows).
- `installed.json`: what `coursekit setup` installed outside the projects (uv tools, voice files, lines added to the shell
  files, user variables of Windows, system packages), so `coursekit uninstall` can take it away.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from coursekit.i18n import t

Say = Callable[[str], None]
RECORD_KINDS = ("uv_tools", "files", "shell_lines", "windows_env", "system", "workspaces")


def home() -> Path:
    override = os.environ.get("COURSEKIT_HOME", "").strip()
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "coursekit"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "coursekit"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "coursekit"


def workspaces_dir() -> Path:
    return home() / "workspaces"


def size(path: Path) -> int:
    """Bytes under a folder (links are not followed)."""
    if not path.exists():
        return 0
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).lstat().st_size
            except OSError:
                pass
    return total


def human(nbytes: int) -> str:
    value = float(nbytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1000 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1000
    return f"{nbytes} B"


# ── the record of what setup installed ───────────────────────────────────────────────────────

def registry_path() -> Path:
    return home() / "installed.json"


def registry() -> dict[str, list]:
    try:
        data = json.loads(registry_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    return {kind: list(data.get(kind) or []) for kind in RECORD_KINDS}


def record(kind: str, value: object) -> None:
    """Remember that setup installed `value` (a name, a path, a {file, line} or {manager, packages})."""
    data = registry()
    if value not in data[kind]:
        data[kind].append(value)
        registry_path().parent.mkdir(parents=True, exist_ok=True)
        registry_path().write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def forget(kind: str, value: object) -> None:
    data = registry()
    if value in data[kind]:
        data[kind].remove(value)
        registry_path().write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


# ── Node workspaces installed once ───────────────────────────────────────────────────────────

def workspace_key(package_json: Path) -> str:
    digest = hashlib.sha256(package_json.read_bytes())
    lock = package_json.with_name("package-lock.json")
    if lock.exists():
        digest.update(lock.read_bytes())
    return digest.hexdigest()[:12]


def ensure_workspace(name: str, package_json: Path, say: Say) -> Path | None:
    """The store workspace for this `package.json`, installed with npm the first time; None if it cannot be installed."""
    folder = workspaces_dir() / f"{name}-{workspace_key(package_json)}"
    if (folder / "node_modules").is_dir():
        return folder
    npm = shutil.which("npm")
    if not npm:
        say(t("setup", "npm_missing"))
        return None
    folder.mkdir(parents=True, exist_ok=True)
    for source in (package_json, package_json.with_name("package-lock.json")):
        if source.exists():
            shutil.copy2(source, folder / source.name)
    say(t("setup", "workspace_installing", path=folder))
    code = subprocess.run([npm, "install", "--silent"], cwd=folder, check=False).returncode
    if code != 0 or not (folder / "node_modules").is_dir():
        shutil.rmtree(folder, ignore_errors=True)
        return None
    record("workspaces", folder.name)
    return folder


def _make_link(link: Path, target: Path) -> bool:
    try:
        if os.name == "nt":
            import _winapi

            _winapi.CreateJunction(str(target), str(link))
        else:
            link.symlink_to(target, target_is_directory=True)
    except (OSError, ImportError, AttributeError):
        return False
    return True


def link_node_modules(project_dir: Path, workspace: Path) -> str:
    """`node_modules` of a project folder pointing at the store: 'linked', 'kept' (the project has its own install) or 'failed'."""
    link, target = project_dir / "node_modules", workspace / "node_modules"
    if link.is_symlink() or link.is_junction():
        if link.resolve() == target.resolve():
            return "linked"
        link.unlink() if link.is_symlink() else os.rmdir(link)
    elif link.exists():
        return "kept"
    return "linked" if _make_link(link, target) else "failed"
