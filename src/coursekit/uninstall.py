"""`coursekit uninstall`: take away what `coursekit setup` installed outside the projects.

It reads the record of the store (`installed.json`) and what it can recognise by itself (the lines coursekit adds to the
shell files, the uv tools of the media tools), shows each group and asks before removing it. Run it *before* removing the
package: afterwards the command no longer exists. It never touches the projects (their folders, `.env`, courses) and never
removes system packages (brew, winget): it lists them with the command to remove them by hand.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from coursekit import store
from coursekit.i18n import t
from coursekit.setup import MEDIA_TOOLS, SHELL_MARKER

Say = Callable[[str], None]
Confirm = Callable[[str], bool]
PACKAGE = "slxd-coursekit"


@dataclass
class Group:
    key: str  # catalog key of the title
    lines: list[str]
    remove: Callable[[], list[str]]
    count: int = 0


@dataclass
class Report:
    groups: list[Group] = field(default_factory=list)
    system: list[str] = field(default_factory=list)


def _rc_files() -> list[Path]:
    return [Path.home() / name for name in (".zshrc", ".bashrc")]


def _marked_lines(path: Path) -> list[int]:
    """Indexes of the marker lines coursekit wrote in a shell file."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [i for i, line in enumerate(lines) if line.strip() == SHELL_MARKER]


def _remove_shell_lines(path: Path) -> int:
    lines = path.read_text(encoding="utf-8").splitlines()
    marks = set(_marked_lines(path))
    keep = []
    skip_next = False
    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue
        if i in marks:
            skip_next = True  # the export line that follows the marker
            if keep and not keep[-1].strip():
                keep.pop()  # the blank line coursekit put before it
            continue
        keep.append(line)
    path.write_text("\n".join(keep) + ("\n" if keep else ""), encoding="utf-8", newline="\n")
    return len(marks)


def _uv_tools() -> set[str]:
    uv = shutil.which("uv")
    if not uv:
        return set()
    result = subprocess.run([uv, "tool", "list"], capture_output=True, text=True, check=False)
    return {line.split()[0] for line in result.stdout.splitlines() if line.strip() and not line.startswith(("-", " "))}


def collect() -> Report:
    data = store.registry()
    report = Report()

    folders = [p for p in sorted(store.workspaces_dir().glob("*")) if p.is_dir()] if store.workspaces_dir().is_dir() else []
    if folders:
        def remove_workspaces() -> list[str]:
            for folder in folders:
                shutil.rmtree(folder, ignore_errors=True)
                store.forget("workspaces", folder.name)
            return [t("uninstall", "removed_workspaces", count=len(folders))]

        report.groups.append(Group("group_workspaces", [t("uninstall", "item_size", path=f.as_posix(), size=store.human(store.size(f)))
                                                        for f in folders], remove_workspaces, len(folders)))

    installed = _uv_tools()
    packages = [p for p in dict.fromkeys([*data["uv_tools"], *MEDIA_TOOLS.values()]) if p in installed]
    if packages:
        def remove_tools() -> list[str]:
            out = []
            for package in packages:
                code = subprocess.run([shutil.which("uv") or "uv", "tool", "uninstall", package], check=False).returncode
                if code == 0:
                    store.forget("uv_tools", package)
                out.append(t("uninstall", "tool_removed" if code == 0 else "tool_failed", package=package))
            return out

        notes = [t("uninstall", "item_recorded" if p in data["uv_tools"] else "item_detected", item=p) for p in packages]
        report.groups.append(Group("group_tools", notes, remove_tools, len(packages)))

    files = [Path(f) for f in data["files"] if Path(f).exists()]
    if files:
        def remove_files() -> list[str]:
            parents = {f.parent for f in files}
            for f in files:
                f.unlink(missing_ok=True)
                store.forget("files", str(f))
            for parent in parents:
                try:
                    parent.rmdir()  # only when it is left empty
                except OSError:
                    pass
            return [t("uninstall", "removed_files", count=len(files))]

        report.groups.append(Group("group_files", [t("uninstall", "item_size", path=f.as_posix(), size=store.human(store.size(f.parent)
                                                    if f.is_dir() else f.stat().st_size)) for f in files], remove_files, len(files)))

    rc = [p for p in _rc_files() if _marked_lines(p)]
    if rc:
        def remove_rc() -> list[str]:
            out = []
            for path in rc:
                out.append(t("uninstall", "shell_cleaned", path=path.as_posix(), count=_remove_shell_lines(path)))
            for entry in list(data["shell_lines"]):
                store.forget("shell_lines", entry)
            return out

        report.groups.append(Group("group_shell", [t("uninstall", "item_lines", path=p.as_posix(), count=len(_marked_lines(p)))
                                                   for p in rc], remove_rc, len(rc)))

    if os.name == "nt" and data["windows_env"]:
        names = list(data["windows_env"])

        def remove_env() -> list[str]:
            for name in names:
                cmd = f"[Environment]::SetEnvironmentVariable('{name}', $null, 'User')"
                subprocess.run(["powershell", "-NoProfile", "-Command", cmd], check=False)
                store.forget("windows_env", name)
            return [t("uninstall", "removed_variables", names=", ".join(names))]

        report.groups.append(Group("group_variables", names, remove_env, len(names)))

    for entry in data["system"]:
        packages_text = " ".join(entry.get("packages") or [])
        command = f"brew uninstall {packages_text}" if entry.get("manager") == "brew" else \
            " && ".join(f"winget uninstall --id {p} -e" for p in entry.get("packages") or [])
        report.system.append(t("uninstall", "system_item", packages=packages_text, command=command))
    return report


def run(say: Say, confirm: Confirm | None, dry_run: bool = False, yes: bool = False) -> int:
    report = collect()
    say(t("uninstall", "store_line", path=store.home().as_posix()))
    if not report.groups:
        say(t("uninstall", "nothing"))
    kept_any = False
    for group in report.groups:
        say("")
        say(t("uninstall", group.key))
        for line in group.lines:
            say(f"  {line}")
        if dry_run:
            continue
        if not yes and not (confirm and confirm(t("uninstall", "ask_remove"))):
            say(t("uninstall", "kept"))
            kept_any = True
            continue
        for line in group.remove():
            say(f"  {line}")
    if report.system:
        say("")
        say(t("uninstall", "system_header"))
        for line in report.system:
            say(f"  {line}")
    if not dry_run and not kept_any:
        for entry in store.registry()["system"]:  # they were only listed above: the record has no more use
            store.forget("system", entry)
        _tidy_store()
    say("")
    say(t("uninstall", "projects_note"))
    say(t("uninstall", "last_step", package=PACKAGE))
    return 0


def _tidy_store() -> None:
    """The store itself goes when nothing of it is left but its (empty) record."""
    data = store.registry()
    if any(data[kind] for kind in store.RECORD_KINDS):
        return
    folder = store.home()
    left = [p for p in folder.glob("*") if p.name not in ("installed.json", "workspaces")] if folder.is_dir() else []
    workspaces = store.workspaces_dir()
    if left or (workspaces.is_dir() and any(workspaces.iterdir())):
        return
    shutil.rmtree(folder, ignore_errors=True)
