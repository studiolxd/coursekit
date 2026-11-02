"""The visual plan of a course: `courses/<CODE>/design/visuals.yaml`.

What the learner will see in each section, decided with the design and signed with it (`coursekit approve design`), so that the
visual side of a course is not left to whoever writes a unit. The design agent writes it; `coursekit sync` puts it in the
skeleton of each section; the writer follows it; `coursekit verify` warns when a section carries fewer visual resources than
its plan. Keys are the sections as `coursekit sync CODE --check` prints them (`U1.S2`), and each entry a resource type id and
what it shows:

    U1.S2:
      - {type: image, what: Capture of the settings window, with the minimum length field}
      - {type: infographic, what: Length against complexity, side by side}
    U1.S3:
      - {type: image, what: A photo of a sticky note with a password on a monitor}
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

import yaml

from coursekit.i18n import t

FILE = Path("design") / "visuals.yaml"
KEY_RE = re.compile(r"^U(\d+)\.S(\d+)$")


def path(course: dict) -> Path:
    return cast("Path", course["_dir"] / FILE)


def load(course: dict, types: list[str] | None = None) -> tuple[dict[tuple[int, int], list[dict]], list[str]]:
    """The plan, by (unit, section), and its problems (a key that is not a section, a type that is not visual)."""
    file = path(course)
    if not file.exists():
        return {}, []
    try:
        data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return {}, [t("visualplan", "bad_yaml", path=FILE.as_posix(), error=str(exc).splitlines()[0])]
    if not isinstance(data, dict):
        return {}, [t("visualplan", "bad_yaml", path=FILE.as_posix(), error="not a mapping")]
    plan: dict[tuple[int, int], list[dict]] = {}
    problems = []
    for key, entries in data.items():
        m = KEY_RE.match(str(key))
        if not m:
            problems.append(t("visualplan", "bad_key", key=key, path=FILE.as_posix()))
            continue
        items = []
        for entry in entries or []:
            kind = str((entry or {}).get("type") or "") if isinstance(entry, dict) else ""
            if types is not None and kind not in types:
                problems.append(t("visualplan", "bad_type", key=key, type=kind or "—", types=", ".join(types)))
                continue
            items.append({"type": kind, "what": str(entry.get("what") or "")})
        plan[(int(m.group(1)), int(m.group(2)))] = items
    return plan, problems


def hint(course: dict | None, unit: int, section: int, words: dict) -> str:
    """The visuals of a section, as the skeleton of `content.md` shows them (` · visuals: Image: …; Infographic: …`)."""
    if course is None:
        return ""
    plan, _ = load(course)
    items = plan.get((unit, section)) or []
    labels = words.get("media_types") or {}
    return f" · visuals: {'; '.join(f'{labels.get(i['type'], i['type'])}: {i['what']}' for i in items)}" if items else ""
