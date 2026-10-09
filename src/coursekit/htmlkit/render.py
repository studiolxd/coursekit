"""Plan -> HTML: one function per brick type (the component). Pure strings, no browser.

The markup is complete without JavaScript (everything readable, answers included); the player (templates/html/player) enhances
it: tabs, carousels, cards, hotspots, the check of the questions, the shuffling and the SCORM tracking. The questions carry their
data in the markup (`data-*` and hidden keys), so the text of every answer is in the document.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from html import escape

from coursekit.htmlkit.sanitize import clean, unwrap

QUESTIONS = {"SINGLE_CHOICE", "MULTI_SELECT", "TRUE_FALSE", "SORTING", "MATCH", "SORTING_GROUPS", "FILL_IN_THE_BLANK", "ORDER_WORDS",
             "SHORT_ANSWER"}
UNSUPPORTED = {"WORD_SEARCH", "WORDLE", "HANGMAN", "PASAPALABRA", "MEMORY", "TRIVIAL"}  # the games: a later delivery
BLANK = re.compile(r"\{([^{}]+)\}")


class RenderError(Exception):
    pass


class Ctx:
    """What a component needs to know about where it is."""

    def __init__(self, ui: dict[str, str], lesson: str, evaluation: bool = False):
        self.ui = ui
        self.lesson = lesson
        self.evaluation = evaluation
        self.n = 0  # bricks of the lesson so far
        self.questions = 0

    def say(self, key: str, **values: object) -> str:
        text = self.ui[key]
        return text.format(**values) if values else text

    def next_id(self) -> str:
        self.n += 1
        return f"{self.lesson}-b{self.n}"


def a(value: object) -> str:
    return escape(str(value), quote=True)


def prop(brick: dict, name: str, default: object = "") -> object:
    return (brick["data"].get("properties") or {}).get(name, default)


def content(brick: dict, name: str = "content") -> str:
    return (brick["data"].get("content") or {}).get(name) or ""


def items(brick: dict) -> list[dict]:
    return brick["data"].get("items") or []


def block(fragment: str | None) -> str:
    return clean(fragment)


def inline(fragment: str | None) -> str:
    return unwrap(fragment)


# ── text ─────────────────────────────────────────────────────────────────────────────────────

def text(brick: dict, ctx: Ctx) -> str:
    return f'<div class="ck-text">{block(content(brick))}</div>'


def heading(brick: dict, ctx: Ctx) -> str:
    level = min(6, max(3, int(prop(brick, "level", 3) or 3)))
    return f"<h{level} class=\"ck-heading\">{inline(content(brick))}</h{level}>"


def code(brick: dict, ctx: Ctx) -> str:
    language = str(prop(brick, "codeLanguage", "auto"))
    css = f' class="language-{a(language)}"' if re.fullmatch(r"[a-z0-9+#-]+", language) and language != "auto" else ""
    return f'<pre class="ck-code" tabindex="0"><code{css}>{escape(content(brick), quote=False)}</code></pre>'


def bullets(brick: dict, ctx: Ctx) -> str:
    tag = "ol" if prop(brick, "listType") == "numbered" else "ul"
    rows = "".join(f"<li>{inline(i.get('content'))}</li>" for i in items(brick))
    return f'<{tag} class="ck-list">{rows}</{tag}>'


def table(brick: dict, ctx: Ctx) -> str:
    rows: dict[int, dict[int, str]] = {}
    for cell in items(brick):
        rows.setdefault(int(cell.get("rowIndex", 0)), {})[int(cell.get("colIndex", 0))] = inline(cell.get("content"))
    header = bool(prop(brick, "headerRow", True))
    out = ['<div class="ck-table-wrap" tabindex="0"><table class="ck-table">']
    for r in sorted(rows):
        tag = "th" if header and r == min(rows) else "td"
        scope = ' scope="col"' if tag == "th" else ""
        out.append("<tr>" + "".join(f"<{tag}{scope}>{rows[r][c]}</{tag}>" for c in sorted(rows[r])) + "</tr>")
    out.append("</table></div>")
    return "".join(out)


def highlight(brick: dict, ctx: Ctx) -> str:
    return f'<aside class="ck-highlight">{block(content(brick))}</aside>'


def note(brick: dict, ctx: Ctx) -> str:
    title = inline(content(brick, "title"))
    head = f'<p class="ck-note-title">{title}</p>' if title else ""
    return f'<aside class="ck-note" role="note">{head}{block(content(brick))}</aside>'


def quote(brick: dict, ctx: Ctx) -> str:
    author = inline(content(brick, "author"))
    caption = f"<figcaption>{author}</figcaption>" if author else ""
    return f'<figure class="ck-quote"><blockquote>{block(content(brick))}</blockquote>{caption}</figure>'


# ── panels ───────────────────────────────────────────────────────────────────────────────────

def accordion(brick: dict, ctx: Ctx) -> str:
    rows = "".join(
        f"<details class=\"ck-details\"><summary>{inline(i.get('title'))}</summary><div>{block(i.get('content'))}</div></details>"
        for i in items(brick))
    return f'<div class="ck-accordion">{rows}</div>'


def panels(brick: dict, widget: str, ctx: Ctx) -> str:
    rows = "".join(f"<section class=\"ck-panel\"><h4 class=\"ck-panel-title\">{inline(i.get('title'))}</h4>"
                   f"<div class=\"ck-panel-body\">{block(i.get('content'))}</div></section>" for i in items(brick))
    return f'<div class="ck-{widget}" data-widget="{widget}" data-id="{a(ctx.next_id())}">{rows}</div>'


def tabs(brick: dict, ctx: Ctx) -> str:
    return panels(brick, "tabs", ctx)


def carousel(brick: dict, ctx: Ctx) -> str:
    return panels(brick, "carousel", ctx)


def carousel_quotes(brick: dict, ctx: Ctx) -> str:
    rows = []
    for i in items(brick):
        author = inline(i.get("author"))
        caption = f"<figcaption>{author}</figcaption>" if author else ""
        rows.append(f"<section class=\"ck-panel\"><figure class=\"ck-quote\"><blockquote>{block(i.get('content'))}</blockquote>"
                    f"{caption}</figure></section>")
    return f'<div class="ck-carousel" data-widget="carousel" data-id="{a(ctx.next_id())}">{"".join(rows)}</div>'


def timeline(brick: dict, ctx: Ctx) -> str:
    rows = []
    for i in items(brick):
        date = f"<span class=\"ck-date\">{a(i['date'])}</span>" if i.get("date") else ""
        rows.append(f"<li>{date}<h4 class=\"ck-panel-title\">{inline(i.get('title'))}</h4>{block(i.get('content'))}</li>")
    return f'<ol class="ck-timeline">{"".join(rows)}</ol>'


def cards(brick: dict, ctx: Ctx, carousel_mode: bool) -> str:
    faces = "".join(
        f'<div class="ck-card" data-widget="card" role="button" tabindex="0" aria-pressed="false" aria-label="{a(ctx.say("flip"))}">'
        f'<div class="ck-front">{inline(i.get("front"))}</div>'
        f'<div class="ck-back">{block(i.get("back"))}</div></div>' for i in items(brick))
    if carousel_mode:
        return f'<div class="ck-carousel ck-cards" data-widget="carousel" data-id="{a(ctx.next_id())}">{faces}</div>'
    return f'<div class="ck-gallery">{faces}</div>'


def flashcards(brick: dict, ctx: Ctx) -> str:
    return cards(brick, ctx, True)


def flashcard_gallery(brick: dict, ctx: Ctx) -> str:
    return cards(brick, ctx, False)


def labelled_graphic(brick: dict, ctx: Ctx) -> str:
    uid = ctx.next_id()
    path = prop(brick, "imagePath")
    points = items(brick)
    listing = "".join(f'<li id="{a(uid)}-p{n}"><h4 class="ck-panel-title">{inline(i.get("title"))}</h4>{block(i.get("content"))}</li>'
                      for n, i in enumerate(points, 1))
    if not path:
        return f'<ol class="ck-hs-list">{listing}</ol>'
    markers = "".join(
        f'<button type="button" class="ck-hs-point" style="left:{float(i.get("x", 50)):g}%;top:{float(i.get("y", 50)):g}%" '
        f'aria-expanded="false" aria-controls="{a(uid)}-p{n}" aria-label="{a(ctx.say("hotspot", n=n))}">{n}</button>'
        for n, i in enumerate(points, 1))
    alt = a(prop(brick, "imageAlt"))
    return (f'<figure class="ck-hotspots" data-widget="hotspots"><div class="ck-hs-stage"><img src="{a(path)}" alt="{alt}">'
            f'{markers}</div><ol class="ck-hs-list">{listing}</ol></figure>')


def dialog(brick: dict, ctx: Ctx) -> str:
    names = [c.get("name") for c in brick["data"].get("characters") or []]
    rows = "".join(
        f'<p class="ck-line ck-char-{names.index(i.get("characterId")) % 4 if i.get("characterId") in names else 0}">'
        f'<strong class="ck-speaker">{a(i.get("characterId"))}</strong> {inline(i.get("content"))}</p>' for i in items(brick))
    return f'<div class="ck-dialog">{rows}</div>'


# ── media ────────────────────────────────────────────────────────────────────────────────────

def caption_of(brick: dict) -> str:
    caption = inline(content(brick))
    return f"<figcaption>{caption}</figcaption>" if caption else ""


def image(brick: dict, ctx: Ctx) -> str:
    alt = prop(brick, "imageAlt") or re.sub(r"<[^>]+>", "", inline(content(brick)))
    return f'<figure class="ck-media"><img src="{a(prop(brick, "imagePath"))}" alt="{a(alt)}" loading="lazy">{caption_of(brick)}</figure>'


def transcript(brick: dict, ctx: Ctx) -> str:
    body = block(content(brick, "transcription"))
    return f'<details class="ck-details"><summary>{a(ctx.say("transcript"))}</summary><div>{body}</div></details>' if body else ""


def video(brick: dict, ctx: Ctx) -> str:
    subs = prop(brick, "subtitlesPath")
    track = f'<track kind="captions" src="{a(subs)}" srclang="und" label="Captions" default>' if subs else ""
    return (f'<figure class="ck-media"><video controls preload="metadata" src="{a(prop(brick, "videoPath"))}">{track}</video>'
            f"{caption_of(brick)}{transcript(brick, ctx)}</figure>")


def audio(brick: dict, ctx: Ctx) -> str:
    source = a(prop(brick, "audioPath"))
    return f'<figure class="ck-media"><audio controls preload="metadata" src="{source}"></audio>{transcript(brick, ctx)}</figure>'


def embed(brick: dict, ctx: Ctx) -> str:
    prefix = str(prop(brick, "embedFolderPrefix")).rstrip("/")
    return (f'<figure class="ck-media ck-embed"><iframe src="{a(prefix)}/index.html" title="{a(prop(brick, "embedTitle"))}" loading="lazy" '
            f'sandbox="allow-scripts allow-same-origin allow-forms"></iframe></figure>')


def attachment(brick: dict, ctx: Ctx) -> str:
    props = brick["data"].get("properties") or {}
    description = inline(content(brick, "description"))
    extra = f' <span class="ck-attachment-info">{description}</span>' if description else ""
    return (f'<p class="ck-attachment"><a href="{a(props.get("filePath"))}" download="{a(props.get("fileName") or "")}">'
            f'{inline(content(brick, "title"))}</a>{extra}</p>')


# ── questions ────────────────────────────────────────────────────────────────────────────────

def feedback(brick: dict) -> str:
    parts = []
    for key, css in (("feedback_correct", "correct"), ("feedback_incorrect", "incorrect"), ("feedback_general", "general")):
        value = content(brick, key)
        if value:
            parts.append(f'<div class="ck-fb ck-fb-{css}" hidden>{inline(value)}</div>')
    return f'<div class="ck-feedback" aria-live="polite">{"".join(parts)}</div>'


def question(kind: str, brick: dict, ctx: Ctx, body: str, label: bool = False) -> str:
    ctx.questions += 1
    uid = ctx.next_id()
    stem = block(content(brick, "question"))
    head = f'<legend class="ck-q-stem">{stem}</legend>' if label else f'<div class="ck-q-stem">{stem}</div>'
    tag = "fieldset" if label else "div"
    number = a(ctx.say("question", n=ctx.questions))
    return (f'<{tag} class="ck-q" data-type="{kind}" data-id="{a(uid)}" data-lesson="{a(ctx.lesson)}" aria-label="{number}">{head}{body}'
            f'<div class="ck-q-actions"></div>{feedback(brick)}</{tag}>')


def choice(brick: dict, ctx: Ctx, multiple: bool) -> str:
    uid = f"{ctx.lesson}-c{ctx.questions + 1}"
    kind = "radio" if not multiple else "checkbox"
    rows = "".join(
        f'<label class="ck-opt"><input type="{kind}" name="{a(uid)}" value="{n}" data-correct="{1 if i.get("isCorrect") else 0}">'
        f'<span>{inline(i.get("content"))}</span></label>' for n, i in enumerate(items(brick)))
    return question("multi" if multiple else "single", brick, ctx, f'<div class="ck-opts">{rows}</div>', label=True)


def single_choice(brick: dict, ctx: Ctx) -> str:
    return choice(brick, ctx, False)


def multi_select(brick: dict, ctx: Ctx) -> str:
    return choice(brick, ctx, True)


def true_false(brick: dict, ctx: Ctx) -> str:
    uid = f"{ctx.lesson}-t{ctx.questions + 1}"
    correct = str(prop(brick, "correctAnswer")) == "true"
    rows = "".join(
        f'<label class="ck-opt"><input type="radio" name="{a(uid)}" value="{value}" '
        f'data-correct="{1 if (value == "true") == correct else 0}"><span>{a(ctx.say("answer_" + value))}</span></label>'
        for value in ("true", "false"))
    return question("single", brick, ctx, f'<div class="ck-opts">{rows}</div>', label=True)


def sorting(brick: dict, ctx: Ctx) -> str:
    rows = "".join(f'<li data-i="{n}">{inline(i.get("content"))}</li>' for n, i in enumerate(items(brick)))
    return question("sorting", brick, ctx, f'<ol class="ck-sort">{rows}</ol>')


def match(brick: dict, ctx: Ctx) -> str:
    rows = "".join(f'<li class="ck-pair"><span class="ck-left">{inline(i.get("left"))}</span> '
                   f'<span class="ck-right">{inline(i.get("right"))}</span></li>' for i in items(brick))
    return question("match", brick, ctx, f'<ul class="ck-pairs">{rows}</ul>')


def sorting_groups(brick: dict, ctx: Ctx) -> str:
    groups = brick["data"].get("groups") or []
    labels = "".join(f'<li data-group="{a(g["id"])}">{inline(g.get("label"))}</li>' for g in groups)
    rows = "".join(f'<li data-group="{a(i.get("groupId"))}">{inline(i.get("content"))}</li>' for i in items(brick))
    return question("groups", brick, ctx, f'<ul class="ck-group-labels">{labels}</ul><ul class="ck-group-items">{rows}</ul>')


def fill_in_the_blank(brick: dict, ctx: Ctx) -> str:
    counter = iter(range(1, 1000))

    def blank(m: re.Match) -> str:
        answers = [x.strip() for x in m.group(1).split("/") if x.strip()]
        n = next(counter)
        return (f'<input type="text" class="ck-blank" data-answers="{a("|".join(answers))}" aria-label="{a(ctx.say("blank", n=n))}" '
                f'autocomplete="off" autocapitalize="off" spellcheck="false"><span class="ck-key" hidden>{a(" / ".join(answers))}</span>')

    ctx.questions += 1
    uid = ctx.next_id()
    stem = BLANK.sub(blank, block(content(brick, "question")))
    label = a(ctx.say("question", n=ctx.questions))
    return (f'<div class="ck-q" data-type="blanks" data-id="{a(uid)}" data-lesson="{a(ctx.lesson)}" aria-label="{label}">'
            f'<div class="ck-q-stem">{stem}</div><div class="ck-q-actions"></div>{feedback(brick)}</div>')


def order_words(brick: dict, ctx: Ctx) -> str:
    lines: dict[str, list[str]] = {line["id"]: [] for line in brick["data"].get("lines") or []}
    for i in items(brick):
        lines.setdefault(i.get("lineId"), []).append(inline(i.get("content")))
    rows = "".join('<ul class="ck-words">' + "".join(f"<li>{w}</li>" for w in words) + "</ul>" for words in lines.values())
    return question("order", brick, ctx, f'<div class="ck-order">{rows}</div>')


def short_answer(brick: dict, ctx: Ctx) -> str:
    answers = [i.get("text") for i in items(brick) if i.get("text")]
    body = (f'<label class="ck-short-label"><span class="ck-visually-hidden">{a(ctx.say("type_answer"))}</span>'
            f'<input type="text" class="ck-short" data-answers="{a("|".join(answers))}" autocomplete="off" spellcheck="false"></label>'
            f'<span class="ck-key" hidden>{a(" / ".join(answers))}</span>')
    return question("short", brick, ctx, body)


RENDERERS: dict[str, Callable[[dict, Ctx], str]] = {
    "TEXT": text, "HEADING": heading, "CODE": code, "LIST": bullets, "TABLE": table, "HIGHLIGHT": highlight, "NOTE": note, "QUOTE": quote,
    "ACCORDION": accordion, "TABS": tabs, "CAROUSEL": carousel, "CAROUSEL_QUOTES": carousel_quotes, "TIMELINE": timeline,
    "FLASHCARD_CAROUSEL": flashcards, "FLASHCARD_GALLERY": flashcard_gallery, "LABELLED_GRAPHIC": labelled_graphic, "DIALOG": dialog,
    "IMAGE": image, "VIDEO": video, "AUDIO": audio, "EMBED": embed, "ATTACHMENT": attachment,
    "SINGLE_CHOICE": single_choice, "MULTI_SELECT": multi_select, "TRUE_FALSE": true_false, "SORTING": sorting, "MATCH": match,
    "SORTING_GROUPS": sorting_groups, "FILL_IN_THE_BLANK": fill_in_the_blank, "ORDER_WORDS": order_words, "SHORT_ANSWER": short_answer,
}


def unsupported_bricks(plan: dict) -> list[str]:
    """The bricks of the plan this backend cannot render yet: `lesson key: BRICK`."""
    return [f"{lesson['key']}: {brick['type']}" for lesson in plan["lessons"] for brick in lesson["bricks"]
            if brick["type"] not in RENDERERS]


def lesson(entry: dict, ui: dict[str, str]) -> str:
    ctx = Ctx(ui, entry["key"], entry["type"] == "evaluation")
    body = "".join(RENDERERS[b["type"]](b, ctx) for b in entry["bricks"])
    quiz = entry.get("quiz") or {}
    settings = json.dumps({"passingGrade": quiz.get("passingGrade"), "maxAttempts": quiz.get("maxAttempts")})
    attrs = f' data-quiz="{a(settings)}"' if ctx.evaluation else ""
    footer = '<div class="ck-quiz-actions"></div>' if ctx.evaluation else ""
    return (f'<section class="ck-lesson" id="{a(entry["key"])}" data-lesson="{a(entry["key"])}" data-type="{entry["type"]}"{attrs}>'
            f'<h2 class="ck-lesson-title" tabindex="-1">{a(entry["title"])}</h2>{body}{footer}</section>')
