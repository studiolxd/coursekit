"""Decision-based courses: the approach of a course and the rules of the approach."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

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
    assert "decision_based.decision_seconds" in out


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
    plan, errors, _ = assemble.build_plan(data, data["units"][0], simulations=True)
    assert not errors
    bricks = plan["lessons"][1]["bricks"]
    assert bricks[0]["type"] == "SIMULATION" and bricks[0]["data"]["id"] == "call" and bricks[0]["data"]["max_score"] == 2
    conditional = bricks[1]
    assert conditional["type"] == "CONDITIONAL" and conditional["data"]["condition"] == "call.risk >= 3"
    assert conditional["data"]["then"][0]["type"] == "TEXT" and conditional["data"]["else"][0]["type"] == "TEXT"
    creator_plan, errors, warnings, counts = assemble.write_plan(data, data["units"][0])
    assert not errors and "SIMULATION" not in counts and "CONDITIONAL" not in counts
    first = creator_plan["lessons"][1]["bricks"]
    assert first[0]["type"] == "NOTE" and first[0]["meta"]["asset"] == "SIM-CALL"
    assert first[1]["type"] == "TEXT" and "No caíste" in first[1]["data"]["content"]["content"]
    assert any("simulation 'call' is not uploaded" in w for w in warnings)
    assert any("the neutral version (:::else)" in w for w in warnings)


def test_scored_simulations_of_the_assessment_need_an_activities_section(decision_course, capsys):
    assessment = ASSESSMENT + "\n" + SCENARIO.replace("id: call", "id: final")
    (decision_course / "assessment.md").write_text(assessment, encoding="utf-8")
    code, out = verify(decision_course, GOOD_SECTION, capsys)
    assert code == 1
    assert "the unit has no activities section to count them in" in out


def test_a_simulation_cannot_take_longer_than_its_section(decision_course, capsys):
    long_text = " ".join(["palabra"] * 400)
    code, out = verify(decision_course, GOOD_SECTION.replace("text: Suena el teléfono. Alguien de soporte te pide tu contraseña.",
                                                            f"text: {long_text}"), capsys)
    assert code == 1
    assert "simulation 'call' takes" in out and "more than the" in out


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
    # longest path: begin + "Se la doy" + leak with its variant? (risk 3: no) + debriefing, or the hotspot path through note
    words, decisions = sim.longest
    assert decisions == 1 and words > 20
    assert sim.time_words(5000, 15) == round(words + 15 * 5000 / 3600)
    assert sim.minutes(5000, 15) == round(60 * sim.time_words(5000, 15) / 5000, 1)


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


# ── html backend ────────────────────────────────────────────────────────────────────────────


def test_the_html_backend_renders_simulations_and_adaptive_blocks(decision_course):
    from coursekit import assemble, course, lang
    from coursekit.htmlkit import render
    from coursekit.project import find_project

    (decision_course / "content.md").write_text(decision_content(GOOD_SECTION), encoding="utf-8")
    data = course.load(find_project(decision_course), "DB1")
    plan, errors, warnings = assemble.build_plan(data, data["units"][0], simulations=True)
    assert not errors and not render.unsupported_bricks(plan)
    assert any("images not produced yet" in w for w in warnings)
    html = render.lesson(plan["lessons"][1], lang.tokens("es")["player"])
    assert '<section class="ck-sim ck-sim-scenario ck-sim-on-phone" data-sim="call"' in html
    payload = html.split('<script type="application/json" class="ck-sim-data">')[1].split("</script>")[0]
    sim = json.loads(payload)
    assert sim["max_score"] == 2 and sim["rewind"] is True and sim["scenes"]["begin"]["text"].startswith("<p>Suena")
    assert sim["scenes"]["begin"]["characters"][0]["_portrait"] is None
    assert '<div class="ck-adaptive" data-condition="call.risk &gt;= 3"><div class="ck-if" hidden>' in html
    assert '<div class="ck-else"><div class="ck-text"><p>No caíste' in html
    assert '<div class="ck-sim-static"><p>Suena el teléfono.' in html  # readable without JavaScript


def test_the_script_of_a_simulation_cannot_close_its_tag():
    from coursekit.htmlkit import render

    brick = {"type": "SIMULATION", "meta": {}, "data": {"id": "x", "kind": "scenario", "title": "T", "scenes": {
        "a": {"text": "<p>see </script><script>alert(1)</script></p>", "ending": "good", "debriefing": "<p>d</p>"}}}}
    html = render.simulation(brick, render.Ctx({}, "U1-S1"))
    assert "<script>alert" not in html and html.count("</script>") == 1


def test_the_player_reads_conditions_like_python(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    import subprocess
    from importlib import resources

    from coursekit import simulation

    source = Path(str(resources.files("coursekit.templates.html"))) / "player" / "expr.js"
    shutil.copy(source, tmp_path / "expr.mjs")
    cases = [("risk >= 3 && !called", {"risk": 3, "called": False}), ("risk > 3 || trust == 2", {"risk": 3, "trust": 1}),
             ("-(a - 2) < 0 || b", {"a": 1, "b": True}), ("call.risk + 1 >= 4", {"call.risk": 3}), ("!(x != 0)", {})]
    script = ("import { test } from './expr.mjs';\n"
              f"const cases = {json.dumps(cases)};\n"
              "console.log(JSON.stringify(cases.map(([c, env]) => test(c, env))));\n")
    (tmp_path / "run.mjs").write_text(script, encoding="utf-8")
    out = subprocess.run([node, "run.mjs"], cwd=tmp_path, capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == [simulation.test(c, env) for c, env in cases]


def test_unknown_and_missing_keys_are_reported():
    from coursekit import simulation

    sim = simulation.parse("scenario", ["id: x", "scenes:", "  a:", "    choices:",
                                        "      - {text: Yes, of course, goto: b}", "  b: {text: B, ending: good, debriefing: D}"], "x")
    assert any("missing 'title'" in e for e in sim.errors)
    assert any("unknown key 'scenes.a.choices[0].of course'" in e for e in sim.errors)
    assert any("missing 'scenes.a.text'" in e for e in sim.errors)


def test_screens_of_the_skins_are_checked():
    from coursekit import simulation

    def errors(top, scene_extra=""):
        body = ["id: x", "title: T", *top, "scenes:", "  a:", "    text: A", *scene_extra.splitlines(),
                "  b: {text: B, ending: good, debriefing: D}"]
        return simulation.parse("scenario", body, "x").errors

    mail = ["skin: mail-desktop", "screen:", "  message: {from: Finanzas, address: f@x.example, subject: Factura, body: Paga ya}"]
    assert errors(mail, "    hotspots:\n      - {label: Remitente, target: address, goto: b}") == []
    assert any("invalid target 'url'" in e for e in errors(mail, "    hotspots:\n      - {label: X, target: url, goto: b}"))
    assert any("'target' needs a 'skin'" in e for e in errors([], "    hotspots:\n      - {label: X, target: url, goto: b}"))
    choice = "    choices: [{text: Y, goto: b}]"
    assert any("unknown key 'screen.channel'" in e for e in errors(["skin: messenger", "screen: {channel: general}"], choice))
    assert any("invalid state 'ringing'" in e for e in errors(["skin: phone", "screen: {state: ringing}"], choice))
    assert any("'screen' needs a 'skin'" in e for e in errors(["screen: {url: x}"], choice))


# ── Media of the simulations ────────────────────────────────────────────────────────────────


def test_media_extract_adds_the_images_of_the_simulations(decision_course, capsys):
    section = GOOD_SECTION.replace("  begin:\n", "  begin:\n    background: Puesto de Marta en ACME\n", 1)
    (decision_course / "content.md").write_text(decision_content(section), encoding="utf-8")
    assert main(["media", "extract", "DB1"]) == 0
    manifest = yaml.safe_load((decision_course.parent.parent / "media" / "manifest.yaml").read_text(encoding="utf-8"))
    by_id = {a["id"]: a for a in manifest["assets"]}
    assert by_id["BG-PUESTO-DE-MARTA-EN-ACME"]["kind"] == "background" and by_id["BG-PUESTO-DE-MARTA-EN-ACME"]["section"] == 2
    assert by_id["CHAR-TECNICO"]["kind"] == "portrait"
    assert by_id["CHAR-TECNICO-CON-PRISA"]["expression"] == "con prisa"
    assert "con prisa" in by_id["CHAR-TECNICO-CON-PRISA"]["description"]
    capsys.readouterr()
    assert main(["media", "plan", "DB1"]) == 0
    out = capsys.readouterr().out
    assert "visual style of the simulations: illustration" in out
    assert "the style sheet of DB1 is not signed" in out


def test_the_style_sheet_is_signed_before_the_images(decision_course, capsys):
    course_dir = decision_course.parent.parent
    section = GOOD_SECTION.replace("  begin:\n", "  begin:\n    background: Puesto de Marta en ACME\n", 1)
    (decision_course / "content.md").write_text(decision_content(section), encoding="utf-8")
    assert main(["media", "extract", "DB1"]) == 0
    capsys.readouterr()
    assert main(["media", "set", "DB1", "BG-PUESTO-DE-MARTA-EN-ACME", "--status", "produced"]) == 1
    assert "style sheet of DB1 is not signed" in capsys.readouterr().err
    assert main(["approve", "style", "DB1", "--yes", "--no-commit"]) == 1
    assert "no style samples" in capsys.readouterr().err
    (course_dir / "media" / "style").mkdir(parents=True)
    (course_dir / "media" / "style" / "background.png").write_bytes(b"png")
    assert main(["approve", "style", "DB1", "--yes", "--no-commit"]) == 0
    approval = yaml.safe_load((course_dir / "course.yaml").read_text(encoding="utf-8"))["approvals"][-1]
    assert approval["gate"] == "style" and approval["files"][0]["name"] == "background.png"
    assert main(["media", "set", "DB1", "BG-PUESTO-DE-MARTA-EN-ACME", "--status", "produced"]) == 0


def test_an_unknown_visual_style_is_an_error(decision_course, capsys):
    project = decision_course.parent.parent.parent.parent
    (project / "config" / "media.yaml").write_text("visual:\n  style: watercolour\n", encoding="utf-8")
    section = GOOD_SECTION.replace("  begin:\n", "  begin:\n    background: Puesto de Marta en ACME\n", 1)
    (decision_course / "content.md").write_text(decision_content(section), encoding="utf-8")
    assert main(["media", "extract", "DB1"]) == 0
    capsys.readouterr()
    assert main(["media", "plan", "DB1"]) == 1
    assert "media › visual › style is 'watercolour'" in capsys.readouterr().err


def test_a_simulation_becomes_an_embed_package_for_creator(decision_course, capsys):
    from coursekit import assemble, course
    from coursekit.project import find_project

    course_dir = decision_course.parent.parent
    (decision_course / "content.md").write_text(decision_content(GOOD_SECTION), encoding="utf-8")
    assert main(["media", "extract", "DB1"]) == 0
    capsys.readouterr()
    assert main(["media", "embed", "DB1", "SIM-CALL"]) == 0
    page = (course_dir / "media" / "src" / "SIM-CALL" / "index.html").read_text(encoding="utf-8")
    assert 'data-sim="call"' in page and "const __expr = (() =>" in page and "__simulation.initSimulations" in page
    assert "import " not in page.split("<script>")[1] and "export " not in page.split("<script>")[1]
    assert main(["media", "set", "DB1", "SIM-CALL", "--status", "uploaded", "--asset-path", "embeds/sim-call", "--force"]) == 0
    data = course.load(find_project(decision_course), "DB1")
    creator_plan, errors, _, _ = assemble.write_plan(data, data["units"][0])
    embed = creator_plan["lessons"][1]["bricks"][0]
    assert embed["type"] == "EMBED" and embed["data"]["properties"]["embedFolderPrefix"] == "embeds/sim-call"


def test_download_writes_inside_the_project_only(project, monkeypatch, capsys):
    from coursekit import mediatools

    monkeypatch.setattr(mediatools, "fetch", lambda req, timeout=300: b"xlsx-bytes")
    assert main(["download", "https://x.example/export", "--out", "courses/a.xlsx"]) == 0
    assert (project / "courses" / "a.xlsx").read_bytes() == b"xlsx-bytes"
    assert main(["download", "https://x.example/export", "--out", "../fuera.xlsx"]) == 1
    assert "outside the project" in capsys.readouterr().err
    assert main(["download", "http://x.example/export", "--out", "courses/b.xlsx"]) == 1


def test_simulation_ids_have_no_hyphen():
    from coursekit import simulation

    sim = simulation.parse("scenario", ["id: sim-u1", "title: T", "scenes:", "  a: {text: A, ending: good, debriefing: D}"], "x")
    assert any("invalid id 'sim-u1'" in e for e in sim.errors)


def test_a_simulation_in_any_part_of_an_assessment_activity_is_assembled(decision_course):
    from coursekit import assemble, course
    from coursekit.project import find_project

    final = SCENARIO.replace("id: call", "id: final")
    assessment = ASSESSMENT.replace("### Banco de preguntas", "### Desarrollo e implementación\n\n" + final + "\n### Banco de preguntas")
    (decision_course / "assessment.md").write_text(assessment, encoding="utf-8")
    (decision_course / "content.md").write_text(decision_content(GOOD_SECTION), encoding="utf-8")
    data = course.load(find_project(decision_course), "DB1")
    plan, errors, _ = assemble.build_plan(data, data["units"][0], simulations=True)
    assert not errors
    test = next(lesson for lesson in plan["lessons"] if lesson["type"] == "evaluation")
    assert [b["data"]["id"] for b in test["bricks"] if b["type"] == "SIMULATION"] == ["final"]


def test_a_scene_can_happen_in_another_application():
    from coursekit import simulation

    body = ["id: x", "title: T", "skin: chat-workspace", "screen: {channel: general}", "scenes:",
            "  a:", "    text: Ramón te avisa por el chat.", "    screen: {messages: [{from: Ramón, text: Mira el correo}]}",
            "    choices: [{text: Abro el correo, goto: b}]",
            "  b:", "    skin: mail-desktop", "    text: El correo.", "    screen: {message: {from: X, address: x@y.example, subject: S}}",
            "    hotspots: [{label: La dirección, target: address, goto: c}]",
            "  c: {text: C, ending: good, debriefing: D}"]
    assert simulation.parse("scenario", body, "x").errors == []
    bad = [line.replace("target: address", "target: message:1") for line in body]
    assert any("invalid target 'message:1'" in e for e in simulation.parse("scenario", bad, "x").errors)
    bad = [line.replace("skin: mail-desktop", "skin: fax") for line in body]
    assert any("unknown skin 'fax'" in e for e in simulation.parse("scenario", bad, "x").errors)


def test_a_section_far_above_its_minimum_gets_a_warning(decision_course, capsys):
    code, out = verify(decision_course, GOOD_SECTION, capsys)
    assert code == 0  # only a warning
    assert "above the minimum (120): the section takes longer than its hours" in out


def test_short_names_and_the_learner_in_the_dialogues(decision_course, capsys):
    from coursekit import course, simulation, story
    from coursekit.project import find_project

    data = course.load(find_project(decision_course), "DB1")
    assert story.canonical(data, "Marta") == "Marta" and story.canonical(data, "técnico") == "Técnico"
    assert story.canonical(data, "Lucía") is None and story.is_learner(data, "Tú")
    assert simulation.portrait_id("Marta", "neutral") == simulation.portrait_id("Marta") == "CHAR-MARTA"
    dialog = ":::dialog\n**Marta:** Hola.\n**Tú:** Hola, Marta.\n**Lucía:** ¿Y yo?\n:::\n"
    code, out = verify(decision_course, GOOD_SECTION + "\n" + dialog, capsys)
    assert code == 1
    assert "'Lucía' speaks in a dialogue but is not in the cast" in out
    assert "'Marta' speaks" not in out and "'Tú' speaks" not in out
    capsys.readouterr()
    assert main(["media", "extract", "DB1"]) == 0
    manifest = yaml.safe_load((decision_course.parent.parent / "media" / "manifest.yaml").read_text(encoding="utf-8"))
    ids = {a["id"] for a in manifest["assets"]}
    assert "CHAR-MARTA" in ids and "CHAR-TU" not in ids
