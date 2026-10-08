"""Who signs approvals and changes: COURSEKIT_USER_NAME / COURSEKIT_USER_EMAIL in the .env.

The git identity is only a suggestion for `coursekit setup`; signatures never depend on it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from coursekit.util import git


@dataclass(frozen=True)
class Identity:
    name: str
    email: str

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"


def current() -> Identity | None:
    name = os.environ.get("COURSEKIT_USER_NAME", "").strip()
    email = os.environ.get("COURSEKIT_USER_EMAIL", "").strip()
    return Identity(name, email) if name and email else None


def suggested() -> Identity | None:
    name, email = git("config", "user.name"), git("config", "user.email")
    return Identity(name, email) if name and email else None


def display_name() -> str:
    """Name for course history entries: the signing identity, else git, else unknown."""
    who = current() or suggested()
    return who.name if who else "unknown"
