"""The icon set of the project: the icons of its design system (`theme/branding/icons/`, which `coursekit brand` fills from the
brand material), plus the ones `/define-theme` and the media agent draw with the rules of the guide for icons. Every icon of
every course comes from this set, so they all speak the same language.

- `index`: `icons/index.json`, each icon with the words it is found by (its name and the `<title>`/`<desc>` of the SVG), and a
  contact sheet (`icons/sheet.svg`, and its PNG when there is a browser) for the agent to see them.
- `find`: the icons of the set that say a term (`coursekit media icons CODE --find "lock"`).
- `base_find` / `base_take`: the shape of an icon of a free set (`media › icons › base`, Lucide by default, ISC licence) to
  start from when the set lacks one: it is redrawn with the stroke, corners and grid of the brand, never used as it is.
  Taking one records its licence in `icons/LICENSES.md`."""

from __future__ import annotations

import base64
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, cast

from coursekit import http, store
from coursekit.i18n import t

INDEX = "index.json"
SHEET = "sheet.svg"
LICENSES = "LICENSES.md"
CDN = "https://unpkg.com/{package}@{version}/{path}"


class IconError(Exception):
    pass


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()


def _words(text: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9]+", _plain(text)) if len(w) > 1]


def folder(brand_folder: Path) -> Path:
    return brand_folder / "icons"


def icon_files(brand_folder: Path) -> list[Path]:
    base = folder(brand_folder)
    return sorted(p for p in base.rglob("*.svg") if p.name != SHEET and "base" not in p.relative_to(base).parts[:-1]) \
        if base.is_dir() else []


def _described(svg: str) -> list[str]:
    found = re.findall(r"<(?:title|desc)[^>]*>(.*?)</(?:title|desc)>", svg, flags=re.S | re.I)
    return [w for text in found for w in _words(re.sub(r"<[^>]+>", " ", text))]


def index(brand_folder: Path) -> list[dict]:
    """Write `icons/index.json` (and the contact sheet) from the SVG files of the set. Returns its entries."""
    base = folder(brand_folder)
    entries = []
    for path in icon_files(brand_folder):
        svg = path.read_text(encoding="utf-8", errors="replace")
        words = list(dict.fromkeys(_words(path.stem) + _described(svg)))
        entries.append({"name": path.stem, "file": path.relative_to(base).as_posix(), "words": words})
    if entries:
        base.mkdir(parents=True, exist_ok=True)
        (base / INDEX).write_text(json.dumps(entries, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        (base / SHEET).write_text(sheet(base, entries), encoding="utf-8")
    return entries


def sheet(base: Path, entries: list[dict], columns: int = 10, cell: int = 120) -> str:
    """Every icon of the set in one drawing, with its name under it: what the agent looks at to choose one."""
    rows = (len(entries) + columns - 1) // columns
    parts = []
    for k, entry in enumerate(entries):
        x, y = (k % columns) * cell, (k // columns) * cell
        data = base64.b64encode((base / entry["file"]).read_bytes()).decode()
        parts.append(f'<image x="{x + cell * 0.3:g}" y="{y + cell * 0.12:g}" width="{cell * 0.4:g}" height="{cell * 0.4:g}" '
                     f'href="data:image/svg+xml;base64,{data}"/>'
                     f'<text x="{x + cell / 2:g}" y="{y + cell * 0.8:g}" font-size="11" text-anchor="middle" '
                     f'font-family="system-ui, sans-serif" fill="#333">{entry["name"][:18]}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{columns * cell}" height="{max(rows, 1) * cell}" '
            f'viewBox="0 0 {columns * cell} {max(rows, 1) * cell}"><rect width="100%" height="100%" fill="#fff"/>'
            + "".join(parts) + "</svg>")


def _score(term: str, name: str, words: list[str]) -> int:
    wanted = _words(term)
    if not wanted:
        return 0
    joined = _plain(name)
    named = _words(name)
    score = sum(4 for w in wanted if w in named)
    score += 3 if named and set(named) <= set(wanted) else 0  # the icon is exactly that, not something with it
    score += sum(2 for w in wanted if w in words)
    score += sum(1 for w in wanted if w in joined)
    return score


def find(brand_folder: Path, term: str, limit: int = 12) -> list[dict]:
    """The icons of the set that best say `term` (the index is written again first, so a new icon is found)."""
    entries = index(brand_folder)
    scored = [(_score(term, e["name"], e["words"]), e) for e in entries]
    return [e for s, e in sorted(scored, key=lambda x: -x[0]) if s > 0][:limit]


# ── The shapes of a free set, to start from ────────────────────────────────────────────────────

def _base_dir(cfg: dict) -> Path:
    return store.home() / "icons" / f"{cfg['package']}-{cfg['version']}"


def _fetch(url: str) -> bytes:
    try:
        return http.request(url, timeout=60).body
    except http.HttpError as exc:
        raise IconError(t("icons", "download_failed", url=url, reason=f"{exc.status} {exc.reason}")) from None
    except http.NetworkError as exc:
        raise IconError(t("icons", "download_failed", url=url, reason=exc.reason)) from None


def _tags(cfg: dict) -> dict[str, list[str]]:
    path = _base_dir(cfg) / "tags.json"
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_fetch(CDN.format(package=cfg["package"], version=cfg["version"], path=cfg.get("tags", "tags.json"))))
    return cast("dict[str, list[str]]", json.loads(path.read_text(encoding="utf-8")))


def base_find(cfg: dict, term: str, limit: int = 12) -> list[dict]:
    """The icons of the free set whose name or tags say `term` (in English, the language of its tags)."""
    tags = _tags(cfg)
    scored = [(_score(term, name, [w for tag in words for w in _words(tag)]), name) for name, words in tags.items()]
    return [{"name": name, "tags": tags[name][:6]} for s, name in sorted(scored, key=lambda x: (-x[0], x[1])) if s > 0][:limit]


def base_take(cfg: dict, name: str, brand_folder: Path, out: Path) -> Path:
    """Download the shape `name` of the free set to `out` (to be redrawn with the rules of the brand) and record its licence in
    the icon set of the project."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        raise IconError(t("icons", "bad_name", name=name))
    if name not in _tags(cfg):
        raise IconError(t("icons", "not_in_base", name=name, package=cfg["package"]))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(_fetch(CDN.format(package=cfg["package"], version=cfg["version"],
                                      path=str(cfg.get("icons", "icons/{name}.svg")).format(name=name))))
    _record_licence(cfg, folder(brand_folder))
    return out


def _record_licence(cfg: dict, base: Path) -> None:
    path = base / LICENSES
    marker = f"<!-- {cfg['package']} -->"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if marker in text:
        return
    licence = _fetch(CDN.format(package=cfg["package"], version=cfg["version"], path=cfg.get("license_file", "LICENSE"))).decode(
        "utf-8", "replace").strip()
    base.mkdir(parents=True, exist_ok=True)
    entry = (f"{marker}\n## {cfg['package']} {cfg['version']} ({cfg.get('license', '')})\n\n"
             f"Some icons of this folder are redrawn from the shapes of this set.\n\n```\n{licence}\n```\n")
    path.write_text((text.rstrip() + "\n\n" if text else "# Licences of the shapes the icons start from\n\n") + entry,
                    encoding="utf-8")


def settings(cfg: dict[str, Any]) -> dict[str, Any]:
    """`media › icons › base`, with its defaults."""
    base = dict((cfg.get("icons") or {}).get("base") or {})
    base.setdefault("package", "lucide-static")
    base.setdefault("version", "1.66.0")
    base.setdefault("license", "ISC")
    return base
