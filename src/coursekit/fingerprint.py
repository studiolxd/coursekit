"""Per-part fingerprints of a unit, to know what changed after its AI review.

A unit is split into parts: each section of content.md and each assessment activity of
assessment.md. `coursekit reviewed` stores their hashes in course.yaml › units[N].reviewed_parts;
`verify` and `review` compare against them.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from coursekit.course import unit_dir
from coursekit.util import edit_yaml, save_yaml


def _patterns(tokens: dict) -> tuple[re.Pattern, re.Pattern]:
    section = re.compile(rf"^## {re.escape(tokens['section'])} (\d+)\b.*$", re.M)
    activity = re.compile(rf"^## {re.escape(tokens['assessment_activity'])} ([\d.]+)\b.*$", re.M)
    return section, activity


def _split(text: str, pattern: re.Pattern, prefix: str) -> dict[str, str]:
    marks = list(pattern.finditer(text))
    parts = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.start() : end].strip()
        parts[f"{prefix} {m.group(1)}"] = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    return parts


def unit_parts(course_dir: Path, n: int, tokens: dict) -> dict[str, str]:
    folder = unit_dir(course_dir, n)
    section, activity = _patterns(tokens)
    parts: dict[str, str] = {}
    for name, pattern, prefix in (("content.md", section, "section"), ("assessment.md", activity, "activity")):
        path = folder / name
        if path.exists():
            parts.update(_split(path.read_text(encoding="utf-8"), pattern, prefix))
    return parts


def changed_since_review(course_dir: Path, unit: dict, tokens: dict) -> list[str] | None:
    """Parts changed (or added/removed) since the AI review; None if there is no baseline."""
    baseline = unit.get("reviewed_parts")
    if not baseline:
        return None
    now = unit_parts(course_dir, unit["n"], tokens)
    return sorted(k for k in set(baseline) | set(now) if baseline.get(k) != now.get(k))


def record_review(course_dir: Path, n: int, tokens: dict) -> None:
    path = course_dir / "course.yaml"
    ry, data = edit_yaml(path)
    unit = next(u for u in data["units"] if u["n"] == n)
    unit["reviewed_parts"] = unit_parts(course_dir, n, tokens)
    save_yaml(ry, data, path)
