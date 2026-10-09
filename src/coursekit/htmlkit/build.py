"""Build the package of a unit for the html backend: plan -> HTML, media, styles, the bundled player, manifest and zip.

The preview (a folder that opens from the disk) is `courses/<CODE>/assembly/html/unit-NN/`; with a version, the zip goes to
`courses/<CODE>/delivery/` with the name the delivery configuration asks for, ready for `coursekit delivery add`.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from html import escape
from importlib import resources
from pathlib import Path

from coursekit import assemble as assemblemod
from coursekit import course as coursemod
from coursekit import delivery as deliverymod
from coursekit import store
from coursekit import theme as thememod
from coursekit.htmlkit import check, manifest, render
from coursekit.i18n import t

Say = Callable[[str], None]


class HtmlBuildError(Exception):
    pass


@dataclass
class BuildResult:
    out_dir: Path
    package: Path | None = None
    warnings: list[str] = field(default_factory=list)
    files: int = 0


def template_dir() -> Path:
    return Path(str(resources.files("coursekit.templates.html")))


def check_unit(course: dict, unit: dict) -> list[str]:
    """For `coursekit verify` with the html backend: the unit converts to a plan and every brick can be rendered."""
    plan, errors, _ = assemblemod.build_plan(course, unit)
    problems = list(errors)
    problems += [t("htmlkit", "unsupported", brick=item) for item in render.unsupported_bricks(plan)]
    return problems


# ── media ────────────────────────────────────────────────────────────────────────────────────

def _local(course: dict, path: object) -> Path | None:
    if not path:
        return None
    for base in (course["_dir"], course["_dir"] / "media"):
        candidate = base / str(path)
        if candidate.exists():
            return candidate
    return None


def _copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)
    else:
        shutil.copy2(source, target)


def prepare_assets(course: dict, out_dir: Path) -> tuple[dict[str, dict], list[str]]:
    """Copy the produced media into the package; the entries come back as the plan reads them (`asset_path` inside the package)."""
    warnings: list[str] = []
    prepared: dict[str, dict] = {}
    for asset_id, asset in assemblemod.manifest_assets(course).items():
        entry = dict(asset)
        if asset.get("status") in ("produced", "uploaded"):
            source = _local(course, asset.get("file"))
            if source is None:
                warnings.append(t("htmlkit", "asset_without_file", asset=asset_id))
            else:
                if source.is_file() and source.name == "index.html":
                    source = source.parent  # a package of a simulation or a demo: its folder
                name = asset_id if source.is_dir() else f"{asset_id}{source.suffix}"
                _copy(source, out_dir / "media" / name)
                entry["status"], entry["asset_path"] = "uploaded", f"media/{name}"
                subtitles = _local(course, asset.get("subtitles_path"))
                if subtitles is not None and subtitles.is_file():
                    _copy(subtitles, out_dir / "media" / f"{asset_id}.vtt")
                    entry["subtitles_path"] = f"media/{asset_id}.vtt"
                elif asset.get("subtitles_path"):
                    entry.pop("subtitles_path", None)  # an upload path of another platform is no use here
        downloads = []
        for download in asset.get("downloads") or []:
            source = _local(course, download.get("file"))
            if source is None or not source.is_file():
                continue
            _copy(source, out_dir / "media" / "files" / source.name)
            downloads.append({**download, "asset_path": f"media/files/{source.name}"})
        entry["downloads"] = downloads
        prepared[asset_id] = entry
    return prepared, warnings


# ── pieces ───────────────────────────────────────────────────────────────────────────────────

def project_css(project, course: dict) -> str:
    parts = [(template_dir() / "styles" / "base.css").read_text(encoding="utf-8")]
    found = thememod.status(project, course)
    if found.state != "missing":
        parts.append(found.path.with_name("tokens.css").read_text(encoding="utf-8") if found.path.with_name("tokens.css").exists()
                     else thememod.css(found.tokens or {}))
    maqueta = project.theme_dir / "maqueta.css"
    if maqueta.exists():
        parts.append(maqueta.read_text(encoding="utf-8"))
    own = course["_dir"] / "theme" / "maqueta.css"
    if own.exists():
        parts.append(own.read_text(encoding="utf-8"))
    parts += [p.read_text(encoding="utf-8") for p in sorted((project.root / "components").glob("*.css"))]
    return "\n".join(parts)


def bundle_player(project, out_file: Path, say: Say) -> None:
    """The player (SCORM runtime and behaviour of the components) as one script, bundled with esbuild from the store workspace."""
    template = template_dir()
    workspace = store.ensure_workspace("html-builder", template / "package.json", say)
    if workspace is None:
        raise HtmlBuildError(t("htmlkit", "no_workspace"))
    sources = workspace / "player"
    shutil.rmtree(sources, ignore_errors=True)
    shutil.copytree(template / "player", sources)
    extra = sorted((project.root / "components").glob("*.js"))
    entry = workspace / "bundle-entry.js"
    entry.write_text("".join(f'import "{p.resolve().as_posix()}";\n' for p in extra) + 'import "./player/entry.js";\n', encoding="utf-8")
    binary = workspace / "node_modules" / ".bin" / ("esbuild.cmd" if os.name == "nt" else "esbuild")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([str(binary), str(entry), "--bundle", "--minify", "--format=iife", "--target=es2018", f"--outfile={out_file}",
                             "--log-level=warning"], cwd=workspace, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not out_file.exists():
        raise HtmlBuildError(t("htmlkit", "bundle_failed", error=(result.stderr or result.stdout).strip()[:500]))


def page(course: dict, plan: dict, standard: str) -> str:
    tokens = coursemod.tokens(course)
    ui = tokens["player"]
    lesson_html = "".join(render.lesson(lesson, ui) for lesson in plan["lessons"])
    nav = "".join(f'<li><a href="#{escape(lesson["key"])}">{escape(lesson["title"])}</a></li>' for lesson in plan["lessons"])
    config = {
        "standard": "2004" if standard == "scorm_2004" else "1.2",
        "course": course["code"],
        "unit": plan["unit"],
        "lessons": [{"key": lesson["key"], "type": lesson["type"]} for lesson in plan["lessons"]],
        "ui": ui,
    }
    data = json.dumps(config, ensure_ascii=False).replace("</", "<\\/")
    title = escape(plan["content_title"])
    return f"""<!doctype html>
<html lang="{escape(coursemod.language(course))}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="assets/styles.css">
</head>
<body>
<a class="ck-skip" href="#ck-main">{escape(ui["skip"])}</a>
<div class="ck-shell">
<header class="ck-header"><h1>{title}</h1>
<div class="ck-progress" role="progressbar" aria-label="{escape(ui["progress"])}" aria-valuemin="0" aria-valuemax="100"
aria-valuenow="0"><span></span></div></header>
<nav class="ck-nav" aria-label="{escape(ui["lessons"])}"><ol>{nav}</ol></nav>
<main class="ck-main" id="ck-main">{lesson_html}</main>
<div class="ck-controls">
<button type="button" class="ck-btn" data-prev>{escape(ui["previous"])}</button>
<button type="button" class="ck-btn ck-btn-primary" data-next>{escape(ui["next"])}</button>
</div>
</div>
<script type="application/json" id="ck-config">{data}</script>
<script src="assets/player.js"></script>
</body>
</html>
"""


def _files(out_dir: Path) -> list[str]:
    return sorted(p.relative_to(out_dir).as_posix() for p in out_dir.rglob("*") if p.is_file() and p.name != "imsmanifest.xml")


def _zip(out_dir: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(out_dir / "imsmanifest.xml", "imsmanifest.xml")  # first, at the root
        for name in _files(out_dir):
            zf.write(out_dir / name, name)


def mark_assembled(course: dict) -> str:
    """When every unit has its package built, the course moves from `media` to `assembly` (as when creator holds every unit)."""
    from coursekit.states import history_entry
    from coursekit.util import edit_yaml, save_yaml

    units = course.get("units") or []
    built = all((course["_dir"] / "assembly" / "html" / f"unit-{u['n']:02d}" / "index.html").exists() for u in units)
    if course["status"] != "media" or not units or not built:
        return ""
    path = course["_dir"] / "course.yaml"
    ry, data = edit_yaml(path)
    data["status"] = "assembly"
    data.setdefault("history", []).append(history_entry("assembly", "Every unit built"))
    save_yaml(ry, data, path)
    course["status"] = "assembly"
    return t("htmlkit", "course_assembled")


def build(course: dict, unit: dict, version: str | None, say: Say = print) -> BuildResult:
    """Build the unit; with a `version` also its zip in delivery/. Raises HtmlBuildError with what is wrong."""
    project = course["_project"]
    out_dir = course["_dir"] / "assembly" / "html" / f"unit-{unit['n']:02d}"
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True)
    assets, warnings = prepare_assets(course, out_dir)
    plan, errors, plan_warnings = assemblemod.build_plan(course, unit, assets)
    warnings += plan_warnings
    problems = list(errors) + [t("htmlkit", "unsupported", brick=item) for item in render.unsupported_bricks(plan)]
    if problems:
        raise HtmlBuildError("\n".join(problems))
    standard = deliverymod.settings(course)["export"]["standard"]
    document = page(course, plan, standard)
    missing = check.missing_words(course, unit, document)
    if missing:
        shown = ", ".join(missing[:20]) + (" …" if len(missing) > 20 else "")
        raise HtmlBuildError(t("htmlkit", "missing_text", count=len(missing), words=shown))
    (out_dir / "index.html").write_text(document, encoding="utf-8", newline="\n")
    (out_dir / "assets").mkdir(exist_ok=True)
    (out_dir / "assets" / "styles.css").write_text(project_css(project, course), encoding="utf-8", newline="\n")
    bundle_player(project, out_dir / "assets" / "player.js", say)
    identifier = re.sub(r"[^A-Za-z0-9_.-]", "-", f"{course['code']}-U{unit['n']:02d}")
    (out_dir / "imsmanifest.xml").write_text(manifest.build(identifier, plan["content_title"], _files(out_dir), standard),
                                             encoding="utf-8", newline="\n")
    result = BuildResult(out_dir, None, warnings, len(_files(out_dir)) + 1)
    if version:
        result.package = course["_dir"] / "delivery" / deliverymod.expected_name(course, unit["n"], version)
        _zip(out_dir, result.package)
    return result
