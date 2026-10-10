"""A project follows the installed coursekit: the first command after an update refreshes what coursekit generates in it.

What is shipped inside the package (skills, commands and agents, project templates, default rules, language files) is fingerprinted.
The fingerprint of the last refresh on this machine is kept in `.coursekit/refreshed.json` (not versioned). When it differs from the
installed one, the managed files (`coursekit init --update`) and the generated agent files (`coursekit agents`) are regenerated
before the command runs. What belongs to the project is never touched."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from coursekit import __version__, envfile
from coursekit import agents as agentsmod
from coursekit import init as initmod
from coursekit.i18n import t
from coursekit.project import Project

STAMP_FILE = Path(".coursekit") / "refreshed.json"
OFF_ENV = "COURSEKIT_NO_REFRESH"
SHIPPED = ("agentkit", "templates", "defaults", "lang")  # folders of the package that end up in a project
# Commands that already refresh (or have nothing to refresh) by themselves.
SKIP = {None, "help", "init", "agents"}


def fingerprint() -> str:
    """Version of coursekit plus the content of everything it generates from."""
    package = Path(__file__).parent
    digest = hashlib.sha256(__version__.encode("utf-8"))
    for folder in SHIPPED:
        for path in sorted((package / folder).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                digest.update(path.relative_to(package).as_posix().encode("utf-8"))
                digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def recorded(root: Path) -> dict:
    path = root / STAMP_FILE
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_stamp(root: Path) -> None:
    path = root / STAMP_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"fingerprint": fingerprint(), "version": __version__}, indent=1) + "\n", encoding="utf-8")


def pending(root: Path) -> bool:
    return recorded(root).get("fingerprint") != fingerprint()


def ensure(root: Path) -> None:
    """Refreshes the project if the installed coursekit is not the one that generated its files. Never stops the command: if the
    refresh fails it says so and the command goes on."""
    if os.environ.get(OFF_ENV) or not pending(root):
        return
    before = recorded(root).get("version")
    try:
        report = initmod.update(root)
        project = Project(root)
        envfile.load(project.env_file)
        agents = agentsmod.generate(project)
        write_stamp(root)
    except Exception as exc:  # noqa: BLE001 — a refresh problem must not block the work; `coursekit agents` shows it in full
        print(t("refresh", "failed", error=exc), file=sys.stderr)
        return
    if before is None:  # the project had never been refreshed on this machine: say nothing unless something changed
        if not (report.created or report.updated or agents.written):
            return
    print(t("refresh", "done", version=__version__, files=len(report.created) + len(report.updated), agents=len(agents.written)),
          file=sys.stderr)
    for path in report.kept_edited:
        print(t("refresh", "kept", path=path), file=sys.stderr)
