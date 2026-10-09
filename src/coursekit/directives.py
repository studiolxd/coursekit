"""`coursekit directives check FILE`: compare the directive registry with the creator brick catalog.

The agent saves the output of the slxd MCP tool `list_brick_types` to a JSON file. Reports
creator bricks that are neither a directive nor in `not_directives` (new in creator), and
registry entries whose brick no longer exists (removed).
"""

from __future__ import annotations

import json
from pathlib import Path

from coursekit.i18n import t


class CatalogError(Exception):
    pass


def creator_bricks(path: Path) -> dict[str, dict]:
    if not path.is_file():
        raise CatalogError(t("directives", "catalog_missing", path=path.as_posix()))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise CatalogError(t("directives", "not_a_catalog", path=path.as_posix())) from exc
    if not isinstance(data, dict):
        raise CatalogError(t("directives", "not_a_catalog", path=path.as_posix()))
    for key in ("result", "structuredContent"):
        if "categories" not in data and isinstance(data.get(key), dict):
            data = data[key]
    bricks = {}
    for category in data.get("categories", []):
        for item in category.get("types", []):
            bricks[item["type"]] = {"category": category.get("category"), "whenToUse": item.get("whenToUse")}
    if not bricks:
        raise CatalogError(t("directives", "not_a_catalog", path=path.as_posix()))
    return bricks


def check(registry: dict, catalog: Path) -> tuple[list[str], list[str], int]:
    """(lines for new bricks, lines for removed ones, number of creator bricks)."""
    mapped = {d["brick"]: name for name, d in (registry.get("directives") or {}).items()}
    ignored = set(registry.get("not_directives") or {})
    creator = creator_bricks(catalog)
    new = [
        t("directives", "new_brick", brick=b, category=creator[b]["category"], when=creator[b]["whenToUse"])
        for b in sorted(set(creator) - set(mapped) - ignored)
    ]
    removed = [
        t("directives", "removed_directive", brick=b, directive=repr(mapped[b]))
        if b in mapped
        else t("directives", "removed_ignored", brick=b)
        for b in sorted((set(mapped) | ignored) - set(creator))
    ]
    return new, removed, len(creator)
