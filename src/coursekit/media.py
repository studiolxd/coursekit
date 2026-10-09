"""`coursekit media`: extract the media placeholders of the content and plan how to produce them.

    coursekit media extract CODE     sync media/manifest.yaml with the placeholders in content.md
    coursekit media plan CODE        per pending asset, the production options available here
    coursekit media providers        which optional providers are available on this machine
    coursekit media set CODE ID …    update an asset (used by the media agent while producing)

Asset ids are U<unit>-S<section>-M<k> (k-th placeholder of the section), the same ids
`coursekit assemble` uses to swap a placeholder for its produced media.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from coursekit import config as configmod
from coursekit import course as coursemod
from coursekit import lang
from coursekit import theme as thememod
from coursekit.i18n import t
from coursekit.util import roundtrip_yaml

FIELD_KEYS = ("title", "description", "how", "specs")  # in the order of the language's placeholder_fields


class MediaError(Exception):
    pass


def in_media_tools(name: str) -> bool:
    """A media tool installed as a command (coursekit setup --media installs them with uv)."""
    return shutil.which(name) is not None


def config(project=None, course: dict | None = None) -> dict:
    return configmod.effective("media", project or (course or {}).get("_project"), course).value


def requirement_met(needs, root: Path | None = None) -> bool | None:
    """True/False for env/bin requirements; None when only the agent can tell (mcp)."""
    if needs in (None, "none"):
        return True
    results = []
    for kind, value in needs.items():
        if kind == "env":
            names = [value] if isinstance(value, str) else list(value)
            results.append(all(os.environ.get(name, "").strip() for name in names))
        elif kind == "bin":
            results.append(shutil.which(value) is not None)
        elif kind == "mcp":
            results.append(None)
        elif kind == "media":
            results.append(in_media_tools(value))
        elif kind == "path":
            results.append(root is not None and (root / value).exists())
    if False in results:
        return False
    return None if None in results else True


def options_for(kind: str, cfg: dict, root: Path | None = None) -> list[dict]:
    chain = []
    for option in cfg["types"].get(kind, []):
        met = requirement_met(option.get("needs"), root)
        if met is not False:
            only = option.get("only")
            if only:
                available = t("media", "available_yes_only" if met else "available_mcp_only", only=only)
            else:
                available = t("media", "available_yes" if met else "available_mcp")
            chain.append({**option, "available": available})
    return chain


def scan(course: dict) -> list[dict]:
    tk = coursemod.tokens(course)
    section_re = re.compile(rf"^## {re.escape(tk['section'])} (\d+)\s*[—-]")
    placeholder_re = re.compile(rf"^>\s*\*\*\[{re.escape(tk['placeholder'])}\s*[—-]\s*(.+?)\]\*\*")
    names = "|".join(re.escape(f) for f in tk["placeholder_fields"])
    field_re = re.compile(rf"^>\s*\*\*({names}):\*\*\s*(.*)$")
    keys = dict(zip(tk["placeholder_fields"], FIELD_KEYS, strict=False))
    assets = []
    for unit in course.get("units") or []:
        path = coursemod.unit_dir(course["_dir"], unit["n"]) / "content.md"
        if not path.exists():
            continue
        section, k, current = None, 0, None
        for line in path.read_text(encoding="utf-8").splitlines():
            m = section_re.match(line)
            if m:
                section, k, current = int(m.group(1)), 0, None
                continue
            m = placeholder_re.match(line)
            if m and section is not None:
                k += 1
                written = m.group(1).strip()
                current = {"id": f"U{unit['n']}-S{section}-M{k}", "unit": unit["n"], "section": section,
                           "type": lang.media_type_id(tk, written) or written}
                assets.append(current)
                continue
            if current is not None:
                f = field_re.match(line)
                if f:
                    current[keys[f.group(1)]] = f.group(2).strip()
                elif not line.startswith(">"):
                    current = None
    return assets


def load_manifest(course_dir):
    ry = roundtrip_yaml()
    path = course_dir / "media" / "manifest.yaml"
    data = ry.load(path.read_text(encoding="utf-8")) if path.exists() else None
    if not data:
        data = {"assets": []}
    if data.get("assets") is None:
        data["assets"] = []
    return ry, path, data


def extract(course: dict) -> dict[str, int]:
    ry, path, data = load_manifest(course["_dir"])
    existing = {a["id"]: a for a in data["assets"]}
    found = scan(course)
    merged = []
    for asset in found:
        old = existing.pop(asset["id"], None)
        if old is not None:
            changed = any(old.get(k) != asset.get(k) for k in ("type", "title", "description", "specs"))
            for k, v in asset.items():
                old[k] = v
            if changed and old.get("status") not in (None, "pending"):
                old["status"] = "pending"
                old["note"] = "The placeholder changed in the content: produce it again"
            merged.append(old)
        else:
            merged.append({**asset, "status": "pending", "recipe": None, "file": None, "asset_path": None,
                           "alt": None, "transcript": None, "subtitles_path": None})
    for orphan in existing.values():
        orphan["status"] = "orphaned"
        merged.append(orphan)
    data["assets"] = merged
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        ry.dump(data, fh)
    by_status: dict[str, int] = {}
    for a in merged:
        by_status[a["status"]] = by_status.get(a["status"], 0) + 1
    return dict(sorted(by_status.items()))


DOWNLOAD_HINT = re.compile(r"\b(pdf|descargable|descarga|download|downloadable|docx|xlsx|pptx)\b", re.I)


def missing_downloads(asset: dict) -> list[str]:
    """Why a produced asset still lacks the downloadable file its specs ask for."""
    if asset.get("status") in (None, "pending", "scripted", "orphaned"):
        return []
    if not DOWNLOAD_HINT.search(f"{asset.get('specs') or ''} {asset.get('how') or ''}"):
        return []
    downloads = asset.get("downloads") or []
    if not downloads:
        return [t("media", "missing_download_specs")]
    if asset.get("status") == "uploaded" and not all(d.get("asset_path") for d in downloads):
        return [t("media", "missing_download_upload")]
    return []


def plan(course: dict) -> tuple[list[str], list[str]]:
    """(warnings, lines): the production options of every pending asset."""
    cfg = config(course=course)
    root = course["_project"].root if course.get("_project") else None
    _, _, data = load_manifest(course["_dir"])
    warnings = [f"{a['id']}: {p}" for a in data["assets"] for p in missing_downloads(a)]
    uses_theme = [a for a in data["assets"] if a["type"] in (cfg.get("uses_theme") or [])]
    if uses_theme and course.get("_project"):
        found = thememod.status(course["_project"], course)
        if found.state != "derived":
            warnings.append(t("media", f"theme_{found.state}", code=course["code"]))
        elif found.tokens:
            current = thememod.fingerprint(found.tokens)
            warnings += [t("media", "theme_changed", asset=a["id"]) for a in uses_theme
                         if a.get("status") in ("produced", "uploaded") and a.get("theme") and a["theme"] != current]
    lines = []
    for a in (a for a in data["assets"] if a.get("status") in ("pending", "scripted")):
        chain = options_for(a["type"], cfg, root)
        lines.append(f"{a['id']} [{a['type']}] {a.get('title', '')}")
        if not chain:
            lines.append(t("media", "no_option"))
        for option in chain:
            lines.append(f"  - {option['id']} ({option['available']}): {option['how']}")
        if a["type"] in ("video", "audio"):
            for group in ("voice", "subtitles"):
                avail = [o["id"] for o in cfg[group] if requirement_met(o.get("needs"), root) is not False]
                lines.append(t("media", f"{group}_options", options=", ".join(avail)) if avail else t("media", f"{group}_none"))
    return warnings, lines


def providers(project) -> list[str]:
    cfg = config(project)
    seen = {}
    for group in [*cfg["types"].values(), cfg["voice"], cfg["subtitles"]]:
        for option in group:
            seen.setdefault(option["id"], option)
    words = {True: t("media", "provider_available"), False: t("media", "provider_missing"), None: t("media", "provider_mcp")}
    width = max(len(w) for w in words.values()) + 1
    out = []
    for oid, option in seen.items():
        met = requirement_met(option.get("needs"), project.root if project else None)
        out.append(f"{oid:<22} {words[met]:<{width}} {option['needs']}")
    return out


def set_asset(course: dict, asset_id: str, **values) -> str:
    """Update an asset of the manifest. `download` adds or updates an extra downloadable file."""
    ry, path, data = load_manifest(course["_dir"])
    asset = next((a for a in data["assets"] if a["id"] == asset_id), None)
    if asset is None:
        raise MediaError(t("media", "asset_not_found", asset_id=asset_id))
    cfg = config(course=course)
    statuses = cfg["statuses"]
    if values.get("status") and values["status"] not in statuses:
        raise MediaError(t("media", "bad_status", statuses=statuses))
    if values.get("status") in ("produced", "uploaded") and asset["type"] in (cfg.get("uses_theme") or []):
        found = thememod.status(course["_project"], course)
        if found.state != "derived" and not values.get("force"):
            raise MediaError(t("media", f"theme_{found.state}", code=course["code"]))
        if found.tokens:
            asset["theme"] = thememod.fingerprint(found.tokens)
    for key in ("status", "recipe", "asset_path", "file", "alt", "transcript", "subtitles_path", "made_with"):
        if values.get(key) is not None:
            asset[key] = values[key]
    download = values.get("download")
    if download:
        downloads = asset.get("downloads") or []
        entry = next((d for d in downloads if d.get("file") == download), None)
        if entry is None:
            entry = {"file": download, "title": None, "asset_path": None, "size": None}
            downloads.append(entry)
        local = course["_dir"] / "media" / download.removeprefix("media/")
        if local.exists():
            entry["size"] = local.stat().st_size
        if values.get("download_title") is not None:
            entry["title"] = values["download_title"]
        if values.get("download_asset_path") is not None:
            entry["asset_path"] = values["download_asset_path"]
        asset["downloads"] = downloads
    elif values.get("download_title") or values.get("download_asset_path"):
        raise MediaError(t("media", "download_needs_file"))
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        ry.dump(data, fh)
    return f"{asset_id}: {asset.get('status')}"
