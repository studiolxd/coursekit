"""Decision-based courses: the approach of a course and the rules of the approach."""

from __future__ import annotations

import pytest
import yaml

from coursekit.cli import main


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
