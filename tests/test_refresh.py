"""A project follows the installed coursekit: the first command after an update regenerates what coursekit generates in it."""

import json

import pytest

from coursekit import refresh
from coursekit.cli import main


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.delenv("COURSEKIT_PROJECT", raising=False)
    root = tmp_path / "demo"
    assert main(["init", str(root), "--yes", "--no-git"]) == 0
    monkeypatch.chdir(root)
    monkeypatch.delenv(refresh.OFF_ENV)
    return root


def stamp(root) -> dict:
    return json.loads((root / refresh.STAMP_FILE).read_text(encoding="utf-8"))


def test_a_new_project_is_stamped_and_the_next_command_refreshes_nothing(project, capsys):
    assert stamp(project)["fingerprint"] == refresh.fingerprint()
    capsys.readouterr()
    assert main(["status"]) in (0, 1)
    assert "brought up to date" not in capsys.readouterr().err


def test_after_an_update_the_first_command_refreshes_the_agents_and_the_managed_files(project, monkeypatch, capsys):
    skill = next((project / ".claude" / "skills").glob("*/SKILL.md"))
    skill.write_text(skill.read_text(encoding="utf-8") + "\nstale tail\n", encoding="utf-8")  # what an older coursekit left
    (project / "AGENTS.md").write_text("old managed text", encoding="utf-8")
    state = json.loads((project / ".coursekit" / "generated.json").read_text(encoding="utf-8"))
    state["files"]["AGENTS.md"] = __import__("hashlib").sha256(b"old managed text").hexdigest()  # recorded: unedited by the person
    (project / ".coursekit" / "generated.json").write_text(json.dumps(state), encoding="utf-8")
    (project / refresh.STAMP_FILE).write_text(json.dumps({"fingerprint": "older", "version": "0.0.1"}), encoding="utf-8")
    capsys.readouterr()
    assert main(["status"]) in (0, 1)
    err = capsys.readouterr().err
    assert "brought up to date" in err
    assert "stale tail" not in skill.read_text(encoding="utf-8")
    assert (project / "AGENTS.md").read_text(encoding="utf-8") != "old managed text"
    assert stamp(project)["fingerprint"] == refresh.fingerprint()


def test_a_managed_file_edited_by_hand_is_kept_and_said(project, capsys):
    (project / "AGENTS.md").write_text("mine", encoding="utf-8")
    (project / refresh.STAMP_FILE).write_text(json.dumps({"fingerprint": "older", "version": "0.0.1"}), encoding="utf-8")
    capsys.readouterr()
    assert main(["status"]) in (0, 1)
    assert "kept (edited by hand" in capsys.readouterr().err
    assert (project / "AGENTS.md").read_text(encoding="utf-8") == "mine"


def test_the_refresh_can_be_turned_off_and_never_blocks_a_command(project, monkeypatch, capsys):
    (project / refresh.STAMP_FILE).write_text(json.dumps({"fingerprint": "older"}), encoding="utf-8")
    monkeypatch.setenv(refresh.OFF_ENV, "1")
    assert main(["status"]) in (0, 1)
    assert stamp(project)["fingerprint"] == "older"
    monkeypatch.delenv(refresh.OFF_ENV)

    def boom(root):
        raise RuntimeError("disk full")

    monkeypatch.setattr(refresh.initmod, "update", boom)
    capsys.readouterr()
    assert main(["status"]) in (0, 1)
    assert "could not be brought up to date (disk full)" in capsys.readouterr().err


def test_outside_a_project_nothing_is_refreshed(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("COURSEKIT_PROJECT", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(refresh.OFF_ENV)
    assert main(["status"]) == 1
    assert "brought up to date" not in capsys.readouterr().err
