"""Clear messages instead of tracebacks, plural forms, the help of write and review, the brief index language and Azure."""

import os

import pytest

from coursekit import i18n, media
from coursekit.cli import main
from tests.test_course_flow import project  # noqa: F401 — an empty project
from tests.test_launch import course  # noqa: F401 — the approved sample course


def test_sync_without_a_saved_design_says_what_to_do(project, capsys):  # noqa: F811
    assert main(["new", "Strong passwords", "1", "--code", "pwd101", "--language", "en"]) == 0
    capsys.readouterr()
    assert main(["sync", "PWD101"]) == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "design/matrix.json" in err and "not saved yet" in err


def test_sync_with_a_broken_matrix(project, capsys):  # noqa: F811
    assert main(["new", "Strong passwords", "1", "--code", "pwd101"]) == 0
    (project / "courses" / "PWD101" / "design" / "matrix.json").write_text("{not json", encoding="utf-8")
    capsys.readouterr()
    assert main(["sync", "PWD101"]) == 1
    assert "design_matrix_get" in capsys.readouterr().err


def test_directives_check_and_tts_with_missing_files(project, capsys):  # noqa: F811
    assert main(["directives", "check", "nothing.json"]) == 1
    assert "nothing.json does not exist" in capsys.readouterr().err
    assert main(["tts", "--in", "nothing.txt", "--out", "out.mp3"]) == 1
    assert "nothing.txt does not exist" in capsys.readouterr().err
    assert main(["subtitles", "--audio", "a.mp3", "--text", "t.txt", "--out", "o.vtt", "--language", "en"]) == 1
    assert "does not exist" in capsys.readouterr().err


def test_write_has_no_review_only_options(capsys):
    with pytest.raises(SystemExit):
        main(["write", "--help"])
    help_text = capsys.readouterr().out
    assert "--full" not in help_text and "--parts" not in help_text
    with pytest.raises(SystemExit):
        main(["review", "--help"])
    help_text = capsys.readouterr().out
    assert "--full" in help_text and "--parts" in help_text
    with pytest.raises(SystemExit) as refused:
        main(["write", "PWD101", "--full"])
    assert refused.value.code == 2


def test_status_uses_the_singular(course, capsys):  # noqa: F811
    assert main(["status"]) == 0
    assert "1 units" not in capsys.readouterr().out
    i18n.use("es")
    assert main(["status"]) == 0
    assert "1 unidades" not in capsys.readouterr().out
    assert i18n.tn("status", "units", 1) == "1 unidad"


def test_publish_without_a_mirror_is_not_an_error(project, capsys):  # noqa: F811
    assert main(["publish"]) == 0
    assert "nothing to publish" in capsys.readouterr().out
    assert main(["publish", "--only-if-configured"]) == 0
    assert capsys.readouterr().out == ""


def test_publish_with_a_provider_and_no_folder_still_fails(project, monkeypatch, capsys):  # noqa: F811
    text = (project / "project.yaml").read_text(encoding="utf-8")
    assert "provider: none" in text
    (project / "project.yaml").write_text(text.replace("provider: none", "provider: folder", 1), encoding="utf-8")
    monkeypatch.delenv("MIRROR_DIR", raising=False)
    assert main(["publish"]) == 1
    assert "no mirror folder configured" in capsys.readouterr().err


def test_azure_needs_the_key_and_the_region(monkeypatch):
    needs = {"env": ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"]}
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)
    assert media.requirement_met(needs) is False
    monkeypatch.setenv("AZURE_SPEECH_KEY", "k")
    assert media.requirement_met(needs) is False
    monkeypatch.setenv("AZURE_SPEECH_REGION", "westeurope")
    assert media.requirement_met(needs) is True
    assert media.requirement_met({"env": "AZURE_SPEECH_KEY"}) is True


def test_brief_index_follows_the_content_language(project, monkeypatch, capsys):  # noqa: F811
    assert main(["new", "Strong passwords", "1", "--code", "pwd101", "--language", "en"]) == 0
    sources = project / "courses" / "PWD101" / "brief" / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    (sources / "guide.md").write_text("# Guide\n\n" + "word " * 40, encoding="utf-8")
    (sources / "logo.png").write_bytes(b"png")
    capsys.readouterr()
    assert main(["brief", "PWD101"]) == 0
    index = (project / "courses" / "PWD101" / "brief" / "index.md").read_text(encoding="utf-8")
    assert "# Reference material — PWD101" in index
    assert "## Documents" in index and "## Images, audio and video" in index
    assert "| image |" in index
    assert "Material de referencia" not in index

    (project / "project.yaml").write_text(
        (project / "project.yaml").read_text(encoding="utf-8").replace("content_language: en", "content_language: es"), encoding="utf-8")
    assert main(["brief"]) == 0
    assert "# Material de referencia" in (project / "brief" / "index.md").read_text(encoding="utf-8")


def test_help_follows_the_language_of_the_env_file(project, monkeypatch, capsys):  # noqa: F811
    monkeypatch.delenv("COURSEKIT_LANG", raising=False)
    (project / ".env").write_text("COURSEKIT_LANG=es\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        main(["write", "--help"])
    assert "para este lanzamiento" in capsys.readouterr().out
    assert os.environ["COURSEKIT_LANG"] == "es"
