"""The crosshairs of the images with points: where each point of a `:::labelled-graphic` and each hotspot with an `area` of a
simulation goes, drawn on the image itself so that whoever reviews it sees it and can ask to move it. They are drawn from what
is written (the `position` of a point, the centre of the `area` of a hotspot), so the image and the content always agree:
`coursekit media anchors` draws them (SVG: one `<g data-ck-anchor>` per point; a raster image: over a clean copy kept next to
it) and records them in the manifest (`anchors`); `verify` fails when the content moved a point and the image was not drawn
again."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from coursekit import course as coursemod
from coursekit import simulation as simmod
from coursekit.i18n import t

DIRECTIVE = "labelled-graphic"
RASTER = (".png", ".jpg", ".jpeg", ".webp")
INK = "#6b7280"  # a subtle grey: it shows where the point goes without competing with the image
HALO = "#ffffff"
ARM = 0.012  # half the cross, as a share of the shorter side of the image
GROUP_RE = re.compile(r'\s*<g data-ck-anchor="[^"]*"[^>]*>.*?</g>', re.S)


class AnchorError(Exception):
    pass


@dataclass
class Point:
    """A place on an image: its label (the title of the point, the label of the hotspot), where it is (in %, None when the
    content does not say) and where it is written."""
    label: str
    at: tuple[float, float] | None
    unit: int
    path: Path
    line: int  # the line of the point (its #### heading, or the directive of the simulation)
    kind: str  # point | hotspot
    position_line: int | None = None  # the `position:` line of a point, when it has one


def _number(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


def graphic_points(course: dict, unit: dict) -> dict[str, list[Point]]:
    """The points of the `:::labelled-graphic` of a unit, by the title of the image they point at."""
    tk = coursemod.tokens(course)
    from coursekit.lang import directive_key

    image_key, position_key = directive_key(tk, "image"), directive_key(tk, "position")
    path = coursemod.unit_dir(course["_dir"], unit["n"]) / "content.md"
    if not path.exists():
        return {}
    found: dict[str, list[Point]] = {}
    image, inside, current = None, False, None
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if stripped == f":::{DIRECTIVE}":
            image, inside, current = None, True, None
        elif inside and stripped == ":::":
            inside = False
        elif inside and stripped.startswith("#### "):
            current = Point(stripped[5:].strip(), None, unit["n"], path, i, "point")
            found.setdefault(image or "", []).append(current)
        elif inside and (m := re.match(rf"^{re.escape(image_key)}:\s*(.+)$", stripped)) and current is None:
            image = m.group(1).strip()
        elif inside and current is not None and (m := re.match(rf"^{re.escape(position_key)}:\s*(.+)$", stripped)):
            parts = [_number(v.strip()) for v in m.group(1).split(",")]
            current.position_line = i
            if len(parts) == 2 and None not in parts:
                current.at = (parts[0], parts[1])
    return found


def hotspot_points(course: dict, unit: dict) -> dict[str, list[Point]]:
    """The hotspots with an `area` of the simulations of a unit, by the asset id of the background they are on."""
    from coursekit.verify import Report, parse_directives

    rules = coursemod.rules(course)["content"]
    names = tuple(rules.get("simulation_directives") or ())
    found: dict[str, list[Point]] = {}
    folder = coursemod.unit_dir(course["_dir"], unit["n"])
    for name in ("content.md", "assessment.md"):
        path = folder / name
        if not path.exists():
            continue
        for line_no, directive, body in parse_directives(path, path.read_text(encoding="utf-8").splitlines(), rules, Report()):
            if directive not in names:
                continue
            try:
                data = yaml.safe_load("\n".join(body))
            except yaml.YAMLError:
                continue
            for scene in ((data or {}).get("scenes") or {}).values() if isinstance(data, dict) else []:
                if not isinstance(scene, dict) or not scene.get("background"):
                    continue
                for spot in scene.get("hotspots") or []:
                    area = spot.get("area") if isinstance(spot, dict) else None
                    if not isinstance(area, list) or len(area) not in (2, 4):
                        continue
                    x, y = float(area[0]), float(area[1])
                    if len(area) == 4:
                        x, y = x + float(area[2]) / 2, y + float(area[3]) / 2
                    found.setdefault(simmod.background_id(str(scene["background"])), []).append(
                        Point(str(spot.get("label") or ""), (round(x, 2), round(y, 2)), unit["n"], path, line_no, "hotspot"))
    return found


def points_of(course: dict, assets: list[dict], units: list[dict] | None = None) -> dict[str, list[Point]]:
    """The points of every image of the manifest that has any, by asset id."""
    by_title = {str(a.get("title") or ""): a["id"] for a in assets}
    out: dict[str, list[Point]] = {}
    for unit in units if units is not None else course.get("units") or []:
        for title, points in graphic_points(course, unit).items():
            if title in by_title:
                out.setdefault(by_title[title], []).extend(points)
        for asset_id, points in hotspot_points(course, unit).items():
            out.setdefault(asset_id, []).extend(points)
    return out


def recorded(points: list[Point]) -> list[dict]:
    """The crosshairs as the manifest keeps them (and as the image shows them)."""
    return [{"label": p.label, "at": [round(p.at[0], 2), round(p.at[1], 2)]} for p in points if p.at is not None]


def set_position(point: Point, at: tuple[float, float], key: str) -> None:
    """Writes the `position:` of a point of a `:::labelled-graphic` in its content."""
    lines = point.path.read_text(encoding="utf-8").splitlines()
    value = f"{key}: {at[0]:g},{at[1]:g}"
    if point.position_line:
        lines[point.position_line - 1] = value
    else:
        lines.insert(point.line, value)
    point.path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _svg_box(text: str) -> tuple[float, float, float, float]:
    box = re.search(r'viewBox="\s*([-\d.]+)[\s,]+([-\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)', text)
    if box:
        return tuple(float(v) for v in box.groups())  # type: ignore[return-value]
    w, h = re.search(r'<svg[^>]*\bwidth="([\d.]+)', text), re.search(r'<svg[^>]*\bheight="([\d.]+)', text)
    if w and h:
        return 0.0, 0.0, float(w.group(1)), float(h.group(1))
    raise AnchorError(t("anchors", "svg_without_size"))


def draw_svg(path: Path, marks: list[dict]) -> None:
    """The crosshairs as groups at the end of the SVG (the ones it had are replaced): a small grey cross with a thin white halo,
    so that it reads on any background, and the number of the point tight in its upper right quadrant."""
    text = GROUP_RE.sub("", path.read_text(encoding="utf-8"))
    x0, y0, w, h = _svg_box(text)
    size = min(w, h) * ARM
    groups = []
    for n, mark in enumerate(marks, 1):
        x, y = x0 + w * mark["at"][0] / 100, y0 + h * mark["at"][1] / 100
        label = mark["label"].replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
        cross = f"M{-size:g} 0H{size:g}M0 {-size:g}V{size:g}"
        groups.append(
            f'<g data-ck-anchor="{label}" transform="translate({x:.2f} {y:.2f})" aria-hidden="true">'
            f'<path d="{cross}" stroke="{HALO}" stroke-opacity="0.8" stroke-width="{size * 0.4:.2f}" stroke-linecap="round"/>'
            f'<path d="{cross}" stroke="{INK}" stroke-width="{size * 0.16:.2f}" stroke-linecap="round"/>'
            f'<text x="{size * 0.22:.2f}" y="{-size * 0.22:.2f}" font-family="sans-serif" font-size="{size * 1.05:.2f}" '
            f'font-weight="600" fill="{INK}" stroke="{HALO}" stroke-opacity="0.8" stroke-width="{size * 0.22:.2f}" '
            f'paint-order="stroke">{n}</text></g>')
    text = text.replace("</svg>", "".join(f"\n  {g}" for g in groups) + "\n</svg>", 1) if groups else text
    path.write_text(text, encoding="utf-8")


def clean_copy(path: Path) -> Path:
    return path.with_name(f"{path.stem}.clean{path.suffix}")


def draw_raster(path: Path, marks: list[dict]) -> None:
    """The crosshairs over the clean copy of the image (kept the first time, `<name>.clean.<ext>`), so moving a point does not
    leave the old cross behind."""
    from PIL import Image, ImageDraw, ImageFont

    clean = clean_copy(path)
    if not clean.exists():
        clean.write_bytes(path.read_bytes())
    with Image.open(clean) as source:
        im = source.convert("RGBA")
    draw = ImageDraw.Draw(im)
    size = max(4, round(min(im.size) * ARM))
    font = ImageFont.load_default(size=max(8, round(size * 1.05)))
    for n, mark in enumerate(marks, 1):
        x, y = im.width * mark["at"][0] / 100, im.height * mark["at"][1] / 100
        for color, width in ((HALO, max(2, round(size * 0.4))), (INK, max(1, round(size * 0.16)))):
            draw.line((x - size, y, x + size, y), fill=color, width=width)
            draw.line((x, y - size, x, y + size), fill=color, width=width)
        gap = max(1, round(size * 0.22))  # the number in the upper right quadrant, tight to the cross
        draw.text((x + gap, y - gap), str(n), font=font, anchor="ls", fill=INK, stroke_width=1, stroke_fill=HALO)
    out = im if path.suffix.lower() == ".png" else im.convert("RGB")
    out.save(path)


def draw(path: Path, marks: list[dict]) -> None:
    if path.suffix.lower() == ".svg":
        draw_svg(path, marks)
    elif path.suffix.lower() in RASTER:
        draw_raster(path, marks)
    else:
        raise AnchorError(t("anchors", "not_an_image", file=path.name))
