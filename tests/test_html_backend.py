"""The html assembly backend: sanitizer, components, package (manifest, zip, media), the check of the words and the guards.
The bundling of the player (npm and esbuild) is replaced by a stub: nothing is ever installed by the tests."""

import json
import shutil
import zipfile
from pathlib import Path

import pytest
import yaml

from coursekit import config, directives, theme
from coursekit.cli import main
from coursekit.htmlkit import build as htmlbuild
from coursekit.htmlkit import check, manifest, render
from coursekit.htmlkit.sanitize import clean, unwrap
from coursekit.project import find_project
from tests.test_course_flow import FIXTURES, write_course_rules

UI = {"flip": "Flip", "hotspot": "Point {n}", "question": "Question {n}", "answer_true": "True", "answer_false": "False",
      "blank": "Blank {n}", "type_answer": "Type", "transcript": "Transcript"}


# ── sanitizer ────────────────────────────────────────────────────────────────────────────────


def test_the_sanitizer_keeps_formatting_and_drops_what_runs():
    dirty = ('<p onclick="x()">Hi <a href="javascript:alert(1)">bad</a> <a href="https://a.example/b">good</a>'
             '<script>alert(1)</script><img src="media/a.png" alt="A" onerror="x()"><iframe src="//evil"></iframe></p>')
    out = clean(dirty)
    assert "onclick" not in out and "javascript" not in out and "<script" not in out and "alert" not in out and "iframe" not in out
    assert '<a href="https://a.example/b" rel="noopener noreferrer">good</a>' in out and '<img src="media/a.png" alt="A">' in out
    assert "bad" in out  # the text of a removed link stays


def test_the_sanitizer_closes_tags_and_unwraps_inline_text():
    assert clean("<div><b>open") == "<div><b>open</b></div>"
    assert unwrap("<p>Title <strong>1</strong></p>") == "Title <strong>1</strong>"
    assert unwrap("<p>one</p><p>two</p>") == "<p>one</p><p>two</p>"
    assert clean('<pre class="language-python x"><code class="language-python">a &lt; b</code></pre>').count('class="language-python"') == 1


# ── components ───────────────────────────────────────────────────────────────────────────────


def brick(kind, data):
    return {"type": kind, "data": data, "meta": {}}


def lesson_html(bricks, evaluation=False):
    entry = {"key": "U1-S1", "type": "evaluation" if evaluation else "content", "title": "T", "bricks": bricks,
             "quiz": {"passingGrade": 50, "maxAttempts": 2}}
    return render.lesson(entry, UI)


def test_accordion_is_native_details_and_tabs_keep_their_titles():
    html = lesson_html([
        brick("ACCORDION", {"items": [{"title": "<p>One</p>", "content": "<p>First</p>"}]}),
        brick("TABS", {"items": [{"title": "<p>A</p>", "content": "<p>aa</p>"}, {"title": "<p>B</p>", "content": "<p>bb</p>"}]}),
    ])
    assert "<details" in html and "<summary>One</summary>" in html
    assert html.count('class="ck-panel"') == 2 and 'data-widget="tabs"' in html and "ck-panel-title" in html


def test_questions_carry_their_answers_and_their_text():
    html = lesson_html([
        brick("SINGLE_CHOICE", {"content": {"question": "<p>Which?</p>", "feedback_correct": "<p>Yes</p>"},
                                "items": [{"content": "<p>a</p>", "isCorrect": False}, {"content": "<p>b</p>", "isCorrect": True}]}),
        brick("TRUE_FALSE", {"properties": {"correctAnswer": "false"}, "content": {"question": "<p>Sure?</p>"}}),
        brick("FILL_IN_THE_BLANK", {"content": {"question": "<p>A {long/big} key</p>"}}),
        brick("SHORT_ANSWER", {"content": {"question": "<p>Name</p>"}, "items": [{"text": "x"}, {"text": "y"}]}),
        brick("ORDER_WORDS", {"content": {"question": "<p>Order</p>"}, "lines": [{"id": "l1"}],
                              "items": [{"content": "<p>one</p>", "lineId": "l1"}, {"content": "<p>two</p>", "lineId": "l1"}]}),
        brick("SORTING_GROUPS", {"content": {"question": "<p>Sort</p>"}, "groups": [{"id": "g1", "label": "<p>G</p>"}],
                                 "items": [{"content": "<p>i</p>", "groupId": "g1"}]}),
        brick("MATCH", {"content": {"question": "<p>Match</p>"}, "items": [{"left": "<p>l</p>", "right": "<p>r</p>"}]}),
        brick("SORTING", {"content": {"question": "<p>Put</p>"}, "items": [{"content": "<p>1</p>"}, {"content": "<p>2</p>"}]}),
    ])
    assert 'data-correct="1"' in html and 'data-correct="0"' in html and "ck-fb-correct" in html and "Yes" in html
    assert html.count('type="radio"') == 4 and "True" in html and "False" in html
    assert 'class="ck-blank" data-answers="long|big"' in html and "long / big" in html  # the answers are in the document
    assert 'data-answers="x|y"' in html
    assert html.index("one") < html.index("two") and "ck-words" in html
    assert 'data-group="g1"' in html and 'class="ck-right"' in html and html.count('class="ck-q"') == 8


def test_media_code_and_attachments():
    html = lesson_html([
        brick("IMAGE", {"properties": {"imagePath": "media/a.svg", "imageAlt": "Alt"}, "content": {"content": "<p>Caption</p>"}}),
        brick("VIDEO", {"properties": {"videoPath": "media/v.mp4", "subtitlesPath": "media/v.vtt"},
                        "content": {"content": "<p>Cap</p>", "transcription": "<p>Said</p>"}}),
        brick("AUDIO", {"properties": {"audioPath": "media/a.mp3"}, "content": {"transcription": "<p>Heard</p>"}}),
        brick("EMBED", {"properties": {"embedFolderPrefix": "media/sim", "embedTitle": "Sim"}}),
        brick("ATTACHMENT", {"properties": {"filePath": "media/files/x.pdf", "fileName": "x.pdf"},
                             "content": {"title": "<p>Get it</p>", "description": "<p>PDF, 2 KB</p>"}}),
        brick("CODE", {"properties": {"codeLanguage": "python"}, "content": {"content": "if a < b:\n    print('x')"}}),
    ])
    assert 'alt="Alt"' in html and "<figcaption>Caption</figcaption>" in html
    assert '<track kind="captions" src="media/v.vtt"' in html and "Said" in html and "Heard" in html
    assert '<iframe src="media/sim/index.html" title="Sim"' in html
    assert 'href="media/files/x.pdf" download="x.pdf"' in html
    assert 'class="language-python"' in html and "a &lt; b" in html


def test_labelled_graphic_without_an_image_is_a_plain_list():
    data = {"properties": {"imagePath": None}, "items": [{"x": 10, "y": 20, "title": "<p>P</p>", "content": "<p>text</p>"}]}
    assert "ck-hs-point" not in lesson_html([brick("LABELLED_GRAPHIC", data)])
    data["properties"] = {"imagePath": "media/i.svg", "imageAlt": "I"}
    html = lesson_html([brick("LABELLED_GRAPHIC", data)])
    assert 'class="ck-hs-point" style="left:10%;top:20%"' in html and 'aria-controls="U1-S1-b1-p1"' in html


def test_a_test_lesson_carries_its_quiz_settings():
    html = lesson_html([], evaluation=True)
    assert 'data-type="evaluation"' in html and "passingGrade" in html and "ck-quiz-actions" in html


def test_every_brick_of_the_registry_is_rendered_or_marked_as_not_available_yet():
    registry = config.effective("directives", None).value["directives"] if False else None
    from coursekit.util import load_yaml

    defaults = load_yaml(Path(config.__file__).parent / "defaults" / "directives.yaml")
    bricks = {d["brick"] for d in defaults["directives"].values()}
    assert bricks <= set(render.RENDERERS) | render.UNSUPPORTED, bricks - set(render.RENDERERS) - render.UNSUPPORTED
    assert not render.UNSUPPORTED & set(render.RENDERERS)
    assert registry is None and directives  # (the registry is read from the defaults, without a project)


# ── manifest ─────────────────────────────────────────────────────────────────────────────────


def test_manifests_for_both_standards():
    one = manifest.build("PWD-U01", "Title & more", ["index.html", "assets/player.js"], "scorm_1_2")
    assert "imscp_rootv1p1p2" in one and "<schemaversion>1.2</schemaversion>" in one and 'adlcp:scormtype="sco"' in one
    assert "Title &amp; more" in one and '<file href="assets/player.js"/>' in one and 'href="index.html"' in one
    two = manifest.build("PWD-U01", "T", ["index.html"], "scorm_2004")
    assert "imscp_v1p1" in two and "2004 4th Edition" in two and 'adlcp:scormType="sco"' in two


# ── a built unit ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def html_course(tmp_path, monkeypatch):
    for key in ("COURSEKIT_PROJECT", "COURSEKIT_USER_NAME", "COURSEKIT_USER_EMAIL"):
        monkeypatch.delenv(key, raising=False)
    root = tmp_path / "demo"
    assert main(["init", str(root), "--yes", "--no-git", "--backend", "html"]) == 0
    monkeypatch.chdir(root)
    (root / ".env").write_text("COURSEKIT_USER_NAME=Ana\nCOURSEKIT_USER_EMAIL=ana@example.com\n", encoding="utf-8")
    assert main(["new", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    course = root / "courses" / "PWD"
    write_course_rules(course)
    shutil.copy(FIXTURES / "matrix.json", course / "design" / "matrix.json")
    assert main(["approve", "design", "PWD", "--yes", "--no-commit"]) == 0
    unit = course / "content" / "unit-01"
    unit.joinpath("content.md").write_text((FIXTURES / "html_content.md").read_text(encoding="utf-8"), encoding="utf-8")
    unit.joinpath("assessment.md").write_text((FIXTURES / "html_assessment.md").read_text(encoding="utf-8"), encoding="utf-8")

    def stub(project, out_file, say):
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text("/* player */", encoding="utf-8")

    monkeypatch.setattr(htmlbuild, "bundle_player", stub)
    return course


def produce_image(course):
    assert main(["media", "extract", "PWD"]) == 0
    (course / "media" / "files").mkdir(parents=True, exist_ok=True)
    (course / "media" / "files" / "U1-S2-M1.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced", "--file", "media/files/U1-S2-M1.svg", "--alt", "Parts"]) == 0


def test_build_writes_the_preview_and_the_zip(html_course, capsys):
    produce_image(html_course)
    capsys.readouterr()
    assert main(["assemble", "build", "PWD", "--unit", "1", "--version", "1.0"]) == 0
    out = capsys.readouterr().out
    assert "unit 1:" in out and "package PWD-U01-v1.0-scorm12.zip" in out
    folder = html_course / "assembly" / "html" / "unit-01"
    assert {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()} == {
        "index.html", "imsmanifest.xml", "assets/styles.css", "assets/player.js", "media/U1-S2-M1.svg"}
    page = (folder / "index.html").read_text(encoding="utf-8")
    assert '<html lang="es">' in page and "Cómo es una contraseña robusta" in page and 'src="media/U1-S2-M1.svg"' in page
    assert page.count('class="ck-lesson"') == 4 and 'data-type="evaluation"' in page
    config_json = json.loads(page.split('id="ck-config">')[1].split("</script>")[0])
    assert config_json["standard"] == "1.2" and [x["key"] for x in config_json["lessons"]] == ["U1-S1", "U1-S2", "U1-S3", "U1-E1.1"]
    assert config_json["ui"]["next"] == "Siguiente"
    css = (folder / "assets" / "styles.css").read_text(encoding="utf-8")
    assert ".ck-lesson" in css and "--color-accent" in css
    with zipfile.ZipFile(html_course / "delivery" / "PWD-U01-v1.0-scorm12.zip") as zf:
        names = zf.namelist()
    assert names[0] == "imsmanifest.xml" and "index.html" in names and "media/U1-S2-M1.svg" in names


def test_the_course_moves_to_assembly_when_every_unit_is_built(html_course, capsys):
    path = html_course / "course.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("status: design_approved", "status: media", 1), encoding="utf-8")
    capsys.readouterr()
    assert main(["assemble", "build", "PWD", "--unit", "1"]) == 0
    assert "every unit is built: the course moves to assembly" in capsys.readouterr().out
    info = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert info["status"] == "assembly" and info["history"][-1]["note"] == "Every unit built"
    assert main(["assemble", "build", "PWD", "--unit", "1"]) == 0  # again: nothing more to say
    assert "moves to assembly" not in capsys.readouterr().out


def test_without_a_version_there_is_only_the_preview(html_course, capsys):
    assert main(["assemble", "build", "PWD", "--unit", "1"]) == 0
    out = capsys.readouterr().out
    assert "preview: open courses/PWD/assembly/html/unit-01/index.html" in out
    assert not (html_course / "delivery").exists() or not list((html_course / "delivery").glob("*.zip"))
    assert "not produced" in out or "warning" in out  # the image of the labelled graphic is still to be produced


def test_a_produced_asset_without_its_file_is_a_warning(html_course, capsys):
    assert main(["media", "extract", "PWD"]) == 0
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced", "--file", "media/files/missing.svg"]) == 0
    capsys.readouterr()
    assert main(["assemble", "build", "PWD", "--unit", "1"]) == 0
    assert "U1-S2-M1 is produced but its file does not exist" in capsys.readouterr().out


def test_scorm_2004_when_the_delivery_asks_for_it(html_course):
    (html_course.parent.parent / "config").mkdir(exist_ok=True)
    (html_course.parent.parent / "config" / "delivery.yaml").write_text("export:\n  standard: scorm_2004\n", encoding="utf-8")
    assert main(["assemble", "build", "PWD", "--unit", "1", "--version", "2.0"]) == 0
    folder = html_course / "assembly" / "html" / "unit-01"
    assert "2004 4th Edition" in (folder / "imsmanifest.xml").read_text(encoding="utf-8")
    assert '"standard": "2004"' in (folder / "index.html").read_text(encoding="utf-8")
    assert (html_course / "delivery" / "PWD-U01-v2.0-scorm2004.zip").exists()


def test_the_theme_and_the_project_styles_reach_the_package(html_course):
    root = html_course.parent.parent
    (root / "theme" / "maqueta.css").write_text(":root { --color-accent: #7a1fa2; }\n.ck-main { max-width: 40rem; }\n", encoding="utf-8")
    (root / "components").mkdir()
    (root / "components" / "extra.css").write_text(".ck-extra { color: red; }\n", encoding="utf-8")
    assert main(["theme", "import", str(root / "theme" / "maqueta.css")]) == 0
    assert main(["assemble", "build", "PWD", "--unit", "1"]) == 0
    css = (html_course / "assembly" / "html" / "unit-01" / "assets" / "styles.css").read_text(encoding="utf-8")
    order = [css.index(text) for text in ("--color-accent: #0a58ca", "--color-accent: #7A1FA2", "max-width: 40rem", ".ck-extra")]
    assert order == sorted(order)  # base layout, then the tokens, then the maqueta of the project, then its components


def test_a_line_the_format_does_not_render_is_reported_as_missing_words(html_course, capsys):
    path = html_course / "content" / "unit-01" / "content.md"
    text = path.read_text(encoding="utf-8").replace("pregunta: ¿Qué hace más fuerte una clave?", "¿Qué hace más fuerte una clave?")
    path.write_text(text, encoding="utf-8")
    capsys.readouterr()
    assert main(["assemble", "build", "PWD", "--unit", "1"]) == 1
    err = capsys.readouterr().err
    assert "does not contain" in err and "hace" in err and "fuerte" in err
    assert not (html_course / "delivery").exists() or not list((html_course / "delivery").glob("*.zip"))


def test_the_games_are_not_available_yet_and_verify_says_so(html_course, capsys):
    path = html_course / "content" / "unit-01" / "content.md"
    game = ":::memory\n- Gestor\n- Clave\n:::\n\n:::dialog"
    path.write_text(path.read_text(encoding="utf-8").replace(":::dialog", game), encoding="utf-8")
    capsys.readouterr()
    assert main(["assemble", "build", "PWD", "--unit", "1"]) == 1
    assert "MEMORY: this component is not available in the html backend yet" in capsys.readouterr().err
    assert main(["verify", "PWD", "--no-update"]) == 1
    assert "not available in the html backend yet" in capsys.readouterr().out


def test_only_the_published_subsections_of_an_activity_are_compared(tmp_path):
    from coursekit import lang

    tokens = lang.tokens("es")
    path = tmp_path / "assessment.md"
    path.write_text("# Unidad 1 — Actividades\n\n## ACTIVIDAD DE EVALUACIÓN 1.1 — Test\n"
                    "### Objetivos que evalúa\nObjetivo interno secreto.\n"
                    "### Instrucciones para el alumno\nResponde con calma.\n### Desarrollo e implementación\nNota interna del equipo.\n"
                    "### Banco de preguntas\n:::single-choice\npregunta: ¿Cuánto?\n- [x] Mucho\n:::\n"
                    "## ACTIVIDAD DE EVALUACIÓN 1.2 — Otro\n### Banco de preguntas\nSegundo banco.\n", encoding="utf-8")
    words = set(check.WORD.findall(check.learner_text(path, tokens, True).casefold()))
    assert {"responde", "calma", "cuánto", "mucho", "segundo", "banco"} <= words
    assert not words & {"secreto", "interno", "equipo", "objetivo"}


def test_the_check_ignores_the_syntax_of_the_format():
    tokens = __import__("coursekit.lang", fromlist=["tokens"]).tokens("es")
    text = check.learner_text(FIXTURES / "html_content.md", tokens, False)
    assert "pregunta" not in text and "objetivo" not in text and ":::" not in text and "Imagen" not in text
    assert "Longitud" in text and "bitwarden" in text and "print" in text and "extensa" in text
    assert "guia" not in text  # the target of a link is not text


# ── guards ───────────────────────────────────────────────────────────────────────────────────


def test_each_backend_refuses_the_commands_of_the_other(html_course, capsys, tmp_path, monkeypatch):
    assert main(["assemble", "plan", "PWD", "--unit", "1"]) == 1
    assert "is assembled with the html backend" in capsys.readouterr().err
    assert main(["status", "PWD"]) == 0
    assert "Assembly: html backend" in capsys.readouterr().out
    # a course can use the other backend than its project
    path = html_course / "course.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "assembly:\n  backend: creator\n", encoding="utf-8")
    assert main(["assemble", "build", "PWD", "--unit", "1"]) == 1
    assert "`build` is for the html backend" in capsys.readouterr().err
    assert main(["assemble", "plan", "PWD", "--unit", "1"]) == 0
    assert main(["assemble", "plan", "PWD"]) == 2
    assert "needs --unit" in capsys.readouterr().err


def test_a_built_package_is_a_valid_delivery(html_course, capsys):
    produce_image(html_course)
    assert main(["assemble", "build", "PWD", "--unit", "1", "--version", "1.0"]) == 0
    path = html_course / "course.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("status: design_approved", "status: assembly", 1), encoding="utf-8")
    capsys.readouterr()
    assert main(["delivery", "add", "PWD", "--unit", "1", "--version", "1.0", "--file",
                 str(html_course / "delivery" / "PWD-U01-v1.0-scorm12.zip")]) == 0
    assert "course delivered" in capsys.readouterr().out
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["status"] == "delivered"


def test_the_tokens_of_the_stylesheet_are_derived_with_their_origin(html_course, capsys):
    root = html_course.parent.parent
    css = root / "theme" / "maqueta.css"
    css.write_text(":root { --color-accent: #7a1fa2; --font-family: 'Acme Sans', sans-serif; }\n", encoding="utf-8")
    capsys.readouterr()
    assert main(["theme", "import", str(css)]) == 0
    out = capsys.readouterr().out
    assert "CSS variables of maqueta.css" in out
    tokens = json.loads((root / "theme" / "tokens.json").read_text(encoding="utf-8"))
    assert tokens["origin"]["source"] == "css" and tokens["origin"]["file"] == "maqueta.css" and len(tokens["origin"]["sha256"]) == 12
    assert tokens["color"]["accent"] == "#7A1FA2" and tokens["color"]["headings"] == "#1A1A1A"  # var(--color-text) resolved
    assert tokens["font"]["headings"] == "'Acme Sans', sans-serif" and tokens["font"]["size-base"] == "16px"
    assert theme.status(find_project(root)).state == "derived"
    assert main(["theme", "show"]) == 0
    assert "origin: CSS variables of maqueta.css" in capsys.readouterr().out
    assert main(["theme", "check"]) == 0


def test_variables_inside_media_queries_are_not_the_theme():
    css = (":root { --color-accent: #111111; }\n@import url(x.css);\n"
           "@media (prefers-color-scheme: dark) { :root { --color-accent: #eeeeee; "
           "--color-text: #fafafa; } }\n:root { --radius: 4px; }")
    assert theme.css_variables(css) == {"color-accent": "#111111", "radius": "4px"}


def test_css_variables_are_resolved_through_var_references():
    variables = theme.css_variables("/* c */ :root { --a: #fff; --b: var(--a); --c: var(--b, #000); --d: var(--missing); }")
    assert variables["b"] == "var(--a)"
    tokens = theme.from_css(":root { --color-text: #111111; --color-headings: var(--color-text); }", "", "x.css", "h")
    assert tokens["color"]["headings"] == "#111111"
    assert theme._resolve_css("var(--d)", variables) == "var(--missing)"  # an unknown variable stays as it is
