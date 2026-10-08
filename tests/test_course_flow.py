"""End to end through the course engine with a small, generic course."""

import shutil
from pathlib import Path

import pytest
import yaml

from coursekit.cli import main

FIXTURES = Path(__file__).parent / "fixtures"

# Small rules so the sample unit stays short: 20 words per page, few placeholders and directives.
COURSE_RULES = """
rules:
  words_per_page: 20
  content:
    placeholders_per_hour: 1
    min_placeholder_types: 1
    interactive_per_hour: 1
    questions_per_objective: 1
"""

WORDS = " ".join(["palabra"] * 60)

CONTENT = f"""# Unidad 1 — Contraseñas que protegen

## Apartado 1 — Introducción y objetivos *(mín. 40 palabras)*

{WORDS}

## Apartado 2 — Cómo es una contraseña robusta *(mín. 120 palabras)*

*[Objetivo U1.1 — Crear]*
*[Objetivo U1.2 — Identificar]*

{WORDS} {WORDS} {WORDS}

:::accordion
## Longitud
Más larga es mejor.
:::

> **[RECURSO MULTIMEDIA — Infografía]**
> **Título:** Anatomía de una contraseña
> **Descripción:** Partes de una contraseña robusta.
> **Cómo se elabora:** SVG con los tokens del proyecto.
> **Especificaciones:** 1600 × 900.

:::single-choice
objetivo: U1.2
¿Cuál es más robusta?
- [ ] 1234
- [x] tres-palabras-largas-juntas
:::

## Apartado 3 — Resumen *(mín. 40 palabras)*

{WORDS}
"""

ASSESSMENT = """# Unidad 1 — Actividades de evaluación

## ACTIVIDAD DE EVALUACIÓN 1.1 — Test de la unidad
### Banco de preguntas

:::single-choice
objetivo: U1.1
¿Qué longitud mínima recomiendas?
- [ ] 4
- [x] 14
:::
"""


@pytest.fixture
def project(tmp_path, monkeypatch):
    for key in ("COURSEKIT_PROJECT", "COURSEKIT_USER_NAME", "COURSEKIT_USER_EMAIL"):
        monkeypatch.delenv(key, raising=False)
    root = tmp_path / "demo"
    assert main(["init", str(root), "--yes", "--no-git", "--client", "Demo"]) == 0
    monkeypatch.chdir(root)
    return root


def write_course_rules(course_dir: Path) -> None:
    path = course_dir / "course.yaml"
    path.write_text(path.read_text(encoding="utf-8") + COURSE_RULES, encoding="utf-8")


def test_full_flow(project, monkeypatch, capsys):
    assert main(["new", "Contraseñas seguras", "1", "--code", "pwd101"]) == 0
    course_dir = project / "courses" / "PWD101"
    data = yaml.safe_load((course_dir / "course.yaml").read_text(encoding="utf-8"))
    assert data["client"] == "Demo"
    assert data["language"] == "es"
    assert data["design"]["grading"]["passing_score"] == 50
    assert (course_dir / "brief" / "notes.md").exists()
    write_course_rules(course_dir)
    shutil.copy(FIXTURES / "matrix.json", course_dir / "design" / "matrix.json")

    # verify refuses before the design is signed
    assert main(["verify", "PWD101"]) == 1

    # approving needs the signing identity of the .env
    assert main(["approve", "design", "PWD101", "--yes", "--no-commit"]) == 1
    assert "coursekit setup --identity" in capsys.readouterr().err
    (project / ".env").write_text("COURSEKIT_USER_NAME=Ana Pérez\nCOURSEKIT_USER_EMAIL=ana@example.com\n", encoding="utf-8")
    assert main(["approve", "design", "PWD101", "--yes", "--no-commit"]) == 0
    assert "design approved by Ana Pérez <ana@example.com>" in capsys.readouterr().out

    data = yaml.safe_load((course_dir / "course.yaml").read_text(encoding="utf-8"))
    assert data["status"] == "design_approved"
    unit = data["units"][0]
    assert [s["kind"] for s in unit["sections"]] == ["intro", "content", "summary"]
    assert [s["min_words"] for s in unit["sections"]] == [40, 120, 40]
    assert [o["id"] for o in unit["objectives"]] == ["U1.1", "U1.2"]
    skeleton = (course_dir / "content" / "unit-01" / "content.md").read_text(encoding="utf-8")
    assert "## Apartado 2 — Cómo es una contraseña robusta *(mín. 120 palabras)*" in skeleton

    # the skeleton does not pass; the written unit does
    assert main(["verify", "PWD101"]) == 1
    (course_dir / "content" / "unit-01" / "content.md").write_text(CONTENT, encoding="utf-8")
    (course_dir / "content" / "unit-01" / "assessment.md").write_text(ASSESSMENT, encoding="utf-8")
    capsys.readouterr()
    assert main(["verify", "PWD101"]) == 0, capsys.readouterr().out
    data = yaml.safe_load((course_dir / "course.yaml").read_text(encoding="utf-8"))
    assert data["units"][0]["status"] == "verified"
    assert data["status"] == "ai_review"

    # AI review recorded, then the person signs the unit
    reviews = course_dir / "reviews"
    (reviews / "unit-01-ai-review.md").write_text("# Revisión\n\nSin incidencias.\n", encoding="utf-8")
    assert main(["reviewed", "PWD101", "1"]) == 0
    assert main(["approve", "content", "PWD101", "--unit", "1", "--yes", "--no-commit"]) == 0
    data = yaml.safe_load((course_dir / "course.yaml").read_text(encoding="utf-8"))
    assert data["units"][0]["status"] == "approved"
    assert data["status"] == "media"
    assert [a["gate"] for a in data["approvals"]] == ["design", "content"]
    assert all(a["by"] == "Ana Pérez <ana@example.com>" for a in data["approvals"])

    # a later edit is caught: back to verified, with the changed part named
    content = course_dir / "content" / "unit-01" / "content.md"
    content.write_text(content.read_text(encoding="utf-8").replace("Más larga es mejor.", "Cuanto más larga, mejor."), encoding="utf-8")
    capsys.readouterr()
    assert main(["verify", "PWD101"]) == 0
    out = capsys.readouterr().out
    assert "content changed after its approval (section 2 changed after the AI review)" in out
    data = yaml.safe_load((course_dir / "course.yaml").read_text(encoding="utf-8"))
    assert data["units"][0]["status"] == "verified"


def test_verify_reports_problems(project, monkeypatch, capsys):
    (project / ".env").write_text("COURSEKIT_USER_NAME=Ana\nCOURSEKIT_USER_EMAIL=ana@example.com\n", encoding="utf-8")
    assert main(["new", "Contraseñas", "1", "--code", "P2"]) == 0
    course_dir = project / "courses" / "P2"
    write_course_rules(course_dir)
    shutil.copy(FIXTURES / "matrix.json", course_dir / "design" / "matrix.json")
    assert main(["approve", "design", "P2", "--yes", "--no-commit"]) == 0
    bad = CONTENT.replace(":::accordion", ":::stepper").replace("*[Objetivo U1.1 — Crear]*\n", "") + "\nUn emoji 😀\n"
    (course_dir / "content" / "unit-01" / "content.md").write_text(bad, encoding="utf-8")
    (course_dir / "content" / "unit-01" / "assessment.md").write_text(ASSESSMENT, encoding="utf-8")
    capsys.readouterr()
    assert main(["verify", "P2", "--no-update"]) == 1
    out = capsys.readouterr().out
    assert "unknown directive ':::stepper' (use: carousel" in out
    assert "objective U1.1 is not tagged" in out
    assert "emoji/pictograph not allowed" in out


def test_status_outline_and_rules(project, capsys):
    assert main(["status"]) == 0
    assert "no courses yet" in capsys.readouterr().out
    assert main(["new", "Contraseñas", "1", "--code", "P3"]) == 0
    capsys.readouterr()
    assert main(["status", "P3"]) == 0
    assert "Next step:" in capsys.readouterr().out
    write_course_rules(project / "courses" / "P3")
    assert main(["rules", "P3", "--changed"]) == 0
    out = capsys.readouterr().out
    assert "words_per_page" in out and "(course)" in out


def test_unknown_course(project, capsys):
    assert main(["status", "NOPE"]) == 1
    assert "course NOPE not found" in capsys.readouterr().err


def test_brief_of_a_course(project, capsys):
    assert main(["new", "Contraseñas", "1", "--code", "P4"]) == 0
    sources = project / "courses" / "P4" / "brief" / "sources"
    (sources / "guia.md").write_text("# Guía\n\n" + " ".join(["texto"] * 40) + "\n", encoding="utf-8")
    capsys.readouterr()
    assert main(["brief", "P4"]) == 0
    index = (project / "courses" / "P4" / "brief" / "index.md").read_text(encoding="utf-8")
    assert "guia.md" in index
    assert (project / "courses" / "P4" / "brief" / "text" / "files" / "guia.md").exists()


def test_approval_commit_is_authored_by_the_signer(tmp_path, monkeypatch, capsys):
    import subprocess

    for key in ("COURSEKIT_PROJECT", "COURSEKIT_USER_NAME", "COURSEKIT_USER_EMAIL"):
        monkeypatch.delenv(key, raising=False)
    root = tmp_path / "repo"
    assert main(["init", str(root), "--yes"]) == 0  # with git init
    run = lambda *a: subprocess.run(["git", *a], cwd=root, capture_output=True, text=True, check=True).stdout  # noqa: E731
    run("config", "user.name", "Some Git Account")
    run("config", "user.email", "git@example.com")
    run("add", "-A")
    run("commit", "-qm", "init")
    monkeypatch.chdir(root)
    (root / ".env").write_text("COURSEKIT_USER_NAME=Ana Pérez\nCOURSEKIT_USER_EMAIL=ana@example.com\n", encoding="utf-8")
    assert main(["new", "Contraseñas", "1", "--code", "P5"]) == 0
    shutil.copy(FIXTURES / "matrix.json", root / "courses" / "P5" / "design" / "matrix.json")
    assert main(["approve", "design", "P5", "--yes"]) == 0
    assert run("log", "-1", "--format=%an <%ae>|%s").strip() == "Ana Pérez <ana@example.com>|Design approval P5"
