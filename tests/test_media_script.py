"""The script of a resource (a screen recording, the montage of a video) is approved by a person before it is made, and an
official video proposed for a resource stops it from being made."""

import pytest
import yaml

from coursekit import capture_session, mcpserver, mediascript, video
from coursekit.cli import main
from coursekit.course import load as load_course
from coursekit.project import find_project
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture
from tests.test_capture import FakeBrowser, configure, interface_asset
from tests.test_exelearning import edit_course

BRIEF = "# Change the minimum length\n\nOpen the security settings and set twelve.\n\nNarration: «Set it to twelve.»\n"


@pytest.fixture
def scripted(course, capsys):  # noqa: F811
    configure(course.parent.parent, profiles={"acme": {"start_url": "https://app.acme.example/", "allow_domains": ["app.acme.example"],
                                                        "login": False}}, redact={"pixel_check": False})
    interface_asset(course, capsys)
    brief = course / "media" / "scripts" / "U1-S2-M1.md"
    brief.parent.mkdir(parents=True, exist_ok=True)
    brief.write_text(BRIEF, encoding="utf-8")
    assert main(["capture", "allow", "PWD", "U1-S2-M1", "--mode", "browser", "--profile", "acme"]) == 0
    capsys.readouterr()
    return course


def loaded():
    return load_course(find_project(), "PWD")


def test_nothing_is_captured_until_a_person_approves_its_script(scripted, capsys):
    with pytest.raises(mcpserver.ToolError, match="waits for a person to approve it .* coursekit approve script PWD --asset U1-S2-M1"):
        capture_session.start(find_project(), "PWD", "U1-S2-M1", FakeBrowser)
    assert main(["media", "plan", "PWD"]) == 0
    assert "script to approve: coursekit approve script PWD --asset U1-S2-M1" in capsys.readouterr().out
    assert main(["approve", "script", "PWD", "--asset", "U1-S2-M1", "--yes", "--no-commit"]) == 0
    assert "script of U1-S2-M1 approved by Ana <ana@example.com>" in capsys.readouterr().out
    signed = mediascript.approval(loaded(), "U1-S2-M1")
    assert signed["by"] == "Ana <ana@example.com>" and signed["files"] == ["U1-S2-M1.md"]
    capture_session.start(find_project(), "PWD", "U1-S2-M1", FakeBrowser).close()


def test_the_steps_a_session_writes_do_not_undo_the_approval_but_a_new_narration_does(scripted, capsys):
    assert main(["approve", "script", "PWD", "--asset", "U1-S2-M1", "--yes", "--no-commit"]) == 0
    capture_session.write_block({"_dir": scripted}, "U1-S2-M1", {"steps": [{"click": {"x": 1, "y": 2}}]})
    assert mediascript.state(loaded(), "U1-S2-M1") == "approved"  # the exact steps of a session are not the script
    brief = scripted / "media" / "scripts" / "U1-S2-M1.md"
    brief.write_text(brief.read_text(encoding="utf-8").replace("twelve.»", "fourteen.»"), encoding="utf-8")
    assert mediascript.state(loaded(), "U1-S2-M1") == "changed"
    with pytest.raises(mcpserver.ToolError, match="changed since it was approved"):
        capture_session.start(find_project(), "PWD", "U1-S2-M1", FakeBrowser)


def test_the_approval_is_for_a_person_and_can_be_turned_off(scripted, capsys):
    from coursekit import agents

    assert "Bash(coursekit approve:*)" in agents.DENY_CLAUDE  # the agents may not sign it, as every approval
    edit_course(scripted, lambda d: d["rules"].setdefault("review", {}).update(scripts="none"))
    capture_session.start(find_project(), "PWD", "U1-S2-M1", FakeBrowser).close()


def test_a_session_of_the_handoff_signs_the_script_by_itself(scripted, monkeypatch):
    from coursekit.handoff import HANDOFF

    monkeypatch.setenv("COURSEKIT_USER_NAME", HANDOFF.name)
    monkeypatch.setenv("COURSEKIT_USER_EMAIL", HANDOFF.email)
    capture_session.start(find_project(), "PWD", "U1-S2-M1", FakeBrowser).close()
    signed = mediascript.approval(loaded(), "U1-S2-M1")
    assert signed["via"] == "handoff" and signed["by"].startswith("Coursekit Handoff")


def test_the_montage_of_a_video_is_its_script_too(course, capsys):  # noqa: F811
    from tests.test_media import prepare_asset

    prepare_asset(course, capsys)
    path = course / "media" / "scripts" / "U1-S2-M1.video.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"scenes": [{"id": "a", "type": "outro", "props": {"title": "Fin"}, "says": "Fin."}]}), encoding="utf-8")
    with pytest.raises(video.VideoError, match="waits for a person to approve it"):
        video.voice(loaded(), "U1-S2-M1", lambda m: None)
    assert main(["approve", "script", "PWD", "--asset", "U1-S2-M1", "--yes", "--no-commit"]) == 0
    assert mediascript.state(loaded(), "U1-S2-M1") == "approved"
    path.write_text(path.read_text(encoding="utf-8").replace("Fin.", "Fin del todo."), encoding="utf-8")
    assert mediascript.state(loaded(), "U1-S2-M1") == "changed"


def test_an_official_video_proposed_for_a_resource_stops_it_until_a_person_decides(scripted, capsys, monkeypatch):
    from coursekit import videos

    assert main(["approve", "script", "PWD", "--asset", "U1-S2-M1", "--yes", "--no-commit"]) == 0
    channel = {"name": "Acme Support", "url": "https://www.youtube.com/@AcmeSupport", "title": "Guide"}
    monkeypatch.setattr(videos, "oembed", lambda url: channel)
    url = "https://www.youtube.com/watch?v=official1"
    assert main(["videos", "propose", "PWD", url, "--why", "Linked from the support site", "--for", "U1-S2-M1"]) == 0
    capsys.readouterr()
    with pytest.raises(mcpserver.ToolError, match="official video proposed .* waits for a person"):
        capture_session.start(find_project(), "PWD", "U1-S2-M1", FakeBrowser)
    assert main(["media", "plan", "PWD"]) == 0
    assert "official video proposed" in capsys.readouterr().out
    assert main(["videos", "approve", "PWD", url]) in (0, 1)
    with pytest.raises(mcpserver.ToolError, match="an official video was approved"):
        capture_session.start(find_project(), "PWD", "U1-S2-M1", FakeBrowser)
    assert main(["videos", "reject", "PWD", url]) in (0, 1)
    capture_session.start(find_project(), "PWD", "U1-S2-M1", FakeBrowser).close()  # rejected: it is made
