"""`coursekit delivery questions`: the tests of a course as a question bank to import in an LMS (Aiken, GIFT or Moodle XML).

With `delivery › assessment › format` set to a bank format, the questions of the tests leave the packages: they are read from the
question bank of each assessment activity of `assessment.md` (the same parse as the plan) and written in `delivery/`:

- `gift` and `moodle-xml`: one file per course, with one category per activity (`<CODE>/U1 E1.1 <activity>`);
- `aiken`: one file per activity (the format has no categories), single-choice questions only.

The feedback, the objective of each question (in its name) and the HTML of the texts are kept where the format allows it; the id of
the common error a distractor represents (`‹id›`) is for the course, never written. A question type the format cannot take is an
error (`coursekit verify` reports it earlier, while writing).
"""

from __future__ import annotations

import html as htmllib
import re
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from coursekit import assemble as assemblemod
from coursekit import course as coursemod
from coursekit.i18n import t

EXTENSIONS = {"aiken": "txt", "gift": "gift", "moodle-xml": "xml"}
DIRECTIVES = {"SINGLE_CHOICE": "single-choice", "MULTI_SELECT": "multi-select", "TRUE_FALSE": "true-false", "MATCH": "match",
              "SORTING_GROUPS": "sorting-groups", "SHORT_ANSWER": "short-answer", "FILL_IN_THE_BLANK": "fill-in-the-blank",
              "SORTING": "sorting", "ORDER_WORDS": "order-words"}
# the fractions Moodle accepts for a partly right answer (100 / n)
FRACTIONS = {1: "100", 2: "50", 3: "33.33333", 4: "25", 5: "20", 6: "16.66667", 7: "14.28571", 8: "12.5", 9: "11.11111", 10: "10"}
BLANK = re.compile(r"\{([^{}]+)\}")


class BankError(Exception):
    pass


@dataclass
class Question:
    name: str            # U1-E1.1-q3 · U1.2
    kind: str            # the brick type
    data: dict


@dataclass
class Activity:
    unit: int
    key: str             # U1-E1.1
    title: str
    questions: list[Question] = field(default_factory=list)


def activities(course: dict) -> tuple[list[Activity], list[str]]:
    """The question banks of the course's tests, in order, and what cannot be read."""
    ctx = assemblemod.context(course)
    found = []
    for unit in course.get("units") or []:
        for lesson in assemblemod.assessment_lessons(course, unit, ctx):
            activity = Activity(unit["n"], lesson["key"], lesson["title"])
            for n, brick in enumerate((b for b in lesson["bricks"] if b["type"] in DIRECTIVES), 1):
                objective = (brick.get("meta") or {}).get("objective")
                name = f"{lesson['key']}-q{n}" + (f" · {objective}" if objective else "")
                activity.questions.append(Question(name, brick["type"], brick["data"]))
            if activity.questions:
                found.append(activity)
    return found, ctx["errors"]


def problems(course: dict, fmt: str, found: list[Activity]) -> list[str]:
    allowed = coursemod.BANK_QUESTIONS[fmt]
    out = []
    for activity in found:
        for q in activity.questions:
            if DIRECTIVES[q.kind] not in allowed:
                out.append(t("questionbank", "type_not_allowed", name=q.name, kind=DIRECTIVES[q.kind], format=fmt,
                             allowed=", ".join(allowed)))
            elif q.kind == "FILL_IN_THE_BLANK" and fmt == "gift" and len(BLANK.findall(q.data["content"]["question"])) != 1:
                out.append(t("questionbank", "gift_one_blank", name=q.name))
    return out


def export(course: dict, version: str, fmt: str | None = None) -> list[Path]:
    """Writes the question bank of the course in `delivery/` and returns the files."""
    fmt = fmt or coursemod.assessment_delivery(course)[1]
    if fmt not in EXTENSIONS:
        raise BankError(t("questionbank", "not_a_bank_format", format=fmt, valid=", ".join(EXTENSIONS)))
    found, errors = activities(course)
    errors += problems(course, fmt, found)
    if errors:
        raise BankError("\n".join(errors))
    if not found:
        raise BankError(t("questionbank", "no_questions", code=course["code"]))
    folder = course["_dir"] / "delivery"
    folder.mkdir(exist_ok=True)
    written = []
    if fmt == "aiken":
        for activity in found:
            path = folder / f"{course['code']}-{activity.key}-v{version}.{EXTENSIONS[fmt]}"
            path.write_text(aiken(activity), encoding="utf-8", newline="\n")
            written.append(path)
        return written
    path = folder / f"{course['code']}-questions-v{version}.{EXTENSIONS[fmt]}"
    text = gift(course, found) if fmt == "gift" else moodle_xml(course, found)
    path.write_text(text, encoding="utf-8", newline="\n")
    return [path]


def category(course: dict, activity: Activity) -> str:
    return f"{course['code']}/{activity.key.replace('-', ' ')} {plain(activity.title).replace('/', '-')}"


def plain(value: str) -> str:
    """HTML of a text as plain text, on one line."""
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


# ── Aiken ──────────────────────────────────────────────────────────────────────────────

def aiken(activity: Activity) -> str:
    blocks = []
    for q in activity.questions:
        items = q.data["items"]
        letters = [chr(ord("A") + i) for i in range(len(items))]
        lines = [plain(q.data["content"]["question"])]
        lines += [f"{letter}. {plain(item['content'])}" for letter, item in zip(letters, items, strict=True)]
        lines.append("ANSWER: " + next(letter for letter, item in zip(letters, items, strict=True) if item["isCorrect"]))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


# ── GIFT ───────────────────────────────────────────────────────────────────────────────

def unwrap(value: str) -> str:
    """The HTML of a one-paragraph text without its paragraph (the plan wraps every short text in one)."""
    value = (value or "").strip()
    inner = value[3:-4] if value.startswith("<p>") and value.endswith("</p>") else None
    return inner if inner is not None and "<p>" not in inner else value


def gift_escape(value: str) -> str:
    return re.sub(r"([~=#{}:])", r"\\\1", value.replace("\n", " "))


def gift_text(value: str) -> str:
    """A text in GIFT: without its paragraph, on one line, its special characters escaped."""
    return gift_escape(unwrap(value))


def gift_feedback(content: dict, key: str) -> str:
    return f"#{gift_text(content[key])}" if content.get(key) else ""


def gift_general(content: dict) -> str:
    return f"####{gift_text(content['feedback_general'])}" if content.get("feedback_general") else ""


def gift_question(q: Question) -> str:
    content, data = q.data["content"], q.data
    title = f"::{gift_text(q.name)}::"
    question = f"[html]{gift_text(content['question'])}"
    right, wrong = gift_feedback(content, "feedback_correct"), gift_feedback(content, "feedback_incorrect")
    if q.kind == "SINGLE_CHOICE":
        answers = [f"{'=' if i['isCorrect'] else '~'}{gift_text(i['content'])}{right if i['isCorrect'] else wrong}" for i in data["items"]]
        return f"{title}{question} {{\n" + "\n".join(answers) + f"\n{gift_general(content)}}}"
    if q.kind == "MULTI_SELECT":
        good = sum(1 for i in data["items"] if i["isCorrect"])
        bad = len(data["items"]) - good
        answers = [f"~%{FRACTIONS[good] if i['isCorrect'] else '-' + FRACTIONS[max(1, bad)]}%{gift_text(i['content'])}"
                   f"{right if i['isCorrect'] else wrong}" for i in data["items"]]
        return f"{title}{question} {{\n" + "\n".join(answers) + f"\n{gift_general(content)}}}"
    if q.kind == "TRUE_FALSE":
        answer = "TRUE" if data["properties"]["correctAnswer"] == "true" else "FALSE"
        return f"{title}{question} {{{answer}{wrong}{right}{gift_general(content)}}}"
    if q.kind in ("MATCH", "SORTING_GROUPS"):
        pairs = [(i["left"], i["right"]) for i in data["items"]] if q.kind == "MATCH" else \
            [(i["content"], next(g["label"] for g in data["groups"] if g["id"] == i["groupId"])) for i in data["items"]]
        answers = [f"={gift_text(plain(a))} -> {gift_text(plain(b))}" for a, b in pairs]
        return f"{title}{question} {{\n" + "\n".join(answers) + f"\n{gift_general(content)}}}"
    if q.kind == "SHORT_ANSWER":
        answers = " ".join(f"={gift_text(i['text'])}" for i in data["items"])
        return f"{title}{question} {{{answers}{right}{gift_general(content)}}}"
    if q.kind == "FILL_IN_THE_BLANK":
        raw = unwrap(content["question"])
        m = BLANK.search(raw)
        answers = " ".join(f"={gift_text(a.strip())}" for a in m.group(1).split("/"))
        before, after = gift_escape(raw[: m.start()]), gift_escape(raw[m.end():])
        return f"{title}[html]{before}{{{answers}{right}{gift_general(content)}}}{after}"
    raise BankError(t("questionbank", "type_not_allowed", name=q.name, kind=DIRECTIVES[q.kind], format="gift", allowed=""))


def gift(course: dict, found: list[Activity]) -> str:
    blocks = []
    for activity in found:
        blocks.append(f"$CATEGORY: $course$/top/{gift_text(category(course, activity))}")
        blocks += [gift_question(q) for q in activity.questions]
    return "\n\n".join(blocks) + "\n"


# ── Moodle XML ─────────────────────────────────────────────────────────────────────────

def cdata(value: str) -> str:
    return "<![CDATA[" + (value or "").replace("]]>", "]]]]><![CDATA[>") + "]]>"


def html_text(tag: str, value: str, extra: str = "") -> str:
    return f'<{tag} format="html"{extra}><text>{cdata(value)}</text></{tag}>'


def moodle_question(q: Question) -> str:
    content, data = q.data["content"], q.data
    kinds = {"SINGLE_CHOICE": "multichoice", "MULTI_SELECT": "multichoice", "TRUE_FALSE": "truefalse", "MATCH": "matching",
             "SORTING_GROUPS": "matching", "SHORT_ANSWER": "shortanswer", "FILL_IN_THE_BLANK": "cloze"}
    if q.kind not in kinds:
        raise BankError(t("questionbank", "type_not_allowed", name=q.name, kind=DIRECTIVES[q.kind], format="moodle-xml", allowed=""))
    question = content["question"]
    if q.kind == "FILL_IN_THE_BLANK":
        def cloze(m: re.Match) -> str:
            return "{1:SHORTANSWER:" + "~".join("=" + a.strip().replace("}", "\\}") for a in m.group(1).split("/")) + "}"
        question = BLANK.sub(cloze, question)
    parts = [f'<question type="{kinds[q.kind]}">', f"<name><text>{xml_escape(q.name)}</text></name>",
             html_text("questiontext", question), html_text("generalfeedback", content.get("feedback_general", "")),
             "<defaultgrade>1</defaultgrade>", "<penalty>0.3333333</penalty>", "<hidden>0</hidden>"]
    right, wrong = content.get("feedback_correct", ""), content.get("feedback_incorrect", "")
    if q.kind in ("SINGLE_CHOICE", "MULTI_SELECT"):
        single = q.kind == "SINGLE_CHOICE"
        good = sum(1 for i in data["items"] if i["isCorrect"])
        bad = len(data["items"]) - good
        parts += [f"<single>{'true' if single else 'false'}</single>", "<shuffleanswers>true</shuffleanswers>",
                  "<answernumbering>abc</answernumbering>", html_text("correctfeedback", right),
                  html_text("partiallycorrectfeedback", wrong), html_text("incorrectfeedback", wrong)]
        for item in data["items"]:
            fraction = ("100" if single else FRACTIONS[good]) if item["isCorrect"] else ("0" if single else "-" + FRACTIONS[max(1, bad)])
            parts.append(f'<answer fraction="{fraction}" format="html"><text>{cdata(item["content"])}</text>'
                         f'{html_text("feedback", right if item["isCorrect"] else wrong)}</answer>')
    elif q.kind == "TRUE_FALSE":
        correct = data["properties"]["correctAnswer"]
        for value in ("true", "false"):
            parts.append(f'<answer fraction="{100 if value == correct else 0}" format="moodle_auto_format"><text>{value}</text>'
                         f'{html_text("feedback", right if value == correct else wrong)}</answer>')
    elif q.kind in ("MATCH", "SORTING_GROUPS"):
        pairs = [(i["left"], i["right"]) for i in data["items"]] if q.kind == "MATCH" else \
            [(i["content"], next(g["label"] for g in data["groups"] if g["id"] == i["groupId"])) for i in data["items"]]
        parts += ["<shuffleanswers>true</shuffleanswers>", html_text("correctfeedback", right),
                  html_text("partiallycorrectfeedback", wrong), html_text("incorrectfeedback", wrong)]
        parts += [f'<subquestion format="html"><text>{cdata(a)}</text><answer><text>{xml_escape(plain(b))}</text></answer></subquestion>'
                  for a, b in pairs]
    elif q.kind == "SHORT_ANSWER":
        parts.append("<usecase>0</usecase>")
        parts += [f'<answer fraction="100" format="moodle_auto_format"><text>{xml_escape(i["text"])}</text>'
                  f'{html_text("feedback", right)}</answer>' for i in data["items"]]
    parts.append("</question>")
    return "\n".join(parts)


def moodle_xml(course: dict, found: list[Activity]) -> str:
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', "<quiz>"]
    for activity in found:
        parts.append(f'<question type="category"><category><text>$course$/top/{xml_escape(category(course, activity))}</text>'
                     "</category></question>")
        parts += [moodle_question(q) for q in activity.questions]
    parts.append("</quiz>")
    return "\n".join(parts) + "\n"
