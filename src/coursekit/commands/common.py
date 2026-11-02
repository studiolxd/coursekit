"""Helpers the commands share: the project, the catalog and the mirror folder, a confirmation."""


from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path

from coursekit import catalog as catalogmod
from coursekit import (
    envfile,
)
from coursekit import publish as publishmod
from coursekit.i18n import t
from coursekit.project import Project, find_project


def project() -> Project:
    project = find_project()
    envfile.load(project.env_file)
    return project

def local_catalog(project: Project) -> Path:
    return project.root / "courses" / catalogmod.file_name(project)

def mirror(project: Project, code: str) -> None:
    """Bring the catalog of the project and the mirror folder up to date after a command that changed the course.

    The catalog in `courses/` is kept up to date, silently (and only written when its data changed). Nothing else happens when
    the project has no mirror; a catalog or a mirror that cannot be written is a warning, never a failure of the command that
    already did its work. The sessions of the agents without an interface (`COURSEKIT_MIRROR=deferred`) leave it to whoever
    started them, which does it once when the session ends instead of after every command the agent runs.
    """
    if os.environ.get("COURSEKIT_MIRROR") == "deferred":
        return
    try:
        catalogmod.build(project, local_catalog(project))
    except OSError as exc:
        print(t("commands", "catalog_not_updated", text=exc), file=sys.stderr)
    try:
        for line in publishmod.publish(project, code, only_if_configured=True):
            print(line)
    except (publishmod.PublishError, OSError) as exc:
        print(t("commands", "mirror_not_updated", text=exc), file=sys.stderr)

def confirm(yes: bool) -> Callable[[str], bool]:
    def ask(question: str) -> bool:
        print(question)
        if yes:
            print(t("commands", "confirmed_yes"))
            return True
        while True:
            answer = input(t("commands", "confirm_prompt")).strip().lower()
            if answer in ("y", "yes", "s", "si", "sí"):
                return True
            if answer in ("", "n", "no"):
                return False

    return ask
