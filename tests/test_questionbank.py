"""The tests of a course apart (`delivery › assessment › placement: separate`) and as a question bank (Aiken, GIFT, Moodle XML)."""

import json
import xml.etree.ElementTree as ET

import yaml

from coursekit.cli import main
from tests.test_assemble import course  # noqa: F401 — the approved Spanish sample course

BANK = """# Unidad 1 — Actividades de evaluación

## ACTIVIDAD DE EVALUACIÓN 1.1 — Test de la unidad
### Instrucciones para el alumno
Responde con calma.
### Banco de preguntas

:::single-choice
objetivo: U1.1
pregunta: ¿Qué longitud mínima recomiendas?
- [ ] 4 ‹corta›
- [x] 14
feedback-correcto: Bien: cuanto más larga, mejor.
feedback-incorrecto: Repasa el apartado 2.
:::

:::multi-select
objetivo: U1.1
pregunta: ¿Qué hace robusta una contraseña?
- [x] La longitud
- [x] Que sea única
- [ ] El año de nacimiento
feedback-correcto: Correcto.
feedback-incorrecto: Revisa el apartado 2.
:::

:::true-false
objetivo: U1.2
pregunta: Una contraseña larga puede ser fácil de recordar.
respuesta: verdadero
feedback-correcto: Sí: una frase.
feedback-incorrecto: Prueba con una frase.
:::

:::match
objetivo: U1.2
pregunta: Relaciona cada término con su definición.
- Gestor :: Guarda las contraseñas
- 2FA :: Un segundo factor
- Frase :: Varias palabras seguidas
feedback: Repasa el glosario.
:::

:::fill-in-the-blank
objetivo: U1.2
pregunta: Una buena contraseña tiene al menos {14/catorce} caracteres.
feedback-correcto: Eso es.
feedback-incorrecto: Son 14.
:::

:::sorting
objetivo: U1.2
pregunta: Ordena los pasos.
- Uno
- Dos
:::
"""


def set_assessment(course_dir, placement: str = "unit", fmt: str = "platform", bank: str = BANK) -> None:
    (course_dir / "content" / "unit-01" / "assessment.md").write_text(bank, encoding="utf-8")
    path = course_dir / "course.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["delivery"] = {"assessment": {"placement": placement, "format": fmt}}
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def plan(course_dir, n: int) -> dict:
    assert main(["assemble", "plan", "PWD", "--unit", str(n)]) == 0
    return json.loads((course_dir / "assembly" / f"unit-{n:02d}.plan.json").read_text(encoding="utf-8"))


def test_separate_tests_go_in_a_package_of_their_own(course):  # noqa: F811
    set_assessment(course, placement="separate")
    unit = plan(course, 1)
    assert [lesson["type"] for lesson in unit["lessons"]] == ["content"] * 3  # the tests left the unit
    assert unit["score_source"] == "lessonProgress"
    tests = plan(course, 2)
    assert [lesson["key"] for lesson in tests["lessons"]] == ["U1-E1.1"]
    assert tests["content_title"] == "Contraseñas seguras. Evaluación" and tests["score_source"] == "quiz"
    assert tests["lessons"][0]["quiz"] == {"passingGrade": 50, "maxAttempts": 2, "courseWeight": 1}
    assert main(["assemble", "link", "PWD", "--unit", "2", "--content-id", "c-tests"]) == 0
    data = yaml.safe_load((course / "course.yaml").read_text(encoding="utf-8"))
    assert data["assessment_unit"]["content_id"] == "c-tests" and len(data["units"]) == 1


def test_with_a_bank_format_the_questions_leave_the_packages(course):  # noqa: F811
    set_assessment(course, fmt="gift")
    lessons = plan(course, 1)["lessons"]
    assert [lesson["type"] for lesson in lessons] == ["content"] * 3
    assert main(["assemble", "plan", "PWD", "--unit", "2"]) == 1  # no package of tests: nothing stays in one


def test_gift_refuses_a_question_it_cannot_take(course, capsys):  # noqa: F811
    set_assessment(course, fmt="gift")
    assert main(["delivery", "questions", "PWD", "--version", "1.0"]) == 1
    assert "“sorting” question does not fit in gift" in capsys.readouterr().err


def test_gift_bank(course, capsys):  # noqa: F811
    set_assessment(course, fmt="gift", bank=BANK.split(":::sorting")[0])
    assert main(["delivery", "questions", "PWD", "--version", "1.0"]) == 0
    text = (course / "delivery" / "PWD-questions-v1.0.gift").read_text(encoding="utf-8")
    assert "$CATEGORY: $course$/top/PWD/U1 E1.1 Test de la unidad" in text
    assert "::U1-E1.1-q1 · U1.1::[html]¿Qué longitud mínima recomiendas? {" in text
    assert "=14#Bien\\: cuanto más larga, mejor." in text and "~4#Repasa el apartado 2." in text and "corta" not in text
    assert "~%50%La longitud" in text and "~%-100%El año de nacimiento" in text
    assert "{TRUE#Prueba con una frase.#Sí\\: una frase.}" in text
    assert "=Gestor -> Guarda las contraseñas" in text and "####Repasa el glosario." in text
    assert "al menos {=14 =catorce#Eso es.} caracteres." in text
    data = yaml.safe_load((course / "course.yaml").read_text(encoding="utf-8"))
    entry = data["deliveries"][-1]
    assert entry["kind"] == "questions" and entry["format"] == "gift" and entry["files"][0]["file"] == "PWD-questions-v1.0.gift"
    assert "pending for v1.0: 1" in capsys.readouterr().out  # the package of the unit is still missing


def test_moodle_xml_bank(course):  # noqa: F811
    set_assessment(course, fmt="moodle-xml", bank=BANK.split(":::sorting")[0])
    assert main(["delivery", "questions", "PWD", "--version", "1.0"]) == 0
    root = ET.parse(course / "delivery" / "PWD-questions-v1.0.xml").getroot()
    kinds = [q.get("type") for q in root]
    assert kinds == ["category", "multichoice", "multichoice", "truefalse", "matching", "cloze"]
    single = root[1]
    assert single.find("single").text == "true"
    assert [a.get("fraction") for a in single.findall("answer")] == ["0", "100"]
    assert [a.get("fraction") for a in root[2].findall("answer")] == ["50", "50", "-100"]
    assert "{1:SHORTANSWER:=14~=catorce}" in root[5].find("questiontext/text").text


def test_aiken_takes_single_choice_only(course, capsys):  # noqa: F811
    set_assessment(course, fmt="aiken")
    assert main(["delivery", "questions", "PWD", "--version", "1.0"]) == 1
    assert "it takes: single-choice" in capsys.readouterr().err
    set_assessment(course, fmt="aiken", bank=BANK.split(":::multi-select")[0])
    assert main(["delivery", "questions", "PWD", "--version", "1.0"]) == 0
    text = (course / "delivery" / "PWD-U1-E1.1-v1.0.txt").read_text(encoding="utf-8")
    assert text == "¿Qué longitud mínima recomiendas?\nA. 4\nB. 14\nANSWER: B\n"


def test_verify_refuses_the_question_types_the_bank_cannot_take(course):  # noqa: F811
    from coursekit import course as coursemod
    from coursekit import verify
    from coursekit.project import find_project

    set_assessment(course, fmt="gift", bank=BANK.replace("al menos {14/catorce} caracteres", "{14} caracteres y {3} tipos"))
    loaded = coursemod.load(find_project(course), "PWD")
    errors = verify.verify_unit(loaded, loaded["units"][0]).errors
    assert any("“sorting” question does not fit in the gift bank" in e for e in errors)
    assert any("a single blank" in e for e in errors)
