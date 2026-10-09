"""The theme is chosen when the project is created: the tenant's default or one made from theme/branding/."""

import json

import pytest
import yaml

from coursekit import handoff, theme
from coursekit.cli import main
from coursekit.project import find_project
from tests.test_init import run_init


def project_data(root) -> dict:
    return yaml.safe_load((root / "project.yaml").read_text(encoding="utf-8"))


def test_the_default_is_the_theme_of_the_tenant_and_the_branding_folder_exists(tmp_path):
    root = tmp_path / "demo"
    assert run_init(root) == 0
    assert project_data(root)["theme"]["source"] == "tenant_default"
    assert (root / "theme" / "branding").is_dir()


def test_the_theme_source_can_be_chosen_with_a_flag(tmp_path, capsys):
    root = tmp_path / "demo"
    assert run_init(root, "--theme-source", "branding") == 0
    assert project_data(root)["theme"]["source"] == "branding"
    assert "theme/branding/" in capsys.readouterr().out  # the notice: put the brand material there
    with pytest.raises(SystemExit):
        main(["init", str(tmp_path / "bad"), "--yes", "--no-git", "--theme-source", "other"])


def wizard(tmp_path, monkeypatch, answers):
    prompts = []
    monkeypatch.setattr("sys.stdin.isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or next(answers))
    root = tmp_path / "demo"
    assert main(["init", str(root), "--no-git"]) == 0
    return root, prompts


def test_the_wizard_asks_for_the_theme_with_creator(tmp_path, monkeypatch):
    answers = iter(["en", "", "Demo", "ACME", "", "", "creator", "", "branding", "none", "Ana Pérez", "ana@example.com", "", "n"])
    root, prompts = wizard(tmp_path, monkeypatch, answers)
    assert any(p.startswith("Theme of the course in creator") for p in prompts)
    assert project_data(root)["theme"]["source"] == "branding"


def test_the_wizard_does_not_ask_for_the_theme_with_html(tmp_path, monkeypatch):
    answers = iter(["en", "", "Demo", "ACME", "", "", "html", "", "none", "Ana Pérez", "ana@example.com", "", "n"])
    root, prompts = wizard(tmp_path, monkeypatch, answers)
    assert not any(p.startswith("Theme of the course in creator") for p in prompts)


def test_html_warns_about_the_brand_material(tmp_path, capsys):
    assert run_init(tmp_path / "demo", "--backend", "html") == 0
    out = capsys.readouterr().out
    assert "theme/branding/" in out and "theme/maqueta.css" in out and "base look" in out


def test_the_tenant_default_needs_no_notice(tmp_path, capsys):
    assert run_init(tmp_path / "demo") == 0
    assert "Brand:" not in capsys.readouterr().out


def test_html_tokens_can_come_from_the_base_layout_alone(tmp_path, monkeypatch, capsys):
    root = tmp_path / "demo"
    assert run_init(root, "--backend", "html") == 0
    monkeypatch.chdir(root)
    capsys.readouterr()
    assert main(["theme", "import"]) == 0  # no file: the base layout
    tokens = json.loads((root / "theme" / "tokens.json").read_text(encoding="utf-8"))
    assert tokens["origin"]["source"] == "css" and tokens["origin"]["file"] == "base layout"
    assert theme.status(find_project(root)).state == "derived"


def test_creator_still_needs_the_theme_file(tmp_path, monkeypatch, capsys):
    root = tmp_path / "demo"
    assert run_init(root) == 0
    monkeypatch.chdir(root)
    capsys.readouterr()
    assert main(["theme", "import"]) == 2
    assert "needs the file" in capsys.readouterr().err


def test_branding_is_needed_until_the_tokens_exist(tmp_path, monkeypatch):
    html = tmp_path / "html"
    assert run_init(html, "--backend", "html") == 0
    assert theme.needs_branding(find_project(html))
    assert not theme.has_branding(find_project(html))
    (html / "theme" / "branding" / "logo.svg").write_text("<svg/>", encoding="utf-8")
    assert theme.has_branding(find_project(html))
    monkeypatch.chdir(html)
    assert main(["theme", "import"]) == 0
    assert not theme.needs_branding(find_project(html))  # the tokens exist now

    tenant = tmp_path / "tenant"
    assert run_init(tenant) == 0
    assert not theme.needs_branding(find_project(tenant))  # the tenant's theme needs no material
    made = tmp_path / "made"
    assert run_init(made, "--theme-source", "branding") == 0
    assert theme.needs_branding(find_project(made))


def test_the_design_agent_is_told_what_to_do_with_the_theme_without_asking(tmp_path):
    tenant, made, html = tmp_path / "tenant", tmp_path / "made", tmp_path / "html"
    assert run_init(tenant) == 0 and run_init(made, "--theme-source", "branding") == 0 and run_init(html, "--backend", "html") == 0
    note = handoff.theme_note(find_project(tenant), "creator")
    assert "isDefault" in note and "do not ask" in note.lower() and "Do not create" in note
    note = handoff.theme_note(find_project(made), "creator")
    assert "theme/branding/" in note and "create_theme" in note and "default theme instead" in note
    note = handoff.theme_note(find_project(html), "html")
    assert "theme/maqueta.css" in note and "without a file" in note


def test_the_handoff_pause_reminds_where_the_brand_goes(tmp_path, monkeypatch, capsys):
    from coursekit import commands

    root = tmp_path / "demo"
    assert run_init(root, "--backend", "html") == 0
    monkeypatch.chdir(root)
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    project = find_project(root)
    (root / "courses" / "PWD" / "brief").mkdir(parents=True)
    commands._pause_for_material(project, root / "courses" / "PWD")
    out = capsys.readouterr().out
    assert "theme/branding/" in out and "theme/maqueta.css" in out

    tenant = tmp_path / "tenant"
    assert run_init(tenant) == 0
    (tenant / "courses" / "PWD" / "brief").mkdir(parents=True)
    capsys.readouterr()
    commands._pause_for_material(find_project(tenant), tenant / "courses" / "PWD")
    assert "theme/branding" not in capsys.readouterr().out
