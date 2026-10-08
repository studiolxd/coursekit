"""`coursekit directives check FILE`: compare the directive registry with the creator brick catalog.

The agent saves the output of the slxd MCP tool `list_brick_types` to a JSON file. Reports
creator bricks that are neither a directive nor in `not_directives` (new in creator), and
registry entries whose brick no longer exists (removed).
"""

from __future__ import annotations

import json
from pathlib import Path


class CatalogError(Exception):
    pass


def creator_bricks(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("result", "structuredContent"):
        if "categories" not in data and isinstance(data.get(key), dict):
            data = data[key]
    bricks = {}
    for category in data.get("categories", []):
        for item in category.get("types", []):
            bricks[item["type"]] = {"category": category.get("category"), "whenToUse": item.get("whenToUse")}
    if not bricks:
        raise CatalogError(f"{path} does not look like a list_brick_types result (no 'categories')")
    return bricks


def check(registry: dict, catalog: Path) -> tuple[list[str], list[str], int]:
    """(lines for new bricks, lines for removed ones, number of creator bricks)."""
    mapped = {d["brick"]: name for name, d in (registry.get("directives") or {}).items()}
    ignored = set(registry.get("not_directives") or {})
    creator = creator_bricks(catalog)
    new = [f"NEW     {b} [{creator[b]['category']}] {creator[b]['whenToUse']}" for b in sorted(set(creator) - set(mapped) - ignored)]
    removed = [f"REMOVED {b} (in {f'directive {mapped[b]!r}' if b in mapped else 'not_directives'})"
               for b in sorted((set(mapped) | ignored) - set(creator))]
    return new, removed, len(creator)
