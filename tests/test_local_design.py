"""The instructional design made in the project (course.yaml › design.tool: local), without slxd: design/design.yaml,
checked and exported by `coursekit design`, then synced and signed like a design made in slxd."""

import json
from pathlib import Path

import pytest
import yaml
from openpyxl import load_workbook

from coursekit import course as coursemod
from coursekit import localdesign
from coursekit.cli import main
from coursekit.project import find_project
from tests.test_course_flow import ASSESSMENT, CONTENT, write_course_rules

DESIGN = """\
profile:
  audience: Personal de oficina sin perfil técnico
  level: Inicial
  context: Migración de las herramientas de ACME a la nube
competencies:
  - id: C1
    text: Proteger sus cuentas de trabajo en el día a día
objectives:
  - id: O1
    text: Aplicar los criterios de una contraseña robusta a una cuenta nueva
    bloom: apply
    competencies: [C1]
  - id: O2
    text: Analizar por qué una contraseña es débil
    bloom: analyze
    competencies: [C1]
units:
  - title: Contraseñas que protegen
    hours: 1
    sections:
      - {title: Introducción y objetivos, hours: 0.2}
      - {title: Cómo es una contraseña robusta, hours: 0.6, objectives: [O1, O2]}
      - {title: Resumen, hours: 0.2}
    learning_activities:
      - {title: Clasifica contraseñas, type: classification, objectives: [O1, O2]}
    assessment_activities:
      - {title: Test de la unidad, instrument: case_study, criterion: Acierta la mitad, weight: 1, passing_score: 50,
         attempts: 2, objectives: [O1, O2]}
"""


@pytest.fixture
def project(tmp_path, monkeypatch):
    for key in ("COURSEKIT_PROJECT", "COURSEKIT_USER_NAME", "COURSEKIT_USER_EMAIL"):
        monkeypatch.delenv(key, raising=False)
    root = tmp_path / "demo"
    assert main(["init", str(root), "--yes", "--no-git", "--client", "Demo"]) == 0
    monkeypatch.chdir(root)
    (root / ".env").write_text("COURSEKIT_USER_NAME=Ana Pérez\nCOURSEKIT_USER_EMAIL=ana@example.com\n", encoding="utf-8")
    return root


def new_local(project: Path, design: str = DESIGN) -> Path:
    assert main(["new", "Contraseñas seguras", "1", "--code", "pwd101", "--design-tool", "local"]) == 0
    course_dir = project / "courses" / "PWD101"
    write_course_rules(course_dir)
    (course_dir / "design" / "design.yaml").write_text(design, encoding="utf-8")
    return course_dir


def findings(project: Path, design: str, **course_design) -> list[localdesign.Finding]:
    course_dir = project / "courses" / "PWD101"
    if not course_dir.exists():
        new_local(project, design)
    (course_dir / "design" / "design.yaml").write_text(design, encoding="utf-8")
    course = coursemod.load(find_project(project), "PWD101")
    course["design"].update(course_design)
    return localdesign.build(course)[1]


def test_a_local_course_designs_exports_syncs_and_signs_without_slxd(project, capsys):
    assert main(["new", "Contraseñas seguras", "1", "--code", "pwd101", "--design-tool", "local"]) == 0
    course_dir = project / "courses" / "PWD101"
    assert yaml.safe_load((course_dir / "course.yaml").read_text(encoding="utf-8"))["design"]["tool"] == "local"
    assert "objectives:" in (course_dir / "design" / "design.yaml").read_text(encoding="utf-8")  # the template to fill in
    write_course_rules(course_dir)
    (course_dir / "design" / "design.yaml").write_text(DESIGN, encoding="utf-8")
    capsys.readouterr()

    assert main(["design", "PWD101", "--check"]) == 0
    assert not (course_dir / "design" / "matrix.json").exists()  # --check writes nothing
    assert main(["design", "PWD101"]) == 0
    out = capsys.readouterr().out
    assert "without errors or warnings" in out and "design/matrix.json" in out
    graph = json.loads((course_dir / "design" / "matrix.json").read_text(encoding="utf-8"))
    assert graph["matrix"]["origen"] == "local" and graph["matrix"]["palabrasPorHora"] == 10 * 20
    assert [o["nivelBloom"] for o in graph["objetivos"]] == ["aplicar", "analizar"]
    assert graph["actividadesEvaluacion"][0]["instrumento"] == "caso_practico"
    assert json.loads((course_dir / "design" / "validation.json").read_text(encoding="utf-8")) == {"hallazgos": []}
    book = load_workbook(course_dir / "design" / "PWD101-instructional-design.xlsx")
    assert book.sheetnames[:4] == ["Profile", "Competencies", "Objectives", "Structure"]
    assert [c.value for c in book["Structure"][4]][:2] == ["Section", "    Cómo es una contraseña robusta"]

    # the same export twice gives the same matrix (stable ids): a signature does not break by exporting again
    first = (course_dir / "design" / "matrix.json").read_bytes()
    assert main(["design", "PWD101"]) == 0
    assert (course_dir / "design" / "matrix.json").read_bytes() == first

    assert main(["sync", "PWD101", "--check"]) == 0
    assert main(["approve", "design", "PWD101", "--yes", "--no-commit"]) == 0
    data = yaml.safe_load((course_dir / "course.yaml").read_text(encoding="utf-8"))
    unit = data["units"][0]
    assert [s["kind"] for s in unit["sections"]] == ["intro", "content", "summary"]
    assert [(o["id"], o["bloom"]) for o in unit["objectives"]] == [("U1.1", "aplicar"), ("U1.2", "analizar")]
    assert unit["activities"]["assessment"][0]["passing_score"] == 50

    # the rest of the flow does not care where the design was made
    (course_dir / "content" / "unit-01" / "content.md").write_text(CONTENT, encoding="utf-8")
    (course_dir / "content" / "unit-01" / "assessment.md").write_text(ASSESSMENT, encoding="utf-8")
    capsys.readouterr()
    assert main(["verify", "PWD101"]) == 0, capsys.readouterr().out

    # design.yaml edited and not exported: the signature no longer holds, and a new one is refused until it is exported
    path = course_dir / "design" / "design.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("Resumen, hours: 0.2", "Resumen, hours: 0.3"), encoding="utf-8")
    course = coursemod.load(find_project(project), "PWD101")
    assert "changed since the last export" in coursemod.approval_problem(course)
    capsys.readouterr()
    assert main(["approve", "design", "PWD101", "--yes", "--no-commit"]) == 1
    assert "coursekit design PWD101" in capsys.readouterr().err


def test_a_course_designed_in_slxd_has_no_local_design(project, capsys):
    assert main(["new", "Contraseñas seguras", "1", "--code", "pwd101"]) == 0
    assert not (project / "courses" / "PWD101" / "design" / "design.yaml").exists()
    assert main(["design", "PWD101"]) == 1
    assert "designs in slxd" in capsys.readouterr().err


def test_the_checks_of_a_design_matrix(project):
    broken = (DESIGN.replace("instrument: case_study", "instrument: quiz")  # a quiz does not reach analyze
              .replace("text: Aplicar los criterios", "text: Comprender los criterios")
              .replace("text: Analizar por qué", "text: Evaluar por qué")
              .replace("{title: Resumen, hours: 0.2}", "{title: Extra, hours: 0.1}\n      - {title: Resumen, hours: 0.2}")
              .replace("objectives: [O1, O2]}\n    assessment", "objectives: [O2]}\n    assessment"))
    found = {f.check: f for f in findings(project, broken)}
    assert found["rigor.instrument_ceiling"].severity == "error"
    assert "level analyze and its evidence is quiz" in found["rigor.instrument_ceiling"].message
    assert found["verbs.vague"].message == "objective O1 starts with 'comprender', a verb that cannot be observed"
    assert "'evaluar', a verb of level evaluate, but declares analyze" in found["verbs.bloom_mismatch"].message
    assert found["hours.children"].message == "'Contraseñas que protegen' declares 1 h and its parts add up to 1.1 h"
    assert "Extra" in found["coverage.orphan_content"].message  # the introduction and the summary are not orphans
    assert found["arc.assessed_without_practice"].message.startswith("objective O1 is assessed without")

    found = {f.check for f in findings(project, DESIGN.replace("objectives: [O1, O2]}\n", "objectives: [O1]}\n", 1)
                                       .replace("C1]\n  - id: O2", "C1]\n  - id: O3\n    text: Detectar una contraseña reutilizada\n"
                                                "    bloom: analyze\n  - id: O2"))}
    assert {"coverage.objective_without_content", "evidence.objective_without_assessment",
            "coverage.objective_without_competency"} <= found

    found = [f.message for f in findings(project, DESIGN.replace("hours: 0.6, objectives: [O1, O2]", "hours: 0.6, objectives: [O1, O9]")
                                         .replace("bloom: apply", "bloom: aply"))]
    assert "'Cómo es una contraseña robusta' names an objective that does not exist: 'O9'" in found
    assert any("'aply' is not valid" in m for m in found)

    found = {f.check for f in findings(project, DESIGN, structure="con_modulos")}
    assert "structure.invalid" in found and "structure.empty" in found


def test_modules_and_subsections(project):
    new_local(project)
    course = coursemod.load(find_project(project), "PWD101")
    course["design"]["structure"] = "con_modulos"
    data = yaml.safe_load(DESIGN)
    data["modules"] = [{"title": "Bloque 1", "units": data.pop("units")}]
    unit = data["modules"][0]["units"][0]
    del unit["hours"]
    unit["sections"][1] = {"title": "Cómo es una contraseña robusta", "subsections": [
        {"title": "Longitud", "hours": 0.3, "objectives": ["O1"]}, {"title": "Señales de debilidad", "hours": 0.3, "objectives": ["O2"]}]}
    builder = localdesign.Builder(course, data)
    graph = builder.build()
    assert not builder.findings, builder.findings
    assert [n["tipo"] for n in graph["nodos"]] == ["modulo", "unidad", "apartado", "apartado", "subapartado", "subapartado", "apartado"]
    assert graph["nodos"][0]["horas"] == 1 and graph["nodos"][3]["horas"] == 0.6  # taken from their parts
