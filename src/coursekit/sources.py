"""Finding the passages of the reference material a section needs (`coursekit brief CODE --find` / `--section`).

A large brief does not fit in an agent's context, and most of it is not about the section being written. The Markdown of
`brief/text/` (of the course and of the project) is cut into passages (by headings and paragraphs, about
`rules › brief › passage_words` words each) and ranked with BM25, locally and without any service: a query (the words
given, or the title, objectives and unit of a section of the design) gets the best passages, each with the file and
lines it comes from, so the writer cites them and opens nothing else.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from coursekit import lang

WORD_RE = re.compile(r"[^\W_]+", re.U)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
K1, B = 1.5, 0.75  # the usual BM25 constants


@dataclass
class Passage:
    file: Path
    start: int  # first line (1-based)
    end: int
    heading: str
    text: str
    terms: Counter


def normalise(word: str) -> str:
    """Lower case, without accents, and a light stem: the plural endings go (so "contraseñas" finds "contraseña")."""
    word = "".join(c for c in unicodedata.normalize("NFD", word.lower()) if unicodedata.category(c) != "Mn")
    for ending in ("es", "s"):
        if len(word) > 4 and word.endswith(ending):
            return word[: -len(ending)]
    return word


def terms(text: str, stopwords: set[str]) -> list[str]:
    return [normalise(w) for w in WORD_RE.findall(text) if len(w) > 1 and normalise(w) not in stopwords and not w.isdigit()]


def passages(files: list[Path], size: int, stopwords: set[str]) -> list[Passage]:
    """The passages of some Markdown files: a heading starts a new one; paragraphs are added until about `size` words."""
    out: list[Passage] = []
    for file in files:
        lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
        heading, chunk, start = "", [], 1
        for i, line in enumerate(lines, 1):
            m = HEADING_RE.match(line)
            if m or (not line.strip() and len(" ".join(chunk).split()) >= size):
                _close(out, file, start, i - 1, heading, chunk, stopwords)
                chunk, start = [], i + (0 if m else 1)
                if m:
                    heading = m.group(2).strip()
                    continue
            chunk.append(line)
        _close(out, file, start, len(lines), heading, chunk, stopwords)
    return out


def _close(out: list[Passage], file: Path, start: int, end: int, heading: str, chunk: list[str], stopwords: set[str]) -> None:
    text = "\n".join(chunk).strip()
    if WORD_RE.search(text):
        out.append(Passage(file, start, end, heading, text, Counter(terms(heading + " " + text, stopwords))))


def rank(found: list[Passage], query: str, stopwords: set[str], top: int) -> list[tuple[float, Passage]]:
    """BM25 of the passages for a query: the `top` best, with their score."""
    wanted = list(dict.fromkeys(terms(query, stopwords)))
    if not found or not wanted:
        return []
    n = len(found)
    average = sum(sum(p.terms.values()) for p in found) / n or 1
    df = {term: sum(1 for p in found if term in p.terms) for term in wanted}
    scored = []
    for p in found:
        length = sum(p.terms.values())
        score = 0.0
        for term in wanted:
            tf = p.terms.get(term, 0)
            if not tf:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * length / average))
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda item: (-item[0], str(item[1].file), item[1].start))
    return scored[:top]


def text_files(*briefs: Path) -> list[Path]:
    """The Markdown of the material of some brief folders (`brief/text/`)."""
    found = []
    for brief in briefs:
        folder = brief / "text"
        if folder.is_dir():
            found += sorted(p for p in folder.rglob("*.md") if p.is_file())
    return found


def stopwords(language: str) -> set[str]:
    return {normalise(w) for w in lang.tokens(language).get("stopwords") or []}


def section_query(course: dict, ref: str) -> tuple[str, str] | None:
    """(query, label) of a section of the design, `U.S` (e.g. 1.2): its title, its objectives and its unit; None if it
    does not exist."""
    m = re.fullmatch(r"(\d+)\.(\d+)", ref.strip())
    if not m:
        return None
    unit = next((u for u in course.get("units") or [] if u["n"] == int(m.group(1))), None)
    if unit is None:
        return None
    section = next((s for s in unit.get("sections") or [] if s.get("n") == int(m.group(2))), None)
    if section is None:
        return None
    objectives = {str(o.get("id")): str(o.get("text") or "") for o in unit.get("objectives") or [] if isinstance(o, dict)}
    texts = [objectives.get(str(o), "") for o in section.get("objectives") or []]
    query = " ".join([section.get("title") or "", section.get("title") or ""] + texts + [unit.get("title") or ""])
    return query, f"{m.group(1)}.{m.group(2)} {section.get('title') or ''}".strip()
