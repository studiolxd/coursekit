import json

import yaml

from coursekit import init
from coursekit.cli import main


def run_init(folder, *extra):
    return main(["init", str(folder), "--yes", "--no-git", *extra])


def test_creates_a_project(tmp_path, capsys):
    root = tmp_path / "demo"
    assert run_init(root, "--client", "ACME", "--tone", "cercano", "--backend", "html") == 0
    data = yaml.safe_load((root / "project.yaml").read_text(encoding="utf-8"))
    assert data["name"] == "demo"
    assert data["client"] == "ACME"
    assert data["content_language"] == "es"
    assert data["address"] == "tu"
    assert data["assembly"]["backend"] == "html"
    for path in ("AGENTS.md", "CLAUDE.md", ".env.example", ".gitignore", "brief/notes.md", "brief/links.md"):
        assert (root / path).exists(), path
    for folder in ("courses", "brief/sources", "config", "theme"):
        assert (root / folder).is_dir(), folder
    assert "ACME" in (root / "AGENTS.md").read_text(encoding="utf-8")
    state = json.loads((root / ".coursekit" / "generated.json").read_text(encoding="utf-8"))
    assert set(state["files"]) == set(init.MANAGED.values())
    assert "next:" in capsys.readouterr().out


def test_english_defaults_to_you(tmp_path):
    root = tmp_path / "en"
    assert run_init(root, "--language", "en") == 0
    data = yaml.safe_load((root / "project.yaml").read_text(encoding="utf-8"))
    assert data["address"] == "you"
    assert data["ui_language"] == "en"


def test_bad_address(tmp_path, capsys):
    assert run_init(tmp_path / "x", "--language", "en", "--address", "usted") == 1
    assert "--address" in capsys.readouterr().err


def test_refuses_an_existing_project(tmp_path, capsys):
    root = tmp_path / "demo"
    assert run_init(root) == 0
    assert run_init(root) == 1
    assert "--update" in capsys.readouterr().err


def test_does_not_overwrite_files_it_did_not_write(tmp_path):
    root = tmp_path / "existing"
    root.mkdir()
    (root / "AGENTS.md").write_text("mine\n", encoding="utf-8")
    assert run_init(root) == 0
    assert (root / "AGENTS.md").read_text(encoding="utf-8") == "mine\n"


def test_update_refreshes_untouched_files_and_keeps_edited_ones(tmp_path, monkeypatch, capsys):
    root = tmp_path / "demo"
    assert run_init(root, "--client", "ACME") == 0
    (root / ".gitignore").write_text("edited by hand\n", encoding="utf-8")
    (root / "CLAUDE.md").unlink()
    # change the project: AGENTS.md (untouched) must follow it
    project = (root / "project.yaml").read_text(encoding="utf-8").replace('client: "ACME"', 'client: "Globex"')
    (root / "project.yaml").write_text(project, encoding="utf-8")
    capsys.readouterr()
    assert main(["init", str(root), "--update"]) == 0
    out = capsys.readouterr().out
    assert "updated: AGENTS.md" in out
    assert "created: CLAUDE.md" in out
    assert "kept (edited by hand, not updated): .gitignore" in out
    assert "Globex" in (root / "AGENTS.md").read_text(encoding="utf-8")
    assert (root / ".gitignore").read_text(encoding="utf-8") == "edited by hand\n"
    # seed files are never rewritten
    assert 'client: "Globex"' in (root / "project.yaml").read_text(encoding="utf-8")


def test_update_needs_a_project(tmp_path, capsys):
    assert main(["init", str(tmp_path), "--update"]) == 1
    assert "not a coursekit project" in capsys.readouterr().err


def test_generated_project_is_found_and_configured(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("COURSEKIT_PROJECT", raising=False)
    root = tmp_path / "demo"
    assert run_init(root) == 0
    monkeypatch.chdir(root / "courses")
    capsys.readouterr()
    assert main(["config", "rules", "--changed"]) == 0
    assert capsys.readouterr().out == ""


def test_free_text_is_yaml_safe(tmp_path):
    root = tmp_path / "q"
    assert run_init(root, "--client", 'ACME "Labs": Spain', "--tone", "claro: sin rodeos") == 0
    data = yaml.safe_load((root / "project.yaml").read_text(encoding="utf-8"))
    assert data["client"] == 'ACME "Labs": Spain'
    assert data["tone"] == "claro: sin rodeos"
