"""Language catalogs of the content format (es, en)."""

from __future__ import annotations

from functools import cache
from importlib import resources

import yaml

LANGUAGES = ("es", "en")


@cache
def tokens(language: str = "es") -> dict:
    code = (language or "es").split("-")[0].lower()
    if code not in LANGUAGES:
        raise ValueError(f"unsupported content language {language!r} (one of: {', '.join(LANGUAGES)})")
    text = resources.files("coursekit.lang").joinpath(f"{code}.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text)


def format_number(number: int, language: str = "es") -> str:
    return f"{number:,}".replace(",", tokens(language)["thousands_separator"])


def media_type_id(tk: dict, label: str) -> str | None:
    """The id of a resource type written in the content (`Infografía`, `Infographic`), or None if the language has no such type."""
    wanted = label.strip().casefold()
    return next((type_id for type_id, written in tk["media_types"].items() if written.casefold() == wanted), None)


def directive_key(tk: dict, name: str) -> str:
    """How a key of the directives is written in the language (`question` -> `pregunta`)."""
    if name == "objective":
        return tk["question_objective_key"].rstrip(":")
    return tk["directive_keys"][name]


def directive_keys(tk: dict) -> set[str]:
    return {directive_key(tk, name) for name in (*tk["directive_keys"], "objective")}


def foreign_key(tk: dict, key: str) -> str | None:
    """The language another language's key belongs to (`pregunta` in an English course -> `es`), when it is not valid in this one."""
    if key in directive_keys(tk):
        return None
    return next((code for code in LANGUAGES if key in directive_keys(tokens(code))), None)
