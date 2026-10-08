"""`coursekit theme`: design tokens of the project theme (theme/tokens.json) for the media.

`tokens` writes theme/tokens.css (CSS custom properties and base classes for simulations);
`check` reports the WCAG contrast of the colour pairs the media and components use.
"""

from __future__ import annotations

import json
from pathlib import Path

from coursekit.project import Project

# (foreground, background, minimum ratio, use)
PAIRS = [
    ("text", "background", 4.5, "body text"),
    ("text-soft", "background", 4.5, "secondary text"),
    ("on-accent", "accent", 4.5, "button text on the accent"),
    ("accent", "background", 3.0, "accent elements and large text"),
    ("text", "surface", 4.5, "text on cards"),
    ("text", "highlight", 4.5, "text on highlights"),
    ("correct", "background", 4.5, "correct feedback"),
    ("wrong", "background", 4.5, "wrong feedback"),
]


class ThemeError(Exception):
    pass


def tokens_path(project: Project) -> Path:
    return project.theme_dir / "tokens.json"


def load(project: Project) -> dict:
    path = tokens_path(project)
    if not path.exists():
        raise ThemeError(f"missing {path.relative_to(project.root)}: derive it from the theme of the assembly platform")
    return json.loads(path.read_text(encoding="utf-8"))


def css(tokens: dict) -> str:
    font = tokens.get("font") or {}
    lines = ["/* Generated from tokens.json by `coursekit theme tokens`. Do not edit by hand. */"]
    if font.get("google"):
        lines.append(f"@import url('{font['google']}');")
    lines.append(":root {")
    for name, value in (tokens.get("color") or {}).items():
        lines.append(f"  --color-{name}: {value};")
    for key, var in (("family", "font-family"), ("size-base", "font-size-base"), ("line-height", "line-height")):
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


def write_css(project: Project) -> Path:
    out = project.theme_dir / "tokens.css"
    out.write_text(css(load(project)), encoding="utf-8", newline="\n")
    return out


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
        if fg in colors and bg in colors:
            ratio = contrast(colors[fg], colors[bg])
            out.append((ratio >= minimum, f"{fg} on {bg} ({use}): {ratio:.2f}:1, needs {minimum}:1"))
    return out
