"""Messages for people (CLI output, errors, help) in the user's language (es, en).

Each module has a catalog, `lang/messages/<module>.yaml`: every key holds its text in both languages.

    created_env:
      es: "ok: .env creado"
      en: "ok: created .env"

and is used as `t("setup", "created_env")`. Texts with values are formatted with `str.format`
(`{path}`; a literal brace is written `{{`); texts without values are returned as they are.
A text that depends on a count has two keys, `units_one` (n is 1) and `units`, and is used as
`tn("status", "units", n)`; `t_in(lang, ...)` gives a text in a given language instead of the current one.

The language is, in this order: the one forced with `use()` (the `init` wizard, once the person has
chosen), `COURSEKIT_LANG` (.env, per person), `ui_language` of the project found from the current
folder, the language of the system, and English.
"""

from __future__ import annotations

import os
from functools import cache
from importlib import resources

import yaml

from coursekit import project as projectmod

LANGUAGES = ("es", "en")
_forced: str | None = None


def use(language: str | None) -> None:
    """Force the language of the messages (None: back to the automatic choice)."""
    global _forced
    _forced = _normalize(language)


def _normalize(language: str | None) -> str | None:
    code = (language or "").strip().replace("-", "_").split("_")[0].lower()
    return code if code in LANGUAGES else None


@cache
def _read_project_language(path: str, mtime_ns: int) -> str | None:  # mtime_ns: invalidates the cache when the file changes
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except (OSError, yaml.YAMLError):
        return None
    return _normalize(str(data.get("ui_language") or data.get("content_language") or ""))


def _project_language() -> str | None:
    try:
        file = projectmod.find_project().file
        return _read_project_language(str(file), file.stat().st_mtime_ns)
    except (projectmod.ProjectNotFound, OSError):
        return None


def _system_language() -> str | None:
    for key in ("LC_ALL", "LC_MESSAGES", "LANG"):
        code = _normalize(os.environ.get(key))
        if code:
            return code
    return None


def language() -> str:
    for candidate in (_forced, _normalize(os.environ.get("COURSEKIT_LANG")), _project_language(), _system_language()):
        if candidate:
            return candidate
    return "en"


@cache
def catalog(module: str) -> dict[str, dict[str, str]]:
    text = resources.files("coursekit.lang.messages").joinpath(f"{module}.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text) or {}


def t_in(lang: str, module: str, key: str, /, **values: object) -> str:
    """The text `key` of the catalog of `module` in the language `lang` (for files written in the language of the content)."""
    text = catalog(module)[key][_normalize(lang) or "en"]
    return text.format(**values) if values else text


def t(module: str, key: str, /, **values: object) -> str:
    """The text `key` of the catalog of `module` in the current language."""
    return t_in(language(), module, key, **values)


def tn(module: str, key: str, n: int, /, **values: object) -> str:
    """A text that depends on a count: `key_one` when n is 1, else `key`; `{n}` is always available."""
    return t(module, f"{key}_one" if n == 1 else key, n=n, **values)
