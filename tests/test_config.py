import json

import pytest

from coursekit import config, envfile
from coursekit.cli import main
from coursekit.project import ProjectNotFound, find_project


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.delenv("COURSEKIT_PROJECT", raising=False)
    (tmp_path / "project.yaml").write_text("name: Demo\nrules:\n  pages_per_hour: 8\n", encoding="utf-8")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "rules.yaml").write_text(
        "words_per_page: 450\ncontent:\n  placeholders_per_hour: 3\n", encoding="utf-8"
    )
    course = tmp_path / "courses" / "ABC101"
    course.mkdir(parents=True)
    (course / "course.yaml").write_text("code: ABC101\nrules:\n  pages_per_hour: 12\n", encoding="utf-8")
    (tmp_path / "courses" / "ABC101" / "content").mkdir()
    return tmp_path


def test_root_is_found_from_a_subfolder(project, monkeypatch):
    monkeypatch.chdir(project / "courses" / "ABC101" / "content")
    assert find_project().root == project


def test_explicit_root_wins(project, tmp_path_factory, monkeypatch):
    monkeypatch.chdir(tmp_path_factory.mktemp("elsewhere"))
    monkeypatch.setenv("COURSEKIT_PROJECT", str(project))
    assert find_project().root == project


def test_no_project(tmp_path, monkeypatch):
    monkeypatch.delenv("COURSEKIT_PROJECT", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ProjectNotFound):
        find_project()


def test_layers_merge_in_order(project):
    p = find_project(project)
    course = {"rules": {"pages_per_hour": 12}}
    layered = config.effective("rules", p, course)
    assert layered.get("pages_per_hour") == 12
    assert layered.origin[("pages_per_hour",)] == "course"
    assert layered.get("words_per_page") == 450
    assert layered.origin[("words_per_page",)] == "config"
    assert layered.get("content", "placeholders_per_hour") == 3
    # siblings of an overridden key keep the package value and origin
    assert layered.get("content", "questions_per_objective") == 5
    assert layered.origin[("content", "questions_per_objective")] == "package"


def test_project_yaml_overrides_config_folder(project):
    layered = config.effective("rules", find_project(project))
    assert layered.get("pages_per_hour") == 8
    assert layered.origin[("pages_per_hour",)] == "project"


def test_lists_replace(project):
    p = find_project(project)
    layered = config.effective("rules", p, {"rules": {"content": {"placeholder_types": ["Imagen"]}}})
    assert layered.get("content", "placeholder_types") == ["Imagen"]
    assert layered.origin[("content", "placeholder_types")] == "course"


def test_package_defaults_are_not_mutated(project):
    config.effective("rules", find_project(project), {"rules": {"content": {"word_margin": 0.5}}})
    assert config.package_defaults("rules")["content"]["word_margin"] == 0.03


def test_unknown_name():
    with pytest.raises(ValueError):
        config.effective("nope")


def test_env_file_never_overrides_the_shell(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        'A_KEY=from-file\nexport B_KEY="quoted # kept"\nC_KEY=plain # comment\nSHELL_KEY=file\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("SHELL_KEY", "shell")
    for key in ("A_KEY", "B_KEY", "C_KEY"):
        monkeypatch.delenv(key, raising=False)
    values = envfile.load(env)
    assert values["B_KEY"] == "quoted # kept"
    assert values["C_KEY"] == "plain"
    import os

    assert os.environ["A_KEY"] == "from-file"
    assert os.environ["SHELL_KEY"] == "shell"


def test_cli_config_shows_origins(project, monkeypatch, capsys):
    monkeypatch.chdir(project)
    assert main(["config", "rules", "--course", "ABC101", "--changed"]) == 0
    out = capsys.readouterr().out
    assert "pages_per_hour" in out and "(course)" in out
    assert "words_per_page" in out and "(config)" in out
    assert "(package)" not in out


def test_cli_config_json(project, monkeypatch, capsys):
    monkeypatch.chdir(project)
    assert main(["config", "delivery", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["export"]["standard"] == "scorm_1_2"


def test_cli_outside_a_project(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("COURSEKIT_PROJECT", raising=False)
    monkeypatch.chdir(tmp_path)
    assert main(["config"]) == 1
    assert "coursekit init" in capsys.readouterr().err
