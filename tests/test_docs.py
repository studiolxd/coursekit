import argparse
import re
from pathlib import Path

import pytest

from coursekit.cli import build_parser

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
LANGS = ("en", "es")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FENCE = re.compile(r"^```.*?^```", re.M | re.S)


def prose(text: str) -> str:
    """The text without fenced code blocks (their `# comments` are not headings and their brackets are not links)."""
    return FENCE.sub("", text)


def doc_files(lang: str) -> list[str]:
    return sorted(p.name for p in (DOCS / lang).glob("*.md"))


def cli_surface() -> tuple[set[str], set[str]]:
    """Every command (with its sub-actions) and every option string of the CLI."""
    commands, options = set(), set()

    def walk(parser: argparse.ArgumentParser, prefix: str) -> None:
        for option in parser._option_string_actions:
            if option not in ("-h", "--help", "--version"):
                options.add(option)
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for name, sub in action.choices.items():
                    commands.add(f"{prefix} {name}".strip())
                    walk(sub, f"{prefix} {name}".strip())

    walk(build_parser(), "")
    return commands, options


def test_both_languages_have_the_same_files():
    assert doc_files("en"), "docs/en is empty"
    assert doc_files("en") == doc_files("es")
    assert "index.md" in doc_files("en") and "03-commands.md" in doc_files("en")


def test_readmes_exist_and_point_to_each_other():
    assert "README.es.md" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "README.md" in (ROOT / "README.es.md").read_text(encoding="utf-8")


def heading_slugs(text: str) -> set[str]:
    """The anchors GitHub gives to the headings: lower case, punctuation removed, spaces as hyphens, repeated ones numbered."""
    found: dict[str, int] = {}
    slugs = set()
    for match in re.finditer(r"^#{1,6} +(.+?) *$", prose(text), re.M):
        slug = re.sub(r"[^\w\- ]", "", match.group(1).lower()).replace(" ", "-")
        count = found.get(slug, 0)
        found[slug] = count + 1
        slugs.add(slug if count == 0 else f"{slug}-{count}")
    return slugs


ALL_DOCS = sorted(DOCS.glob("*/*.md")) + [ROOT / "README.md", ROOT / "README.es.md"]


@pytest.mark.parametrize("path", ALL_DOCS, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_links_resolve_and_no_emojis(path):
    text = path.read_text(encoding="utf-8")
    for target in LINK.findall(prose(text)):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        name, _, anchor = target.partition("#")
        destination = path.parent / name if name else path
        assert destination.exists(), f"{path.name}: broken link {target}"
        if anchor and destination.suffix == ".md":
            assert anchor in heading_slugs(destination.read_text(encoding="utf-8")), f"{path.name}: no heading for the anchor {target}"
    allowed = set("★✔✘·—‹›")
    emojis = [c for c in text if ord(c) >= 0x1F000 or (0x2600 <= ord(c) <= 0x27BF and c not in allowed)]
    assert not emojis, f"{path.name}: {emojis}"


def test_the_headings_of_both_languages_have_the_same_shape():
    for name in doc_files("en"):
        shapes = []
        for lang in LANGS:
            text = prose((DOCS / lang / name).read_text(encoding="utf-8"))
            shapes.append([len(m.group(1)) for m in re.finditer(r"^(#{1,6}) ", text, re.M)])
        assert shapes[0] == shapes[1], f"{name}: the English and Spanish headings differ in number or level"


def test_the_contributor_guides_have_the_same_shape_and_point_to_each_other():
    root = DOCS.parent
    texts = {name: (root / name).read_text(encoding="utf-8") for name in ("CONTRIBUTING.md", "CONTRIBUTING.es.md")}
    shapes = [[len(m.group(1)) for m in re.finditer(r"^(#{1,6}) ", prose(text), re.M)] for text in texts.values()]
    assert shapes[0] == shapes[1], "CONTRIBUTING.md and CONTRIBUTING.es.md differ in number or level of headings"
    assert "CONTRIBUTING.es.md" in texts["CONTRIBUTING.md"] and "CONTRIBUTING.md" in texts["CONTRIBUTING.es.md"]


@pytest.mark.parametrize("lang", LANGS)
def test_the_command_reference_covers_every_command_and_option(lang):
    text = (DOCS / lang / "03-commands.md").read_text(encoding="utf-8")
    commands, options = cli_surface()
    missing = sorted(f"coursekit {c}" for c in commands if f"coursekit {c}" not in text)
    assert not missing, f"docs/{lang}/03-commands.md does not mention: {missing}"
    missing = sorted(o for o in options if not re.search(rf"(?<![\w-]){re.escape(o)}(?![\w-])", text))
    assert not missing, f"docs/{lang}/03-commands.md does not mention the options: {missing}"
