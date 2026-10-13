"""Skins of the project (components/skins/<name>.yaml and .js): they join the built-in ones for verify, paths, the player
and the packages."""

from coursekit import agents, simulation
from coursekit.project import Project

YAML = "screen: [queue, ticket]\ntargets: [requester, priority, 'ticket:']\n"
SIM = """id: t
title: El ticket
skin: ticket-desk
screen: {queue: Cola, ticket: {subject: Urgente}}
scenes:
  a:
    text: Mira el ticket.
    hotspots:
      - {label: Remitente, target: requester, goto: b}
      - {label: Ticket, target: "ticket:1", goto: b}
  b: {text: Hecho., ending: good, debriefing: D}
""".splitlines()


def skins_dir(root):
    folder = root / "components" / "skins"
    folder.mkdir(parents=True)
    return folder


def test_a_skin_of_the_project_is_valid_like_the_built_in_ones(tmp_path):
    folder = skins_dir(tmp_path)
    (folder / "ticket-desk.yaml").write_text(YAML, encoding="utf-8")
    (folder / "ticket-desk.js").write_text("window.coursekitSkins = {};", encoding="utf-8")
    try:
        assert simulation.use_project_skins(tmp_path) == []
        assert "ticket-desk" in simulation.SKINS and simulation.TARGETS["ticket-desk"] == ("requester", "priority", "ticket:")
        assert simulation.parse("scenario", SIM, "x").errors == []
        wrong = [line.replace("target: requester", "target: sender") for line in SIM]
        assert any("invalid target 'sender' for this skin" in e for e in simulation.parse("scenario", wrong, "x").errors)
        extra = [line.replace("queue: Cola", "queue: Cola, colour: red") for line in SIM]
        assert any("unknown key 'screen.colour'" in e for e in simulation.parse("scenario", extra, "x").errors)
    finally:
        simulation.use_project_skins(tmp_path / "nothing")
    assert "ticket-desk" not in simulation.SKINS  # another project: only the built-in ones


def test_a_skin_badly_declared_is_reported_and_not_used(tmp_path):
    folder = skins_dir(tmp_path)
    (folder / "phone.yaml").write_text(YAML, encoding="utf-8")
    (folder / "phone.js").write_text("", encoding="utf-8")
    (folder / "no-js.yaml").write_text(YAML, encoding="utf-8")
    (folder / "broken.yaml").write_text("screen: queue\n", encoding="utf-8")
    (folder / "broken.js").write_text("", encoding="utf-8")
    try:
        problems = "\n".join(simulation.use_project_skins(tmp_path))
        assert "phone.yaml: the name of the skin is the file's" in problems
        assert "no-js.yaml: no-js.js, which draws it, is missing" in problems
        assert "broken.yaml: a skin declares 'screen'" in problems
        assert simulation.SKINS == list(simulation.BUILTIN_SKINS)
    finally:
        simulation.use_project_skins(tmp_path / "nothing")


def test_the_writer_is_told_the_skins_of_the_project(tmp_path):
    project = Project(tmp_path)
    assert agents.project_skins(project) == "none"
    folder = skins_dir(tmp_path)
    (folder / "ticket-desk.yaml").write_text(YAML + "chat: true\n", encoding="utf-8")
    (folder / "ticket-desk.js").write_text("", encoding="utf-8")
    try:
        assert agents.project_skins(project) == "`ticket-desk` (screen: queue, ticket; targets: requester, priority, ticket:N; chat)"
    finally:
        simulation.use_project_skins(tmp_path / "nothing")
