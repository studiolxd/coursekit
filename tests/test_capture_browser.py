"""The browser mode of `coursekit capture` with a real browser: Playwright and the Chrome, Edge or Chromium of the machine, on an
invented panel ("ACME") served on this machine. Skipped where Playwright (the capture extra) or a browser is missing."""

import json
import shutil
from pathlib import Path

import pytest

from coursekit import capture_replay, capture_session, mcpserver
from coursekit.cli import main
from coursekit.htmlkit.playcheck import find_browser
from coursekit.project import find_project
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture
from tests.test_capture import asset_capture, configure, interface_asset


@pytest.fixture(autouse=True)
def no_script_gate(request, monkeypatch):
    """These tests are about what is made, not about its sign-off: the approval of the script is tested in test_media_script."""
    from coursekit import mediascript

    monkeypatch.setattr(mediascript, "required", lambda _course: False)


pytest.importorskip("playwright.sync_api")
if not find_browser():
    pytest.skip("no Chrome, Edge or Chromium", allow_module_level=True)

PANEL = Path(__file__).parent / "fixtures" / "capture" / "acme"


@pytest.fixture
def panel(course, capsys):  # noqa: F811
    server = capture_session.serve_folder(PANEL)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    profile = {"start_url": url, "allow_domains": ["127.0.0.1"], "login": False, "account": "demo"}
    configure(course.parent.parent, profiles={"acme": profile}, browser={"visible": False},
              redact={"pixel_check": False}, replay={"pause_ms": 50, "move_ms": 100, "type_delay_ms": 10, "fps": 15})
    interface_asset(course, capsys)
    assert main(["capture", "allow", "PWD", "U1-S2-M1", "--mode", "browser", "--profile", "acme"]) == 0
    capsys.readouterr()
    yield course
    server.shutdown()


def _model_point(session, selector):
    """The centre of an element, in the coordinates of what the agent sees."""
    box = session.backend.page.locator(selector).bounding_box()
    return (box["x"] + box["width"] / 2) / session._scale, (box["y"] + box["height"] / 2) / session._scale


def test_a_real_page_never_shows_its_personal_data_and_nothing_editable_is_changed(panel):
    session = capture_session.start(find_project(), "PWD", "U1-S2-M1")
    try:
        page = session.backend.page
        page.wait_for_selector("#billing h2")  # what arrives later is replaced too
        session.screenshot()  # waits until the page is clean
        text = page.inner_text("body")
        for real in ("Ana López", "ana.lopez@acme.example", "612 345 678", "2100 0418"):
            assert real not in text
        assert "@example.com" in text and "IBAN ES" in text
        assert "Ana López" not in page.title()
        assert page.input_value("#email") == "ana.lopez@acme.example"  # never its value: it would be saved
        assert "ck-blur-field" in page.get_attribute("#email", "class") and "ck-blur" in page.get_attribute("img.user-avatar", "class")
        assert sorted(session.seen) == ["email", "iban", "name", "phone"]
    finally:
        session.close()


def test_the_agent_clicks_types_and_never_leaves_or_types_a_secret(panel):
    session = capture_session.start(find_project(), "PWD", "U1-S2-M1")
    try:
        session.screenshot()
        page = session.backend.page
        session.click(*_model_point(session, "#length"))
        page.fill("#length", "")  # an empty field, as a person would leave it
        session.type("12")
        session.click(*_model_point(session, "#save"))
        assert page.inner_text("#status") == "Guardado: 12 caracteres"
        assert session.steps[-1]["click"]["target"] == {"role": "button", "name": "Guardar"}
        session.click(*_model_point(session, "#current"))
        with pytest.raises(mcpserver.ToolError, match="password or a code"):
            session.type("hunter2")
        with pytest.raises(mcpserver.ToolError, match="never leaves the application"):
            session.navigate("https://elsewhere.example/")
        with pytest.raises(mcpserver.ToolError, match="elsewhere.example is not in the allow_domains"):
            session.click(*_model_point(session, "#away"))  # a link out: the browser does not go, and the agent is told
        assert page.url.startswith("http://127.0.0.1:") and "Guardado" in page.inner_text("#status")
        shot = session.save_shot()
        assert shot.exists() and shot.stat().st_size > 1000
    finally:
        session.close()


def test_a_replay_with_a_real_browser_records_a_video_and_its_events(panel):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg is not installed")
    capture_session.write_block({"_dir": panel}, "U1-S2-M1", {"steps": [
        {"record": "start"}, {"point": {"label": "Longitud mínima", "note": "the minimum length"}},
        {"fill": {"label": "Longitud mínima", "value": "14"}}, {"click": {"role": "button", "name": "Guardar"}}, {"wait": 400},
        {"record": "stop"}, {"shot": True}]})
    result = capture_replay.replay(find_project(), "PWD", "U1-S2-M1")
    video = result["video"]
    assert video.exists() and video.stat().st_size > 1000 and result["shots"]
    events = json.loads(result["events"].read_text(encoding="utf-8"))["events"]
    assert [e["kind"] for e in events] == ["point", "click", "click"] and events[0]["label"] == "the minimum length"
    assert all(0 <= e["fx"] <= 1 and 0 <= e["fy"] <= 1 for e in events) and events[0]["t"] < events[-1]["t"]
    assert asset_capture(panel)["state"] == "captured" and asset_capture(panel)["source"] == "replay"
