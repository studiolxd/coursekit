"""Personal data in the text of a capture: what is found, and the invented data that replaces it.

`find(text, rules, people)` returns the stretches of a text that hold personal data: the kinds of `capture.yaml › redact ›
patterns` (a regular expression per id), the names of people (a known first name followed by one or two capitalised words)
and the `extra_terms`. Where the text is exact (`strict`, the text of a page) the known ids are also checked (the digits of a
phone, the check digits of an IBAN, a card or a Spanish DNI/NIE, the numbers of an IP), so that a reference or a version
number is not taken for one; on the pixels (`strict=False`) every text with the shape is covered, because the reading can
be wrong.

`fake(kind, value, people)` is what replaces a stretch: always the same for the same value, of a similar length and with the
same shape (an IBAN still looks like an IBAN), with the invented people and companies of the course language
(`lang/<code>.yaml › capture_people`).
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

from coursekit import lang

NAME_WORD = r"[A-ZÁÉÍÓÚÑÜÇ][a-záéíóúñüçàèìòùâêîôûäëïöÿ'’-]+"


@dataclass(frozen=True)
class Finding:
    kind: str
    start: int
    end: int


@dataclass
class People:
    """The invented people of one language (for what replaces) and the names of every language (to find them)."""

    women: list[str]
    men: list[str]
    last_names: list[str]
    companies: list[str]
    email_domain: str
    known_women: frozenset[str]
    known_men: frozenset[str]

    @property
    def known_first(self) -> frozenset[str]:
        return self.known_women | self.known_men


def people(language: str) -> People:
    own = lang.tokens(language)["capture_people"]
    every = [lang.tokens(code)["capture_people"] for code in lang.LANGUAGES]
    return People(list(own["women"]), list(own["men"]), list(own["last_names"]), list(own["companies"]), str(own["email_domain"]),
                  frozenset(n for p in every for n in p["women"]), frozenset(n for p in every for n in p["men"]))


# ── checks of the known kinds (where the text is exact) ──────────────────────────────────────

def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def _luhn(number: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(number)):
        d = int(ch)
        if i % 2:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


def _iban(value: str) -> bool:
    text = value.replace(" ", "").upper()
    if not 15 <= len(text) <= 34:
        return False
    moved = text[4:] + text[:4]
    return int("".join(str(int(ch, 36)) for ch in moved)) % 97 == 1


def _national_id(value: str) -> bool:
    text = re.sub(r"[- ]", "", value.upper())
    number = text[:-1].replace("X", "0").replace("Y", "1").replace("Z", "2")
    return number.isdigit() and "TRWAGMYFPDXBNJZSQVHLCKE"[int(number) % 23] == text[-1]


CHECKS = {
    "phone": lambda v: 9 <= len(_digits(v)) <= 15,
    "card": lambda v: 13 <= len(_digits(v)) <= 19 and _luhn(_digits(v)),
    "iban": _iban,
    "national_id": _national_id,
    "ip": lambda v: all(int(part) <= 255 for part in v.split(".")),
}


# ── finding ──────────────────────────────────────────────────────────────────────────────────

def _plain(word: str) -> str:
    """A word without accents, lowercase: a reading that lost the accents (`Lucia`) still matches `Lucía`."""
    return unicodedata.normalize("NFKD", word).encode("ascii", "ignore").decode().lower()


def _names(text: str, known_first: frozenset[str]) -> list[Finding]:
    known = {_plain(n) for n in known_first}
    found = []
    for match in re.finditer(rf"(?<![\w@.])({NAME_WORD})((?:[ ]{NAME_WORD}){{1,2}})(?![\w@])", text):
        if _plain(match.group(1)) in known:
            found.append(Finding("name", match.start(), match.end()))
    return found


def find(text: str, rules: dict, who: People, terms: list[str] = (), strict: bool = True) -> list[Finding]:
    """The stretches of `text` with personal data, without overlaps (the first kind of `patterns` wins, then the longest)."""
    candidates: list[tuple[int, Finding]] = []
    for rank, (kind, expression) in enumerate((rules.get("patterns") or {}).items()):
        if not expression:
            continue
        for match in re.finditer(expression, text):
            check = CHECKS.get(kind)
            if strict and check and not check(match.group(0)):
                continue
            candidates.append((rank, Finding(kind, match.start(), match.end())))
    rank = len(rules.get("patterns") or {})
    if rules.get("names"):
        candidates += [(rank, f) for f in _names(text, who.known_first)]
    for term in [*(rules.get("extra_terms") or []), *terms]:
        if str(term).strip():
            candidates += [(-1, Finding("term", m.start(), m.end())) for m in re.finditer(re.escape(str(term)), text, re.I)]
    chosen: list[Finding] = []
    for _, finding in sorted(candidates, key=lambda c: (c[0], -(c[1].end - c[1].start), c[1].start)):
        if all(finding.end <= other.start or finding.start >= other.end for other in chosen):
            chosen.append(finding)
    return sorted(chosen, key=lambda f: f.start)


# ── invented data ────────────────────────────────────────────────────────────────────────────

def _seed(*parts: str) -> int:
    return int.from_bytes(hashlib.sha256("\x00".join(parts).encode("utf-8")).digest()[:8], "big")


def _closest(pool: list[str], word: str) -> str:
    """The invented word of a length closest to the real one, always the same for the same word, never the word itself."""
    options = [p for p in pool if p.casefold() != word.casefold()] or pool
    return min(options, key=lambda p: (abs(len(p) - len(word)), _seed(word, p)))


def scramble(value: str, salt: str = "") -> str:
    """The same shape with other characters: each digit another digit, each letter another letter of the same case."""
    out = []
    for i, ch in enumerate(value):
        n = _seed(salt, value, str(i))
        if ch.isdigit():
            out.append(str((int(ch) + 1 + n % 9) % 10))
        elif ch.isascii() and ch.isalpha():
            letter = chr(ord("a") + (ord(ch.lower()) - ord("a") + 1 + n % 25) % 26)
            out.append(letter.upper() if ch.isupper() else letter)
        else:
            out.append(ch)
    return "".join(out)


def _ascii(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower().replace(" ", "")


def fake_name(value: str, who: People) -> str:
    """An invented person of the same gender as the first name (when the lists know it) and similar length."""
    words = value.split(" ")
    first = who.men if words[0] in who.known_men and words[0] not in who.known_women else who.women
    out = [_closest(first, words[0])]
    out += [_closest(who.last_names, w) for w in words[1:]]
    return " ".join(out)


def fake(kind: str, value: str, who: People) -> str:
    """What replaces `value` on screen: the same for the same value, of a similar length and shape."""
    if kind == "name":
        return fake_name(value, who)
    if kind == "email":
        local = value.split("@", 1)[0]
        first, last = _closest(who.women + who.men, local), _closest(who.last_names, value)
        return f"{_ascii(first)}.{_ascii(last)}@{who.email_domain}"
    if kind == "term":
        return _closest(who.companies, value)
    if kind == "ip":
        return f"192.0.2.{1 + _seed(value) % 254}"  # the range reserved for documentation
    if kind == "iban":
        return value[:2] + scramble(value[2:], kind)
    return scramble(value, kind)


def replace(text: str, rules: dict, who: People, terms: list[str] = ()) -> str:
    """The text with every stretch of personal data replaced by its invented counterpart (the text of a page is exact)."""
    out, last = [], 0
    for finding in find(text, rules, who, terms, strict=True):
        out += [text[last:finding.start], fake(finding.kind, text[finding.start:finding.end], who)]
        last = finding.end
    return "".join(out) + text[last:]
