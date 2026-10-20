import json
import threading
import urllib.error
import urllib.request

import yaml

from coursekit import course as coursemod
from coursekit import mediagallery
from coursekit.cli import main
from coursekit.preview import Server
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture
from tests.test_media import import_theme, manifest


def prepared(course):  # noqa: F811
    import_theme(course)
    assert main(["media", "extract", "PWD"]) == 0
    files = course / "media" / "files"
    files.mkdir(exist_ok=True)
    (files / "U1-S2-M1.png").write_bytes(b"\x89PNG" + b"0" * 64)
    (files / "U1-S2-M1.transcript.txt").write_text("Texto de la transcripción", encoding="utf-8")
    assert main(["media", "set", "PWD", "U1-S2-M1", "--file", "media/files/U1-S2-M1.png"]) == 0
    return course


def load(course):  # noqa: F811
    from coursekit import project as projectmod

    return coursemod.load(projectmod.find_project(course), "PWD")


def test_gallery_page_has_place_texts_and_pending(course, capsys):  # noqa: F811
    prepared(course)
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced", "--depicts", "concept"]) == 0
    capsys.readouterr()
    assert main(["media", "gallery", "PWD"]) == 0
    printed = capsys.readouterr().out
    assert "resources/index.html" in printed
    page = (course.parent.parent / ".cache" / "media" / "PWD" / "resources" / "index.html").read_text(encoding="utf-8")
    assert "U1-S2-M1" in page and "Anatomía de una contraseña" in page
    assert 'class="card done"' in page  # it has its file
    assert "content.md" in page  # the line of its placeholder
    assert "Texto de la transcripción" in page  # what coursekit holds about it goes with it
    assert "../../../../courses/PWD/media/files/U1-S2-M1.png" in page  # relative: it opens from disk


def test_a_resource_without_file_is_pending(course, capsys):  # noqa: F811
    import_theme(course)
    assert main(["media", "extract", "PWD"]) == 0
    capsys.readouterr()
    entries = mediagallery.collect(load(course))
    assert [e["id"] for e in entries] == ["U1-S2-M1"] and entries[0]["pending"] and entries[0]["path"] is None
    page = mediagallery.render(load(course), entries)
    assert 'class="card todo"' in page and 'class="pending"' in page


def test_a_pending_resource_keeps_showing_its_previous_file(course):  # noqa: F811
    prepared(course)
    assert manifest(course)[0]["status"] == "pending"
    entry = mediagallery.collect(load(course))[0]
    assert entry["pending"] and entry["path"] is not None
    assert 'class="stale"' in mediagallery.render(load(course), [entry])


def test_server_serves_only_the_gallery_and_the_media_with_ranges(course):  # noqa: F811
    prepared(course)
    loaded = load(course)
    mediagallery.build(loaded)
    (course.parent.parent / "secret.txt").write_text("no", encoding="utf-8")
    server = Server(("127.0.0.1", 0), mediagallery._handler(loaded, {"version": 7}))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        assert b"U1-S2-M1" in urllib.request.urlopen(base + "/").read()
        assert json.loads(urllib.request.urlopen(base + "/version.json").read()) == {"version": 7}
        request = urllib.request.Request(base + "/courses/PWD/media/files/U1-S2-M1.png", headers={"Range": "bytes=0-3"})
        answer = urllib.request.urlopen(request)
        assert answer.status == 206 and answer.read() == b"\x89PNG"
        for path in ("/secret.txt", "/.env", "/courses/PWD/course.yaml", "/../secret.txt"):
            try:
                urllib.request.urlopen(base + path)
                raise AssertionError(path)
            except urllib.error.HTTPError as exc:
                assert exc.code == 404, path
    finally:
        server.shutdown()
        server.server_close()


def test_stamp_changes_when_the_manifest_changes(course):  # noqa: F811
    prepared(course)
    loaded = load(course)
    before = mediagallery.stamp(mediagallery.watched(loaded))
    path = course / "media" / "manifest.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["assets"][0]["title"] = "Otro título"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    assert mediagallery.stamp(mediagallery.watched(loaded)) != before
