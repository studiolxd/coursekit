"""`coursekit outline`: compact map of a course for the agents, so they need not load every unit.

Without options: every unit with its status, objectives and sections (title, objectives, minimum
words and how much is written). With --section U.S: only the text of that section (e.g. 2.3), to
check what an earlier unit already says about a topic.
"""

from __future__ import annotations

import re
from pathlib import Path

from coursekit import course as coursemod
from coursekit.i18n import t
from coursekit.lang import format_number

WORD = re.compile(r"\w+")


def sections_text(content: str, tokens: dict) -> dict[int, str]:
    """Body of each section, without HTML comments."""
    heading = re.compile(rf"^## {re.escape(tokens['section'])} (\d+)\s*[—-]\s*(.+?)\s*(?:\*\(.*\)\*)?\s*$", re.M)
    marks = list(heading.finditer(content))
    out = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(content)
        out[int(m.group(1))] = re.sub(r"<!--.*?-->", "", content[m.end() : end], flags=re.S).strip()
    return out


def written(course_dir: Path, n: int, tokens: dict) -> dict[int, str]:
    path = coursemod.unit_dir(course_dir, n) / "content.md"
    return sections_text(path.read_text(encoding="utf-8"), tokens) if path.exists() else {}


def outline(course: dict) -> str:
    tokens = coursemod.tokens(course)
    fmt = lambda n: format_number(n, coursemod.language(course))  # noqa: E731
    lines = [f"{course['code']} — {course['title']} ({course['design']['hours']} h)"]
    for u in course.get("units") or []:
        texts = written(course["_dir"], u["n"], tokens)
        lines.append(f"\nU{u['n']} {u['title']} · {u['hours']} h · {u.get('status', 'pending')}")
        for o in u.get("objectives") or []:
            lines.append(f"  {o['id']} ({o.get('bloom')}): {o['text']}")
        for s in u.get("sections") or []:
            words = len(WORD.findall(texts.get(s["n"], "")))
            state = t("outline", "words_written", words=fmt(words)) if words else t("outline", "not_written")
            objs = f" [{', '.join(s['objectives'])}]" if s.get("objectives") else ""
            lines.append(
                t("outline", "section_line", unit=u["n"], section=s["n"], title=s["title"], objectives=objs,
                  minimum=fmt(s["min_words"]), state=state)
            )
            for sub in s.get("subsections") or []:
                lines.append(f"      · {sub}")
    lines.append("\n" + t("outline", "read_one_section"))
    return "\n".join(lines)


def section(course: dict, ref: str) -> str:
    try:
        n, s = (int(x) for x in ref.split("."))
    except ValueError as exc:
        raise ValueError(t("outline", "section_takes")) from exc
    text = written(course["_dir"], n, coursemod.tokens(course)).get(s)
    return text or t("outline", "section_not_written", ref=ref)
