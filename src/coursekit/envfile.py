"""Read the personal `.env` of a project (keys, models, local paths, identity).

The real environment always wins: a value already set in the shell is never overridden.
"""

from __future__ import annotations

import os
from pathlib import Path


def parse(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip().removeprefix("export ").strip(), value.strip()
        if value[:1] in ("'", '"') and value[0] in value[1:]:
            value = value[1 : value.index(value[0], 1)]  # quoted: keep as is, drop what follows
        else:
            value = value.split(" #", 1)[0].split("\t#", 1)[0].strip()  # unquoted: drop inline comment
            if value.startswith("#"):
                value = ""
        values[key] = value
    return values


def load(path: Path) -> dict[str, str]:
    """Load the file into os.environ without overriding it (an empty value counts as not set); return what the file defines."""
    if not path.exists():
        return {}
    values = parse(path.read_text(encoding="utf-8"))
    for key, value in values.items():
        if value:
            os.environ.setdefault(key, value)
    return values
