"""The mechanics of a scene beyond choosing: diagnosis (symptoms), investigation (clues), inbox and allocation (tasks graded
by how many things are right). They keep the graph of scenes: verify, paths, points and the checker."""

from coursekit import simulation as simmod
from coursekit.htmlkit import playcheck

BODY = """id: triage
title: La mañana de los avisos
state: {bien: 0, horas: 0}
scenes:
  bandeja:
    text: Clasifica lo que ha llegado.
    inbox:
      categories: [Reportar, Ignorar]
      items:
        - {text: Factura de un dominio raro, answer: Reportar}
        - {text: Boletín interno, answer: Ignorar}
        - {text: Aviso de contraseña con enlace, answer: Reportar}
      points: 2
      store: bien
    next: [{if: "bien >= 3", goto: fin_bien}, {goto: equipo}]
  equipo:
    text: Tu equipo va lento.
    symptoms: [Ventanas que se abren solas, El ventilador no para]
    clues: [{label: Registro, text: Un proceso extraño}, {label: Correo, text: Abriste un adjunto}]
    min_clues: 1
    choices:
      - {text: Es un programa malicioso, goto: reparto, score: 2}
      - {text: Es la red, goto: reparto, score: -1}
  reparto:
    text: Reparte las horas del equipo.
    allocation:
      total: 10
      options: [{label: Revisar, target: [4, 6]}, {label: Formar, target: [2, 4]}, {label: Informar, target: [1, 2]}]
      store: horas
    next: [{if: "horas == 3", goto: fin_bien}, {goto: fin_medio}]
  fin_bien: {text: Bien., ending: good, debriefing: D}
  fin_medio: {text: Casi., ending: mixed, debriefing: D}
"""


def parse(text=BODY):
    return simmod.parse("scenario", text.splitlines(), "x")


def test_the_mechanics_parse_and_their_results_are_the_ways_out():
    sim = parse()
    assert sim.errors == []
    # an inbox of 3 gives 4 results; 3 of them go to the investigation, whose 2 decisions lead to an allocation of 4 results
    assert len(sim.paths) == 1 + 3 * 2 * 4
    # two right in the inbox, the right cause and the three options in range (9) beat the whole inbox right (3 × 2)
    assert sim.max_score == 2 * 2 + 2 + 3
    assert max(p["score"] for p in sim.paths if len(p["steps"]) == 1) == 6
    assert all(p["ending"] in ("fin_bien", "fin_medio") for p in sim.paths)


def test_a_badly_shaped_mechanic_is_an_error():
    broken = (BODY.replace("answer: Ignorar", "answer: Archivar").replace("store: horas", "store: nada")
              .replace("target: [1, 2]", "target: [0, 2]").replace("min_clues: 1", "min_clues: 5"))
    text = "\n".join(parse(broken).errors)
    assert "every item needs 'text' and 'answer', one of the categories (Reportar, Ignorar)" in text
    assert "'store' must be a variable of 'state'" in text
    assert "every option needs 'label' and 'target'" in text
    assert "'min_clues' must be a number between 1 and the clues of the scene (2), not 5" in text
    with_choices = BODY.replace("    next: [{if: \"bien >= 3\"", "    choices: [{text: X, goto: equipo}]\n    next: [{if: \"bien >= 3\"")
    assert any("a task goes on only by 'next'" in e for e in parse(with_choices).errors)
    over = BODY.replace("target: [4, 6]", "target: [8, 9]")
    assert any("the minimums of the options add up to 11 and there are only 10" in e for e in parse(over).errors)


def test_the_time_counts_what_the_mechanics_show():
    plain = parse(BODY.replace("    symptoms: [Ventanas que se abren solas, El ventilador no para]\n", ""))
    assert parse().longest[0] > plain.longest[0]


def test_the_checker_replays_a_task_as_how_many_are_right():
    sim = parse()
    path = next(p for p in sim.paths if [label for _, label in p["steps"]] == ["task:1", "Es la red", "task:3"])
    assert playcheck.decision_steps(sim, path) == [{"task": 1}, 1, {"task": 3}]


def test_paths_shows_the_result_of_a_task():
    from coursekit import paths

    assert paths._step("task:2") == "task: 2 right" and paths._step("Es la red") == "Es la red"


def test_the_texts_of_the_mechanics_are_sanitised_for_the_page():
    from coursekit.htmlkit import render

    data = parse().data
    data["scenes"]["equipo"]["clues"][0]["text"] = "<script>x()</script>Un proceso"
    clean = render._clean_simulation(data)
    assert "<script" not in clean["scenes"]["equipo"]["clues"][0]["text"]
    assert clean["scenes"]["bandeja"]["inbox"]["items"][0]["text"] == "Factura de un dominio raro"
