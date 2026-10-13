"""`coursekit preview`: the local server of the html backend with a simulated LMS (page, units, stamps, guards)."""

import json
import os
import threading
import urllib.error
import urllib.request

import pytest

from coursekit import course as coursemod
from coursekit import preview
from coursekit.cli import main
from coursekit.project import find_project
from tests.test_html_backend import html_course  # noqa: F401 - the fixture


def _get(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.status, response.headers.get("Content-Type"), response.read()


@pytest.fixture
def served(html_course):  # noqa: F811
    assert main(["assemble", "build", "PWD", "--unit", "1"]) == 0
    course = coursemod.load(find_project(), "PWD")
    server = preview.serve(course, course["units"], 1, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}", course
    server.shutdown()
    server.server_close()


def test_the_page_holds_both_scorm_apis_and_the_units(served):
    base, _ = served
    status, kind, body = _get(base + "/")
    page = body.decode("utf-8")
    assert status == 200 and kind.startswith("text/html")
    assert "window.API = " in page and "window.API_1484_11 = " in page and '<html lang="es">' in page
    config = json.loads(page.split("const config = ")[1].split(";\n")[0])
    assert config["course"] == "PWD" and config["standard"] == "1.2" and config["first"] == 1
    assert config["units"] == [{"n": 1, "title": config["units"][0]["title"], "built": True}]
    assert config["texts"]["reopen"] == "Exit and reopen" and set(config["texts"]) == set(preview.PANEL_TEXTS)


def test_the_unit_is_served_and_nothing_outside_it(served):
    base, _ = served
    status, kind, body = _get(base + "/unit/01/index.html")
    assert status == 200 and kind == "text/html; charset=utf-8" and b"ck-config" in body
    assert _get(base + "/unit/01/assets/player.js")[0] == 200
    for path in ("/unit/01/../../course.yaml", "/unit/01/%2e%2e/%2e%2e/course.yaml", "/unit/02/index.html", "/course.yaml"):
        with pytest.raises(urllib.error.HTTPError) as error:
            _get(base + path)
        assert error.value.code == 404


def test_the_stamps_change_when_the_unit_is_built_again(served):
    base, course = served
    before = json.loads(_get(base + "/__ck/stamps")[2])["1"]
    assert before > 0
    index = preview.unit_dir(course, 1) / "index.html"
    os.utime(index, (before + 10, before + 10))
    assert json.loads(_get(base + "/__ck/stamps")[2])["1"] == before + 10


def test_preview_builds_the_unit_it_opens_and_refuses_creator(html_course, monkeypatch, capsys):  # noqa: F811
    calls = []
    monkeypatch.setattr(preview, "run", lambda course, units, first, port, open_browser: calls.append((first, port, open_browser)) or 0)
    assert main(["preview", "PWD", "--no-open", "--port", "9001"]) == 0
    assert "building unit 1" in capsys.readouterr().out
    assert calls == [(1, 9001, False)] and (preview.unit_dir(coursemod.load(find_project(), "PWD"), 1) / "index.html").exists()
    assert main(["preview", "PWD", "--no-open"]) == 0
    assert "building" not in capsys.readouterr().out  # already built: it is not built again without --build
    assert main(["preview", "PWD", "--unit", "7"]) == 1
    capsys.readouterr()
    monkeypatch.setattr(coursemod, "backend", lambda course: "creator")
    assert main(["preview", "PWD"]) == 1
    assert "creator backend" in capsys.readouterr().err
