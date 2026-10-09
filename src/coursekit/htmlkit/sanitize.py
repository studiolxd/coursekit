"""Allow-list sanitizer for the HTML fragments of the content: what the authors write reaches the package, never a script."""

from __future__ import annotations

import re
from html import escape
from html.parser import HTMLParser

ALLOWED_TAGS = {
    "p", "br", "hr", "strong", "em", "b", "i", "u", "s", "del", "ins", "mark", "small", "sub", "sup", "code", "kbd", "pre", "span",
    "a", "ul", "ol", "li", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "table", "thead", "tbody", "tfoot", "tr", "th", "td",
    "caption", "img", "figure", "figcaption", "div",
}
DROP_WITH_CONTENT = {"script", "style", "iframe", "object", "embed", "template", "noscript"}
VOID = {"br", "hr", "img"}
ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "width", "height"},
    "th": {"colspan", "rowspan", "scope"},
    "td": {"colspan", "rowspan"},
    "code": {"class"},
    "pre": {"class"},
    "*": {"lang"},
}
SAFE_URL = re.compile(r"^(?:https?:|mailto:|#|/|\.{0,2}/|[A-Za-z0-9_.~%-]+(?:/|$))", re.I)
SAFE_CLASS = re.compile(r"^language-[a-z0-9+#-]+$", re.I)


class _Cleaner(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = 0
        self.open: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.skip or tag in DROP_WITH_CONTENT:
            self.skip += 1 if tag in DROP_WITH_CONTENT or self.skip else 0
            return
        if tag not in ALLOWED_TAGS:
            return
        kept = []
        for name, value in attrs:
            value = value or ""
            if name not in ATTRIBUTES.get(tag, set()) | ATTRIBUTES["*"]:
                continue
            if name in ("href", "src") and not SAFE_URL.match(value.strip()):
                continue
            if name == "class" and not SAFE_CLASS.match(value):
                continue
            kept.append(f' {name}="{escape(value, quote=True)}"')
        if tag == "a" and any(a.startswith(" href=") for a in kept):
            kept.append(' rel="noopener noreferrer"')
        self.out.append(f"<{tag}{''.join(kept)}>")
        if tag not in VOID:
            self.open.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in DROP_WITH_CONTENT:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip or tag not in ALLOWED_TAGS or tag in VOID:
            return
        if tag in self.open:
            while self.open:
                last = self.open.pop()
                self.out.append(f"</{last}>")
                if last == tag:
                    break

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.out.append(escape(data, quote=False))

    def close(self) -> None:
        super().close()
        while self.open:
            self.out.append(f"</{self.open.pop()}>")


def clean(fragment: str | None) -> str:
    """The fragment with only allowed tags and attributes, and every tag closed."""
    cleaner = _Cleaner()
    cleaner.feed(fragment or "")
    cleaner.close()
    return "".join(cleaner.out)


def unwrap(fragment: str | None) -> str:
    """An inline fragment (`<p>text</p>` as the plan stores titles and captions) without its paragraph."""
    text = clean(fragment).strip()
    match = re.fullmatch(r"<p>(.*)</p>", text, re.S)
    return match.group(1) if match and "<p>" not in match.group(1) else text
