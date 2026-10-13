"""Readability of the prose (per language and audience) and the closing reflection of a unit: warnings of verify, and the
`:::reflection` directive as it is assembled."""

import shutil

from coursekit import course as coursemod
from coursekit import readability as r
from coursekit.cli import main
from coursekit.project import find_project
from tests.test_course_flow import ASSESSMENT, CONTENT, FIXTURES, project, write_course_rules  # noqa: F401 - fixture


def test_spanish_and_english_syllables():
    assert [r.syllables_es(w) for w in ("contraseña", "aplicación", "leer", "país", "ciudad", "muy", "y", "verificación")] == \
        [4, 4, 2, 2, 2, 1, 1, 5]
    assert [r.syllables_en(w) for w in ("password", "strong", "verification", "people", "the", "created")] == [2, 1, 5, 2, 1, 2]


def test_only_running_prose_is_measured():
    lines = ["Primera frase del párrafo. Segunda frase, más larga.", "", "- Un elemento de lista", "",
             ":::accordion", "#### Título", "Texto de dentro que no cuenta.", ":::", "",
             ":::if llamada.riesgo >= 3", "Rama del si.", ":::else", "Rama neutra.", ":::", "",
             "> **[RECURSO MULTIMEDIA — Imagen]**", "| a | b |", "```", "codigo()", "```", "<!-- comentario. -->", "Cierre."]
    assert r.sentences(r.prose(lines)) == ["Primera frase del párrafo.", "Segunda frase, más larga.", "Un elemento de lista",
                                           "Rama del si.", "Rama neutra.", "Cierre."]


def test_the_index_follows_the_language():
    easy = ["El gato duerme. La casa es azul. Hoy hace sol. Me gusta el pan."] * 3
    hard = ["La implementación de mecanismos de autenticación multifactorial constituye una contramedida "
            "indispensable frente a la reutilización indiscriminada de credenciales comprometidas en filtraciones."] * 3
    assert r.measure(easy, "es", 30).index > 80 > 40 > r.measure(hard, "es", 30).index
    english = r.measure(["The cat sat on the mat. It was a sunny day."], "en", 30)
    assert english.index_name == "Flesch" and english.index > 80
    other = r.measure(["Le chat dort sur le tapis."], "fr", 30)
    assert other.index is None and other.sentences == 1


HARD = " ".join(["La implementación sistemática de mecanismos de autenticación multifactorial constituye una contramedida "
                 "organizativa indispensable frente a la reutilización indiscriminada de credenciales previamente "
                 "comprometidas en filtraciones masivas de bases de datos corporativas, especialmente cuando las "
                 "organizaciones carecen de políticas formalizadas de gestión centralizada de identidades digitales."] * 12)


def test_verify_warns_of_hard_prose_and_of_a_unit_without_reflection(project, capsys):  # noqa: F811
    (project / ".env").write_text("COURSEKIT_USER_NAME=Ana\nCOURSEKIT_USER_EMAIL=ana@example.com\n", encoding="utf-8")
    assert main(["new", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    course_dir = project / "courses" / "PWD"
    write_course_rules(course_dir)
    shutil.copy(FIXTURES / "matrix.json", course_dir / "design" / "matrix.json")
    assert main(["approve", "design", "PWD", "--yes", "--no-commit"]) == 0
    unit = course_dir / "content" / "unit-01"
    (unit / "assessment.md").write_text(ASSESSMENT, encoding="utf-8")
    hard = CONTENT.replace("## Apartado 2 — Cómo es una contraseña robusta *(mín. 120 palabras)*\n",
                           "## Apartado 2 — Cómo es una contraseña robusta *(mín. 120 palabras)*\n\n" + HARD + "\n")
    (unit / "content.md").write_text(hard, encoding="utf-8")
    capsys.readouterr()
    assert main(["verify", "PWD", "--no-update"]) == 0
    out = capsys.readouterr().out
    assert "Apartado 2: readability index 0 (Szigriszt-Pazos)" in out and "(Szigriszt-Pazos), below 55 for a general audience" in out
    assert "Apartado 2: 13 of 13 sentences go over 30 words (general audience)" in out
    assert "Apartado 3: the unit does not close with a reflection" in out

    closed = CONTENT.replace("## Apartado 3 — Resumen *(mín. 40 palabras)*\n",
                             "## Apartado 3 — Resumen *(mín. 40 palabras)*\n\n:::reflection\n¿Qué harías distinto mañana?\n:::\n")
    (unit / "content.md").write_text(closed, encoding="utf-8")
    path = course_dir / "course.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "  readability: {audience: specialist}\n", encoding="utf-8")
    capsys.readouterr()
    assert main(["verify", "PWD", "--no-update"]) == 0
    out = capsys.readouterr().out
    assert "reflection" not in out and "readability index" not in out

    from coursekit import assemble

    course = coursemod.load(find_project(), "PWD")
    plan, errors, _ = assemble.build_plan(course, course["units"][0])
    note = [b for b in plan["lessons"][2]["bricks"] if b["type"] == "NOTE"][0]
    assert note["data"]["content"]["title"] == "<p>Para reflexionar</p>" and "harías distinto" in note["data"]["content"]["content"]
