"""eXeLearning packages (`.elp`): read the tree of pages and iDevices and convert it to Markdown for the brief.

The `.elp` of eXeLearning 2.x and 3.x is a zip with `contentv3.xml` (the object graph of the package serialised as XML) and
the media files at its root. `read` turns it into pages and iDevices; `to_markdown` writes them with the directives of the
content format, keeping the kind of interactivity of the source (accordion, tabs, carousel, flashcards, map, questions).

What each iDevice becomes is in `defaults/import.yaml` (rules by title and label, overridable by the project); the
collections of the effects of eXeLearning (`exe-accordion`, `exe-tabs`, `exe-carousel`) are read from the HTML, wherever
they are. Nothing is dropped silently: what is left out or not understood goes in the report of the conversion.
"""

from __future__ import annotations

import html
import json
import posixpath
import re
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

from coursekit import lang as langmod
from coursekit.i18n import t

NS = "{http://www.exelearning.org/content/v0.3}"
CONTENT = "contentv3.xml"
EXPORTS_V4 = "content.xml"  # eXeLearning 4 (.elpx): another reader to add
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")


class ExeError(Exception):
    pass


# ── Reading the package ─────────────────────────────────────────────────────────────────────────

def _pairs(element: ET.Element | None) -> dict[str, ET.Element]:
    """`key, value, key, value…` of a `<dictionary>` element."""
    out: dict[str, ET.Element] = {}
    if element is None:
        return out
    items = list(element)
    for i in range(0, len(items) - 1, 2):
        if items[i].get("role") == "key":
            out[items[i].get("value") or ""] = items[i + 1]
    return out


def _value(element: ET.Element | None) -> str:
    return (element.get("value") or "") if element is not None else ""


@dataclass
class Idevice:
    cls: str       # class of the object without its module: JsIdevice, GenericIdevice, MultichoiceIdevice…
    kind: str      # JsIdevice: its directory (`text`, `flipcards-activity`…); GenericIdevice: its title; otherwise `cls`
    title: str
    data: dict[str, ET.Element]
    package: Package
    element: ET.Element

    def fields(self) -> list[tuple[str, dict[str, ET.Element]]]:
        """The fields of a generic or JS iDevice: (label, data)."""
        out = []
        for item in self.package.items(self.data.get("fields")):
            d = _pairs(item.find(NS + "dictionary"))
            out.append((_value(d.get("_name")).strip(), d))
        return out


@dataclass
class Page:
    title: str
    idevices: list[Idevice] = field(default_factory=list)
    children: list[Page] = field(default_factory=list)


@dataclass
class Package:
    path: Path
    title: str = ""
    language: str = ""
    author: str = ""
    root: Page | None = None
    names: dict[str, str] = field(default_factory=dict)   # lower-case basename -> name in the zip
    refs: dict[str, ET.Element] = field(default_factory=dict)

    def resolve(self, element: ET.Element | None) -> ET.Element:
        if element is not None and element.tag == NS + "reference":
            found = self.refs.get(element.get("key") or "")
            if found is not None:
                return found
        return element if element is not None else ET.Element("none")

    def items(self, element: ET.Element | None) -> list[ET.Element]:
        return [self.resolve(child) for child in (element if element is not None else [])]

    def page(self, element: ET.Element) -> Page:
        d = _pairs(self.resolve(element).find(NS + "dictionary"))
        page = Page(title=_value(d.get("_title")).strip())
        for item in self.items(d.get("idevices")):
            idev = _pairs(item.find(NS + "dictionary"))
            cls = (item.get("class") or "").rsplit(".", 1)[-1]
            title = _value(idev.get("_title")).strip()
            kind = _value(idev.get("_iDeviceDir")) if cls == "JsIdevice" else (title if cls == "GenericIdevice" else cls)
            page.idevices.append(Idevice(cls, kind or cls, title, idev, self, item))
        page.children = [self.page(child) for child in self.items(d.get("children"))]
        return page


def read(path: Path) -> Package:
    try:
        archive = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise ExeError(t("exelearning", "not_a_package", file=path.name)) from exc
    with archive:
        names = archive.namelist()
        if CONTENT not in names:
            key = "package_v4" if EXPORTS_V4 in names else "not_a_package"
            raise ExeError(t("exelearning", key, file=path.name))
        try:
            root = ET.fromstring(archive.read(CONTENT))
        except ET.ParseError as exc:
            raise ExeError(t("exelearning", "broken_xml", file=path.name, error=exc)) from exc
    package = Package(path=path)
    package.names = {posixpath.basename(n).lower(): n for n in names if not n.endswith("/")}
    package.refs = {e.get("reference"): e for e in root.iter(NS + "instance") if e.get("reference")}
    data = _pairs(root.find(NS + "dictionary"))
    package.title = _value(data.get("_title")).strip()
    package.language = _value(data.get("_lang")).strip()
    package.author = _value(data.get("_author")).strip()
    nodes = _pairs(package.resolve(data.get("_nodeIdDict")))  # keyed by the id of the page: "0" is the root
    first = nodes.get("0") if nodes.get("0") is not None else next(iter(nodes.values()), None)
    if first is None:
        raise ExeError(t("exelearning", "no_pages", file=path.name))
    package.root = package.page(first)
    return package


def media_bytes(package: Package, name: str) -> bytes | None:
    with zipfile.ZipFile(package.path) as archive:
        try:
            return archive.read(name)
        except KeyError:
            return None


# ── HTML to Markdown ────────────────────────────────────────────────────────────────────────────

VOID = {"br", "img", "hr", "input", "source", "meta", "link", "col", "area", "base", "wbr", "track", "embed"}
BLOCKS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "table", "blockquote", "pre", "hr", "iframe", "video",
          "audio", "figure", "section", "article", "header", "footer", "li", "tr", "object"}
SKIP = {"script", "style", "noscript", "head"}


def _wrap(opening: str, inner: str, closing: str | None = None) -> str:
    """Markdown marks around the text, keeping the spaces of the source outside them (`**a **b` would join the words)."""
    core = inner.strip()
    if not core:
        return inner
    lead, trail = inner[:len(inner) - len(inner.lstrip())], inner[len(inner.rstrip()):]
    return f"{lead}{opening}{core}{closing if closing is not None else opening}{trail}"


@dataclass
class Dom:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list[Dom | str] = field(default_factory=list)

    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Dom("root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Dom(tag, {k: v or "" for k, v in attrs})
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Dom(tag, {k: v or "" for k, v in attrs}))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_html(text: str) -> Dom:
    parser = _Parser()
    parser.feed(text or "")
    parser.close()
    return parser.root


def is_noise(node: Dom) -> bool:
    return bool(node.classes() & {"gtx-trans", "gtx-trans-icon"}) or node.attrs.get("id", "") in ("gtx-trans", "gtx-trans-icon")


def plain(node: Dom | str) -> str:
    """The text of a node, without tags (and without what the conversion leaves out: scripts and browser artefacts)."""
    if isinstance(node, str):
        return node
    if node.tag in SKIP or is_noise(node):
        return ""
    glue = " " if node.tag in BLOCKS or node.tag in ("br", "td", "th") else ""
    return glue + "".join(plain(c) for c in node.children) + glue


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def words_of(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold())


FX = {"exe-accordion": "accordion", "exe-tabs": "tabs", "exe-carousel": "carousel"}
BROWSER_NOISE = ("gtx-trans", "gtx-trans-icon")  # the artefacts of a browser translation extension left in the content


class _Markup:
    """HTML to Markdown, copying the images it finds; collects what it did for the report."""

    def __init__(self, package: Package, media_dir: Path, media_rel: str, rules: list[dict], language: str, hosts: list[str] | None = None):
        self.package = package
        self.media_dir = media_dir
        self.media_rel = media_rel          # how the Markdown refers to the folder of the images
        self.rules = rules
        self.tk = langmod.tokens(language)
        self.depth = 0                      # inside a directive: headings are bold lines
        self.copied: dict[str, str] = {}
        self.report = Report(package.title)
        self.source_words: list[str] = []
        self.output_words: list[str] = []
        self.hosts = [h.lower() for h in (hosts or [])]

    # -- directives -------------------------------------------------------------------------------

    def key(self, name: str) -> str:
        return langmod.directive_key(self.tk, name)

    def directive(self, name: str, body: str, title: str | None = None) -> str:
        head = f"{self.key('title')}: {title}\n" if title else ""
        return f":::{name}\n{head}{body.strip()}\n:::"

    # -- media ------------------------------------------------------------------------------------

    def asset(self, src: str) -> str | None:
        """Copies the image the HTML refers to (`resources/x.png` or `x.png`) and returns its path as the Markdown refers to it."""
        base = posixpath.basename(urllib.parse.unquote(src.split("?")[0].split("#")[0])).lower()
        if base in self.copied:
            return self.copied[base]
        name = self.package.names.get(base)
        if name is None or not base.endswith(IMAGE_SUFFIXES):
            return None
        data = media_bytes(self.package, name)
        if data is None:
            return None
        self.media_dir.mkdir(parents=True, exist_ok=True)
        (self.media_dir / posixpath.basename(name)).write_bytes(data)
        self.copied[base] = f"{self.media_rel}/{posixpath.basename(name)}"
        self.report.images += 1
        return self.copied[base]

    # -- inline -----------------------------------------------------------------------------------

    def inline(self, node: Dom | str) -> str:
        if isinstance(node, str):
            return re.sub(r"\s+", " ", node.replace("\xa0", " "))
        tag = node.tag
        if tag in SKIP or node.classes() & set(BROWSER_NOISE) or node.attrs.get("id", "") in BROWSER_NOISE:
            return ""
        inner = "".join(self.inline(c) for c in node.children)
        if tag in ("strong", "b"):
            return _wrap("**", inner)
        if tag in ("em", "i"):
            return _wrap("*", inner)
        if tag == "code":
            return _wrap("`", inner)
        if tag == "br":
            return "  \n"
        if tag == "a":
            href = node.attrs.get("href", "")
            if not href or href.startswith("#") or not inner.strip():
                return inner
            self.link(href)
            return _wrap("[", inner, f"]({href})")
        if tag == "img":
            alt = squash(node.attrs.get("alt", ""))
            path = self.asset(node.attrs.get("src", ""))
            if path is None:
                self.report.missing_images.append(node.attrs.get("src", ""))
                return f"*[{alt or node.attrs.get('src', '')}]*" if alt or node.attrs.get("src") else ""
            return f"![{alt}]({path})"
        if tag in BLOCKS:
            return inner
        return inner

    def link(self, url: str) -> None:
        host = re.sub(r"^https?://", "", url).split("/")[0].lower()
        if host and "." in host:
            self.report.hosts[host] = self.report.hosts.get(host, 0) + 1

    # -- blocks -----------------------------------------------------------------------------------

    def flow(self, children: list[Dom | str]) -> list[str]:
        """The children as blocks of Markdown."""
        blocks: list[str] = []
        buffer: list[str] = []

        def flush() -> None:
            text = "".join(buffer).strip()
            buffer.clear()
            if text:
                blocks.append(re.sub(r"[ \t]+\n", "\n", re.sub(r" {2,}(?!\n)", " ", text)))

        for child in children:
            if isinstance(child, str) or child.tag not in BLOCKS or child.tag == "li":
                if not isinstance(child, str) and (child.tag in SKIP or child.classes() & set(BROWSER_NOISE)
                                                  or child.attrs.get("id", "") in BROWSER_NOISE):
                    continue
                buffer.append(self.inline(child))
                continue
            flush()
            blocks.extend(self.block(child))
        flush()
        return blocks

    def block(self, node: Dom) -> list[str]:
        tag = node.tag
        if node.classes() & set(BROWSER_NOISE) or node.attrs.get("id", "") in BROWSER_NOISE:
            return []
        fx = next((FX[c] for c in node.classes() if c in FX), None)
        if tag == "div" and fx:
            return [self.collection(fx, node)]
        if re.fullmatch(r"h[1-6]", tag):
            text = squash("".join(self.inline(c) for c in node.children))
            if not text:
                return []
            if self.depth:
                return [f"**{text}**"]
            return ["#" * min(6, int(tag[1]) + 3) + " " + text]
        if tag in ("ul", "ol"):
            return [self.list(node)]
        if tag == "table":
            return [self.table(node)]
        if tag == "blockquote":
            inner = "\n\n".join(self.flow(node.children))
            return ["\n".join("> " + line if line else ">" for line in inner.splitlines())] if inner else []
        if tag == "pre":
            return ["```\n" + plain(node).strip("\n") + "\n```"]
        if tag == "hr":
            return []
        if tag in ("iframe", "video", "audio", "object"):
            return [self.embedded(node)]
        if tag == "li":
            return self.flow(node.children)
        return self.flow(node.children)

    def embedded(self, node: Dom) -> str:
        src = node.attrs.get("src") or next((c.attrs.get("src", "") for c in node.children if isinstance(c, Dom) and c.tag == "source"), "")
        kind = {"iframe": "video", "video": "video", "audio": "audio"}.get(node.tag, "embed")
        host = re.sub(r"^https?://", "", src).split("/")[0].lower() if src else ""
        self.report.embeds.append((kind, src, host))
        label = {"video": "Video", "audio": "Audio", "embed": "Embed"}[kind]
        flagged = bool(host) and any(host == h or host.endswith(f".{h}") for h in self.hosts)
        if flagged:
            self.report.forbidden_embeds.append(src)
        mark = " (forbidden host: keep it only if its channel is official, see `coursekit videos`; else replace it)" if flagged else ""
        return f"> **[{label}]** {src}{mark}" if src else f"> **[{label}]**"

    def list(self, node: Dom) -> str:
        ordered = node.tag == "ol"
        lines = []
        n = 0
        for child in node.children:
            if isinstance(child, Dom) and child.tag in ("ul", "ol"):  # a list written straight inside another one
                lines += ["   " + line for line in self.list(child).splitlines()]
            elif isinstance(child, Dom) and child.tag == "li":
                n += 1
                inner = self.flow([c for c in child.children if not (isinstance(c, Dom) and c.tag in ("ul", "ol"))])
                text = squash(" ".join(inner)) if inner else ""
                lines.append(f"{n}. {text}" if ordered else f"- {text}")
                for sub in (c for c in child.children if isinstance(c, Dom) and c.tag in ("ul", "ol")):
                    lines += ["   " + line for line in self.list(sub).splitlines()]
        return "\n".join(lines)

    def table(self, node: Dom) -> str:
        rows = []

        def walk(n: Dom) -> None:
            for c in n.children:
                if isinstance(c, Dom):
                    if c.tag == "tr":
                        rows.append([squash("".join(self.inline(x) for x in cell.children)).replace("|", "\\|")
                                     for cell in c.children if isinstance(cell, Dom) and cell.tag in ("td", "th")])
                    else:
                        walk(c)

        walk(node)
        rows = [r for r in rows if r]
        if not rows:
            return ""
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width]
        out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
        return "\n".join(out)

    def collection(self, kind: str, node: Dom) -> str:
        """An effect of eXeLearning: a `<h2>` per panel, tab or slide, followed by its content."""
        items: list[tuple[str, list[Dom | str]]] = []
        for child in node.children:
            if isinstance(child, Dom) and child.tag in ("h2", "h3"):
                items.append((squash("".join(self.inline(c) for c in child.children)), []))
            elif items:
                items[-1][1].append(child)
            elif not isinstance(child, str) or child.strip():
                items.append(("", [child]))
        self.depth += 1
        try:
            parts = []
            provisional = 0
            for title, body in items:
                text = "\n\n".join(self.flow(body))
                if not title:
                    title = str(len(parts) + 1)  # provisional: the design gives the real one
                    provisional += 1
                parts.append(f"#### {title}\n{text}".rstrip())
        finally:
            self.depth -= 1
        if provisional:
            self.report.note("untitled_items", kind=kind, count=provisional)
        self.report.count(kind)
        return self.directive(kind, "\n".join(parts))

    def html_to_md(self, text: str) -> str:
        return "\n\n".join(self.flow(parse_html(text).children))

    def html_to_md_children(self, node: Dom) -> str:
        return "\n\n".join(self.flow(node.children))


# ── iDevices ────────────────────────────────────────────────────────────────────────────────────

CONTENT_KEYS = ("content_w_resourcePaths", "content")
GAME_DATA = re.compile(r'<div class="[\w-]*DataGame[^"]*">(.*?)</div>', re.S)
QUIZZES = ("MultichoiceIdevice", "TrueFalseIdevice", "MultiSelectIdevice")
CARD_GAMES = {"flipcards-activity": "flashcards", "relaciona-activity": "match"}


def _bare(text: str) -> str:
    """Markdown without its marks (images, link addresses, emphasis): the words a person reads."""
    text = re.sub(r"\]\([^)]*\)", "", re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text))
    return re.sub(r"[*`]", "", text.replace("[", " "))


def _unquote(text: object) -> str:
    return urllib.parse.unquote(str(text or "")).strip()


def _html_of(package: Package, element: ET.Element | None) -> str:
    """The HTML of a text field (an instance with a dictionary)."""
    if element is None:
        return ""
    d = _pairs(package.resolve(element).find(NS + "dictionary"))
    return next((_value(d[k]) for k in CONTENT_KEYS if k in d and _value(d[k])), "")


def _all_html(idev: Idevice) -> list[str]:
    """Every HTML text of an iDevice in document order, whatever its fields are."""
    out = []
    for dictionary in idev.element.iter(NS + "dictionary"):
        d = _pairs(dictionary)
        for key in CONTENT_KEYS:
            if key in d and _value(d[key]).strip():
                out.append(_value(d[key]))
                break
    return out


@dataclass
class Report:
    title: str
    images: int = 0
    missing_images: list[str] = field(default_factory=list)
    embeds: list[tuple[str, str, str]] = field(default_factory=list)   # (kind, address, host)
    hosts: dict[str, int] = field(default_factory=dict)               # hosts of the links
    counts: dict[str, int] = field(default_factory=dict)              # directives written
    dropped: dict[str, dict[str, int]] = field(default_factory=dict)  # kind -> {text: times}
    unmapped: dict[str, int] = field(default_factory=dict)            # kinds converted as plain text
    notes: list[tuple[str, dict]] = field(default_factory=list)
    pages: int = 0
    empty_pages: list[str] = field(default_factory=list)
    questions: int = 0
    forbidden_embeds: list[str] = field(default_factory=list)         # addresses of embedded content on a forbidden host
    forbidden_terms: dict[str, int] = field(default_factory=dict)     # forbidden term -> times it appears
    missing_words: list[str] = field(default_factory=list)
    words_source: int = 0
    words_output: int = 0

    def note(self, key: str, **values: object) -> None:
        self.notes.append((key, values))

    def count(self, name: str) -> None:
        self.counts[name] = self.counts.get(name, 0) + 1

    def drop(self, kind: str, text: str) -> None:
        bucket = self.dropped.setdefault(kind, {})
        key = squash(text)[:160]
        bucket[key] = bucket.get(key, 0) + 1


def _rule_for(rules: list[dict], target: str) -> dict | None:
    for rule in rules:
        if re.search(str(rule.get("match") or "$^"), target, re.I):
            return rule
    return None


class Converter(_Markup):
    """Writes one package as Markdown: what each iDevice becomes (rules, quizzes, games) on top of the HTML conversion."""

    def rich(self, raw: object) -> str:
        """A text of the data of a game: it may carry HTML. Its words count as source words; it comes back as Markdown."""
        text = _unquote(raw)
        if not text:
            return ""
        dom = parse_html(text)
        self.source_words += words_of(plain(dom))
        return self.html_to_md_children(dom) if re.search(r"<\w", text) else text

    def idevice(self, idev: Idevice) -> str:
        """One iDevice as Markdown ('' when it is left out)."""
        package = self.package
        if idev.cls in QUIZZES:
            return self.quiz(idev)
        labelled = idev.fields() if idev.cls in ("GenericIdevice", "JsIdevice") else []
        label = next((name for name, _ in labelled if name), "")
        if idev.cls == "JsIdevice" and idev.kind in (*CARD_GAMES, "mapa-activity"):
            return self.game(idev)
        target = f"{idev.title} {label}" if idev.cls == "GenericIdevice" else idev.kind
        rule = _rule_for(self.rules, target) if idev.kind != "text" else None
        texts = [h for h in (_html_of(package, f) for f in package.items(idev.data.get("fields"))) if h.strip()] \
            if idev.cls in ("GenericIdevice", "JsIdevice") else _all_html(idev)
        if idev.cls not in ("GenericIdevice", "JsIdevice") or not texts:
            texts = texts or _all_html(idev)
        if rule and rule.get("action") == "drop":
            self.report.drop(idev.kind, " ".join(squash(plain(parse_html(t_))) for t_ in texts) or label)
            return ""
        before = sum(self.report.counts.values())
        body = []
        for text in texts:
            self.source_words += words_of(plain(parse_html(text)))
            body.append(self.html_to_md(text))
        effect = sum(self.report.counts.values()) > before  # a collection of eXeLearning inside: its kind is already kept
        if idev.kind != "text" and rule is None and not effect:
            self.report.unmapped[idev.kind] = self.report.unmapped.get(idev.kind, 0) + 1
        body_text = "\n\n".join(b for b in body if b)
        if not body_text:
            return ""
        action = (rule or {}).get("action", "text")
        if action in ("note", "reflection", "quote"):
            self.report.count(action)
            return self.directive(action, body_text, label or None)
        if action == "highlight":
            self.report.count("highlight")
            return self.directive("highlight", f"**{label}**\n\n{body_text}" if label else body_text)
        return body_text


    def quiz(self, idev: Idevice) -> str:
        package = self.package
        out = []
        intro = [idev.title] if idev.title else []
        instructions = _html_of(package, idev.data.get("instructionsForLearners"))
        if instructions:
            self.source_words += words_of(plain(parse_html(instructions)))
            intro.append(self.html_to_md(instructions))
        if intro:
            out.append("\n\n".join(i for i in intro if i))
            self.source_words += words_of(idev.title)
        for question in package.items(idev.data.get("questions")):
            q = _pairs(question.find(NS + "dictionary"))

            def text(key: str, q=q) -> str:
                raw = _html_of(package, q.get(key))
                self.source_words += words_of(plain(parse_html(raw)))
                return squash(self.html_to_md(raw).replace("\n", " "))

            stem, feedback = text("questionTextArea"), text("feedbackTextArea")
            self.report.questions += 1
            if idev.cls == "TrueFalseIdevice":
                truth = "true" if _value(q.get("isCorrect")) == "1" else "false"
                lines = [f"{self.key('question')}: {stem}", f"{self.key('answer')}: {self.tk['directive_words'][truth]}"]
                if feedback:
                    lines.append(f"{self.key('feedback')}: {feedback}")
                self.report.count("true-false")
                out.append(self.directive("true-false", "\n".join(lines)))
                continue
            options = []
            for option in package.items(q.get("options")):
                o = _pairs(option.find(NS + "dictionary"))
                options.append((text_of := squash(self.html_to_md(_html_of(package, o.get("answerTextArea"))).replace("\n", " ")),
                                _value(o.get("isCorrect")) == "1",
                                squash(self.html_to_md(_html_of(package, o.get("feedbackTextArea"))).replace("\n", " "))))
                self.source_words += words_of(text_of)
                self.source_words += words_of(options[-1][2])
            correct = sum(1 for _, ok, _ in options if ok)
            kind = "multi-select" if idev.cls == "MultiSelectIdevice" or correct > 1 else "single-choice"
            lines = [f"{self.key('question')}: {stem}"] + [f"- [{'x' if ok else ' '}] {label}" for label, ok, _ in options]
            def joined(chosen: list[tuple[str, str]]) -> str:
                return chosen[0][1] if len(chosen) == 1 else " ".join(f"({name}) {fb}" for name, fb in chosen)

            right = joined([(name, fb) for name, ok, fb in options if ok and fb]) or feedback
            wrong = joined([(name, fb) for name, ok, fb in options if not ok and fb])
            if right:
                lines.append(f"{self.key('feedback_correct')}: {right}")
            if wrong:
                lines.append(f"{self.key('feedback_incorrect')}: {wrong}")
            self.report.count(kind)
            out.append(self.directive(kind, "\n".join(lines)))
        return "\n\n".join(out)


    def game(self, idev: Idevice) -> str:
        """The games of eXeLearning keep their data as JSON in a hidden `<div>`."""
        html_text = "\n".join(_all_html(idev))
        found = GAME_DATA.search(html_text)
        try:
            data = json.loads(html.unescape(found.group(1))) if found else {}
        except ValueError:
            data = {}
        if not data:
            self.report.unmapped[idev.kind] = self.report.unmapped.get(idev.kind, 0) + 1
            return self.html_to_md(html_text)
        dom = parse_html(html_text)
        texts: dict[str, str] = {}
        instructions: list[str] = []

        def scan(node: Dom) -> None:
            for child in node.children:
                if not isinstance(child, Dom):
                    continue
                names = " ".join(child.classes())
                if "LinkTextsPoints" in names:
                    texts[child.attrs.get("data-id", "")] = self.html_to_md_children(child)
                elif names.endswith("-instructions") or "-instructions " in names:
                    instructions.append(squash(plain(child)))  # the notice that our interactives bring themselves
                else:
                    scan(child)

        scan(dom)
        self.report.drop(idev.kind, " ".join(instructions))
        if idev.kind == "mapa-activity":
            return self.map(data, texts)
        cards = data.get("cardsGame") or []
        parts = []
        for n, card in enumerate(cards, 1):
            front, back = squash(self.rich(card.get("eText")).replace("\n", " ")), self.rich(card.get("eTextBk"))
            images = [self.asset(card.get(k) or "") for k in ("url", "urlBk")]
            if idev.kind == "flipcards-activity":
                pictures = [f"![{squash(card.get(alt) or '')}]({path})"
                            for path, alt in zip(images, ("alt", "altBk"), strict=True) if path]
                body = "\n\n".join(x for x in (back, *pictures) if x)
                parts.append(f"#### {front or squash(card.get('alt') or '') or n}\n{body}".rstrip())
            else:
                parts.append(f"- {front or squash(card.get('alt') or '') or n} :: {back or squash(card.get('altBk') or '') or n}")
        kind = CARD_GAMES[idev.kind]
        self.report.count(kind)
        if kind == "match":
            stem = squash(self.html_to_md(str(data.get("instructions") or "")).replace("\n", " "))
            self.source_words += words_of(plain(parse_html(str(data.get("instructions") or ""))))
            return self.directive(kind, "\n".join([f"{self.key('question')}: {stem}", *parts]))
        return self.directive(kind, "\n".join(parts))


    def map(self, data: dict, texts: dict[str, str]) -> str:
        image = self.asset(str(data.get("url") or ""))
        lines = [f"{self.key('image')}: {image or squash(str(data.get('altImage') or ''))}"]
        empty = 0
        for point in data.get("points") or []:
            linked = texts.get(str(point.get("id") or ""), "")
            self.source_words += words_of(_bare(linked))
            parts = [linked]
            parts += [self.rich(point.get(k)) for k in ("eText", "footer", "question")]
            parts += [self.rich(slide.get(k)) for slide in point.get("slides") or [] for k in ("title", "footer")]
            body = "\n\n".join(dict.fromkeys(x for x in parts if x))
            pictures = [self.asset(str(x.get("url") or "")) for x in point.get("slides") or []] + [self.asset(str(point.get("url") or ""))]
            body = "\n\n".join([body, *(f"![]({p})" for p in dict.fromkeys(p for p in pictures if p))]).strip()
            if not body:
                empty += 1
            if any(sub.get("eText") or sub.get("url") or sub.get("footer") for sub in (point.get("map") or {}).get("pts") or []):
                self.report.note("map_nested")
            lines += [f"#### {squash(str(point.get('title') or '')) or len(lines)}", body,
                      f"{self.key('position')}: {round(float(point.get('x') or 0) * 100)},{round(float(point.get('y') or 0) * 100)}"]
        if empty:
            self.report.note("map_point_empty", count=empty)
        self.report.count("labelled-graphic")
        return self.directive("labelled-graphic", "\n".join(x for x in lines if x != ""))


# ── Conversion of a package ─────────────────────────────────────────────────────────────────────

def convert(path: Path, media_dir: Path, media_rel: str, rules: list[dict], language: str,
            forbidden: dict | None = None) -> tuple[str, Report]:
    """The Markdown of a package, with its images in `media_dir`, and the report of what was done. `forbidden` is
    `rules › forbidden`: the report names the embedded content on those hosts and counts those terms."""
    package = read(path)
    forbidden = forbidden or {}
    hosts = [str(h).strip().lower().lstrip(".") for h in forbidden.get("hosts") or []]
    conv = Converter(package, media_dir, media_rel, rules, language, hosts)
    out = [f"# {package.title}" if package.title else ""]

    def walk(page: Page, depth: int) -> None:
        conv.report.pages += 1
        blocks = [b for b in (conv.idevice(i) for i in page.idevices) if b.strip()]
        start = len(out)
        if depth:
            out.append("#" * min(depth + 1, 6) + f" {page.title}")
        out.extend(blocks)
        for child in page.children:
            walk(child, depth + 1)
        if depth and len(out) == start + 1:
            out.pop()
            conv.report.empty_pages.append(page.title)

    walk(package.root, 0)
    text = "\n\n".join(x for x in out if x).strip() + "\n"
    report = conv.report
    wanted = {}
    for w in conv.source_words:
        wanted[w] = wanted.get(w, 0) + 1
    bare = _bare(text)
    for w in words_of(bare):
        if wanted.get(w):
            wanted[w] -= 1
    for term in (str(x).strip() for x in forbidden.get("terms") or []):
        found = len(re.findall(rf"(?<!\w){re.escape(term)}(?!\w)", bare, re.I)) if term else 0
        if found:
            report.forbidden_terms[term] = found
    report.missing_words = sorted(w for w, n in wanted.items() if n > 0)
    report.words_source = len(conv.source_words)
    report.words_output = len(words_of(bare))
    return text, report


def summary_notes(report: Report) -> list[tuple[str, dict]]:
    """What a person should look at, as keys of the messages of the brief."""
    notes = []
    if report.missing_words:
        notes.append(("exe_missing_words", {"count": len(report.missing_words)}))
    if report.unmapped:
        notes.append(("exe_unmapped", {"kinds": ", ".join(sorted(report.unmapped))}))
    if report.missing_images:
        notes.append(("exe_missing_images", {"count": len(report.missing_images)}))
    return notes


def render_report(reports: list[tuple[str, Report]], lang: str) -> str:
    from coursekit import i18n

    def say(key: str, **values: object) -> str:
        return i18n.t_in(lang, "exelearning", key, **values)

    out = [say("report_title"), "", say("report_intro"), ""]
    for source, r in reports:
        out += [f"## {source}", "", say("report_summary", title=r.title, pages=r.pages, source=r.words_source, output=r.words_output,
                                         images=r.images), ""]
        if r.counts:
            out += [say("report_directives", items=", ".join(f"{k} {v}" for k, v in sorted(r.counts.items()))), ""]
        if r.questions:
            out += [say("report_questions", count=r.questions), ""]
        if r.dropped:
            out += [say("report_dropped")]
            for kind, texts in sorted(r.dropped.items()):
                total = sum(texts.values())
                examples = "; ".join(f"“{x}” ×{n}" for x, n in sorted(texts.items(), key=lambda kv: -kv[1])[:4] if x)
                out.append(f"- `{kind}` ×{total}" + (f": {examples}" if examples else ""))
            out.append("")
        if r.unmapped:
            out += [say("report_unmapped"), *[f"- `{k}` ×{n}" for k, n in sorted(r.unmapped.items())], ""]
        if r.embeds:
            hosts: dict[str, int] = {}
            for kind, _, host in r.embeds:
                hosts[f"{kind} · {host or '—'}"] = hosts.get(f"{kind} · {host or '—'}", 0) + 1
            out += [say("report_embeds"), *[f"- {k} ×{n}" for k, n in sorted(hosts.items())], ""]
        if r.forbidden_embeds:
            out += [say("report_forbidden_embeds", count=len(r.forbidden_embeds)), *[f"- {a}" for a in r.forbidden_embeds[:20]], ""]
        if r.forbidden_terms:
            out += [say("report_forbidden_terms", terms=", ".join(f"“{k}” ×{v}" for k, v in sorted(r.forbidden_terms.items()))), ""]
        if r.empty_pages:
            out += [say("report_empty_pages", pages=", ".join(r.empty_pages)), ""]
        if r.missing_images:
            out += [say("report_missing_images", files=", ".join(sorted(set(r.missing_images))[:10])), ""]
        grouped: dict[str, list[dict]] = {}
        for key, values in r.notes:
            grouped.setdefault(key, []).append(values)
        for key, items in grouped.items():
            if "count" in items[0]:
                out += [say(f"note_{key}", count=sum(i["count"] for i in items), kind=items[0].get("kind", "")), ""]
            else:
                out += [say(f"note_{key}", **items[0]), ""]
        out += [say("report_fidelity_ok") if not r.missing_words else say("report_fidelity", words=", ".join(r.missing_words[:30])), ""]
    return "\n".join(out)
