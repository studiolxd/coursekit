"""Locate a coursekit project and its folders.

A project is a folder with a `project.yaml` at its root. Commands can run from any folder
inside it: the root is found by walking up, the way git finds `.git`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_FILE = "project.yaml"
ROOT_ENV = "COURSEKIT_PROJECT"  # explicit project root, overrides the search


class ProjectNotFound(Exception):
    def __init__(self, start: Path):
        super().__init__(start)
        self.start = start

    def __str__(self) -> str:
        # Translated when shown, not when raised: i18n itself looks for the project to choose the language,
        # and it imports this module (hence the lazy import).
        from coursekit.i18n import t

        return t("project", "not_found", file=PROJECT_FILE, start=self.start)


@dataclass(frozen=True)
class Project:
    root: Path

    @property
    def file(self) -> Path:
        return self.root / PROJECT_FILE

    @property
    def config_dir(self) -> Path:
        return self.root / "config"

    @property
    def courses_dir(self) -> Path:
        return self.root / "courses"

    @property
    def brief_dir(self) -> Path:
        return self.root / "brief"

    @property
    def theme_dir(self) -> Path:
        return self.root / "theme"

    @property
    def cache_dir(self) -> Path:
        return self.root / ".cache"

    @property
    def env_file(self) -> Path:
        return self.root / ".env"

    def course_dir(self, code_or_path: str) -> Path:
        """Accept a course code (ABC101) or a path to the course folder."""
        path = Path(code_or_path)
        if (path / "course.yaml").exists():
            return path.resolve()
        return self.courses_dir / code_or_path

    def iter_courses(self) -> list[Path]:
        return sorted(p.parent for p in self.courses_dir.glob("*/course.yaml"))


def find_root(start: Path | None = None) -> Path:
    explicit = os.environ.get(ROOT_ENV)
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if (root / PROJECT_FILE).exists():
            return root
        raise ProjectNotFound(root)
    here = (start or Path.cwd()).resolve()
    for folder in (here, *here.parents):
        if (folder / PROJECT_FILE).exists():
            return folder
    raise ProjectNotFound(here)


def find_project(start: Path | None = None) -> Project:
    return Project(find_root(start))
