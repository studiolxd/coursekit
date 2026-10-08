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
