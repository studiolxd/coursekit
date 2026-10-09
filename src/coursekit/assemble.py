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

from coursekit import config, lang
from coursekit import course as coursemod
from coursekit.i18n import t
from coursekit.states import history_entry
from coursekit.util import edit_yaml, load_yaml, save_yaml

MD = MarkdownIt("commonmark").enable("table")
CODE_LANGUAGES = {
    "javascript", "typescript", "python", "html", "css", "java", "go", "rust", "sql", "json", "yaml",
    "bash", "c", "cpp", "csharp", "php", "ruby", "swift", "kotlin", "markdown", "xml",
}
LANGUAGE_ALIASES = {"js": "javascript", "ts": "typescript", "py": "python", "sh": "bash", "shell": "bash",
                    "zsh": "bash", "console": "bash", "yml": "yaml", "c++": "cpp", "cs": "csharp", "md": "markdown"}

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


def directive_brick(name: str, body: list[str], ctx: dict) -> dict:
    registry = ctx["registry"]
    if name not in registry:
        raise PlanError(t("assemble", "unknown_directive", name=name))
    brick_type = registry[name]["brick"]
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
        image = ctx["media_by_title"].get(values.get(syntax.key("image"), ""))
        points = panels(rest)
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
        data = {"characters": [{"name": c} for c in characters], "items": items}
    elif brick_type == "CAROUSEL_QUOTES":
        items = []
        for block in "\n".join(rest).strip().split("\n\n"):
            lines = [ln for ln in block.splitlines() if ln.strip()]
            author = lines.pop()[2:].strip() if lines and lines[-1].startswith("— ") else ""
            items.append({"content": inline(" ".join(lines)), "author": inline(author) if author else ""})
        data = {"items": items}
    elif brick_type == "NOTE":
        data = {"content": {"title": inline(values.get(syntax.key("title"), syntax.t["note"])), "content": html("\n".join(rest))}}
    elif brick_type == "HIGHLIGHT":
        data = {"content": {"content": html("\n".join(rest))}}
    elif brick_type == "QUOTE":
        lines = [ln for ln in rest if ln.strip()]
        author = lines.pop()[2:].strip() if lines and lines[-1].startswith("— ") else ""
        data = {"content": {"content": html("\n".join(lines)), "author": inline(author) if author else ""}}
    elif brick_type in ("SINGLE_CHOICE", "MULTI_SELECT"):
        options = [(m.group(1).lower() == "x", m.group(2)) for m in map(OPTION_RE.match, rest) if m]
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
        for category, content in panels(rest):
            categories.append({"name": category})
            for block in content.split("\n\n"):
                q_values, q_rest = key_values(block.splitlines())
                syntax.check_keys(q_values)
                options = [{"text": m.group(2), "isCorrect": m.group(1).lower() == "x"} for m in map(OPTION_RE.match, q_rest) if m]
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


def placeholder_brick(kind: str, fields: dict, asset: dict | None, label: str, written: str | None = None) -> dict:
    """`kind` is the id of the resource type; `written` how the content names it (for the note that stands for it)."""
    title = fields.get("title", "")
    media = MEDIA_KIND.get(kind)
    meta = {"placeholder": kind, "title": title}
    if asset and asset.get("asset_path") and asset.get("status") == "uploaded":
        meta["asset"] = asset["id"]
        caption = inline(title)
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
    placeholder_n = 0

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
            lang = LANGUAGE_ALIASES.get(lang, lang)
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            bricks.append({"type": "CODE", "data": {"properties": {"codeLanguage": lang if lang in CODE_LANGUAGES else "auto"},
                                                    "content": {"content": "\n".join(code)}}, "meta": {}})
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
            placeholder_n += 1
            asset_id = f"{section_key}-M{placeholder_n}"
            asset = ctx["assets"].get(asset_id)
            bricks.append(placeholder_brick(kind, fields, asset, syntax.t["placeholder"].capitalize(), written))
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
    """Title of the unit's creator content: the course title when there is a single unit."""
    if len(course.get("units") or []) == 1:
        return course["title"]
    return f"{coursemod.tokens(course)['unit']} {unit['n']}. {unit['title']}"


def manifest_assets(course: dict) -> dict[str, dict]:
    manifest_path = course["_dir"] / "media" / "manifest.yaml"
    return {a["id"]: a for a in (load_yaml(manifest_path).get("assets") or [])} if manifest_path.exists() else {}


def build_plan(course: dict, unit: dict, assets: dict[str, dict] | None = None) -> tuple[dict, list[str], list[str]]:
    """The plan of a unit. `assets` are the media of the manifest as the plan reads them (the html backend gives its own copies)."""
    folder = coursemod.unit_dir(course["_dir"], unit["n"])
    syntax = Syntax(coursemod.tokens(course))
    assets = manifest_assets(course) if assets is None else assets
    ctx = {
        "registry": config.effective("directives", course.get("_project"), course).value["directives"],
        "syntax": syntax,
        "assets": assets,
        "media_by_title": {a.get("title"): a for a in assets.values()},
        "errors": [],
        "warnings": [],
    }
    sections = {s["n"]: s for s in unit.get("sections") or []}
    lessons = []
    for m, lines in split((folder / "content.md").read_text(encoding="utf-8"), syntax.section):
        n = int(m.group(1))
        spec = sections.get(n)
        if spec is None:
            ctx["errors"].append(t("assemble", "section_not_in_design", section=syntax.t["section"], n=n))
            continue
        key = f"U{unit['n']}-S{n}"
        lessons.append({"key": key, "type": "content", "title": spec["title"], "kind": spec["kind"],
                        "slxd_node_id": spec.get("slxd_id"), "bricks": parse_blocks(lines, ctx, key)})

    assessment = folder / "assessment.md"
    grading = course["design"].get("grading") or {}
    if assessment.exists():
        for m, lines in split(assessment.read_text(encoding="utf-8"), syntax.assessment):
            parts = {sm.group(1): sl for sm, sl in split("\n".join(lines), re.compile(r"^### (.+?)\s*$"))}
            body = parts.get(syntax.t["assessment_instructions"], []) + [""] + parts.get(syntax.t["assessment_bank"], [])
            key = f"U{unit['n']}-E{m.group(1)}"
            lessons.append({"key": key, "type": "evaluation", "title": m.group(2), "kind": "assessment",
                            "quiz": {"passingGrade": grading.get("passing_score"), "maxAttempts": grading.get("attempts")},
                            "bricks": parse_blocks(body, ctx, key)})

    for lesson in lessons:
        for brick in lesson["bricks"]:
            brick["hash"] = brick_hash(brick)
        if lesson["type"] == "content" and not lesson["bricks"]:
            ctx["warnings"].append(t("assemble", "lesson_without_content", key=lesson["key"]))
    plan = {"course": course["code"], "unit": unit["n"], "content_id": unit.get("content_id"),
            "content_title": content_title(course, unit), "lessons": lessons}
    return plan, ctx["errors"], ctx["warnings"]


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
        if old.get("title") != lesson["title"]:
            ops.insert(0, {"op": "rename_lesson", "title": lesson["title"]})
        result["lessons"].append({"key": lesson["key"], "lessonId": old["lessonId"], "title": lesson["title"],
                                  "action": "update" if ops else "unchanged", "ops": ops})
    planned = {lesson["key"] for lesson in plan["lessons"]}
    for key, old in applied["lessons"].items():
        if key not in planned:
            result["lessons"].append({"key": key, "lessonId": old["lessonId"], "action": "delete", "ops": []})
    return result


def record_lesson(course: dict, unit: dict, lesson_key: str, lesson_id: str, brick_ids: list[str]) -> str:
    plan_path, applied_path = paths(course["_dir"], unit["n"])
    plan = _read(plan_path)
    lesson = next((lesson for lesson in plan["lessons"] if lesson["key"] == lesson_key), None)
    if lesson is None:
        raise AssembleError(t("assemble", "lesson_not_in_plan", key=lesson_key))
    if len(brick_ids) != len(lesson["bricks"]):
        raise AssembleError(t("assemble", "brick_count_mismatch", ids=len(brick_ids), bricks=len(lesson["bricks"]), key=lesson_key))
    applied = _read(applied_path, {"lessons": {}})
    applied["lessons"][lesson_key] = {
        "lessonId": lesson_id,
        "title": lesson["title"],
        "bricks": [{"brickId": bid, "type": b["type"], "hash": b["hash"]} for bid, b in zip(brick_ids, lesson["bricks"], strict=True)],
    }
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
        lesson["key"] in applied and [b["hash"] for b in applied[lesson["key"]]["bricks"]] == [b["hash"] for b in lesson["bricks"]]
        for lesson in plan["lessons"]
    )


def mark_assembled(course: dict) -> str:
    """When every unit is in creator exactly as planned, the course moves from `media` to `assembly`."""
    if course["status"] != "media" or not all(unit_in_sync(course["_dir"], u["n"]) for u in course["units"]):
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
    for u in data["units"]:
        if u["n"] == unit["n"]:
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
