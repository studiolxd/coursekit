"""Does the package carry every word of the content? The words the learner reads in content.md and assessment.md must all be in
the page: a brick that was dropped on the way would be missing here.

Only learner-facing text counts (the syntax of the format, the metadata and the media placeholders do not), compared as sets
of words, so the check cannot fail because of how a component lays the text out.
"""

from __future__ import annotations

import html as htmllib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import yaml

from coursekit import course as coursemod
from coursekit import lang
from coursekit.misconceptions import strip_tag

WORD = re.compile(r"\w+", re.UNICODE)
FENCE = re.compile(r"^\s*(```|~~~)")


SIMULATION_OPEN = re.compile(r"^\s*:::(scenario|conversation)\s*$")
TEXT_KEYS = ("title", "text", "label", "feedback", "debriefing")  # what the learner reads in a simulation (besides `screen`)


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.simulations: list[str] = []  # the data of the simulations the player reads
        self.skip = 0
        self.in_data = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in ("script", "style"):
            self.skip += 1
            self.in_data = tag == "script" and "ck-sim-data" in (dict(attrs).get("class") or "")
            if self.in_data:
                self.simulations.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self.skip -= 1
            self.in_data = False

    def handle_data(self, data: str) -> None:
        if self.in_data:
            self.simulations[-1] += data
        elif not self.skip:
            self.parts.append(data)


def simulation_text(value: object, key: str = "", screen: bool = False) -> list[str]:
    """The texts a learner reads in the data of a simulation: situations, variants, decisions, feedback, debriefings, titles and
    whatever its screens show; not its ids, conditions or the names of the files."""
    if isinstance(value, dict):
        return [t for k, v in value.items() if not str(k).startswith("_")
                for t in simulation_text(v, k, screen or k == "screen")]
    if isinstance(value, list):
        return [t for v in value for t in simulation_text(v, key, screen)]
    if isinstance(value, str) and (screen or key in TEXT_KEYS):
        return [value]
    return []


def page_words(page: str) -> set[str]:
    parser = _Text()
    parser.feed(page)
    texts = parser.parts[:]
    for raw in parser.simulations:
        try:
            texts += simulation_text(json.loads(raw.replace("<\\/", "</")))
        except ValueError:
            continue
    return set(WORD.findall(htmllib.unescape(re.sub(r"<[^>]+>", " ", " ".join(texts))).casefold()))


def learner_text(path: Path, tokens: dict, assessment: bool) -> str:
    """The text of a content file as the learner reads it, without the syntax of the format."""
    ignored_keys = {lang.directive_key(tokens, name) for name in ("objective", "image", "position")}
    key_re = re.compile(r"^\s*([a-zà-ÿ][a-zà-ÿ-]*):\s*(.*)$")
    kept: list[str] = []
    in_fence = in_placeholder = False
    published = {tokens["assessment_instructions"], tokens["assessment_bank"]}  # the only subsections of an activity the plan renders
    in_published = not assessment
    text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
    lines = text.splitlines()
    if not assessment:  # the unit header before the first section (hours, minimums, objectives) is for the writer, not published
        first = next((n for n, line in enumerate(lines) if line.startswith(f"## {tokens['section']} ")), 0)
        lines = lines[first:]
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not in_fence and SIMULATION_OPEN.match(line):  # its YAML: what the learner reads in it, wherever it is
            body = []
            while i < len(lines) and lines[i].strip() != ":::":
                body.append(lines[i])
                i += 1
            i += 1
            try:
                kept += simulation_text(yaml.safe_load("\n".join(body)))
            except yaml.YAMLError:
                pass
            continue
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
        if re.match(r"^\s*[-*]\s+\[[ xX]\]\s+", line):
            line = strip_tag(re.sub(r"^\s*[-*]\s+\[[ xX]\]\s+", "", line))[0]
        line = re.sub(r"^\s*\d+[.)]\s+", "", line)  # the number of a numbered list is drawn by the list
        kept.append(line)
    out = "\n".join(kept)
    out = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", out)
    out = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", out)
    out = re.sub(r"<[^>]+>", " ", out)
    return htmllib.unescape(out)


def missing_words(course: dict, unit: dict, page: str) -> list[str]:
    """The words of the unit's `.md` the learner should read that the page lacks. The tests are checked where they go: in their unit,
    or in the package of the tests when they go apart; with a question-bank format they leave the packages and are not checked."""
    tokens = coursemod.tokens(course)
    placement, fmt = coursemod.assessment_delivery(course)
    files: list[tuple[Path, bool]] = []
    if unit.get("kind") == "assessment":
        sources = [coursemod.unit_dir(course["_dir"], n) for n in unit.get("sources") or []]
        files += [(folder / "assessment.md", True) for folder in sources if fmt == "platform"]
    else:
        folder = coursemod.unit_dir(course["_dir"], unit["n"])
        files.append((folder / "content.md", False))
        if placement == "unit" and fmt == "platform":
            files.append((folder / "assessment.md", True))
    wanted: set[str] = set()
    for path, assessment in files:
        if path.exists():
            wanted |= set(WORD.findall(learner_text(path, tokens, assessment).casefold()))
    return sorted(wanted - page_words(page))
