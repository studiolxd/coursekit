"""Launchers with fake tools: no model is ever called."""

import shutil
from pathlib import Path

import pytest
import yaml

from coursekit import launch
from coursekit.cli import main
from coursekit.states import set_unit_status

FIXTURES = Path(__file__).parent / "fixtures"


class FakeTools:
    """Records each launch; `effect(args)` can change the course like the agent would."""

    def __init__(self, monkeypatch):
        self.calls: list[list[str]] = []
        self.effect = None
        monkeypatch.setattr(launch.shutil, "which", lambda tool: f"/fake/{tool}")
        monkeypatch.setattr(launch.subprocess, "call", self.call)

    def call(self, args, **kwargs):
        self.calls.append(list(args))
        if "stdout" in kwargs:  # headless: write a session log like the tool would
            kwargs["stdout"].write('{"type": "result", "result": "Done: unit written."}\n')
        if self.effect:
            return self.effect(args) or 0
        return 0


@pytest.fixture
def course(tmp_path, monkeypatch):
    for key in ("COURSEKIT_PROJECT", *(f"{r}_{k}" for r in ("WRITER", "REVIEWER", "DESIGN") for k in ("AGENT", "MODEL"))):
        monkeypatch.delenv(key, raising=False)
    root = tmp_path / "demo"
    assert main(["init", str(root), "--yes", "--no-git"]) == 0
    monkeypatch.chdir(root)
    (root / ".env").write_text("COURSEKIT_USER_NAME=Ana\nCOURSEKIT_USER_EMAIL=ana@example.com\n", encoding="utf-8")
    assert main(["new", "Contraseñas", "1", "--code", "PWD"]) == 0
    course_dir = root / "courses" / "PWD"
    shutil.copy(FIXTURES / "matrix.json", course_dir / "design" / "matrix.json")
    assert main(["approve", "design", "PWD", "--yes", "--no-commit"]) == 0
    return course_dir


def unit(course_dir, key):
    return yaml.safe_load((course_dir / "course.yaml").read_text(encoding="utf-8"))["units"][0].get(key)


def test_write_interactive_with_claude(course, monkeypatch):
    tools = FakeTools(monkeypatch)
    monkeypatch.setenv("WRITER_MODEL", "sonnet")
    assert main(["write", "PWD", "1"]) == 0
    assert tools.calls == [["/fake/claude", "--model", "sonnet", "/write-unit PWD 1"]]
    assert unit(course, "written_with") == "claude · sonnet"


def test_one_off_agent_override(course, monkeypatch):
    tools = FakeTools(monkeypatch)
    monkeypatch.setenv("WRITER_AGENT", "claude")
    monkeypatch.setenv("WRITER_MODEL", "sonnet")
    assert main(["write", "PWD", "1", "--agent", "codex"]) == 0
    assert tools.calls[0][0] == "/fake/codex"
    assert "--model" not in tools.calls[0]  # --agent alone: that tool's default model
    assert ".coursekit/agents/commands/write-unit.md" in tools.calls[0][-1]
    assert unit(course, "written_with") == "codex · default model"


def test_headless_sequence_and_logs(course, monkeypatch, capsys):
    tools = FakeTools(monkeypatch)
    tools.effect = lambda args: set_unit_status(course, 1, "verified") and 0
    assert main(["write", "PWD", "--headless"]) == 0
    args = tools.calls[0]
    assert args[:2] == ["/fake/claude", "-p"]
    assert "Bash(coursekit approve:*)" in args[args.index("--disallowedTools") + 1 :]
    assert "nobody can answer you" in args[2]
    out = capsys.readouterr().out
    assert "Done: unit written." in out
    assert "unit 1: verified · session in .cache/logs/PWD-u01-write-" in out
    # nothing left to write
    assert main(["write", "PWD"]) == 0
    assert "nothing to write in PWD" in capsys.readouterr().out


def test_headless_stops_when_the_unit_does_not_end_verified(course, monkeypatch, capsys):
    FakeTools(monkeypatch)
    assert main(["write", "PWD", "--headless"]) == 1
    assert "unit 1: pending" in capsys.readouterr().out


def test_review_warns_on_same_model_and_records_reviewer(course, monkeypatch, capsys):
    tools = FakeTools(monkeypatch)
    monkeypatch.setenv("WRITER_MODEL", "opus")
    monkeypatch.setenv("REVIEWER_AGENT", "claude")
    monkeypatch.setenv("REVIEWER_MODEL", "opus")
    assert main(["write", "PWD", "1"]) == 0
    set_unit_status(course, 1, "verified")
    capsys.readouterr()
    assert main(["review", "PWD"]) == 0
    assert "the same tool and model as this review" in capsys.readouterr().err
    assert unit(course, "reviewed_with") == "claude · opus"
    assert "You are the reviewer (claude · opus)" in tools.calls[-1][-1]


def test_partial_review_from_fingerprints(course, monkeypatch):
    tools = FakeTools(monkeypatch)
    monkeypatch.setenv("REVIEWER_AGENT", "opencode")
    monkeypatch.setenv("REVIEWER_MODEL", "acme/model")
    data_path = course / "course.yaml"
    data = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    data["units"][0]["status"] = "verified"
    data["units"][0]["reviewed_parts"] = {"section 1": "0000", "section 2": "x", "section 3": "y"}
    data_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    assert main(["review", "PWD", "1"]) == 0
    text = tools.calls[-1][-1]
    assert tools.calls[-1][:2] == ["/fake/opencode", "--prompt"]
    assert "PARTIAL REVIEW" in text and "section 1" in text
    # the opencode reviewer agent carries the model of the .env
    assert "model: acme/model" in (course.parent.parent / ".opencode/agent/reviewer.md").read_text(encoding="utf-8")
    assert main(["review", "PWD", "1", "--full"]) == 0
    assert "PARTIAL REVIEW" not in tools.calls[-1][-1]
    assert main(["review", "PWD", "1", "--parts", "section 2"]) == 0
    assert "section 2." in tools.calls[-1][-1]


def test_run_uses_the_role_of_the_command(course, monkeypatch, capsys):
    tools = FakeTools(monkeypatch)
    monkeypatch.setenv("ASSEMBLY_AGENT", "codex")
    monkeypatch.setenv("ASSEMBLY_MODEL", "gpt-x")
    assert main(["run", "assemble", "PWD", "1", "--headless"]) == 0
    args = tools.calls[0]
    assert args[:4] == ["/fake/codex", "exec", "--model", "gpt-x"]
    assert '.coursekit/agents/commands/assemble.md with the arguments "PWD 1"' in args[-1]
    assert "with the assembly agent (codex · gpt-x)" in capsys.readouterr().out


def test_run_design_headless_with_claude_allows_the_mcp(course, monkeypatch):
    tools = FakeTools(monkeypatch)
    assert main(["run", "design-change", "PWD", "más", "práctica", "--headless"]) == 0
    args = tools.calls[0]
    assert args[2].startswith("/design-change PWD más práctica")
    assert "mcp__slxd-creator" in args


def test_roles_and_bad_tool(course, monkeypatch, capsys):
    FakeTools(monkeypatch)
    assert main(["roles"]) == 0
    out = capsys.readouterr().out
    assert "writer" in out and "assembly" in out
    monkeypatch.setenv("WRITER_AGENT", "nope")
    assert main(["write", "PWD", "1"]) == 1
    assert "WRITER_AGENT=nope is not valid" in capsys.readouterr().err


def test_write_rejects_review_options(course, capsys):
    assert main(["write", "PWD", "1", "--full"]) == 2


def test_run_passes_the_command_options_through(course, monkeypatch):
    tools = FakeTools(monkeypatch)
    assert main(["run", "new-course", '"Curso nuevo"', "2", "--code", "ABC", "--model", "opus"]) == 0
    assert tools.calls[0] == ["/fake/claude", "--model", "opus", '/new-course "Curso nuevo" 2 --code ABC']
