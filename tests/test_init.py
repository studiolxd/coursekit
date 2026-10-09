import json

import pytest
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
    assert "skills, commands and agent settings" in capsys.readouterr().out


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


def test_the_language_of_the_interface_comes_first_and_the_courses_default_to_it(tmp_path, monkeypatch):
    prompts = []
    answers = iter(["es", "en", "Demo", "ACME", "", "", "slxd creator", "", "", "", "Ana Pérez", "ana@example.com", "", "n"])
    monkeypatch.setattr("sys.stdin.isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or next(answers))
    root = tmp_path / "demo"
    assert main(["init", str(root), "--no-git"]) == 0
    assert prompts[0].startswith("Idioma / Language") and "(es)" in prompts[0]
    assert prompts[1].startswith("Idioma de los cursos") and "(es)" in prompts[1]  # it defaults to the language just chosen
    assert prompts[2].startswith("Nombre del proyecto")  # everything after the first answer speaks the interface language
    data = yaml.safe_load((root / "project.yaml").read_text(encoding="utf-8"))
    assert data["ui_language"] == "es" and data["content_language"] == "en"
    assert "COURSEKIT_LANG=es" in (root / ".env").read_text(encoding="utf-8")


def test_interactive_wizard_asks_language_first_and_speaks_it(tmp_path, monkeypatch):
    prompts = []
    answers = iter(["en", "", "Demo", "ACME", "friendly", "", "slxd creator", "", "", "", "Ana Pérez", "ana@example.com", "", "n"])

    def fake_input(prompt):
        prompts.append(prompt)
        return next(answers)

    monkeypatch.setattr("sys.stdin.isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", fake_input)
    root = tmp_path / "demo"
    assert main(["init", str(root), "--no-git"]) == 0
    assert prompts[0].startswith("Idioma / Language")
    assert prompts[1].startswith("Language of the courses")
    assert prompts[6].startswith("Assembly backend [SLXD Creator/HTML]")
    assert prompts[7].startswith("slxd MCP server URL")
    assert prompts[8].startswith("Theme of the course in creator")
    assert prompts[10].startswith("Your name")
    assert (root / ".env").read_text(encoding="utf-8").count("Ana") == 1
    data = yaml.safe_load((root / "project.yaml").read_text(encoding="utf-8"))
    assert data["content_language"] == "en"
    assert data["assembly"]["backend"] == "creator"


def test_mirror_details_are_asked_and_saved(tmp_path, monkeypatch, capsys):
    synced = tmp_path / "SharePoint" / "Cursos"
    synced.mkdir(parents=True)
    url = "https://acme.sharepoint.com/sites/cursos/Documentos compartidos/Cursos"
    answers = iter(["es", "", "Demo", "ACME", "", "", "", "", "", "sharepoint", f'"{synced}"', url,
                    "Ana Pérez", "ana@example.com", "", "n"])
    prompts = []

    def fake_input(prompt):
        prompts.append(prompt)
        return next(answers)

    monkeypatch.setattr("sys.stdin.isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", fake_input)
    root = tmp_path / "demo"
    assert main(["init", str(root), "--no-git"]) == 0
    assert prompts[10].startswith("Ruta local de la carpeta sincronizada")
    assert prompts[11].startswith("Dirección web de la carpeta")
    data = yaml.safe_load((root / "project.yaml").read_text(encoding="utf-8"))
    assert data["mirror"] == {"provider": "sharepoint", "url": url}
    assert f"MIRROR_DIR={synced}" in (root / ".env").read_text(encoding="utf-8")


def test_mirror_flags_without_a_terminal(tmp_path):
    synced = tmp_path / "shared"
    synced.mkdir()
    root = tmp_path / "demo"
    assert run_init(root, "--mirror", "folder", "--mirror-dir", str(synced)) == 0
    assert yaml.safe_load((root / "project.yaml").read_text(encoding="utf-8"))["mirror"]["provider"] == "folder"
    assert f"MIRROR_DIR={synced}" in (root / ".env").read_text(encoding="utf-8")


def test_config_examples_are_the_complete_package_defaults(tmp_path):
    from coursekit import config

    root = tmp_path / "demo"
    assert run_init(root) == 0
    assert init.CONFIG_NAMES == config.NAMES  # a new configuration needs its example too
    for name in config.NAMES:
        example = root / "config" / f"{name}.example.yaml"
        assert yaml.safe_load(example.read_text(encoding="utf-8")) == config.package_defaults(name), name
        assert not (root / "config" / f"{name}.yaml").exists()  # the examples are not read: no override until the person asks
    assert config.effective("rules", None).value == config.package_defaults("rules")


def test_init_ends_inviting_to_create_the_first_course(tmp_path, capsys):
    assert run_init(tmp_path / "demo") == 0
    out = capsys.readouterr().out
    assert 'Next step: create your first course.' in out
    assert '/new-course "Course title" <hours>' in out
    assert 'coursekit run new-course' in out
    assert 'brief/sources/' in out and 'config/*.example.yaml' in out


def test_mcp_url_is_asked_for_creator_and_configures_the_tools(tmp_path, monkeypatch, capsys):
    url = "https://acme.slxd.app/mcp/creator"
    answers = iter(["en", "", "Demo", "ACME", "", "", "", "not a url", url, "", "none", "Ana Pérez", "ana@example.com", "", "n", "n"])
    monkeypatch.setattr("sys.stdin.isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr("shutil.which", lambda tool: "/bin/" + tool)
    root = tmp_path / "demo"
    assert main(["init", str(root), "--no-git"]) == 0  # the last "n": do not create the first course now
    captured = capsys.readouterr()
    assert "http://" in captured.err
    assert yaml.safe_load((root / "project.yaml").read_text(encoding="utf-8"))["platform"]["slxd"]["mcp_url"] == url
    assert json.loads((root / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["slxd-creator"]["url"] == url
    assert "its URL is missing" not in captured.out


def test_without_the_mcp_url_it_warns_and_does_not_offer_the_course(tmp_path, capsys):
    assert run_init(tmp_path / "demo") == 0
    out = capsys.readouterr().out
    assert "its URL is missing" in out
    assert run_init(tmp_path / "other", "--backend", "html") == 0
    assert "its URL is missing" in capsys.readouterr().out  # the design is done in creator with either backend


def test_mcp_url_flag_is_validated(tmp_path):
    assert run_init(tmp_path / "bad", "--mcp-url", "slxd.app") == 1
    assert run_init(tmp_path / "ok", "--mcp-url", "https://acme.slxd.app/mcp/creator") == 0


def test_the_first_course_can_be_started_at_the_end(tmp_path, monkeypatch):
    from coursekit import launch

    url = "https://acme.slxd.app/mcp/creator"
    answers = iter(["en", "", "Demo", "ACME", "", "", "", url, "", "none", "Ana Pérez", "ana@example.com", "", "n",
                    "", "", "Passwords \"101\"", "abc", "0", "1,5", "", ""])
    launched = []
    monkeypatch.chdir(tmp_path)  # init changes folder to start the course: restore it afterwards
    monkeypatch.setattr("sys.stdin.isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr("shutil.which", lambda tool: "/bin/" + tool)
    monkeypatch.setattr(launch, "execute", lambda project, agent, text, headless, log: launched.append((agent.tool, text)) or (0, None, ""))
    assert main(["init", str(tmp_path / "demo"), "--no-git"]) == 0
    assert len(launched) == 1
    tool, text = launched[0]
    assert tool == "claude" and '/new-course "Passwords 101" 1.5' in text


def test_the_wizard_pauses_for_the_reference_material_before_the_first_course(tmp_path, monkeypatch, capsys):
    from coursekit import launch

    url = "https://acme.slxd.app/mcp/creator"
    prompts = []
    answers = iter(["en", "", "Demo", "ACME", "", "", "", url, "", "none", "Ana Pérez", "ana@example.com", "", "n",
                    "", "Passwords", "1", "", "y", ""])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or next(answers))
    monkeypatch.setattr("shutil.which", lambda tool: "/bin/" + tool)
    monkeypatch.setattr(launch, "execute", lambda project, agent, text, headless, log: (0, None, ""))
    capsys.readouterr()
    assert main(["init", str(tmp_path / "demo"), "--no-git"]) == 0
    out = capsys.readouterr().out
    asked = [p for p in prompts if p.startswith("Before designing")]
    assert len(asked) == 1
    assert "brief/sources" in out and "brief/links.md" in out and "brief/notes.md" in out
    assert any(p.startswith("Press Enter when") for p in prompts)
    assert prompts.index(asked[0]) > next(i for i, p in enumerate(prompts) if p.startswith("Handoff") or p.startswith("Do the whole"))


def test_the_wizard_without_material_says_the_design_starts_on_assumptions(tmp_path, monkeypatch, capsys):
    from coursekit import launch

    url = "https://acme.slxd.app/mcp/creator"
    answers = iter(["en", "", "Demo", "ACME", "", "", "", url, "", "none", "Ana Pérez", "ana@example.com", "", "n",
                    "", "Passwords", "1", "", ""])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr("shutil.which", lambda tool: "/bin/" + tool)
    monkeypatch.setattr(launch, "execute", lambda project, agent, text, headless, log: (0, None, ""))
    assert main(["init", str(tmp_path / "demo"), "--no-git"]) == 0
    assert "marked as an assumption" in capsys.readouterr().out


def test_the_wizard_can_hand_the_whole_process_off(tmp_path, monkeypatch, capsys):
    url = "https://acme.slxd.app/mcp/creator"
    answers = iter(["en", "", "Demo", "ACME", "", "", "", url, "", "none", "Ana Pérez", "ana@example.com", "", "n",
                    "", "Passwords", "1", "y"])
    started = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr("shutil.which", lambda tool: "/bin/" + tool)
    from coursekit import handoff

    monkeypatch.setattr(handoff, "start", lambda *args, **kwargs: started.append(args) or {"code": "PASSWORDS", "status": "delivered"})
    monkeypatch.setattr("coursekit.status.detail", lambda course: "detail")
    assert main(["init", str(tmp_path / "demo"), "--no-git"]) == 0
    assert len(started) == 1 and started[0][1:3] == ("Passwords", 1.0)
    assert "Handoff mode" in capsys.readouterr().out


def test_pending_lines_are_what_a_paste_leaves_and_never_wait():
    import os

    reader, writer = os.pipe()
    stream = os.fdopen(reader, "r", encoding="utf-8")
    assert init.pending_lines(stream) == []  # nothing waiting: it returns at once, it does not block
    os.write(writer, b"second line\n\nthird line\n")
    assert init.pending_lines(stream) == ["second line", "third line"]
    assert init.pending_lines(stream) == []
    os.close(writer)
    stream.close()


def test_a_free_text_answer_pasted_over_several_lines_is_one_answer(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt: "Cercano y fresco:")
    monkeypatch.setattr(init, "pending_lines", lambda stream=None: ["frases cortas  ", "y ejemplos."])
    assert init.ask("Tono") == "Cercano y fresco: frases cortas y ejemplos."


def test_choice_questions_do_not_swallow_what_follows(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    monkeypatch.setattr(init, "pending_lines", lambda stream=None: pytest.fail("a choice question must not read ahead"))
    assert init.ask("Backend", "creator", ("creator", "html")) == "creator"


def test_without_a_terminal_nothing_is_read_ahead(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt: "answer")
    monkeypatch.setattr(init, "pending_lines", lambda stream=None: pytest.fail("no terminal: nothing to read ahead"))
    assert init.ask("Question") == "answer"
