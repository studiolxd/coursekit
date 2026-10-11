"""Decision-based courses: the approach of a course and the rules of the approach."""

from __future__ import annotations

import shutil

import pytest
import yaml

from coursekit.cli import main
from tests.test_course_flow import ASSESSMENT, FIXTURES, WORDS, write_course_rules


@pytest.fixture
def project(tmp_path, monkeypatch):
    for key in ("COURSEKIT_PROJECT", "COURSEKIT_USER_NAME", "COURSEKIT_USER_EMAIL"):
        monkeypatch.delenv(key, raising=False)
    root = tmp_path / "demo"
    assert main(["init", str(root), "--yes", "--no-git", "--client", "ACME"]) == 0
    monkeypatch.chdir(root)
    return root


def course_data(root, code):
    return yaml.safe_load((root / "courses" / code / "course.yaml").read_text(encoding="utf-8"))


def test_new_course_is_expository_by_default(project):
    assert main(["new", "Strong passwords", "1", "--code", "PWD"]) == 0
    assert course_data(project, "PWD")["design"]["approach"] == "expository"


def test_new_course_takes_the_approach(project):
    assert main(["new", "Strong passwords", "1", "--code", "PWD", "--approach", "decision-based"]) == 0
    assert course_data(project, "PWD")["design"]["approach"] == "decision-based"


def test_project_default_approach(project):
    (project / "config" / "rules.yaml").write_text("defaults:\n  approach: decision-based\n", encoding="utf-8")
    assert main(["new", "Strong passwords", "1", "--code", "PWD"]) == 0
    assert course_data(project, "PWD")["design"]["approach"] == "decision-based"


def test_unknown_default_approach_is_an_error(project, capsys):
    (project / "config" / "rules.yaml").write_text("defaults:\n  approach: gamified\n", encoding="utf-8")
    assert main(["new", "Strong passwords", "1", "--code", "PWD"]) == 1
    assert "unknown approach: gamified (valid: expository, decision-based)" in capsys.readouterr().err
    assert not (project / "courses" / "PWD").exists()


def test_decision_based_rules_are_configurable(project, capsys):
    capsys.readouterr()
    assert main(["config", "rules"]) == 0
    out = capsys.readouterr().out
    assert "decision_based.cycle" in out
    assert "decision_based.minutes.scene" in out


# ── Simulations and verify ──────────────────────────────────────────────────────────────────

SCENARIO = """:::scenario
id: call
title: La llamada de soporte
skin: phone
objective: [U1.1, U1.2]
scored: true
state: {risk: 0, trust: 2, called: false}
scenes:
  begin:
    characters: [{name: Técnico, expression: con prisa}]
    text: Suena el teléfono. Alguien de soporte te pide tu contraseña.
    choices:
      - {text: Se la doy, goto: leak, effects: {risk: 3}, score: -2}
      - {text: Le llamo yo a su extensión, goto: safe, set: {called: true}, score: 2}
      - {text: Lo consulto con mi responsable, goto: safe, if: "trust >= 2 && !called", score: 1}
    hotspots:
      - {label: Pósit en el monitor, area: [62, 30, 8, 6], goto: note, effects: {risk: 1}}
  note:
    text: En el pósit está tu contraseña.
    next: [{if: "risk >= 1", goto: leak}, {goto: safe}]
  safe:
    text: El supuesto técnico cuelga.
    ending: good
    debriefing: Verificar por otro canal corta el engaño.
  leak:
    text: Tres días después tu cuenta envía correos a clientes.
    variants: [{if: "risk >= 4", text: Además, el pósit seguía en el monitor.}]
    ending: bad
    debriefing: La urgencia es la palanca habitual de la ingeniería social.
:::
"""

ADAPTIVE = """:::if call.risk >= 3
Le diste tu contraseña al supuesto técnico. Veamos qué recursos usó.
:::else
No caíste, pero muchas personas sí lo hacen. Veamos por qué.
:::
"""


def decision_content(section2: str) -> str:
    return f"""# Unidad 1 — Contraseñas que protegen

## Apartado 1 — Introducción y objetivos *(mín. 40 palabras)*

{WORDS}

## Apartado 2 — Cómo es una contraseña robusta *(mín. 120 palabras)*

{section2}

## Apartado 3 — Resumen *(mín. 40 palabras)*

{WORDS}
"""


GOOD_SECTION = f"""{SCENARIO}
{ADAPTIVE}
*[Objetivo U1.1 — Crear]*
*[Objetivo U1.2 — Identificar]*

{WORDS} {WORDS} {WORDS}

:::accordion
#### Longitud
Más larga es mejor.
:::

> **[RECURSO MULTIMEDIA — Infografía]**
> **Título:** Anatomía de una contraseña
> **Descripción:** Partes de una contraseña robusta.
> **Cómo se elabora:** SVG con los tokens del proyecto.
> **Especificaciones:** 1600 × 900.
"""


STORY = """---
world: ACME, una aseguradora mediana, hoy
protagonist: {role: auxiliar administrativo recién llegado, mission: mantener seguras las cuentas del equipo}
characters:
  - {name: Marta, role: responsable de seguridad, personality: tranquila y directa, expressions: [neutral, preocupada]}
  - {name: Técnico, role: falso técnico de soporte, personality: "con prisa, seguro de sí mismo"}
---
# Biblia narrativa — Contraseñas

## Mundo
ACME se muda a la nube y todo el mundo tiene prisa.
"""


@pytest.fixture
def decision_course(project):
    (project / ".env").write_text("COURSEKIT_USER_NAME=Ana\nCOURSEKIT_USER_EMAIL=ana@example.com\n", encoding="utf-8")
    assert main(["new", "Contraseñas", "1", "--code", "DB1", "--approach", "decision-based", "--language", "es"]) == 0
    course_dir = project / "courses" / "DB1"
    write_course_rules(course_dir)
    shutil.copy(FIXTURES / "matrix.json", course_dir / "design" / "matrix.json")
    (course_dir / "design" / "story.md").write_text(STORY, encoding="utf-8")
    assert main(["approve", "design", "DB1", "--yes", "--no-commit"]) == 0
    unit = course_dir / "content" / "unit-01"
    unit.mkdir(parents=True, exist_ok=True)
    (unit / "assessment.md").write_text(ASSESSMENT, encoding="utf-8")
    return unit


def verify(unit, section2, capsys):
    (unit / "content.md").write_text(decision_content(section2), encoding="utf-8")
    capsys.readouterr()
    code = main(["verify", "DB1", "--no-update"])
    return code, capsys.readouterr().out


def test_a_decision_based_unit_verifies(decision_course, capsys):
    code, out = verify(decision_course, GOOD_SECTION, capsys)
    assert code == 0, out
    assert "not assembled by any backend yet" in out


def test_the_section_must_open_with_a_simulation(decision_course, capsys):
    code, out = verify(decision_course, f"{WORDS}\n\n{GOOD_SECTION}", capsys)
    assert code == 1
    assert "opens with a simulation" in out


def test_every_objective_is_practised_in_a_simulation(decision_course, capsys):
    code, out = verify(decision_course, GOOD_SECTION.replace("objective: [U1.1, U1.2]", "objective: U1.1"), capsys)
    assert code == 1
    assert "objective U1.2 is not practised in any simulation" in out


def test_dead_ends_and_unknown_scenes(decision_course, capsys):
    broken = GOOD_SECTION.replace('next: [{if: "risk >= 1", goto: leak}, {goto: safe}]', 'next: [{if: "risk >= 5", goto: leak}]')
    code, out = verify(decision_course, broken, capsys)
    assert code == 1
    assert "dead end in scene 'note'" in out
    code, out = verify(decision_course, GOOD_SECTION.replace("goto: leak, effects: {risk: 3}", "goto: nowhere, effects: {risk: 3}"), capsys)
    assert "scene 'nowhere' does not exist" in out


def test_conditions_use_code_syntax_and_declared_variables(decision_course, capsys):
    code, out = verify(decision_course, GOOD_SECTION.replace('"trust >= 2 && !called"', '"trust >= 2 y no called"'), capsys)
    assert code == 1
    assert "variable 'y' is not in 'state'" in out or "unexpected" in out
    code, out = verify(decision_course, GOOD_SECTION.replace('"trust >= 2 && !called"', '"mood > 1"'), capsys)
    assert "variable 'mood' is not in 'state'" in out


def test_adaptive_blocks_need_else_and_known_variables(decision_course, capsys):
    no_else = GOOD_SECTION.replace(":::else\nNo caíste, pero muchas personas sí lo hacen. Veamos por qué.\n", "")
    code, out = verify(decision_course, no_else, capsys)
    assert code == 1
    assert "':::if' without ':::else'" in out
    code, out = verify(decision_course, GOOD_SECTION.replace(":::if call.risk >= 3", ":::if other.risk >= 3"), capsys)
    assert "reads 'other.risk', which is not a variable of an earlier simulation" in out


def test_simulation_ids_are_unique_in_the_course(decision_course, capsys):
    code, out = verify(decision_course, GOOD_SECTION + "\n" + SCENARIO, capsys)
    assert code == 1
    assert "simulation 'call' appears more than once" in out


def test_the_plan_carries_simulations_and_adaptive_blocks(decision_course, capsys):
    from coursekit import assemble, course
    from coursekit.project import find_project

    (decision_course / "content.md").write_text(decision_content(GOOD_SECTION), encoding="utf-8")
    data = course.load(find_project(decision_course), "DB1")
    plan, errors, _ = assemble.build_plan(data, data["units"][0])
    assert not errors
    bricks = plan["lessons"][1]["bricks"]
    assert bricks[0]["type"] == "SIMULATION" and bricks[0]["data"]["id"] == "call" and bricks[0]["data"]["max_score"] == 2
    conditional = bricks[1]
    assert conditional["type"] == "CONDITIONAL" and conditional["data"]["condition"] == "call.risk >= 3"
    assert conditional["data"]["then"][0]["type"] == "TEXT" and conditional["data"]["else"][0]["type"] == "TEXT"
    _, errors, _, _ = assemble.write_plan(data, data["units"][0])
    assert any("not assembled in creator yet" in e for e in errors)


def test_simulation_words_do_not_count_and_only_the_else_branch_does():
    from coursekit import lang
    from coursekit.verify import Syntax, learner_words

    syntax = Syntax.for_tokens(lang.tokens("es"))
    lines = (SCENARIO + ADAPTIVE).splitlines()
    assert learner_words(lines, syntax, ("scenario",)) == len("No caíste, pero muchas personas sí lo hacen. Veamos por qué.".split())


def test_paths_and_points():
    from coursekit import simulation

    body = SCENARIO.splitlines()[1:-1]
    sim = simulation.parse("scenario", body, "x")
    assert not sim.errors
    assert sim.max_score == 2 and sim.min_score == -2
    assert sorted(p["ending"] for p in sim.paths) == ["leak", "leak", "safe", "safe"]
    assert simulation.grade(sim, 1) == 50
    assert sim.minutes({"scene": 1.5, "decision": 1, "debriefing": 1.5}) == 3 * 1.5 + 1 + 1.5


def test_condition_language():
    from coursekit import simulation as s

    env = {"risk": 3, "called": False, "trust": 1}
    assert s.test("risk >= 3 && !called", env)
    assert not s.test("risk > 3 || trust == 2", env)
    assert s.test("risk - 1 == 2", env)
    for bad in ("risk >=", "risk >= 3 &&", "(risk > 1", "risk y 3", "risk => 3"):
        with pytest.raises(s.ExpressionError):
            s.parse_expression(bad)



# ── Story bible ─────────────────────────────────────────────────────────────────────────────


def test_the_design_is_not_signed_without_the_story_bible(project, capsys):
    (project / ".env").write_text("COURSEKIT_USER_NAME=Ana\nCOURSEKIT_USER_EMAIL=ana@example.com\n", encoding="utf-8")
    assert main(["new", "Contraseñas", "1", "--code", "DB2", "--approach", "decision-based", "--language", "es"]) == 0
    course_dir = project / "courses" / "DB2"
    shutil.copy(FIXTURES / "matrix.json", course_dir / "design" / "matrix.json")
    capsys.readouterr()
    assert main(["approve", "design", "DB2", "--yes", "--no-commit"]) == 1
    assert "design/story.md is missing" in capsys.readouterr().err
    (course_dir / "design" / "story.md").write_text("---\nworld: ACME\ncharacters: [{role: x}]\n---\n", encoding="utf-8")
    assert main(["approve", "design", "DB2", "--yes", "--no-commit"]) == 1
    err = capsys.readouterr().err
    assert "'protagonist' is missing" in err and "character 1 has no 'name'" in err
    (course_dir / "design" / "story.md").write_text(STORY, encoding="utf-8")
    assert main(["approve", "design", "DB2", "--yes", "--no-commit"]) == 0
    approval = yaml.safe_load((course_dir / "course.yaml").read_text(encoding="utf-8"))["approvals"][-1]
    assert approval["story_sha256"]


def test_changing_the_story_after_the_sign_off_needs_a_new_one(decision_course, capsys):
    story = decision_course.parent.parent / "design" / "story.md"
    story.write_text(STORY + "\nUn cambio.\n", encoding="utf-8")
    code, out = verify(decision_course, GOOD_SECTION, capsys)
    assert code == 1


def test_characters_come_from_the_cast(decision_course, capsys):
    code, out = verify(decision_course, GOOD_SECTION.replace("{name: Técnico, expression", "{name: Lucía, expression"), capsys)
    assert code == 1
    assert "character 'Lucía' is not in the cast of design/story.md" in out


# ── Paths report ────────────────────────────────────────────────────────────────────────────


def test_paths_report(decision_course, capsys):
    (decision_course / "content.md").write_text(decision_content(GOOD_SECTION), encoding="utf-8")
    capsys.readouterr()
    assert main(["paths", "DB1"]) == 0
    assert "unit 1: 1 simulations → courses/DB1/reviews/unit-01-paths.md" in capsys.readouterr().out
    report = (decision_course.parent.parent / "reviews" / "unit-01-paths.md").read_text(encoding="utf-8")
    assert "## scenario `call` — La llamada de soporte" in report
    assert "```mermaid" in report and "flowchart TD" in report
    assert '-->|"Se la doy · risk +3, score -2"|' in report
    assert "| 1 | Le llamo yo a su extensión | safe (good) | 2 | 100 % |" in report
    assert "points from -2 to 2" in report


def test_paths_report_refuses_broken_simulations(decision_course, capsys):
    broken = GOOD_SECTION.replace("goto: leak, effects: {risk: 3}", "goto: nowhere, effects: {risk: 3}")
    (decision_course / "content.md").write_text(decision_content(broken), encoding="utf-8")
    capsys.readouterr()
    assert main(["paths", "DB1", "--unit", "1"]) == 1
    assert "scene 'nowhere' does not exist" in capsys.readouterr().err
