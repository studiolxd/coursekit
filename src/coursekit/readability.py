"""How hard the prose of a section is to read, for `coursekit verify` (warnings only).

Two measures on the learner's prose (paragraphs and list items; not directives, placeholders, headings, tables, code or
comments): the share of long sentences, and a readability index of the language, both calibrated by the audience of the
course (`rules › readability › audience`):

- Spanish: Szigriszt-Pazos (the INFLESZ scale): 206.835 − 62.3 · syllables/words − words/sentences.
- English: Flesch reading ease: 206.835 − 84.6 · syllables/words − 1.015 · words/sentences.
- Other languages: only the length of the sentences.

Both indexes read alike: around 65 or more is easy, 55–65 normal, 40–55 somewhat hard, below 40 hard.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

FENCE_RE = re.compile(r"^\s*(```|~~~)")
DIRECTIVE_OPEN_RE = re.compile(r"^:::[a-z]")
DIRECTIVE_CLOSE_RE = re.compile(r"^:::\s*$")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
SENTENCE_END_RE = re.compile(r"(?<=[.!?…])[\"'»”)\]]*\s+")
WORD_RE = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*")

INDEXES = {"es": "Szigriszt-Pazos", "en": "Flesch"}


def prose(lines: list[str]) -> list[str]:
    """The paragraphs and list items the learner reads as running text, one string each."""
    text = COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), "\n".join(lines))
    blocks: list[str] = []
    current: list[str] = []
    stack: list[str] = []  # the open directives; an adaptive block (:::if … :::else … :::) is prose, both branches
    fenced = False

    def flush() -> None:
        if current:
            blocks.append(" ".join(current))
            current.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if FENCE_RE.match(line):
            fenced = not fenced
            flush()
            continue
        if fenced:
            continue
        if re.match(r"^:::(else\s*|elif\s.*)$", line):
            flush()
            continue
        if DIRECTIVE_OPEN_RE.match(line):
            stack.append("if" if re.match(r"^:::if\s", line) else "directive")
            flush()
            continue
        if DIRECTIVE_CLOSE_RE.match(line) and stack:
            stack.pop()
            flush()
            continue
        skipping = "directive" in stack
        if skipping or not line or line.startswith(("#", ">", "|", "*[", "![")):
            flush()
            continue
        item = re.match(r"^(?:[-*+]|\d+[.)])\s+(.*)$", line)
        if item:
            flush()
            blocks.append(item.group(1))
            continue
        current.append(line)
    flush()
    return [re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", re.sub(r"[*_`]", "", block)) for block in blocks]


def stretches(lines: list[str]) -> list[str]:
    """The runs of prose the learner reads without a break, one string each: paragraphs one after another (a blank line does
    not break them) until a heading, a directive, a medium or a highlight (`>`), a list, a table, an image or code."""
    text = COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), "\n".join(lines))
    runs: list[str] = []
    current: list[str] = []
    depth = 0  # inside a directive: its body is not running prose (an adaptive block breaks the run too)
    fenced = False

    def flush() -> None:
        if current:
            runs.append(" ".join(current))
            current.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if FENCE_RE.match(line):
            fenced = not fenced
            flush()
            continue
        if fenced:
            continue
        if DIRECTIVE_OPEN_RE.match(line):
            depth += 1
            flush()
            continue
        if DIRECTIVE_CLOSE_RE.match(line) and depth:
            depth -= 1
            flush()
            continue
        if not line:
            continue
        if depth or line.startswith(("#", ">", "|", "*[", "![", ":::")) or re.match(r"^(?:[-*+]|\d+[.)])\s+", line):
            flush()
            continue
        current.append(line)
    flush()
    return [re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", re.sub(r"[*_`]", "", run)) for run in runs]


def sentences(blocks: list[str]) -> list[str]:
    out = []
    for block in blocks:
        out += [s.strip() for s in SENTENCE_END_RE.split(block) if WORD_RE.search(s)]
    return out


def words(sentence: str) -> list[str]:
    return WORD_RE.findall(sentence)


ES_VOWELS = "aeiouáéíóúü"
ES_STRONG = "aeoáéíóú"  # stressed i/u break a diphthong


def syllables_es(word: str) -> int:
    """Spanish syllables: groups of vowels, where two strong vowels (or a stressed weak one) make a hiatus."""
    w = word.lower()
    count = 0
    previous = ""
    for ch in w:
        if ch in ES_VOWELS:
            if not previous or (previous in ES_STRONG and ch in ES_STRONG):
                count += 1
            previous = ch
        else:
            previous = ""
    if w.endswith("y") and len(w) > 1 and w[-2] not in ES_VOWELS:  # "muy", "hoy" end in a vowel sound
        count += 1
    return max(1, count)


def syllables_en(word: str) -> int:
    """English syllables, by the usual heuristic: groups of vowels, a silent final e, -le and -ed endings."""
    w = word.lower().strip("'’")
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|(?<![td])ed|[^laeiouy]e)$", "", w)  # "created" keeps its -ted
    w = re.sub(r"^y", "", w)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", w)))


SYLLABLES = {"es": syllables_es, "en": syllables_en}


def index(language: str, n_sentences: int, n_words: int, n_syllables: int) -> float | None:
    if not n_sentences or not n_words:
        return None
    per_word, per_sentence = n_syllables / n_words, n_words / n_sentences
    if language == "es":
        value = 206.835 - 62.3 * per_word - per_sentence
    elif language == "en":
        value = 206.835 - 84.6 * per_word - 1.015 * per_sentence
    else:
        return None
    return max(0.0, min(100.0, value))  # both scales go from 0 (very hard) to 100 (very easy)


@dataclass
class Measure:
    sentences: int = 0
    words: int = 0
    long: list[str] = field(default_factory=list)  # the long sentences
    index: float | None = None
    index_name: str = ""

    @property
    def average(self) -> float:
        return self.words / self.sentences if self.sentences else 0.0


def measure(lines: list[str], language: str, long_words: int) -> Measure:
    found = sentences(prose(lines))
    count = SYLLABLES.get(language)
    result = Measure(sentences=len(found), index_name=INDEXES.get(language, ""))
    n_syllables = 0
    for sentence in found:
        tokens = words(sentence)
        result.words += len(tokens)
        if len(tokens) > long_words:
            result.long.append(sentence)
        if count:
            n_syllables += sum(count(token) for token in tokens)
    if count:
        result.index = index(language, result.sentences, result.words, n_syllables)
    return result


def start(sentence: str, n: int = 8) -> str:
    """The first words of a sentence, to find it."""
    tokens = sentence.split()
    return " ".join(tokens[:n]) + (" …" if len(tokens) > n else "")
