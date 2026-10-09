"""The words of the content format per language: resource types and keys of the directives have an id and a word per language."""

import json
from pathlib import Path

import yaml

from coursekit import agents, config, lang
from coursekit.cli import main
from coursekit.project import find_project
from tests.test_assemble import course  # noqa: F401 — the approved Spanish sample course
from tests.test_course_flow import FIXTURES, write_course_rules


def test_both_languages_define_the_same_ids():
    es, en = lang.tokens("es"), lang.tokens("en")
    assert set(es["media_types"]) == set(en["media_types"])
    assert set(es["directive_keys"]) == set(en["directive_keys"])
    assert set(es["directive_words"]) == set(en["directive_words"])


def test_the_configuration_uses_the_ids(tmp_path, monkeypatch):
    monkeypatch.delenv("COURSEKIT_PROJECT", raising=False)
    assert main(["init", str(tmp_path / "p"), "--yes", "--no-git"]) == 0
    project = find_project(tmp_path / "p")
    ids = set(lang.tokens("es")["media_types"])
    assert set(config.effective("rules", project).get("content", "placeholder_types")) == ids
    media = config.effective("media", project).value
    assert set(media["types"]) <= ids and set(media["uses_theme"]) <= ids
    assert "terminal_demo" in media["types"] and "Imagen" not in media["types"]


def test_a_type_is_found_by_the_word_of_its_language():
    es, en = lang.tokens("es"), lang.tokens("en")
    assert lang.media_type_id(es, "Infografía") == "infographic" and lang.media_type_id(en, "Infographic") == "infographic"
    assert lang.media_type_id(en, "  infographic ") == "infographic"  # case and spaces do not matter
    assert lang.media_type_id(en, "Infografía") is None and lang.media_type_id(es, "Image") is None


def test_keys_of_the_other_language_are_recognised():
    es, en = lang.tokens("es"), lang.tokens("en")
    assert lang.foreign_key(en, "pregunta") == "es" and lang.foreign_key(es, "question") == "en"
    assert lang.foreign_key(en, "question") is None and lang.foreign_key(en, "feedback") is None
    assert lang.foreign_key(en, "anything-else") is None
    assert lang.directive_key(en, "objective") == "objective" and lang.directive_key(es, "objective") == "objetivo"


def english_course(tmp_path, monkeypatch):
    monkeypatch.delenv("COURSEKIT_PROJECT", raising=False)
    root = tmp_path / "en"
    assert main(["init", str(root), "--yes", "--no-git", "--language", "en"]) == 0
    monkeypatch.chdir(root)
    (root / ".env").write_text("COURSEKIT_USER_NAME=Ann\nCOURSEKIT_USER_EMAIL=ann@example.com\n", encoding="utf-8")
    assert main(["new", "Strong passwords", "1", "--code", "EN1"]) == 0
    course_dir = root / "courses" / "EN1"
    write_course_rules(course_dir)
    matrix = json.loads((FIXTURES / "matrix.json").read_text(encoding="utf-8"))
    names = {"Introducción y objetivos": "Introduction and objectives", "Resumen": "Summary"}
    for node in matrix["nodos"]:
        node["titulo"] = names.get(node["titulo"], node["titulo"])
    (course_dir / "design" / "matrix.json").write_text(json.dumps(matrix), encoding="utf-8")
    assert main(["approve", "design", "EN1", "--yes", "--no-commit"]) == 0
    return course_dir


QUESTIONS = """
:::single-choice
objective: U1.1
question: Which is stronger?
- [ ] 1234
- [x] three-long-words
feedback-correct: Length wins.
feedback-incorrect: Review section 2.
:::

:::true-false
question: Reusing a password is fine.
answer: false
:::

:::fill-in-the-blank
question: A strong password is {long}.
:::

:::short-answer
question: Name a password manager.
answers: one | another
:::

:::pasapalabra
- A (starts): Opposite of weak :: Strong
- B (contains): Used to log in :: Username
:::

:::note
title: Remember
Use a manager.
:::
"""


def plan_bricks(course_dir, capsys):
    capsys.readouterr()
    code = main(["assemble", "plan", "EN1", "--unit", "1"])
    out = capsys.readouterr()
    plan = json.loads((course_dir / "assembly" / "unit-01.plan.json").read_text(encoding="utf-8")) if code == 0 else None
    return code, out, plan


def test_an_english_course_is_written_with_english_words(tmp_path, monkeypatch, capsys):
    course_dir = english_course(tmp_path, monkeypatch)
    path = course_dir / "content" / "unit-01" / "content.md"
    path.write_text(path.read_text(encoding="utf-8") + QUESTIONS, encoding="utf-8")
    code, out, plan = plan_bricks(course_dir, capsys)
    assert code == 0, out.out
    bricks = [b for lesson in plan["lessons"] for b in lesson["bricks"]]
    single = next(b for b in bricks if b["type"] == "SINGLE_CHOICE")
    assert single["data"]["content"]["question"] == "<p>Which is stronger?</p>"
    assert single["data"]["content"]["feedback_correct"] == "<p>Length wins.</p>"
    assert single["meta"]["objective"] == "U1.1"
    assert next(b for b in bricks if b["type"] == "TRUE_FALSE")["data"]["properties"]["correctAnswer"] == "false"
    assert [i["text"] for i in next(b for b in bricks if b["type"] == "SHORT_ANSWER")["data"]["items"]] == ["one", "another"]
    pasapalabra = next(b for b in bricks if b["type"] == "PASAPALABRA")["data"]["items"]
    assert [i["mode"] for i in pasapalabra] == ["starts", "contains"]
    assert next(b for b in bricks if b["type"] == "NOTE" and "Remember" in json.dumps(b))["data"]["content"]["title"] == "<p>Remember</p>"


def test_spanish_words_in_an_english_course_are_an_error_that_says_what_to_use(tmp_path, monkeypatch, capsys):
    course_dir = english_course(tmp_path, monkeypatch)
    path = course_dir / "content" / "unit-01" / "content.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n:::single-choice\npregunta: ¿Cuál?\n- [x] a\n- [ ] b\n:::\n", encoding="utf-8")
    code, out, _ = plan_bricks(course_dir, capsys)
    assert code == 1
    assert "the key 'pregunta:' belongs to the language 'es'" in out.out + out.err
    assert "question" in out.out + out.err


def test_true_false_needs_the_words_of_the_language(tmp_path, monkeypatch, capsys):
    course_dir = english_course(tmp_path, monkeypatch)
    path = course_dir / "content" / "unit-01" / "content.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n:::true-false\nquestion: Q?\nanswer: verdadero\n:::\n", encoding="utf-8")
    code, out, _ = plan_bricks(course_dir, capsys)
    assert code == 1 and "needs 'answer: true|false'" in out.out + out.err


def test_a_placeholder_type_of_the_other_language_is_reported_with_the_valid_ones(tmp_path, monkeypatch, capsys):
    course_dir = english_course(tmp_path, monkeypatch)
    path = course_dir / "content" / "unit-01" / "content.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n> **[MEDIA ASSET — Infografía]**\n> **Title:** t\n", encoding="utf-8")
    capsys.readouterr()
    assert main(["verify", "EN1", "--no-update"]) == 1
    out = capsys.readouterr().out
    assert "unknown or not allowed placeholder type 'Infografía' (use: Image, Video, Animated GIF, Infographic" in out


def test_the_manifest_keeps_the_type_id_in_both_languages(course, tmp_path, monkeypatch, capsys):  # noqa: F811
    assert main(["media", "extract", "PWD"]) == 0
    manifest = yaml.safe_load((course / "media" / "manifest.yaml").read_text(encoding="utf-8"))["assets"]
    assert manifest[0]["type"] == "infographic"  # `Infografía` in the Spanish content
    course_dir = english_course(tmp_path, monkeypatch)
    path = course_dir / "content" / "unit-01" / "content.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n> **[MEDIA ASSET — Infographic]**\n> **Title:** t\n", encoding="utf-8")
    assert main(["media", "extract", "EN1"]) == 0
    manifest = yaml.safe_load((course_dir / "media" / "manifest.yaml").read_text(encoding="utf-8"))["assets"]
    assert manifest[0]["type"] == "infographic"


def test_the_format_reference_speaks_the_words_of_the_course(tmp_path, monkeypatch):
    monkeypatch.delenv("COURSEKIT_PROJECT", raising=False)
    for code, key, word, kind in (("en", "question: <question>", "answer: true|false", "`Image` (image)"),
                                  ("es", "pregunta: <question>", "respuesta: verdadero|falso", "`Imagen` (image)")):
        root = tmp_path / code
        assert main(["init", str(root), "--yes", "--no-git", "--language", code]) == 0
        fmt = (root / ".coursekit/docs/content-format.md").read_text(encoding="utf-8")
        assert key in fmt and word in fmt and kind in fmt
        assert "{{" not in fmt
        assert agents.context(find_project(root))["k_question"] == key.split(":")[0]


def test_the_defaults_are_written_in_english():
    for name in ("rules", "directives", "media"):
        text = (Path(config.__file__).parent / "defaults" / f"{name}.yaml").read_text(encoding="utf-8")
        assert not [c for c in text if c in "áéíóúñ¿¡"], f"{name}.yaml has Spanish text"
