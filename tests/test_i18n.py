import ast
import string
from importlib import resources
from pathlib import Path

import pytest

from coursekit import i18n

SRC = Path(__file__).resolve().parent.parent / "src" / "coursekit"
MODULES = sorted(p.stem for p in (SRC / "lang" / "messages").glob("*.yaml"))


def fields(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


@pytest.mark.parametrize("module", MODULES)
def test_every_message_exists_in_both_languages_with_the_same_values(module):
    for key, texts in i18n.catalog(module).items():
        assert set(texts) == set(i18n.LANGUAGES), f"{module}.{key}"
        assert all(isinstance(t, str) and t.strip() for t in texts.values()), f"{module}.{key}"
        assert fields(texts["es"]) == fields(texts["en"]), f"{module}.{key}: different {{values}}"


def test_every_message_used_in_the_code_exists():
    used = []
    for path in SRC.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in ("t", "tn")
                and len(node.args) >= 2
                and all(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in node.args[:2])
            ):
                plural = node.func.id == "tn"
                given = {k.arg for k in node.keywords} | ({"n"} if plural else set())
                used.append((path.name, node.args[0].value, node.args[1].value, given, plural))
    assert used
    for file, module, key, given, plural in used:
        assert module in MODULES, f"{file}: no catalog {module}"
        for name in (key, f"{key}_one") if plural else (key,):
            assert name in i18n.catalog(module), f"{file}: {module}.{name} is not in the catalog"
            needed = fields(i18n.catalog(module)[name]["en"])
            assert needed <= given or None in given, f"{file}: {module}.{name} needs {needed - given}"


def test_plural_texts(monkeypatch):
    i18n.use("es")
    assert i18n.tn("status", "units", 1) == "1 unidad"
    assert i18n.tn("status", "units", 3) == "3 unidades"
    i18n.use("en")
    assert i18n.tn("status", "units", 1) == "1 unit"
    assert i18n.t_in("es", "status", "units", n=2) == "2 unidades"
    i18n.use(None)


def test_catalogs_are_unused_free_of_emojis():
    for module in MODULES:
        text = resources.files("coursekit.lang.messages").joinpath(f"{module}.yaml").read_text(encoding="utf-8")
        assert not [c for c in text if ord(c) > 0x2FFF], module


def test_language_order(monkeypatch, tmp_path):
    monkeypatch.delenv("COURSEKIT_PROJECT", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LANG", "es_ES.UTF-8")
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.delenv("COURSEKIT_LANG", raising=False)
    i18n.use(None)
    assert i18n.language() == "es"  # the system
    (tmp_path / "project.yaml").write_text("ui_language: en\n", encoding="utf-8")
    assert i18n.language() == "en"  # the project beats the system
    monkeypatch.setenv("COURSEKIT_LANG", "es")
    assert i18n.language() == "es"  # the person beats the project
    i18n.use("en")
    assert i18n.language() == "en"  # forced beats everything
    i18n.use(None)
