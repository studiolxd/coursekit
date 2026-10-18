"""`coursekit assemble` (creator backend): turn a unit's content.md / assessment.md into a plan of creator bricks, and diff it
against what was applied before.

The plan is deterministic: the same Markdown always gives the same bricks. The agent applies
it with the slxd MCP (add_brick / update_brick / delete_brick) and records the resulting
brick ids, so later edits become minimal update operations instead of a rebuild.

Files (courses/<CODE>/assembly/, versioned):
    unit-NN.plan.json      lessons and bricks generated from the Markdown
    unit-NN.applied.json   what is in creator: per lesson, the bricks with their ids

Commands:
    coursekit assemble plan CODE --unit N      write the plan, print warnings
    coursekit assemble diff CODE --unit N      operations to bring creator in line with the plan
    coursekit assemble applied CODE --unit N --lesson KEY --lesson-id ID --brick-ids ID1,ID2,...
                                              record a lesson as applied (ids in plan order)
    coursekit assemble applied CODE --unit N --content
                                              record the content title as applied (after update_content)
    coursekit assemble link CODE --unit N --content-id ID
                                              store the creator content id of the unit
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from markdown_it import MarkdownIt

from coursekit import config, lang, simulation
from coursekit import course as coursemod
from coursekit import story as storymod
from coursekit.i18n import t
from coursekit.misconceptions import strip_tag
from coursekit.states import history_entry
from coursekit.util import character_asset_id, edit_yaml, load_yaml, save_yaml

MD = MarkdownIt("commonmark").enable("table")
CODE_LANGUAGES = {
    "javascript", "typescript", "python", "html", "css", "java", "go", "rust", "sql", "json", "yaml",
    "bash", "c", "cpp", "csharp", "php", "ruby", "swift", "kotlin", "markdown", "xml",
}
LANGUAGE_ALIASES = {"js": "javascript", "ts": "typescript", "py": "python", "sh": "bash", "zsh": "bash", "yml": "yaml",
                    "c++": "cpp", "cs": "csharp", "md": "markdown", "cmd": "bash", "bat": "bash", "patch": "diff",
                    "docker": "dockerfile"}
# Languages that, when creator has them (`rules › assembly › code_languages`), replace a nearby one: the fence may name them or one
# of their aliases; without them the second is used.
LANGUAGE_UPGRADES = {"shell": ("bash", ("shell", "console", "terminal", "shell-session")),
                     "powershell": ("bash", ("powershell", "pwsh", "ps1"))}
# A fence with no language, or `text`, holds the output of a program or a conversation, or commands. Creator takes plain text
# only if it lists `plaintext`; otherwise it guesses (`auto`), which is bad with short code.
TEXT_FENCES = {"", "text", "txt", "plain", "plaintext", "output"}
COMMAND_PROGRAMS = "coursekit|git|uv|cd|ls|pwd|mkdir|claude|opencode|codex|npm|npx|curl|irm|brew|echo|export|source"
PROMPT_LINE = re.compile(r"^(\S+@\S+\s.*[%$#]|PS [A-Za-z]:\\.*>|\$)(\s|$)")  # `ana@mac ~ % pwd`, `PS C:\Users\ana>`, `$ pwd`
COMMAND_LINE = re.compile(rf"(\$ |/[a-z][\w-]*(\s|$)|({COMMAND_PROGRAMS})\b)")


def code_language(fence: str, code: list[str], extra: list[str] | tuple[str, ...] = ()) -> str:
    """The `codeLanguage` of a code block. `extra` are the languages creator has added to its list. The language of the fence if
    creator knows it; a `text` block that is a terminal session (it has prompts) or only commands is `shell` (`bash` without it);
    other text is `plaintext` (`auto` without it)."""
    known = CODE_LANGUAGES | set(extra)
    for language, (fallback, names) in LANGUAGE_UPGRADES.items():
        if fence in names:
            return language if language in known else fallback
    lang = LANGUAGE_ALIASES.get(fence, fence)
    if lang in known:
        return lang
    lines = [line.strip() for line in code if line.strip()]
    terminal = "shell" if "shell" in known else "bash"
    session = any(PROMPT_LINE.match(line) for line in lines) or all(COMMAND_LINE.match(line) for line in lines)
    if lang in TEXT_FENCES and lines and session:
        return terminal
    return "plaintext" if "plaintext" in known else "auto"

DIRECTIVE_OPEN_RE = re.compile(r"^:::([a-z][a-z-]*)\s*$")
DIRECTIVE_CLOSE_RE = re.compile(r"^:::\s*$")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
LIST_ITEM_RE = re.compile(r"^(\s*)([-*]|\d+[.)])\s+(.*)$")
OPTION_RE = re.compile(r"^\s*[-*]\s+\[( |x|X)\]\s+(.*)$")
KV_RE = re.compile(r"^([a-zà-ÿ][a-zà-ÿ-]*):\s*(.*)$")

# The brick each resource type becomes once it is produced (the type ids are those of `lang/<language>.yaml › media_types`).
MEDIA_KIND = {
    "image": "image", "infographic": "image", "diagram": "image", "animated_gif": "image",
    "video": "video", "audio": "audio", "simulation": "embed", "terminal_demo": "embed",
}
PANEL_BRICKS = ("ACCORDION", "TABS", "CAROUSEL", "TIMELINE", "FLASHCARD_CAROUSEL", "FLASHCARD_GALLERY")
FIELD_KEYS = ("title", "description", "how", "specs")  # in the order of the language's placeholder_fields


class Syntax:
    """Content-format patterns of one language (headings, tags, placeholders)."""

    def __init__(self, t: dict):
        self.t = t
        self.section = re.compile(rf"^## {re.escape(t['section'])} (\d+)\s*[—-]\s*(.+?)\s*(\*\(.*\)\*)?\s*$")
        self.assessment = re.compile(rf"^## {re.escape(t['assessment_activity'])}\s+([\d.]+)\s*[—-]\s*(.+?)\s*$")
        self.objective_tag = re.compile(rf"^\*\[{re.escape(t['objective'])}[^\]]*\]\*\s*$")
        self.placeholder = re.compile(rf"^>\s*\*\*\[{re.escape(t['placeholder'])}\s*[—-]\s*(.+?)\]\*\*")
        names = "|".join(re.escape(f) for f in t["placeholder_fields"])
        self.placeholder_field = re.compile(rf"^>\s*\*\*({names}):\*\*\s*(.*)$")
        self.field_key = dict(zip(t["placeholder_fields"], FIELD_KEYS, strict=False))

    def key(self, name: str) -> str:
        """How the key `name` of the directives is written in this language."""
        return lang.directive_key(self.t, name)

    def word(self, name: str) -> str:
        return self.t["directive_words"][name]

    def media_type(self, label: str) -> str | None:
        return lang.media_type_id(self.t, label)

    def media_label(self, type_id: str) -> str:
        return self.t["media_types"].get(type_id, type_id)

    def check_keys(self, values: dict[str, str]) -> None:
        """A key that belongs to another language (`pregunta:` in an English course) is an error, not an ignored line."""
        for key in values:
            other = lang.foreign_key(self.t, key)
            if other:
                valid = ", ".join(sorted(lang.directive_keys(self.t)))
                raise PlanError(t("assemble", "foreign_key", key=key, language=other, valid=valid))


class PlanError(Exception):
    pass


# ── Markdown helpers ─────────────────────────────────────────────────────────

def html(md_text: str) -> str:
    return MD.render(md_text.strip()).strip()


def inline(md_text: str) -> str:
    return f"<p>{MD.renderInline(md_text.strip())}</p>"


def strip_comments(text: str) -> str:
    return HTML_COMMENT_RE.sub("", text)


def panels(body: list[str]) -> list[tuple[str, str]]:
    """Split a directive body on '#### ' headings: [(title, markdown)]."""
    out: list[tuple[str, list[str]]] = []
    for line in body:
        if line.startswith("#### "):
            out.append((line[5:].strip(), []))
        elif out:
            out[-1][1].append(line)
    return [(title, "\n".join(lines).strip()) for title, lines in out]


def key_values(body: list[str]) -> tuple[dict[str, str], list[str]]:
    """'clave: valor' lines (lowercase keys) and the remaining lines."""
    values, rest = {}, []
    for line in body:
        m = KV_RE.match(line.strip())
        if m and not line.lstrip().startswith(("-", "*")):
            values[m.group(1)] = m.group(2).strip()
        else:
            rest.append(line)
    return values, rest


def list_items(lines: list[str]) -> list[str]:
    items: list[list[str]] = []
    for line in lines:
        m = LIST_ITEM_RE.match(line)
        if m and not m.group(1):
            items.append([m.group(3)])
        elif items and line.strip():
            items[-1].append(line.strip())
    return [" ".join(i).strip() for i in items]


# ── Directive → brick ─────────────────────────────────────────────────────────

def question_content(values: dict[str, str], syntax: Syntax) -> dict:
    content = {"question": inline(values.get(syntax.key("question"), ""))}
    for key, field in (("feedback_correct", "feedback_correct"), ("feedback_incorrect", "feedback_incorrect"),
                       ("feedback", "feedback_general")):
        if values.get(syntax.key(key)):
            content[field] = inline(values[syntax.key(key)])
    return content


def screen_html(value: object, key: str = "") -> object:
    """The texts of the screen of a skin: `body` and `text` are Markdown, the rest short texts; numbers and flags as they are."""
    if isinstance(value, dict):
        return {k: screen_html(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [screen_html(v, key) for v in value]
    if isinstance(value, str):
        return html(value) if key in ("body", "text") else inline(value)
    return value


def simulation_brick(name: str, body: list[str], ctx: dict) -> dict:
    """A simulation as the plan carries it: its checked data with the texts in HTML, the maximum points, and the images it
    uses (by the id of their asset) with the path of those already produced."""
    sim = simulation.parse(name, body, f":::{name}")
    if sim.errors:
        raise PlanError(sim.errors[0])
    data = json.loads(json.dumps(sim.data))
    data["title"] = inline(str(data.get("title") or ""))
    if data.get("screen"):
        data["screen"] = screen_html(data["screen"])
    for scene in (data.get("scenes") or {}).values():
        for key in ("text", "debriefing"):
            if scene.get(key):
                scene[key] = html(str(scene[key]))
        for variant in scene.get("variants") or []:
            variant["text"] = html(str(variant.get("text") or ""))
        if scene.get("screen"):
            scene["screen"] = screen_html(scene["screen"])
        for decision in (scene.get("choices") or []) + (scene.get("hotspots") or []):
            for key in ("text", "label", "feedback"):
                if decision.get(key):
                    decision[key] = inline(str(decision[key]))
        from coursekit.htmlkit.render import _clean_mechanics

        _clean_mechanics(scene, lambda text: inline(text), lambda text: html(text))
    media: dict[str, dict] = {}
    missing = 0
    for ref in simulation.media_refs(sim.data):
        asset = ctx["assets"].get(ref["id"]) or {}
        if asset.get("asset_path") and asset.get("status") in ("uploaded", "produced"):
            media[ref["id"]] = {"path": asset["asset_path"], "alt": asset.get("alt") or ref["description"] or ref["character"]}
        else:
            missing += 1
    if missing:
        ctx["warnings"].append(t("assemble", "simulation_media_missing", id=sim.id, count=missing))

    def portrait(person: str, expression: object = None) -> dict | None:
        return media.get(simulation.portrait_id(person, expression)) or media.get(simulation.portrait_id(person))

    character = str(data.get("character") or "")
    if character:
        data["_portrait"] = portrait(character)
    for sid, scene in (data.get("scenes") or {}).items():  # the media of each scene, resolved for the player (`_` keys)
        if data.get("audio") is True:
            scene["_audio"] = media.get(simulation.voice_id(sim.id, str(sid)))
        if scene.get("background"):
            scene["_background"] = media.get(simulation.background_id(str(scene["background"])))
        for layer in scene.get("layers") or []:
            layer["_image"] = media.get(simulation.layer_id(str(layer.get("image") or "")))
        for person in scene.get("characters") or []:
            person["_portrait"] = portrait(str(person.get("name") or ""), person.get("expression"))
        if character:
            scene["_portrait"] = portrait(character, scene.get("expression"))
    rewind = (coursemod.rules(course=ctx["course"]).get("decision_based") or {}).get("rewind", True) if ctx.get("course") else True
    data.update({"kind": name, "max_score": sim.max_score, "rewind": bool(rewind)})
    return {"type": "SIMULATION", "data": data, "meta": {"directive": name, "simulation": sim.id}}


def simulation_blocks(lines: list[str], ctx: dict) -> list[str]:
    """The lines of the simulation directives among some lines (the other parts of an assessment activity are for people)."""
    names = {name for name, d in ctx["registry"].items() if d.get("role") == "simulation"}
    out: list[str] = []
    inside = False
    for line in lines:
        m = DIRECTIVE_OPEN_RE.match(line.strip())
        if not inside and m and m.group(1) in names:
            inside = True
        if inside:
            out.append(line)
            if DIRECTIVE_CLOSE_RE.match(line.strip()) and len(out) > 1 and not DIRECTIVE_OPEN_RE.match(line.strip()):
                inside = False
                out.append("")
    return out


def conditional_parts(lines: list[str], start: int) -> tuple[list[tuple[str, list[str]]], list[str], int]:
    """From the `:::if` line at `start`: ([(condition, lines) of the :::if branch and of each :::elif], lines of the :::else
    branch, index of the closing line). Directives inside the branches are kept whole."""
    branches: list[tuple[str, list[str]]] = [(simulation.IF_RE.match(lines[start].strip()).group(1), [])]
    other: list[str] = []
    target = branches[0][1]
    i = start + 1
    in_directive = in_code = False
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("```"):
            in_code = not in_code
        elif not in_code:
            if in_directive:
                in_directive = not DIRECTIVE_CLOSE_RE.match(stripped)
            elif simulation.ELIF_RE.match(stripped):
                branches.append((simulation.ELIF_RE.match(stripped).group(1), []))
                target = branches[-1][1]
                i += 1
                continue
            elif simulation.ELSE_RE.match(stripped):
                target = other
                i += 1
                continue
            elif DIRECTIVE_CLOSE_RE.match(stripped):
                return branches, other, i
            elif DIRECTIVE_OPEN_RE.match(stripped):
                in_directive = True
        target.append(lines[i])
        i += 1
    return branches, other, i


def directive_brick(name: str, body: list[str], ctx: dict) -> dict:
    registry = ctx["registry"]
    if name not in registry:
        raise PlanError(t("assemble", "unknown_directive", name=name))
    brick_type = registry[name]["brick"]
    if registry[name].get("role") == "simulation":
        return simulation_brick(name, body, ctx)
    syntax: Syntax = ctx["syntax"]
    values, rest = key_values(body)
    syntax.check_keys(values)
    meta = {"directive": name}
    if values.get(syntax.key("objective")):
        meta["objective"] = values[syntax.key("objective")]

    if brick_type in ("ACCORDION", "TABS", "CAROUSEL"):
        items = [{"title": inline(text), "content": html(c)} for text, c in panels(body)]
        data = {"items": items}
    elif brick_type == "TIMELINE":
        items = []
        for title, content in panels(body):
            date, _, rest_title = title.partition(" — ")
            items.append({"date": date.strip() if rest_title else "", "title": inline(rest_title or title), "content": html(content)})
        data = {"items": items}
    elif brick_type in ("FLASHCARD_CAROUSEL", "FLASHCARD_GALLERY"):
        data = {"items": [{"front": inline(text), "back": html(c)} for text, c in panels(body)]}
    elif brick_type == "LABELLED_GRAPHIC":
        first = next((i for i, line in enumerate(body) if line.startswith("#### ")), len(body))
        values, _ = key_values(body[:first])  # a `position:` under a point belongs to the point, not to the graphic
        image = ctx["media_by_title"].get(values.get(syntax.key("image"), ""))
        points = panels(body)
        items = []
        for i, (title, content) in enumerate(points):
            sub_values, sub_rest = key_values(content.splitlines())
            syntax.check_keys(sub_values)
            x, y = 20 + (60 * i // max(1, len(points) - 1) if len(points) > 1 else 30), 50
            if sub_values.get(syntax.key("position")):
                x, y = (float(v) for v in sub_values[syntax.key("position")].split(","))
            items.append({"x": x, "y": y, "title": inline(title), "content": html("\n".join(sub_rest))})
        data = {"properties": {"markerStyle": "numbered", "imagePath": image.get("asset_path") if image else None,
                               "imageAlt": image.get("alt") if image else None}, "items": items}
        if not image or not image.get("asset_path"):
            ctx["warnings"].append(t("assemble", "image_not_produced", image=values.get(syntax.key("image"), "")))
    elif brick_type == "DIALOG":
        characters, items = [], []
        for line in rest:
            m = re.match(r"^\*\*(.+?):\*\*\s*(.*)$", line.strip())
            if m:
                if m.group(1) not in characters:
                    characters.append(m.group(1))
                items.append({"characterId": m.group(1), "content": inline(m.group(2))})
        people = []
        course = ctx.get("course")
        for name in characters:
            if course and (storymod.is_learner(course, name) or storymod.is_anonymous(course, name)):
                people.append({"name": name})
                continue
            full = (storymod.canonical(course, name) if course and course.get("_dir") else None) or name
            portrait = ctx["assets"].get(character_asset_id(full))
            if portrait and portrait.get("asset_path") and portrait.get("status") == "uploaded":
                people.append({"name": name, "imagePath": portrait["asset_path"], "imageAlt": portrait.get("alt") or name})
            else:
                people.append({"name": name})
                ctx["warnings"].append(t("assemble", "character_not_produced", name=name))
        data = {"characters": people, "items": items}
    elif brick_type == "CAROUSEL_QUOTES":
        items = []
        for block in "\n".join(rest).strip().split("\n\n"):
            lines = [ln for ln in block.splitlines() if ln.strip()]
            author = lines.pop()[2:].strip() if lines and lines[-1].startswith("— ") else ""
            items.append({"content": inline(" ".join(lines)), "author": inline(author) if author else ""})
        data = {"items": items}
    elif brick_type == "NOTE":
        default = syntax.t["reflection"] if name == "reflection" else syntax.t["note"]
        data = {"content": {"title": inline(values.get(syntax.key("title"), default)), "content": html("\n".join(rest))}}
    elif brick_type == "HIGHLIGHT":
        data = {"content": {"content": html("\n".join(rest))}}
    elif brick_type == "QUOTE":
        lines = [ln for ln in rest if ln.strip()]
        author = lines.pop()[2:].strip() if lines and lines[-1].startswith("— ") else ""
        data = {"content": {"content": html("\n".join(lines)), "author": inline(author) if author else ""}}
    elif brick_type in ("SINGLE_CHOICE", "MULTI_SELECT"):
        # the `‹id›` of a distractor (the common error it represents) is for the course, not for the learner
        options = [(m.group(1).lower() == "x", strip_tag(m.group(2))[0]) for m in map(OPTION_RE.match, rest) if m]
        if brick_type == "SINGLE_CHOICE" and sum(c for c, _ in options) != 1:
            raise PlanError(t("assemble", "one_correct_option", name=name))
        data = {"content": question_content(values, syntax), "items": [{"content": inline(text), "isCorrect": c} for c, text in options]}
    elif brick_type == "TRUE_FALSE":
        answer = values.get(syntax.key("answer"), "").lower()
        if answer not in (syntax.word("true"), syntax.word("false")):
            raise PlanError(t("assemble", "true_false_answer", key=syntax.key("answer"), true=syntax.word("true"),
                              false=syntax.word("false")))
        correct = "true" if answer == syntax.word("true") else "false"
        data = {"properties": {"correctAnswer": correct}, "content": question_content(values, syntax)}
    elif brick_type == "SORTING":
        data = {"content": question_content(values, syntax), "items": [{"content": inline(text)} for text in list_items(rest)]}
    elif brick_type == "MATCH":
        pairs = [item.split("::", 1) for item in list_items(rest) if "::" in item]
        data = {"content": question_content(values, syntax), "items": [{"left": inline(a), "right": inline(b)} for a, b in pairs]}
    elif brick_type == "SORTING_GROUPS":
        groups, items = [], []
        for gi, (label, content) in enumerate(panels(rest), 1):
            groups.append({"id": f"g{gi}", "label": inline(label)})
            items += [{"content": inline(text), "groupId": f"g{gi}"} for text in list_items(content.splitlines())]
        data = {"content": question_content(values, syntax), "groups": groups, "items": items}
    elif brick_type == "FILL_IN_THE_BLANK":
        if "{" not in values.get(syntax.key("question"), ""):
            raise PlanError(t("assemble", "fill_blank", example="{" + syntax.key("answer") + "}", key=syntax.key("question")))
        data = {"content": question_content(values, syntax)}
    elif brick_type == "ORDER_WORDS":
        lines, items = [], []
        for li, sentence in enumerate(list_items(rest), 1):
            lines.append({"id": f"l{li}"})
            items += [{"content": inline(word), "lineId": f"l{li}"} for word in sentence.split()]
        data = {"content": question_content(values, syntax), "lines": lines, "items": items}
    elif brick_type == "SHORT_ANSWER":
        answers = [a.strip() for a in values.get(syntax.key("answers"), "").split("|") if a.strip()]
        data = {"content": question_content(values, syntax), "items": [{"text": a} for a in answers]}
    elif brick_type in ("WORD_SEARCH", "WORDLE", "HANGMAN"):
        data = {"items": [{"word": w.split()[0].upper()} for w in list_items(rest)]}
    elif brick_type == "MEMORY":
        data = {"items": [{"content": inline(text)} for text in list_items(rest)]}
    elif brick_type == "PASAPALABRA":
        items = []
        for item in list_items(rest):
            starts, contains = syntax.word("starts"), syntax.word("contains")
            m = re.match(rf"^(\S{{1,3}})\s*\(({re.escape(starts)}|{re.escape(contains)})\):\s*(.+?)\s*::\s*(.+)$", item)
            if not m:
                raise PlanError(t("assemble", "pasapalabra_items", starts=starts, contains=contains))
            items.append({"letter": m.group(1).upper(), "mode": "starts" if m.group(2) == starts else "contains",
                          "definition": m.group(3), "answer": m.group(4)})
        data = {"items": items}
    elif brick_type == "TRIVIAL":
        categories, items = [], []
        for category, content in panels(body):  # the whole body: each question keeps its own `question:` line
            categories.append({"name": category})
            for block in content.split("\n\n"):
                q_values, q_rest = key_values(block.splitlines())
                syntax.check_keys(q_values)
                options = [{"text": strip_tag(m.group(2))[0], "isCorrect": m.group(1).lower() == "x"}
                           for m in map(OPTION_RE.match, q_rest) if m]
                if q_values.get(syntax.key("question")):
                    items.append({"categoryId": category, "content": inline(q_values[syntax.key("question")]), "options": options})
        data = {"properties": {"categories": categories}, "items": items}
    else:
        raise PlanError(t("assemble", "not_supported", name=name, brick=brick_type))
    if brick_type in PANEL_BRICKS and not data["items"]:
        raise PlanError(t("assemble", "no_panels", name=name))
    return {"type": brick_type, "data": data, "meta": meta}


# ── Section parsing ──────────────────────────────────────────────────────────

def download_bricks(asset: dict | None, download_label: str) -> list[dict]:
    """An ATTACHMENT after the media brick for each uploaded download of the asset (e.g. a PDF)."""
    if not asset or asset.get("status") != "uploaded":
        return []
    out = []
    for d in asset.get("downloads") or []:
        if not d.get("asset_path"):
            continue
        ext = Path(d.get("file") or d["asset_path"]).suffix
        stem = d.get("name") or asset.get("title") or Path(d.get("file") or d["asset_path"]).stem
        name = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode().lower()).strip("-") + ext
        title = d.get("title") or f"{download_label}: {asset.get('title') or name}"
        size = d.get("size")
        description = f"{Path(name).suffix.lstrip('.').upper()}" + (f", {size / 1_000_000:.1f} MB" if size and size >= 1_000_000
                                                                   else f", {round(size / 1000)} KB" if size else "")
        out.append({"type": "ATTACHMENT",
                    "data": {"properties": {"filePath": d["asset_path"], "fileName": name, "fileSize": size,
                                            "showDownloadIcon": True},
                             "content": {"title": inline(title), "description": html(description)}},
                    "meta": {"download": d["asset_path"], "asset": asset["id"]}})
    return out


def placeholder_brick(kind: str, fields: dict, asset: dict | None, label: str, written: str | None = None,
                      svg_as_image: bool = False) -> dict:
    """`kind` is the id of the resource type; `written` how the content names it (for the note that stands for it)."""
    title = fields.get("title", "")
    media = MEDIA_KIND.get(kind)
    meta = {"placeholder": kind, "title": title}
    if asset and asset.get("asset_path") and asset.get("status") == "uploaded":
        meta["asset"] = asset["id"]
        caption = inline(title)
        if media == "image" and not svg_as_image and str(asset.get("file") or "").lower().endswith(".svg"):
            media = "embed"  # creator does not take SVG as an image: it goes up as an EMBED package (`coursekit media embed`)
        if media == "image":
            return {"type": "IMAGE", "data": {"properties": {"imagePath": asset["asset_path"], "imageAlt": asset.get("alt")},
                                              "content": {"content": caption}}, "meta": meta}
        if media == "video":
            props = {"videoPath": asset["asset_path"]}
            if asset.get("subtitles_path"):
                props["subtitlesPath"] = asset["subtitles_path"]
            return {"type": "VIDEO", "data": {"properties": props, "content": {"content": caption,
                    "transcription": html(asset.get("transcript") or "")}}, "meta": meta}
        if media == "audio":
            return {"type": "AUDIO", "data": {"properties": {"audioPath": asset["asset_path"]},
                    "content": {"transcription": html(asset.get("transcript") or "")}}, "meta": meta}
        if media == "embed":
            return {"type": "EMBED", "data": {"properties": {"embedFolderPrefix": asset["asset_path"], "embedTitle": title}}, "meta": meta}
    names = fields.get("_names", {})
    body = "\n\n".join(f"**{names.get(k, k)}:** {fields[k]}" for k in ("description", "specs") if fields.get(k))
    return {"type": "NOTE", "data": {"content": {"title": inline(f"{label} — {written or kind}: {title}"), "content": html(body)}},
            "meta": meta}


def parse_blocks(lines: list[str], ctx: dict, section_key: str) -> list[dict]:
    syntax: Syntax = ctx["syntax"]
    bricks: list[dict] = []
    paragraph: list[str] = []
    counters = ctx.setdefault("placeholders", {})  # numbered across the branches of the adaptive blocks of the section

    def flush() -> None:
        text = "\n".join(paragraph).strip()
        paragraph.clear()
        if text:
            if bricks and bricks[-1]["type"] == "TEXT" and bricks[-1]["meta"].get("merge"):
                bricks[-1]["data"]["content"]["content"] += "\n" + html(text)
            else:
                bricks.append({"type": "TEXT", "data": {"content": {"content": html(text)}}, "meta": {"merge": True}})

    def close_text() -> None:
        flush()
        if bricks and bricks[-1]["type"] == "TEXT":
            bricks[-1]["meta"].pop("merge", None)

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            close_text()
            lang = stripped[3:].strip().lower()
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            bricks.append({"type": "CODE", "data": {"properties": {"codeLanguage": code_language(lang, code, ctx["code_languages"])},
                                                    "content": {"content": "\n".join(code)}}, "meta": {}})
        elif simulation.IF_RE.match(stripped):
            close_text()
            branches, other, i = conditional_parts(lines, i)
            # creator's general form: one or more branches with a condition, in order, and the neutral one
            bricks.append({"type": "CONDITIONAL", "data": {
                "branches": [{"condition": condition, "bricks": parse_blocks(part, ctx, section_key)} for condition, part in branches],
                "else": parse_blocks(other, ctx, section_key)}, "meta": {}})
        elif DIRECTIVE_OPEN_RE.match(stripped):
            close_text()
            name = DIRECTIVE_OPEN_RE.match(stripped).group(1)
            body = []
            i += 1
            while i < len(lines) and not DIRECTIVE_CLOSE_RE.match(lines[i].strip()):
                body.append(lines[i])
                i += 1
            try:
                bricks.append(directive_brick(name, body, ctx))
            except PlanError as exc:
                ctx["errors"].append(f"{section_key}: {exc}")
        elif syntax.placeholder.match(stripped):
            close_text()
            written = syntax.placeholder.match(stripped).group(1).strip()
            kind = syntax.media_type(written) or written
            fields: dict = {"_names": {v: k for k, v in syntax.field_key.items()}}
            while i + 1 < len(lines) and lines[i + 1].startswith(">"):
                i += 1
                m = syntax.placeholder_field.match(lines[i])
                if m:
                    fields[syntax.field_key[m.group(1)]] = m.group(2).strip()
            counters[section_key] = counters.get(section_key, 0) + 1
            asset_id = f"{section_key}-M{counters[section_key]}"
            asset = ctx["assets"].get(asset_id)
            html_backend = bool(ctx.get("course") and ctx["course"].get("_project") and coursemod.backend(ctx["course"]) == "html")
            bricks.append(placeholder_brick(kind, fields, asset, syntax.t["placeholder"].capitalize(), written,
                                            svg_as_image=html_backend))  # a browser shows an SVG; only creator needs an EMBED
            bricks[-1]["meta"]["placeholder_id"] = asset_id
            bricks.extend(download_bricks(asset, syntax.t["download"]))
        elif stripped.startswith(">"):
            close_text()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            bricks.append({"type": "HIGHLIGHT", "data": {"content": {"content": html("\n".join(quote))}}, "meta": {}})
            continue
        elif re.match(r"^#{3,6} ", stripped):
            close_text()
            level = len(stripped.split(" ", 1)[0]) - 1
            bricks.append({"type": "HEADING", "data": {"properties": {"level": level},
                                                       "content": {"content": inline(stripped.split(" ", 1)[1])}}, "meta": {}})
        elif stripped.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?[\s:|-]+\|?$", lines[i + 1].strip()):
            close_text()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows if not re.match(r"^\|?[\s:|-]+\|?$", r)]
            items = [{"rowIndex": ri, "colIndex": ci, "content": inline(c)} for ri, row in enumerate(cells) for ci, c in enumerate(row)]
            bricks.append({"type": "TABLE", "data": {"properties": {"rowCount": len(cells), "columnCount": max(map(len, cells)),
                                                                    "headerRow": True}, "items": items}, "meta": {}})
            continue
        elif LIST_ITEM_RE.match(line) and not LIST_ITEM_RE.match(line).group(1):
            close_text()
            numbered = LIST_ITEM_RE.match(line).group(2)[0].isdigit()
            block = []
            while i < len(lines) and (LIST_ITEM_RE.match(lines[i]) or (lines[i].startswith(("  ", "\t")) and lines[i].strip())):
                block.append(lines[i])
                i += 1
            bricks.append({"type": "LIST", "data": {"properties": {"listType": "numbered" if numbered else "bulleted"},
                                                    "items": [{"content": html(text)} for text in list_items(block)]}, "meta": {}})
            continue
        elif syntax.objective_tag.match(stripped) or stripped == "---":
            close_text()
        elif not stripped:
            flush()
        else:
            paragraph.append(line)
        i += 1
    close_text()
    for b in bricks:
        b["meta"].pop("merge", None)
    return bricks


def split(text: str, heading_re: re.Pattern) -> list[tuple[re.Match, list[str]]]:
    parts: list[tuple[re.Match, list[str]]] = []
    for line in strip_comments(text).splitlines():
        m = heading_re.match(line)
        if m:
            parts.append((m, []))
        elif parts:
            parts[-1][1].append(line)
    return parts


def brick_hash(brick: dict) -> str:
    raw = json.dumps({"type": brick["type"], "data": brick["data"]}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def content_title(course: dict, unit: dict) -> str:
    """Title of the unit's creator content: the course title when there is a single unit; for the package of the tests when they
    go apart, the course title and its own."""
    if unit.get("kind") in ("assessment", "bank"):
        return f"{course['title']}. {unit['title']}"
    if len(course.get("units") or []) == 1:
        return course["title"]
    return f"{coursemod.tokens(course)['unit']} {unit['n']}. {unit['title']}"


def manifest_assets(course: dict) -> dict[str, dict]:
    manifest_path = course["_dir"] / "media" / "manifest.yaml"
    return {a["id"]: a for a in (load_yaml(manifest_path).get("assets") or [])} if manifest_path.exists() else {}


def quiz_settings(course: dict, unit: dict, number: str, title: str) -> dict:
    """Settings of the quiz of an assessment activity: the ones the design gives it (weight, pass mark, attempts), else the
    course's `design.grading` (weight 1). The activity is the one with that title, else the one in that position of the unit."""
    items = (unit.get("activities") or {}).get("assessment") or []
    found = next((a for a in items if (a.get("title") or "").strip() == title.strip()), None)
    if found is None:
        position = number.rsplit(".", 1)[-1]
        found = items[int(position) - 1] if position.isdigit() and 0 < int(position) <= len(items) else {}
    grading = course["design"].get("grading") or {}

    def pick(own, fallback):
        return fallback if own is None else own

    return {"passingGrade": pick(found.get("passing_score"), grading.get("passing_score")),
            "maxAttempts": pick(found.get("max_attempts"), grading.get("attempts")),
            "courseWeight": pick(found.get("weight"), 1)}


def branch_bricks(brick: dict) -> list[dict]:
    """The bricks inside the branches of an adaptive block (every branch, then the neutral one)."""
    data = brick["data"]
    return [b for branch in data.get("branches") or [] for b in branch.get("bricks") or []] + list(data.get("else") or [])


def conditions(brick: dict) -> list[str]:
    return [str(branch.get("condition") or "") for branch in brick["data"].get("branches") or []]


def walk(bricks: list[dict]):
    """The bricks, and those inside the branches of the adaptive blocks."""
    for brick in bricks:
        yield brick
        if brick["type"] == "CONDITIONAL":
            yield from walk(branch_bricks(brick))


def for_creator(bricks: list[dict], ctx: dict, key: str) -> list[dict]:
    """Creator has no adaptive content (its neutral branch is assembled) and takes a simulation as an EMBED of its package
    (`SIM-<id>` in the manifest, built with `coursekit media embed` and uploaded); until it is uploaded, a note stands for it.
    A simulation marked `meta.blocks` (it opens a section of a decision-based course) blocks the lesson until it reaches an
    ending (the package says `complete`), so the learner decides before reading."""
    from coursekit.htmlkit.simpackage import asset_id

    out: list[dict] = []
    for brick in bricks:
        if brick["type"] == "CONDITIONAL":
            ctx["warnings"].append(t("assemble", "adaptive_neutral", key=key, condition=" | ".join(conditions(brick))))
            out += for_creator(brick["data"].get("else") or [], ctx, key)
        elif brick["type"] == "SIMULATION":
            sid = str(brick["data"].get("id") or "")
            asset = ctx["assets"].get(asset_id(sid)) or {}
            title = re.sub(r"<[^>]+>", "", str(brick["data"].get("title") or sid))
            meta = {**brick["meta"], "asset": asset_id(sid)}
            if asset.get("asset_path") and asset.get("status") == "uploaded":
                # creator keeps its state and counts its grade by `simulationId` (unique in the content: coursekit's ids are
                # unique in the course); `scored` and `weight` as the simulation says
                properties = {"embedFolderPrefix": asset["asset_path"], "embedTitle": title, "simulationId": sid,
                              "scored": brick["data"].get("scored") is True, "weight": float(brick["data"].get("weight") or 1)}
                if brick["meta"].get("blocks"):
                    properties["blocker_enabled"] = True
                out.append({"type": "EMBED", "data": {"properties": properties}, "meta": meta})
            else:
                ctx["warnings"].append(t("assemble", "simulation_not_uploaded", key=key, id=sid, asset=asset_id(sid)))
                out.append({"type": "NOTE", "data": {"content": {"title": inline(f"{title}"),
                                                                  "content": html(t("assemble", "simulation_note", asset=asset_id(sid)))}},
                            "meta": meta})
        else:
            out.append(brick)
    return out


def context(course: dict, assets: dict[str, dict] | None = None) -> dict:
    """What turning the `.md` of a course into bricks needs: the directives, the syntax of the language, the media."""
    assets = manifest_assets(course) if assets is None else assets
    return {
        "course": course,
        "registry": config.effective("directives", course.get("_project"), course).value["directives"],
        "syntax": Syntax(coursemod.tokens(course)),
        "assets": assets,
        "media_by_title": {a.get("title"): a for a in assets.values()},
        "code_languages": (coursemod.rules(course=course).get("assembly") or {}).get("code_languages") or [],
        "errors": [],
        "warnings": [],
    }


def build_plan(course: dict, unit: dict, assets: dict[str, dict] | None = None,
               simulations: bool = False) -> tuple[dict, list[str], list[str]]:
    """The plan of a unit. `assets` are the media of the manifest as the plan reads them (the html backend gives its own copies).
    With the creator backend the simulations become embeds and the adaptive blocks their neutral branch, unless `simulations`
    asks for them as they are (to build their packages)."""
    folder = coursemod.unit_dir(course["_dir"], unit["n"])
    ctx = context(course, assets)
    syntax = ctx["syntax"]
    placement, fmt = coursemod.assessment_delivery(course)
    lessons = []
    if unit.get("kind") == "assessment":  # the package of the tests when they go apart: those of every unit, in order
        for source in course.get("units") or []:
            lessons += assessment_lessons(course, source, ctx, fmt)
    elif unit.get("kind") == "bank":  # the questions of every test, for creator to export as the bank
        for source in course.get("units") or []:
            lessons += assessment_lessons(course, source, ctx, fmt, questions=True)
    else:
        sections = {s["n"]: s for s in unit.get("sections") or []}
        for m, lines in split((folder / "content.md").read_text(encoding="utf-8"), syntax.section):
            n = int(m.group(1))
            spec = sections.get(n)
            if spec is None:
                ctx["errors"].append(t("assemble", "section_not_in_design", section=syntax.t["section"], n=n))
                continue
            key = f"U{unit['n']}-S{n}"
            lessons.append({"key": key, "type": "content", "title": spec["title"], "kind": spec["kind"],
                            "slxd_node_id": spec.get("slxd_id"), "bricks": parse_blocks(lines, ctx, key)})
        if placement == "unit":
            lessons += assessment_lessons(course, unit, ctx, fmt)

    if (course.get("design") or {}).get("approach") == "decision-based":
        # the simulation that opens a content section holds the rest of the lesson until it reaches an ending: the learner
        # decides before reading (creator: the EMBED's blocking; html: the player hides what follows)
        for lesson in lessons:
            if lesson["type"] == "content" and lesson["bricks"] and lesson["bricks"][0]["type"] == "SIMULATION":
                lesson["bricks"][0]["meta"]["blocks"] = True
    if coursemod.backend(course) == "creator" and not simulations and course.get("_project"):
        for lesson in lessons:
            lesson["bricks"] = for_creator(lesson["bricks"], ctx, lesson["key"])
    for lesson in lessons:
        for brick in lesson["bricks"]:
            brick["hash"] = brick_hash(brick)
        if lesson["type"] == "content" and not lesson["bricks"]:
            ctx["warnings"].append(t("assemble", "lesson_without_content", key=lesson["key"]))
    plan = {"course": course["code"], "unit": unit["n"], "content_id": unit.get("content_id"),
            "content_title": content_title(course, unit), "lessons": lessons}
    if unit.get("kind") != "bank" and (placement == "separate" or fmt != "platform"):  # a package without tests reports progress
        plan["score_source"] = "quiz" if any(lesson["type"] == "evaluation" for lesson in lessons) else "lessonProgress"
        if plan["score_source"] == "lessonProgress":  # and its status is completed or incomplete: there is nothing to pass
            plan["reporting"] = "completed_incomplete"
    return plan, ctx["errors"], ctx["warnings"]


def assessment_lessons(course: dict, unit: dict, ctx: dict, fmt: str = "platform", questions: bool = False) -> list[dict]:
    """The evaluation lessons of the assessment activities of a unit (its assessment.md). With a question-bank format the questions
    leave the package (`coursekit delivery questions`): a lesson keeps only its scored simulations, and one without any is left out.
    With `questions`, the other way round: only the question bank of each activity (the content creator exports as the bank)."""
    syntax: Syntax = ctx["syntax"]
    assessment = coursemod.unit_dir(course["_dir"], unit["n"]) / "assessment.md"
    if not assessment.exists():
        return []
    lessons = []
    for m, lines in split(assessment.read_text(encoding="utf-8"), syntax.assessment):
        parts = {sm.group(1): sl for sm, sl in split("\n".join(lines), re.compile(r"^### (.+?)\s*$"))}
        # the learner sees the instructions, the simulations wherever the activity has them, and the question bank
        played = [line for name, part in parts.items() if name not in (syntax.t["assessment_instructions"], syntax.t["assessment_bank"])
                  for line in simulation_blocks(part, ctx)]
        bank = parts.get(syntax.t["assessment_bank"], []) if fmt == "platform" or questions else []
        body = bank if questions else parts.get(syntax.t["assessment_instructions"], []) + [""] + played + [""] + bank
        key = f"U{unit['n']}-E{m.group(1)}"
        bricks = parse_blocks(body, ctx, key)
        if questions and not bricks:
            continue
        if fmt != "platform" and not questions and not any(b["type"] == "SIMULATION" for b in walk(bricks)):
            continue
        lessons.append({"key": key, "type": "evaluation", "title": m.group(2), "kind": "assessment",
                        "quiz": quiz_settings(course, unit, m.group(1), m.group(2)), "bricks": bricks})
    return lessons


# ── Plan, diff and applied state ─────────────────────────────────────────────────────────────


class AssembleError(Exception):
    pass


def paths(course_dir: Path, n: int) -> tuple[Path, Path]:
    folder = course_dir / "assembly"
    return folder / f"unit-{n:02d}.plan.json", folder / f"unit-{n:02d}.applied.json"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _read(path: Path, default: dict | None = None) -> dict:
    if not path.exists():
        if default is None:
            raise AssembleError(t("assemble", "plan_missing", name=path.name))
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_plan(course: dict, unit: dict) -> tuple[dict | None, list[str], list[str], dict[str, int]]:
    """Build and save the plan. Returns (plan or None on errors, errors, warnings, bricks per type)."""
    plan, errors, warnings = build_plan(course, unit)
    if errors:
        return None, errors, warnings, {}
    plan_path, _ = paths(course["_dir"], unit["n"])
    write_json(plan_path, plan)
    counts: dict[str, int] = {}
    for lesson in plan["lessons"]:
        for b in lesson["bricks"]:
            counts[b["type"]] = counts.get(b["type"], 0) + 1
    return plan, errors, warnings, dict(sorted(counts.items()))


def diff(course: dict, unit: dict) -> dict:
    plan_path, applied_path = paths(course["_dir"], unit["n"])
    plan = _read(plan_path)
    applied = _read(applied_path, {"lessons": {}})
    title = plan.get("content_title")
    result = {"content_id": plan["content_id"],
              "content": {"title": title, "action": "unchanged" if applied.get("content_title") == title else "rename"},
              "lessons": []}
    for lesson in plan["lessons"]:
        old = applied["lessons"].get(lesson["key"])
        new = lesson["bricks"]
        if old is None:
            result["lessons"].append({"key": lesson["key"], "title": lesson["title"], "type": lesson["type"],
                                      "action": "create", "quiz": lesson.get("quiz"),
                                      "ops": [{"op": "add", "position": i, "type": b["type"], "data": b["data"]}
                                              for i, b in enumerate(new)]})
            continue
        ops = []
        matcher = difflib.SequenceMatcher(a=[b["hash"] for b in old["bricks"]], b=[b["hash"] for b in new], autojunk=False)
        for tag, a0, a1, b0, b1 in matcher.get_opcodes():
            if tag == "equal":
                continue
            olds, news = old["bricks"][a0:a1], new[b0:b1]
            for k in range(max(len(olds), len(news))):
                o = olds[k] if k < len(olds) else None
                b = news[k] if k < len(news) else None
                if o and b and o["type"] == b["type"]:
                    ops.append({"op": "update", "brickId": o["brickId"], "type": b["type"], "data": b["data"]})
                else:
                    if o:
                        ops.append({"op": "delete", "brickId": o["brickId"]})
                    if b:
                        ops.append({"op": "add", "position": b0 + k, "type": b["type"], "data": b["data"]})
        if lesson.get("quiz") and old.get("quiz") != lesson["quiz"]:
            ops.insert(0, {"op": "update_quiz", "quiz": lesson["quiz"]})
        if old.get("title") != lesson["title"]:
            ops.insert(0, {"op": "rename_lesson", "title": lesson["title"]})
        result["lessons"].append({"key": lesson["key"], "lessonId": old["lessonId"], "title": lesson["title"],
                                  "action": "update" if ops else "unchanged", "ops": ops})
    planned = {lesson["key"] for lesson in plan["lessons"]}
    for key, old in applied["lessons"].items():
        if key not in planned:
            result["lessons"].append({"key": key, "lessonId": old["lessonId"], "action": "delete", "ops": []})
    return result


def record_lesson(course: dict, unit: dict, lesson_key: str, lesson_id: str | None, brick_ids: list[str], keep: bool = False,
                  replace: dict[str, str] | None = None) -> str:
    """Records what is now in creator for a lesson. With `keep` the brick ids already recorded are kept, in their positions (what
    `update_brick` leaves: the same bricks with new content), `replace` swapping those of the bricks that were deleted and added again."""
    plan_path, applied_path = paths(course["_dir"], unit["n"])
    plan = _read(plan_path)
    lesson = next((lesson for lesson in plan["lessons"] if lesson["key"] == lesson_key), None)
    if lesson is None:
        raise AssembleError(t("assemble", "lesson_not_in_plan", key=lesson_key))
    if keep:
        before = (_read(applied_path, {"lessons": {}})["lessons"]).get(lesson_key)
        if before is None:
            raise AssembleError(t("assemble", "keep_ids_nothing_recorded", key=lesson_key))
        replace = replace or {}
        brick_ids = [replace.get(b["brickId"], b["brickId"]) for b in before["bricks"]]
        lesson_id = lesson_id or before["lessonId"]
        if len(brick_ids) != len(lesson["bricks"]):
            raise AssembleError(t("assemble", "keep_ids_count", key=lesson_key, ids=len(brick_ids), bricks=len(lesson["bricks"])))
    if len(brick_ids) != len(lesson["bricks"]):
        raise AssembleError(t("assemble", "brick_count_mismatch", ids=len(brick_ids), bricks=len(lesson["bricks"]), key=lesson_key))
    applied = _read(applied_path, {"lessons": {}})
    applied["lessons"][lesson_key] = {
        "lessonId": lesson_id,
        "title": lesson["title"],
        "bricks": [{"brickId": bid, "type": b["type"], "hash": b["hash"]} for bid, b in zip(brick_ids, lesson["bricks"], strict=True)],
    }
    if lesson.get("quiz"):
        applied["lessons"][lesson_key]["quiz"] = lesson["quiz"]
    write_json(applied_path, applied)
    return t("assemble", "recorded_lesson", key=lesson_key, count=len(brick_ids)) + mark_assembled(course)


def record_content_title(course: dict, unit: dict) -> str:
    plan_path, applied_path = paths(course["_dir"], unit["n"])
    plan = _read(plan_path)
    applied = _read(applied_path, {"lessons": {}})
    applied["content_title"] = plan["content_title"]
    write_json(applied_path, applied)
    return t("assemble", "recorded_title", title=plan["content_title"]) + mark_assembled(course)


def unit_in_sync(course_dir: Path, n: int) -> bool:
    plan_path, applied_path = paths(course_dir, n)
    if not (plan_path.exists() and applied_path.exists()):
        return False
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    applied_all = json.loads(applied_path.read_text(encoding="utf-8"))
    if applied_all.get("content_title") != plan.get("content_title"):
        return False
    applied = applied_all["lessons"]
    return all(
        lesson["key"] in applied
        and [b["hash"] for b in applied[lesson["key"]]["bricks"]] == [b["hash"] for b in lesson["bricks"]]
        and (not lesson.get("quiz") or applied[lesson["key"]].get("quiz") == lesson["quiz"])
        for lesson in plan["lessons"]
    )


def _fingerprint(applied: dict) -> str:
    """What the closing checks vouch for: the content title and the bricks (types and hashes) of every lesson as recorded."""
    state = [applied.get("content_title"), {key: [(b["type"], b["hash"]) for b in lesson["bricks"]]
                                            for key, lesson in sorted((applied.get("lessons") or {}).items())}]
    return hashlib.sha1(json.dumps(state, ensure_ascii=False).encode("utf-8")).hexdigest()


def record_checked(course: dict, unit: dict) -> str:
    """Records that the closing checks of the assembly (accessibility, text against the `.md`, snapshot, links and review version)
    were done on what is in creator now. Any later change to the recorded bricks makes them pending again."""
    if not unit_in_sync(course["_dir"], unit["n"]):
        raise AssembleError(t("assemble", "checked_not_in_sync", n=unit["n"]))
    _, applied_path = paths(course["_dir"], unit["n"])
    applied = _read(applied_path)
    applied["checked"] = _fingerprint(applied)
    write_json(applied_path, applied)
    return t("assemble", "recorded_checked", n=unit["n"]) + mark_assembled(course)


def unit_checked(course_dir: Path, n: int) -> bool:
    _, applied_path = paths(course_dir, n)
    if not applied_path.exists():
        return False
    applied = json.loads(applied_path.read_text(encoding="utf-8"))
    return applied.get("checked") == _fingerprint(applied)


def mark_assembled(course: dict) -> str:
    """When every unit is in creator exactly as planned, the course moves from `media` to `assembly`."""
    if course["status"] != "media" or not all(unit_in_sync(course["_dir"], u["n"]) for u in coursemod.package_units(course)):
        return ""
    path = course["_dir"] / "course.yaml"
    ry, data = edit_yaml(path)
    data["status"] = "assembly"
    data.setdefault("history", []).append(history_entry("assembly", "Every unit assembled"))
    save_yaml(ry, data, path)
    course["status"] = "assembly"
    return t("assemble", "course_assembled")


def link(course: dict, unit: dict, content_id: str | None = None, preview: str | None = None, review: str | None = None) -> str:
    """Record the creator content of a unit and, once it exists, its preview and client-review links."""
    path = course["_dir"] / "course.yaml"
    ry, data = edit_yaml(path)
    extra = {"assessment": "assessment_unit", "bank": "bank_unit"}.get(unit.get("kind") or "")
    if extra and not isinstance(data.get(extra), dict):
        data[extra] = {}
    for u in [data[extra]] if extra else data["units"]:
        if extra or u["n"] == unit["n"]:
            if content_id:
                u["content_id"] = content_id
            if preview or review:
                links = u.get("links") or {}
                for key, value in (("preview", preview), ("review", review)):
                    if value:
                        links[key] = value
                u["links"] = links
    save_yaml(ry, data, path)
    parts = [t("assemble", f"linked_{key}", value=value)
             for key, value in (("content", content_id), ("preview", preview), ("review", review)) if value]
    return t("assemble", "linked", n=unit["n"], what="; ".join(parts))


def check_unit(course: dict, unit: dict) -> list[str]:
    """For `coursekit verify`: the content must convert to bricks (same parse as the plan)."""
    _, errors, _ = build_plan(course, unit)
    return errors
