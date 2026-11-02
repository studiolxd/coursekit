"""The reference of the commands (`docs/<lang>/03-commands.md`) for `coursekit help COMMAND`.

The wheel carries the file as `coursekit/manual/<lang>/03-commands.md` (pyproject.toml › force-include); a clone reads it from
`docs/`."""

from __future__ import annotations

import re
from importlib import resources
from pathlib import Path

FILE = "03-commands.md"


def reference(language: str) -> str | None:
    packaged = resources.files("coursekit").joinpath("manual", language, FILE)
    if packaged.is_file():
        return packaged.read_text(encoding="utf-8")
    clone = Path(__file__).resolve().parents[2] / "docs" / language / FILE
    return clone.read_text(encoding="utf-8") if clone.is_file() else None


def section(command: str, language: str) -> str | None:
    """The part of the reference about `coursekit COMMAND`: from its heading to the next heading of the same level or higher."""
    text = reference(language)
    if text is None:
        return None
    found = re.search(rf"^### `coursekit {re.escape(command)}`\n.*?(?=^#{{1,3}} |\Z)", text, re.M | re.S)
    return found.group(0).rstrip() if found else None
