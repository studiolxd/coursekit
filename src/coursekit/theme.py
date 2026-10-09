"""`coursekit theme`: design tokens of the theme (theme/tokens.json) for the media.

The tokens are derived from the theme of the authoring platform, never written by hand: `import` converts the
saved result of the platform's `get_theme` into tokens.json and records where they come from (`origin`).
A project has one theme (theme/); a course can have its own (courses/<CODE>/theme/), which wins for that course.
`tokens` writes tokens.css next to the tokens (CSS custom properties and base classes for simulations);
`check` reports the WCAG contrast of the colour pairs the media and components use; `show` says which tokens a
course uses and where they come from.
"""

from __future__ import annotations

import colorsys
import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from coursekit.i18n import t
from coursekit.project import Project
from coursekit.util import edit_yaml, save_yaml

# (foreground, background, minimum ratio, key of the use in the messages catalog)
PAIRS = [
    ("text", "background", 4.5, "use_body_text"),
    ("text-soft", "background", 4.5, "use_secondary_text"),
    ("on-accent", "accent", 4.5, "use_button_text"),
    ("accent", "background", 3.0, "use_accent"),
    ("text", "surface", 4.5, "use_card_text"),
    ("text", "highlight", 4.5, "use_highlight_text"),
    ("correct", "background", 4.5, "use_correct"),
    ("wrong", "background", 4.5, "use_wrong"),
]


class ThemeError(Exception):
    pass


def course_theme_dir(course: dict) -> Path:
    return course["_dir"] / "theme"


def tokens_path(project: Project, course: dict | None = None) -> Path:
    """The tokens a course uses: its own when it has them, else the project's."""
    if course is not None and (course_theme_dir(course) / "tokens.json").exists():
        return course_theme_dir(course) / "tokens.json"
    return project.theme_dir / "tokens.json"


def load(project: Project, course: dict | None = None) -> dict:
    path = tokens_path(project, course)
    if not path.exists():
        raise ThemeError(t("theme", "missing_tokens", path=path.relative_to(project.root).as_posix()))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ThemeError(t("theme", "bad_tokens", path=path.relative_to(project.root).as_posix())) from exc
    if not isinstance(data, dict):
        raise ThemeError(t("theme", "bad_tokens", path=path.relative_to(project.root).as_posix()))
    return data


@dataclass
class ThemeStatus:
    state: str  # missing | manual | derived
    path: Path
    scope: str  # project | course
    tokens: dict | None = None
    origin: dict = field(default_factory=dict)


def status(project: Project, course: dict | None = None) -> ThemeStatus:
    """Where the tokens are and whether they were derived from the theme of the platform."""
    path = tokens_path(project, course)
    scope = "course" if path.parent != project.theme_dir else "project"
    if not path.exists():
        return ThemeStatus("missing", path, scope)
    tokens = load(project, course)
    origin = tokens.get("origin") or {}
    return ThemeStatus("derived" if origin.get("source") in ("creator", "css") else "manual", path, scope, tokens, origin)


FINGERPRINT_KEYS = ("color", "font", "radius", "space", "shadow")


def fingerprint(tokens: dict) -> str:
    """Identifies the look of the tokens (not their origin or date): media made with other tokens must be redone."""
    return hashlib.sha256(json.dumps({k: tokens.get(k) for k in FINGERPRINT_KEYS}, sort_keys=True).encode()).hexdigest()[:12]


def css(tokens: dict) -> str:
    font = tokens.get("font") or {}
    lines = ["/* Generated from tokens.json by `coursekit theme tokens`. Do not edit by hand. */"]
    if font.get("google"):
        lines.append(f"@import url('{font['google']}');")
    lines.append(":root {")
    for name, value in (tokens.get("color") or {}).items():
        lines.append(f"  --color-{name}: {value};")
    for key, var in (("family", "font-family"), ("headings", "font-family-headings"), ("ui", "font-family-ui"),
                     ("size-base", "font-size-base"), ("line-height", "line-height")):
        if font.get(key):
            lines.append(f"  --{var}: {font[key]};")
    if tokens.get("radius"):
        lines.append(f"  --radius: {tokens['radius']};")
    for group in ("shadow", "space"):
        for name, value in (tokens.get(group) or {}).items():
            lines.append(f"  --{group}-{name}: {value};")
    lines += [
        "}",
        "",
        "/* Base for simulations: import this file and build on these classes. */",
        "body { margin: 0; font-family: var(--font-family); font-size: var(--font-size-base);",
        "  line-height: var(--line-height); color: var(--color-text); background: var(--color-background); }",
        ".btn { font: 700 1rem var(--font-family); color: var(--color-on-accent); background: var(--color-accent);",
        "  border: 2px solid var(--color-accent); border-radius: var(--radius);",
        "  padding: var(--space-sm) var(--space-md); cursor: pointer; }",
        ".btn:hover { color: var(--color-accent); background: var(--color-background); }",
        ".btn:focus-visible, [tabindex]:focus-visible {",
        "  outline: 3px solid var(--color-accent-strong, var(--color-accent)); outline-offset: 2px; }",
        ".card { background: var(--color-background); border: 1px solid var(--color-line); border-radius: var(--radius);",
        "  box-shadow: var(--shadow-soft); padding: var(--space-md); }",
        ".is-correct { color: var(--color-correct); } .is-wrong { color: var(--color-wrong); }",
        ".note { background: var(--color-highlight); border-left: 4px solid var(--color-accent); padding: var(--space-md); }",
        "",
    ]
    return "\n".join(lines)


def write_css(project: Project, course: dict | None = None) -> Path:
    out = tokens_path(project, course).with_name("tokens.css")
    out.write_text(css(load(project, course)), encoding="utf-8", newline="\n")
    return out


def to_hex(value: object) -> str | None:
    """A CSS colour (hex, rgb(), hsl(), white, black) as #RRGGBB, without alpha; None when it cannot be resolved."""
    text = str(value or "").strip().lower()
    if text in ("white", "black"):
        return "#FFFFFF" if text == "white" else "#000000"
    if re.fullmatch(r"#[0-9a-f]{3,8}", text):
        digits = text[1:]
        if len(digits) in (3, 4):
            digits = "".join(c * 2 for c in digits)
        if len(digits) in (6, 8):
            return "#" + digits[:6].upper()
        return None
    match = re.fullmatch(r"(rgb|hsl)a?\(([^)]*)\)", text)
    if not match:
        return None
    parts = [p for p in re.split(r"[\s,/]+", match.group(2).strip()) if p]
    try:
        if match.group(1) == "rgb":
            rgb = [round(float(p[:-1]) * 2.55) if p.endswith("%") else round(float(p)) for p in parts[:3]]
        else:
            h = float(parts[0].removesuffix("deg")) / 360
            sat, light = (float(p.rstrip("%")) / 100 for p in parts[1:3])
            rgb = [round(c * 255) for c in colorsys.hls_to_rgb(h % 1, light, sat)]
    except (ValueError, IndexError):
        return None
    return "#" + "".join(f"{max(0, min(255, c)):02X}" for c in rgb)


def _luminance(hex_color: str) -> float:
    value = hex_color.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    channels = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def check(tokens: dict) -> list[tuple[bool, str]]:
    colors = tokens.get("color") or {}
    out = []
    for fg, bg, minimum, use in PAIRS:
        if to_hex(colors.get(fg)) and to_hex(colors.get(bg)):
            ratio = contrast(to_hex(colors[fg]), to_hex(colors[bg]))
            out.append((ratio >= minimum, t("theme", "pair_line", fg=fg, bg=bg, use=t("theme", use), ratio=ratio, minimum=minimum)))
    return out


# ── derive the tokens from the theme of the authoring platform ─────────────────────────────────────

SYSTEM_FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
MONO_FONT = "ui-monospace, 'SF Mono', Consolas, monospace"
DEFAULT_ROLES = {"background": "#FFFFFF", "headings": "#000000", "text": "#000000", "correct": "#1DA34E", "wrong": "#EF4444"}
DEFAULT_RADIUS = "8px"
DEFAULT_SPACE = {"xs": "4px", "sm": "8px", "md": "16px", "lg": "24px", "xl": "32px"}
DEFAULT_SHADOW = {"soft": "0 2px 8px rgba(0, 0, 0, 0.12)"}


def mix(a: str, b: str, amount: float) -> str:
    """`a` with `amount` (0 to 1) of `b` mixed in, as #RRGGBB."""
    ca = [int(a[i : i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * amount):02X}" for x, y in zip(ca, cb, strict=True))


def _config(response: dict) -> dict:
    """The `config` of a get_theme result (it also accepts the theme or the config alone)."""
    node = response
    for key in ("theme", "config"):
        if isinstance(node.get(key), dict):
            node = node[key]
    if not isinstance(node.get("colors"), dict):
        raise ThemeError(t("theme", "not_a_theme"))
    return node


def _resolve(ref: object, palette: dict[str, str], semantic: dict, seen: tuple[str, ...] = ()) -> str | None:
    if not isinstance(ref, dict):
        return None
    if ref.get("custom"):
        return to_hex(ref["custom"])
    pid = str(ref.get("paletteId") or "")
    if pid.startswith("semantic:"):
        role = pid.split(":", 1)[1]
        return None if role in seen else _resolve(semantic.get(role), palette, semantic, (*seen, role))
    return to_hex(palette.get(pid))


def _font(ref: object, assignments: dict, custom: dict[str, str], notes: list[str]) -> str:
    ref = str(ref or "system")
    if ref in ("text", "headings", "ui") and ref in assignments and assignments[ref] != ref:
        ref = str(assignments[ref] or "system")
    if ref == "system":
        return SYSTEM_FONT
    if ref == "system-mono":
        return MONO_FONT
    if ref in custom:
        return f"'{custom[ref]}', {SYSTEM_FONT}"
    notes.append(t("theme", "note_font", font=ref))
    return f"'{ref}', {SYSTEM_FONT}"


def from_creator(response: dict) -> dict:
    """The tokens of a `get_theme` result of the authoring platform, with their origin."""
    cfg = _config(response)
    colors = cfg["colors"]
    palette = {str(p.get("id")): p.get("value") for p in colors.get("palette") or [] if isinstance(p, dict)}
    semantic = colors.get("semantic") or {}
    notes: list[str] = []

    def role(name: str, fallback: str | None = None) -> str | None:
        found = _resolve(semantic.get(name), palette, semantic)
        if found:
            return found
        if semantic.get(name):
            notes.append(t("theme", "note_color", role=name))
        return fallback

    text = role("text", DEFAULT_ROLES["text"])
    background = role("background", DEFAULT_ROLES["background"])
    accent = role("accent") or to_hex(palette.get("accent")) or "#0A58CA"
    chosen = {
        "background": background,
        "text": text,
        "headings": role("headings", text),
        "accent": accent,
        "on-accent": role("accentText", text),
        "link": role("link", text),
        "correct": role("correct", DEFAULT_ROLES["correct"]),
        "on-correct": role("correctText", text),
        "wrong": role("wrong", DEFAULT_ROLES["wrong"]),
        "on-wrong": role("wrongText", text),
    }
    # The platform has no such roles: soft variants of its colours, kept readable on the background.
    soft = 0.35
    while soft > 0 and contrast(mix(text, background, soft), background) < 4.5:
        soft -= 0.05
    derived = {
        "text-soft": mix(text, background, max(soft, 0)),
        "surface": mix(background, text, 0.04),
        "highlight": mix(background, accent, 0.12),
        "line": mix(background, text, 0.2),
        "accent-strong": accent,
    }
    fonts = cfg.get("fonts") or {}
    assignments = fonts.get("assignments") or {}
    custom = {str(f.get("id")): str(f.get("name")) for f in fonts.get("customFonts") or [] if isinstance(f, dict) and f.get("name")}
    size, line = fonts.get("baseFontSize") or 16, fonts.get("baseLineHeight") or 1.6
    scheme = cfg.get("colorMode") or {}
    dark = scheme.get("mode") in ("dark", "auto") or bool(scheme.get("toggle")) or bool(cfg.get("variants"))
    if dark:
        notes.append(t("theme", "note_dark"))
    meta = response if "themeId" in response else {}
    return {
        "origin": {
            "source": "creator",
            "theme_id": meta.get("themeId"),
            "name": meta.get("name") or (response.get("theme") or {}).get("name"),
            "version": meta.get("version"),
            "imported_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "derived": sorted(derived),
            "defaults": ["radius", "space", "shadow"],
            "notes": notes,
        },
        "color": {**{k: v for k, v in chosen.items() if v}, **derived},
        "font": {
            "family": _font("text", assignments, custom, notes),
            "headings": _font("headings", assignments, custom, notes),
            "ui": _font("ui", assignments, custom, notes),
            "size-base": f"{size}px",
            "line-height": str(line),
        },
        "radius": DEFAULT_RADIUS,
        "space": DEFAULT_SPACE,
        "shadow": DEFAULT_SHADOW,
    }


# ── derive the tokens from the CSS variables of the html backend's base layout ─────────────────────

DECLARATION = re.compile(r"--([a-z0-9-]+)\s*:\s*([^;}]+)[;}]", re.I)
VAR_REF = re.compile(r"var\(\s*--([a-z0-9-]+)\s*(?:,[^)]*)?\)", re.I)


def _without_at_rules(text: str) -> str:
    """The stylesheet without its `@media`, `@supports`... blocks: their variables (a dark mode, a print layout) are not the theme."""
    out, depth, skipping = [], 0, False
    for char in text:
        if char == "@" and depth == 0:
            skipping = True
        if skipping and char == "{":
            depth += 1
        elif skipping and char == "}":
            depth -= 1
            if depth == 0:
                skipping = False
            continue
        if not skipping:
            out.append(char)
        elif depth == 0 and char == ";":
            skipping = False  # an at-rule without a block (@import, @charset)
    return "".join(out)


def css_variables(text: str) -> dict[str, str]:
    """The custom properties a stylesheet declares outside at-rules (the last declaration wins), without comments."""
    text = _without_at_rules(re.sub(r"/\*.*?\*/", "", text, flags=re.S))
    return {name.lower(): value.strip() for name, value in DECLARATION.findall(text)}


def _resolve_css(value: str, variables: dict[str, str], seen: tuple[str, ...] = ()) -> str:
    def replace(match: re.Match) -> str:
        name = match.group(1).lower()
        if name in seen or name not in variables:
            return match.group(0)
        return _resolve_css(variables[name], variables, (*seen, name))

    return VAR_REF.sub(replace, value)


def from_css(base: str, overrides: str, source: str, digest: str) -> dict:
    """The tokens of the base layout of the html backend with the project's stylesheet over it."""
    variables = {**css_variables(base), **css_variables(overrides)}
    resolved = {name: _resolve_css(value, variables) for name, value in variables.items()}
    colors: dict[str, str] = {}
    space, shadow = {}, {}
    font: dict[str, str] = {}
    radius = DEFAULT_RADIUS
    notes: list[str] = []
    for name, value in resolved.items():
        if name.startswith("color-"):
            hex_value = to_hex(value)
            colors[name[6:]] = hex_value or value
            if not hex_value:
                notes.append(t("theme", "note_css_color", name=name, value=value))
        elif name.startswith("space-"):
            space[name[6:]] = value
        elif name.startswith("shadow-"):
            shadow[name[7:]] = value
        elif name == "radius":
            radius = value
    for name, key in (("font-family", "family"), ("font-family-headings", "headings"), ("font-family-ui", "ui"),
                      ("font-size-base", "size-base"), ("line-height", "line-height")):
        if name in resolved:
            font[key] = resolved[name]
    return {
        "origin": {"source": "css", "file": source, "sha256": digest,
                   "imported_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "notes": notes},
        "color": colors, "font": font, "radius": radius, "space": space or DEFAULT_SPACE, "shadow": shadow or DEFAULT_SHADOW,
    }


def import_creator(project: Project, course: dict | None, file: Path) -> tuple[Path, dict]:
    """Convert a saved get_theme result, or the stylesheet of the html backend (.css), into the tokens of the project (or of the
    course) and write tokens.json and tokens.css."""
    if not file.is_file():
        raise ThemeError(t("theme", "file_missing", path=file.as_posix()))
    if file.suffix.lower() == ".css":
        from importlib import resources

        base = resources.files("coursekit.templates.html").joinpath("styles", "base.css").read_text(encoding="utf-8")
        text = file.read_bytes()
        tokens = from_css(base, text.decode("utf-8", errors="replace"), file.name, hashlib.sha256(text).hexdigest()[:12])
    else:
        try:
            response = json.loads(file.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise ThemeError(t("theme", "not_a_theme")) from exc
        if not isinstance(response, dict):
            raise ThemeError(t("theme", "not_a_theme"))
        tokens = from_creator(response)
    folder = course_theme_dir(course) if course is not None else project.theme_dir
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "tokens.json"
    path.write_text(json.dumps(tokens, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (folder / "tokens.css").write_text(css(tokens), encoding="utf-8", newline="\n")
    if course is not None and tokens["origin"].get("theme_id"):  # only the themes of a platform have an id
        course_path = course["_dir"] / "course.yaml"
        ry, data = edit_yaml(course_path)
        if (data.get("slxd") or {}).get("theme_id") != tokens["origin"]["theme_id"]:
            data["slxd"]["theme_id"] = tokens["origin"]["theme_id"]
            save_yaml(ry, data, course_path)
    return path, tokens
