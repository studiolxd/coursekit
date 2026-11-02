"""The optional extras of the package and the command that installs one without losing the others.

`uv tool install --force "slxd-coursekit[capture]"` replaces the installed tool: an extra installed before and not named again is
removed. Every message that asks for an extra gives the command with the extras already installed plus the one missing.
"""

from __future__ import annotations

import importlib.util

from coursekit.updatecheck import PACKAGE

# Each extra and the modules that tell whether it is installed (all of them must be importable).
EXTRAS = {
    "docs": ("markitdown",),
    "capture": ("playwright", "pyte"),
}


def has(extra: str) -> bool:
    return all(importlib.util.find_spec(module) is not None for module in EXTRAS[extra])


def installed() -> list[str]:
    return [name for name in EXTRAS if has(name)]


def install_command(*needed: str) -> str:
    """The command that installs the extras `needed` and keeps the ones already installed."""
    names = [name for name in EXTRAS if name in needed or has(name)]
    return f'uv tool install --force "{PACKAGE}[{",".join(names)}]"'
