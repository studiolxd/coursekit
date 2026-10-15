"""A synthetic eXeLearning package (`.elp`, contentv3.xml) with invented content, for the tests of the import."""

from __future__ import annotations

import json
import struct
import urllib.parse
import zipfile
import zlib
from pathlib import Path
from xml.sax.saxutils import quoteattr

NS = "http://www.exelearning.org/content/v0.3"


def key(name: str) -> str:
    return f'<string role="key" value={quoteattr(name)}></string>'


def u(value: str) -> str:
    return f"<unicode value={quoteattr(value)}></unicode>"


def listing(items: list[str]) -> str:
    return "<list>" + "".join(items) + "</list>"


def dictionary(**pairs: str) -> str:
    return "<dictionary>" + "".join(key(k) + v for k, v in pairs.items()) + "</dictionary>"


def instance(cls: str, **pairs: str) -> str:
    return f'<instance class="exe.engine.{cls}">{dictionary(**pairs)}</instance>'


def text_field(html: str, name: str = "") -> str:
    return instance("field.TextAreaField", _name=u(name), content_w_resourcePaths=u(html))


def js_text(html: str) -> str:
    return instance("jsidevice.JsIdevice", _iDeviceDir=u("text"), _title=u("Text"), fields=listing([text_field(html)]))


def generic(title: str, label: str, html: str) -> str:
    return instance("genericidevice.GenericIdevice", _title=u(title), fields=listing([text_field(html, label)]))


def js_game(kind: str, html: str) -> str:
    return instance("jsidevice.JsIdevice", _iDeviceDir=u(kind), _title=u(kind), fields=listing([text_field(html)]))


def game_html(prefix: str, instructions: str, data: dict, extra: str = "") -> str:
    return (f'<div class="{prefix}-IDevice"><div class="{prefix}-instructions gameQP-instructions"><p>{instructions}</p></div>'
            f'<div class="{prefix}-DataGame js-hidden">{json.dumps(data)}</div>{extra}'
            f'<div class="{prefix}-bns js-hidden">Your browser is not compatible.</div></div>')


def multichoice(title: str, stem: str, options: list[tuple[str, bool, str]]) -> str:
    opts = [instance("field.QuizOptionField", answerTextArea=text_field(a), feedbackTextArea=text_field(f), isCorrect=u("1" if ok else "0"))
            for a, ok, f in options]
    question = instance("field.QuizQuestionField", questionTextArea=text_field(stem), feedbackTextArea=text_field(""),
                        options=listing(opts))
    return instance("multichoiceidevice.MultichoiceIdevice", _title=u(title), questions=listing([question]))


def true_false(title: str, instructions: str, stem: str, truth: bool, feedback: str) -> str:
    question = instance("truefalseidevice.TrueFalseQuestion", questionTextArea=text_field(stem), feedbackTextArea=text_field(feedback),
                        isCorrect=u("1" if truth else "0"))
    return instance("truefalseidevice.TrueFalseIdevice", _title=u(title), instructionsForLearners=text_field(instructions),
                    questions=listing([question]))


def node(title: str, idevices: list[str] | None = None, children: list[str] | None = None) -> str:
    return instance("node.Node", _title=u(title), idevices=listing(idevices or []), children=listing(children or []))


def png() -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    raw = b"\x00\xff\x00\x00"
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def package(path: Path, title: str, pages: list[str], media: dict[str, bytes] | None = None, language: str = "es") -> Path:
    root = node(title, children=pages)
    xml = (f'<?xml version="1.0" encoding="utf-8"?><instance xmlns="{NS}" reference="1" version="0.3" '
           f'class="exe.engine.package.Package">'
           + dictionary(_title=u(title), _lang=u(language), _author=u(""), _nodeIdDict=dictionary(**{"0": root})) + "</instance>")
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("contentv3.xml", xml.replace("<dictionary><string role=\"key\" value=\"0\"></string>",
                                                       "<dictionary><unicode role=\"key\" value=\"0\"></unicode>"))
        for name, data in (media or {}).items():
            archive.writestr(name, data)
    return path


def sample(path: Path, title: str = "Strong passwords") -> Path:
    """Two pages with text, a template's boxes, effects, a game, a map and the three kinds of questions."""
    fx = ('<div class="exe-fx exe-accordion"><h2>Length</h2><p>Longer is better.</p><h2>Variety</h2><p>Mix kinds of characters.</p></div>'
          '<div class="exe-fx exe-tabs"><h2>Keyboard</h2><p>Keyboard content.</p><h2>Phone</h2><p>Phone content.</p></div>'
          '<div class="exe-fx exe-carousel"><h2></h2><p>First slide text.</p><h2></h2><p>Second slide text.</p></div>')
    back = urllib.parse.quote("A long password made of words.")
    cards = {"typeGame": "FlipCards", "cardsGame": [{"eText": urllib.parse.quote("Passphrase"), "eTextBk": back, "url": "", "urlBk": ""}]}
    match = {"typeGame": "Relaciona", "instructions": "<p>Match each term.</p>",
             "cardsGame": [{"eText": "Manager", "eTextBk": urllib.parse.quote("Stores your passwords"), "url": "", "urlBk": ""}]}
    points = {"typeGame": "Mapa", "url": "resources/map.png",
              "points": [{"id": "p1", "title": "1", "x": 0.25, "y": 0.5, "eText": "", "footer": "", "question": "", "slides": [{}],
                          "map": {"pts": [{}]}}]}
    linked = '<div class="js-hidden mapa-LinkTextsPoints" data-id="p1"><p>Point one explains the length.</p></div>'
    page1 = node("Introduction", [
        js_text('<p>Welcome to <strong>strong</strong> passwords.</p><img src="resources/photo.png" alt="A padlock" />'
                '<iframe src="https://www.youtube.com/embed/abc"></iframe>'),
        generic("Tpl_Click", "Instruction", "Click on the arrows to see the content."),
        generic("Tpl_Warning", "Attention", "<p>Never reuse a password.</p>"),
        generic("Tpl_Concept", "Definition", "<p>A passphrase is a long password.</p>"),
        generic("Tpl_Slider", "Slider", fx),
    ])
    page2 = node("Practice", [
        js_game("flipcards-activity", game_html("flipcards", "Click the cards.", cards)),
        js_game("relaciona-activity", game_html("relaciona", "Match the terms.", match)),
        js_game("mapa-activity", game_html("mapa", "Click the areas.", points, linked)),
        multichoice("Now you", "<p>Which is stronger?</p>",
                    [("1234", False, "<p>Too short.</p>"), ("three long words", True, "<p>Length wins.</p>")]),
        true_false("Activities", "<p>True or false</p>", "<p>Reusing a password is safe.</p>", False,
                   "<p>Each service needs its own.</p>"),
    ])
    return package(path, title, [page1, node("Empty cover"), page2], {"photo.png": png(), "map.png": png()})
