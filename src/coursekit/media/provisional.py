"""Provisional images: a visual resource that is not produced yet is never left out of the assembled course. In its place
goes an image in the theme of the course, with the size of its specifications, its type, its title and what is missing
("Pending: capture of the application"), with nothing that imitates an interface. The page keeps its layout when the real
image arrives, and whoever reviews the course sees the gap.

The html backend draws it by itself when it builds the package. With creator, `coursekit media provisional CODE` writes
`media/placeholders/<id>.png`, the media agent uploads it to the content of the unit and records it with
`coursekit media set CODE ID --provisional-path PATH`; the assembly shows it until the real asset is uploaded."""

from __future__ import annotations

import html
import re
import textwrap
from pathlib import Path
from typing import Any

from coursekit import course as coursemod
from coursekit.i18n import t

TYPES = ("image", "illustration", "icon", "infographic", "diagram", "animated_gif", "video")  # what the learner sees
FOLDER = "media/placeholders"
SIZE = re.compile(r"(\d{3,4})\s*[x×]\s*(\d{3,4})")


def applies(asset: dict | None) -> bool:
    """A visual resource of the content still to produce (the images of the simulations and the portraits have their own
    stand-ins: the initials, a simulation without its image)."""
    if not asset:
        return False
    return asset.get("type") in TYPES and not asset.get("kind") and not asset.get("character") \
        and asset.get("status") not in ("produced", "uploaded", "orphaned")


def waiting(course: dict, unit: int | None = None) -> list[str]:
    """The ids of the visual resources of the course (or of one unit) that the assembly shows as provisional images."""
    from coursekit import assemble

    return [a["id"] for a in assemble.manifest_assets(course).values()
            if applies(a) and (unit is None or a.get("unit") == unit)]


def size(asset: dict) -> tuple[int, int]:
    found = SIZE.search(str(asset.get("specs") or ""))
    if found:
        return int(found.group(1)), int(found.group(2))
    return (800, 800) if asset.get("type") == "icon" else (1600, 900)


def _tokens(course: dict) -> dict:
    from coursekit import theme as thememod

    project = course.get("_project")
    found = thememod.status(project, course) if project else None
    return (found.tokens if found and found.tokens else {}) or {}


def svg(course: dict, asset: dict) -> str:
    """The provisional image of `asset`, as SVG, in the colours and fonts of the theme of the course."""
    tokens = _tokens(course)
    color: dict[str, Any] = tokens.get("color") or {}
    font: dict[str, Any] = tokens.get("font") or {}
    words = coursemod.tokens(course)
    missing = (words.get("provisional") or {})
    status = missing.get("video" if asset.get("type") in ("video", "animated_gif") else
                         "capture" if asset.get("depicts") == "interface" else "image", "")
    label = (words.get("media_types") or {}).get(asset["type"], asset["type"])
    width, height = size(asset)
    unit = min(width, height) / 100
    background = color.get("surface") or "#F5F5F5"
    line = color.get("border") or "#CCCCCC"
    muted = color.get("text-muted") or "#595959"
    heading = color.get("headings") or color.get("text") or "#1A1A1A"
    accent = color.get("accent-ink") or color.get("accent") or "#0A58CA"
    family = html.escape(str(font.get("headings") or font.get("family") or "system-ui, sans-serif"), quote=True)
    title = textwrap.wrap(str(asset.get("title") or asset["id"]), max(16, int(width / (unit * 4.4))))[:3]
    size_title, size_small = unit * 7, unit * 4
    top = height / 2 - (len(title) * size_title * 1.25) / 2
    lines = "".join(f'<text x="{width / 2:g}" y="{top + (k + 0.8) * size_title * 1.25:.0f}" font-size="{size_title:.0f}" '
                    f'fill="{heading}" font-weight="600">{html.escape(text)}</text>' for k, text in enumerate(title))
    inset = unit * 4
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'role="img" font-family="{family}" text-anchor="middle">'
            f'<title>{html.escape(f"{label}: {asset.get("title") or asset["id"]}")}</title>'
            f'<desc>{html.escape(status)}</desc>'
            f'<rect width="{width}" height="{height}" fill="{background}"/>'
            f'<rect x="{inset:.0f}" y="{inset:.0f}" width="{width - 2 * inset:.0f}" height="{height - 2 * inset:.0f}" fill="none" '
            f'stroke="{line}" stroke-width="{unit * 0.6:.1f}" stroke-dasharray="{unit * 3:.0f} {unit * 2:.0f}"/>'
            f'<text x="{width / 2:g}" y="{top - size_title * 0.9:.0f}" font-size="{size_small:.0f}" fill="{muted}" '
            f'letter-spacing="{size_small * 0.08:.1f}">{html.escape(label.upper())}</text>{lines}'
            f'<text x="{width / 2:g}" y="{top + len(title) * size_title * 1.25 + size_small * 2.2:.0f}" font-size="{size_small:.0f}" '
            f'fill="{accent}">{html.escape(status)}</text>'
            f'<text x="{width - inset * 2:.0f}" y="{height - inset * 2:.0f}" font-size="{size_small * 0.7:.0f}" fill="{muted}" '
            f'text-anchor="end">{html.escape(asset["id"])}</text></svg>')


def alt(course: dict, asset: dict) -> str:
    """The alternative text of a provisional image: what it stands for, and that it is missing."""
    words = coursemod.tokens(course)
    label = (words.get("media_types") or {}).get(asset["type"], asset["type"])
    missing = (words.get("provisional") or {}).get("capture" if asset.get("depicts") == "interface" else "image", "")
    return f"{label}: {asset.get('title') or asset['id']} ({missing})"


def write(course: dict, asset: dict, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{asset['id']}.svg"
    path.write_text(svg(course, asset), encoding="utf-8")
    return path


def make(course: dict, ids: list[str] | None = None, png: bool | None = None) -> list[str]:
    """`coursekit media provisional`: the provisional image of every visual resource still to produce (or of `ids`), in
    `media/placeholders/`, and its PNG when the course assembles in creator (or `png`), which only takes PNG, JPEG, WebP and
    GIF. Returns one line per image."""
    from coursekit import assemble
    from coursekit.media import tools as mediatools

    assets = assemble.manifest_assets(course)
    wanted = [assets[i] for i in ids if i in assets] if ids else list(assets.values())
    unknown = [i for i in ids or [] if i not in assets]
    if unknown:
        from coursekit.media import MediaError

        raise MediaError(t("media", "asset_not_found", asset_id=", ".join(unknown)))
    as_png = png if png is not None else coursemod.backend(course) == "creator"
    folder = course["_dir"] / FOLDER
    fonts_css = None
    if as_png and course.get("_project"):  # the text drawn in the fonts of the brand, whatever the machine has
        from coursekit import brand

        sheet = brand.fonts_stylesheet(course["_project"], course)
        if sheet:
            try:
                fonts_css = brand.inline_fonts(sheet, course["_project"].root)[0]
            except brand.BrandError:
                fonts_css = None
    lines = []
    for asset in wanted:
        if not applies(asset):
            continue
        path = write(course, asset, folder)
        made = path
        if as_png:
            mediatools.render_svg(path, path.with_suffix(".png"), None, fonts_css)
            made = path.with_suffix(".png")
        lines.append(t("media", "provisional_made", asset=asset["id"], file=made.relative_to(course["_dir"]).as_posix()))
    return lines
