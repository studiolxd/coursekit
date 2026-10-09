"""Does the package carry every word of the content? The words the learner reads in content.md and assessment.md must all be in
the page: a brick that was dropped on the way would be missing here.

Only learner-facing text counts (the syntax of the format, the metadata and the media placeholders do not), compared as sets
of words, so the check cannot fail because of how a component lays the text out.
"""

from __future__ import annotations

import html as htmllib
import re
from html.parser import HTMLParser
from pathlib import Path

from coursekit import course as coursemod
from coursekit import lang

WORD = re.compile(r"\w+", re.UNICODE)
FENCE = re.compile(r"^\s*(```|~~~)")


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self.skip -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)


def page_words(page: str) -> set[str]:
    parser = _Text()
    parser.feed(page)
    return set(WORD.findall(" ".join(parser.parts).casefold()))


def learner_text(path: Path, tokens: dict, assessment: bool) -> str:
    """The text of a content file as the learner reads it, without the syntax of the format."""
    ignored_keys = {lang.directive_key(tokens, name) for name in ("objective", "image", "position")}
    key_re = re.compile(r"^\s*([a-zà-ÿ][a-zà-ÿ-]*):\s*(.*)$")
    kept: list[str] = []
    in_fence = in_placeholder = False
    published = {tokens["assessment_instructions"], tokens["assessment_bank"]}  # the only subsections of an activity the plan renders
    in_published = not assessment
    text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        stripped = line.strip()
        if in_fence:
            kept.append(line)
            continue
        if re.match(rf"^>\s*\*\*\[{re.escape(tokens['placeholder'])}", stripped):
            in_placeholder = True
            continue
        if in_placeholder:
            if stripped.startswith(">"):
                continue
            in_placeholder = False
        if assessment and stripped.startswith("## "):
            in_published = False
        if re.match(r"^#{1,2} ", stripped) or stripped.startswith(":::") or stripped == "---":
            continue
        if assessment and re.match(r"^### (.+?)\s*$", stripped):
            in_published = stripped[4:].strip() in published
            continue
        if assessment and not in_published:
            continue
        if re.match(rf"^\*\[{re.escape(tokens['objective'])}", stripped):
            continue
        match = key_re.match(line)
        if match and not stripped.startswith(("-", "*")):
            if match.group(1) in ignored_keys:
                continue
            if match.group(1) in lang.directive_keys(tokens):
                line = match.group(2)
        line = re.sub(r"^\s*[-*]\s+\[[ xX]\]\s+", "", line)
        line = re.sub(r"^\s*\d+[.)]\s+", "", line)  # the number of a numbered list is drawn by the list
        kept.append(line)
    out = "\n".join(kept)
    out = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", out)
    out = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", out)
    out = re.sub(r"<[^>]+>", " ", out)
    return htmllib.unescape(out)


def missing_words(course: dict, unit: dict, page: str) -> list[str]:
    tokens = coursemod.tokens(course)
    folder = coursemod.unit_dir(course["_dir"], unit["n"])
    wanted: set[str] = set()
    for name, assessment in (("content.md", False), ("assessment.md", True)):
        path = folder / name
        if path.exists():
            wanted |= set(WORD.findall(learner_text(path, tokens, assessment).casefold()))
    return sorted(wanted - page_words(page))
