"""`coursekit capture`: profiles of a web application and permissions to capture, given only by a person."""

import datetime as dt
import json
import os

import pytest
import yaml

from coursekit import agents, capture, launch
from coursekit.cli import main
from coursekit.project import find_project
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture
from tests.test_media import prepare_asset

PROFILE = {"start_url": "https://app.acme.example/settings", "allow_domains": ["app.acme.example", "sso.acme.example"],
           "account": "demo administrator"}


def configure(root, **values):
    data = {"enabled": True, "profiles": {"acme-admin": PROFILE}, **values}
    (root / "config" / "capture.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


@pytest.fixture
def browser(monkeypatch):
    """No real browser: the login only records where it would open."""
    opened = []

    def fake(folder, url):
        folder.joinpath("Default").mkdir(parents=True, exist_ok=True)
        opened.append((folder, url))

    monkeypatch.setattr(capture, "_launch_login", fake)
    return opened


def interface_asset(course_dir, capsys):
    prepare_asset(course_dir, capsys)
    assert main(["media", "set", "PWD", "U1-S2-M1", "--depicts", "interface", "--status", "scripted", "--recipe", "screenshot"]) == 0
    capsys.readouterr()


def test_nothing_is_captured_until_the_project_turns_it_on(course, browser, capsys):  # noqa: F811
    assert main(["capture", "login", "acme-admin"]) == 1
    assert "capture is turned off" in capsys.readouterr().err
    assert not browser


def test_a_domain_covers_its_subdomains_and_nothing_else():
    assert capture.domain_allowed("app.acme.example", ["acme.example"])
    assert capture.domain_allowed("ACME.example.", ["acme.example"])
    assert not capture.domain_allowed("acme.example.evil.test", ["acme.example"])
    assert not capture.domain_allowed("notacme.example", ["acme.example"])


def test_a_profile_must_say_where_it_starts_and_the_only_domains_it_opens():
    cfg = {"profiles": {"a": {"start_url": "https://other.test/", "allow_domains": ["acme.example"]},
                        "b": {"start_url": "https://acme.example/"}, "c": {"start_url": "ftp://acme.example/", "allow_domains": ["x"]}}}
    for name, text in (("a", "is not in its allow_domains"), ("b", "needs allow_domains"), ("c", "full http(s) start_url"),
                       ("zz", "is not in capture.yaml › profiles"), ("Bad Name", "is not a profile name")):
        with pytest.raises(capture.CaptureError, match=text.replace("(", r"\(").replace(")", r"\)")):
            capture.profile_config(cfg, name)


def test_login_keeps_the_session_outside_the_project_for_that_project_only(course, browser, capsys):  # noqa: F811
    root = course.parent.parent
    configure(root)
    assert main(["capture", "login", "acme-admin"]) == 0
    folder, url = browser[0]
    assert url == PROFILE["start_url"]
    store_home = os.environ["COURSEKIT_HOME"]
    assert str(folder).startswith(store_home) and root not in folder.parents
    assert capture.project_key(find_project()) in str(folder)
    if os.name != "nt":
        assert (folder.stat().st_mode & 0o777) == 0o700 and (folder.parent.stat().st_mode & 0o777) == 0o700
    assert "session kept in the profile acme-admin" in capsys.readouterr().out
    assert main(["capture", "profiles"]) == 0
    out = capsys.readouterr().out
    assert "acme-admin · demo administrator · https://app.acme.example/settings · session since" in out
    meta = json.loads((folder.parent / "acme-admin.json").read_text(encoding="utf-8"))
    assert meta["by"] == "Ana <ana@example.com>" and "password" not in json.dumps(meta)
    assert main(["capture", "logout", "acme-admin"]) == 0
    assert not folder.exists() and "deleted with its session" in capsys.readouterr().out
    assert main(["capture", "logout", "acme-admin"]) == 0
    assert "had no session" in capsys.readouterr().out


def test_a_session_whose_profile_left_the_configuration_is_listed_to_delete_it(course, browser, capsys):  # noqa: F811
    root = course.parent.parent
    configure(root)
    assert main(["capture", "login", "acme-admin"]) == 0
    configure(root, profiles={})
    capsys.readouterr()
    assert main(["capture", "profiles"]) == 0
    assert "no longer in capture.yaml" in capsys.readouterr().out


def test_a_grant_is_signed_expires_and_names_what_it_covers(course, browser, capsys):  # noqa: F811
    root = course.parent.parent
    configure(root)
    interface_asset(course, capsys)
    assert main(["capture", "allow", "PWD", "--mode", "browser", "--profile", "acme-admin"]) == 1
    assert "has no session" in capsys.readouterr().err  # log in first
    assert main(["capture", "login", "acme-admin"]) == 0
    assert main(["capture", "allow", "PWD", "U1-S2-M1", "--mode", "browser", "--profile", "acme-admin", "--minutes", "30"]) == 0
    assert "permission to capture for PWD: browser (acme-admin), resources: U1-S2-M1" in capsys.readouterr().out
    project = find_project()
    grant = capture.active_grant(project, "PWD", "U1-S2-M1")
    assert grant["by"] == "Ana <ana@example.com>" and grant["mode"] == "browser" and grant["window"] is None
    granted = dt.datetime.fromisoformat(grant["granted_at"])
    assert dt.datetime.fromisoformat(grant["expires_at"]) - granted == dt.timedelta(minutes=30)
    assert capture.active_grant(project, "PWD", "OTHER") is None
    assert capture.active_grant(project, "PWD", now=granted + dt.timedelta(minutes=31)) is None
    assert main(["capture", "revoke", "PWD"]) == 0
    assert capture.active_grant(project, "PWD") is None
    assert main(["capture", "revoke", "PWD"]) == 0
    assert "had no permission" in capsys.readouterr().out


def test_without_ids_a_grant_covers_every_resource_that_shows_an_interface(course, browser, capsys):  # noqa: F811
    root = course.parent.parent
    configure(root, grant_minutes=5)
    prepare_asset(course, capsys)
    assert main(["capture", "allow", "PWD", "--mode", "desktop", "--window", "Calculator"]) == 1
    assert "no resources that show an interface" in capsys.readouterr().err
    interface_asset(course, capsys)
    assert main(["capture", "allow", "PWD", "--mode", "desktop", "--window", "Calculator"]) == 0
    assert "every one that shows an interface" in capsys.readouterr().out
    grant = capture.active_grant(find_project(), "PWD", "U1-S2-M1")
    assert grant["assets"] is None and grant["window"] == "Calculator" and grant["profile"] is None


def test_a_grant_is_refused_when_something_is_missing(course, browser, capsys, monkeypatch):  # noqa: F811
    root = course.parent.parent
    configure(root, modes=["browser"])
    interface_asset(course, capsys)
    cases = [
        (["--mode", "desktop", "--window", "W"], "the mode desktop is not allowed"),
        (["--mode", "browser"], "--mode browser needs --profile"),
        (["NOPE", "--mode", "browser", "--profile", "acme-admin"], "NOPE are not resources of PWD"),
        (["--mode", "browser", "--profile", "acme-admin", "--minutes", "0"], "more than zero minutes"),
    ]
    assert main(["capture", "login", "acme-admin"]) == 0
    for extra, text in cases:
        assert main(["capture", "allow", "PWD", *extra]) == 1
        assert text in capsys.readouterr().err
    assert main(["capture", "allow", "PWD"]) == 2
    monkeypatch.delenv("COURSEKIT_USER_NAME", raising=False)
    monkeypatch.setattr("coursekit.envfile.load", lambda path: None)
    assert main(["capture", "allow", "PWD", "--mode", "browser", "--profile", "acme-admin"]) == 1
    assert "signed by a person" in capsys.readouterr().err


def test_only_a_person_logs_in_or_gives_the_permission():
    for action in ("login", "logout", "allow", "revoke"):
        assert f"Bash(coursekit capture {action}:*)" in agents.DENY_CLAUDE
        assert f"Bash(coursekit capture {action}:*)" in launch.CLAUDE_DENY
        assert agents.DENY_OPENCODE[f"*coursekit capture {action}*"] == "deny"
    assert not any("capture profiles" in rule for rule in agents.DENY_CLAUDE)


def test_uninstall_takes_away_the_capture_sessions(course, browser, capsys, monkeypatch):  # noqa: F811
    from coursekit import store

    configure(course.parent.parent)
    assert main(["capture", "login", "acme-admin"]) == 0
    monkeypatch.setattr("coursekit.uninstall._uv_tools", lambda: set())
    assert main(["uninstall", "--yes"]) == 0
    assert "removed the capture profiles and permissions of 1 project(s)" in capsys.readouterr().out
    assert not (store.home() / "capture").exists()


# ── personal data and the invented data that replaces it ─────────────────────────────────────

from PIL import Image  # noqa: E402

from coursekit import config, pii, redact  # noqa: E402

RULES = config.package_defaults("capture")["redact"]
SAMPLE = ("Usuario: Lucía Martín Pardo · lucia.martin@acme.example · Tel. +34 612 345 678 · IBAN ES91 2100 0418 4502 0005 1332"
          " · DNI 12345678Z · IP 10.0.0.12 · Tarjeta 4111 1111 1111 1111 · Bravant · v1.2.3 · 2024-01-15")


def kinds(text, strict=True, terms=()):
    return [(f.kind, text[f.start:f.end]) for f in pii.find(text, RULES, pii.people("es"), list(terms), strict=strict)]


def test_the_kinds_of_personal_data_are_found_without_overlaps():
    found = dict(kinds(SAMPLE, terms=["bravant"]))
    assert found == {"name": "Lucía Martín Pardo", "email": "lucia.martin@acme.example", "phone": "+34 612 345 678",
                     "iban": "ES91 2100 0418 4502 0005 1332", "national_id": "12345678Z", "ip": "10.0.0.12",
                     "card": "4111 1111 1111 1111", "term": "Bravant"}


def test_where_the_text_is_exact_the_check_digits_are_checked_and_on_the_pixels_not():
    wrong = "DNI 12345678A · IBAN ES00 2100 0418 4502 0005 1332 · Tarjeta 4111 1111 1111 1112 · IP 300.1.1.1"
    strict = {k for k, _ in kinds(wrong)}
    assert not strict & {"national_id", "iban", "card", "ip"}
    loose = dict((v, k) for k, v in kinds(wrong, strict=False))
    assert {loose.get("12345678A"), loose.get("4111 1111 1111 1112")} == {"national_id", "card"}
    assert "300.1.1.1" in loose and loose["ES00 2100 0418 4502 0005 1332"] == "iban"  # covered, whatever kind


def test_a_name_needs_a_known_first_name_and_a_capitalised_word():
    assert kinds("Ana López y Emma Taylor firmaron") == [("name", "Ana López"), ("name", "Emma Taylor")]
    assert kinds("Pulsa Guardar Cambios para seguir") == []
    assert kinds("Ana firmó") == []


def test_the_invented_data_is_stable_keeps_the_shape_and_the_gender():
    who = pii.people("es")
    out = pii.replace(SAMPLE, RULES, who, ["bravant"])
    assert out == pii.replace(SAMPLE, RULES, who, ["bravant"])  # the same value, the same invented one
    for real in ("Lucía", "lucia.martin@acme.example", "612 345 678", "2100 0418", "12345678Z", "10.0.0.12", "4111", "Bravant"):
        assert real not in out
    assert "v1.2.3" in out and "2024-01-15" in out  # what is not personal stays
    assert "@example.com" in out and "192.0.2." in out and "IBAN ES" in out
    name = out.split("Usuario: ")[1].split(" ·")[0]
    assert name.split()[0] in who.women and len(name.split()) == 3
    assert pii.fake_name("Daniel Ruiz", who).split()[0] in who.men
    assert pii.scramble("AB-12 cd") != "AB-12 cd" and len(pii.scramble("AB-12 cd")) == 8


def test_every_language_has_its_invented_people():
    from coursekit import lang

    for code in lang.LANGUAGES:
        people = lang.tokens(code)["capture_people"]
        assert people["women"] and people["men"] and people["last_names"] and people["companies"] and people["email_domain"]


# ── on the pixels ────────────────────────────────────────────────────────────────────────────

def screen(path):
    """A fake screen: white, with a dark band where the email is written."""
    image = Image.new("RGB", (400, 120), "white")
    image.paste((20, 20, 20), (100, 40, 300, 60))
    image.save(path)
    return path


def fake_reader(image):
    return [redact._line_from_words([("Email:", (20, 40, 70, 20)), ("ana.lopez@acme.example", (100, 40, 200, 20))]),
            redact._line_from_words([("Guardar", (20, 90, 60, 20))])]


def test_only_the_personal_data_is_covered(tmp_path):
    source, target, sheet = screen(tmp_path / "in.png"), tmp_path / "out.png", tmp_path / "review.png"
    rules = {**RULES, "faces": False, "pixels": "solid", "padding": 2}
    report = redact.redact_image(source, target, redact.Redactor(rules, pii.people("es"), [], fake_reader, "fake"), sheet)
    assert report.findings == {"email": 1} and report.samples[0]["boxes"] == [[100, 40, 200, 20, "email"]]
    with Image.open(target) as out:
        assert out.getpixel((200, 50)) == (40, 40, 40)  # covered
        assert out.getpixel((40, 95)) == (255, 255, 255) and out.getpixel((99, 30)) == (255, 255, 255)  # the rest is intact
    assert sheet.exists()


def test_pixelate_and_blur_change_only_the_box(tmp_path):
    image = Image.new("RGB", (100, 40), "white")
    for x in range(10, 60, 2):
        image.paste((0, 0, 0), (x, 10, x + 1, 30))
    for style in ("pixelate", "blur"):
        out = redact.cover(image, [redact.Box(10, 10, 50, 20, "email")], style, 0)
        assert out.crop((10, 10, 60, 30)).tobytes() != image.crop((10, 10, 60, 30)).tobytes()
        assert out.crop((70, 0, 100, 40)).tobytes() == image.crop((70, 0, 100, 40)).tobytes()


def test_without_the_face_detector_the_review_says_so():
    redactor = redact.Redactor({**RULES, "faces": True}, pii.people("en"), [], fake_reader, "fake")
    if redactor.faces is None:
        assert any("faces were not looked for" in w for w in redactor.report.warnings)


# ── a recording a person provided ────────────────────────────────────────────────────────────

@pytest.fixture
def recording(course, capsys, monkeypatch):  # noqa: F811
    configure(course.parent.parent, redact={"faces": False, "pixels": "solid"})
    interface_asset(course, capsys)
    monkeypatch.setattr(redact, "reader", lambda choice, language: ("fake", fake_reader))
    folder = course / "media" / "recordings"
    folder.mkdir(parents=True, exist_ok=True)
    screen(folder / "U1-S2-M1.png")
    return course


def asset_capture(course_dir):
    return yaml.safe_load((course_dir / "media" / "manifest.yaml").read_text(encoding="utf-8"))["assets"][0].get("capture")


def test_redact_moves_the_original_out_and_waits_for_a_person(recording, capsys):
    course_dir = recording
    assert main(["capture", "redact", "PWD", "U1-S2-M1"]) == 0
    out = capsys.readouterr().out
    assert "U1-S2-M1: covered (email 1) in courses/PWD/media/recordings/U1-S2-M1.png" in out and "review.html" in out
    state = asset_capture(course_dir)
    assert state["state"] == "captured" and state["findings"] == {"email": 1} and state["engine"] == "fake"
    raw = capture._raw_file(find_project(), "PWD", "U1-S2-M1")
    assert raw is not None and course_dir.parent.parent not in raw.parents  # the original is outside the project
    review = (course_dir.parent.parent / ".cache" / "capture" / "PWD" / "U1-S2-M1" / "review.html").read_text(encoding="utf-8")
    assert "ana.lopez" not in review and "email 1" in review  # never the real value
    # until a person approves it, it cannot be produced
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced", "--recipe", "screenshot"]) == 1
    assert "waits for a person to review it" in capsys.readouterr().err
    assert main(["capture", "review", "PWD", "U1-S2-M1"]) == 0
    assert capsys.readouterr().out.strip().endswith("review.html")


def test_a_rejection_covers_it_again_from_the_original_with_what_was_missing(recording, capsys):
    course_dir = recording
    assert main(["capture", "redact", "PWD", "U1-S2-M1"]) == 0
    assert main(["capture", "reject", "PWD", "U1-S2-M1"]) == 1
    assert "reject needs --note" in capsys.readouterr().err
    assert main(["capture", "reject", "PWD", "U1-S2-M1", "--note", "the button shows the company", "--mask", "Guardar"]) == 0
    state = asset_capture(course_dir)
    assert state["state"] == "rejected" and state["masks"] == ["Guardar"] and state["by"] == "Ana <ana@example.com>"
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced", "--recipe", "screenshot"]) == 1
    capsys.readouterr()
    assert main(["capture", "redact", "PWD", "U1-S2-M1"]) == 0  # from the original kept outside
    assert asset_capture(course_dir)["findings"] == {"email": 1, "term": 1}


def test_approving_deletes_the_original_and_lets_it_be_produced(recording, capsys):
    course_dir = recording
    assert main(["capture", "approve", "PWD", "U1-S2-M1"]) == 1
    assert "no capture waiting for review" in capsys.readouterr().err
    assert main(["capture", "redact", "PWD", "U1-S2-M1"]) == 0
    assert main(["capture", "approve", "PWD", "U1-S2-M1"]) == 0
    assert asset_capture(course_dir)["state"] == "approved"
    assert capture._raw_file(find_project(), "PWD", "U1-S2-M1") is None
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced", "--recipe", "screenshot"]) == 0


def test_originals_are_deleted_after_the_days_they_are_kept(recording, capsys):
    assert main(["capture", "redact", "PWD", "U1-S2-M1"]) == 0
    project = find_project()
    later = dt.datetime.now().astimezone() + dt.timedelta(days=8)
    assert capture.purge_raw(project, now=later) == 1 and capture._raw_file(project, "PWD", "U1-S2-M1") is None


def test_only_a_person_approves_or_rejects_a_capture():
    for action in ("approve", "reject"):
        assert f"Bash(coursekit capture {action}:*)" in agents.DENY_CLAUDE
        assert f"Bash(coursekit capture {action}:*)" in launch.CLAUDE_DENY
        assert agents.DENY_OPENCODE[f"*coursekit capture {action}*"] == "deny"
    assert not any("capture redact" in rule or "capture review" in rule for rule in agents.DENY_CLAUDE)


def test_a_video_is_covered_between_readings(tmp_path, monkeypatch):
    cv2 = pytest.importorskip("cv2")
    import shutil as sh

    import numpy as np

    if not sh.which("ffmpeg"):
        pytest.skip("ffmpeg is not installed")
    source = tmp_path / "in.mp4"
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"mp4v"), 10, (400, 120))
    for _ in range(20):
        writer.write(np.full((120, 400, 3), 255, np.uint8))
    writer.release()
    rules = {**RULES, "faces": False, "pixels": "solid", "padding": 0}
    target = tmp_path / "out.mp4"
    report = redact.redact_video(source, target, redact.Redactor(rules, pii.people("en"), [], fake_reader, "fake"), 2,
                                 tmp_path / "sheet")
    assert report.frames == 20 and len(report.samples) == 4 and target.exists()
    video = cv2.VideoCapture(str(target))
    ok, frame = video.read()
    assert ok and frame[50, 200].max() < 90 and frame[100, 30].min() > 200


# ── the MCP server ───────────────────────────────────────────────────────────────────────────

from coursekit import capture_session, mcpserver  # noqa: E402


def test_the_mcp_server_answers_the_protocol():
    def boom(args):
        raise mcpserver.ToolError("not now")

    tools = [mcpserver.Tool("echo", "Echo.", mcpserver.schema({"v": {"type": "string"}}, ["v"]),
                            lambda a: [mcpserver.text(a["v"])]), mcpserver.Tool("boom", "Fails.", mcpserver.schema(), boom)]
    server = mcpserver.Server("test", "1.0", tools, "Use it well.")
    import io

    lines = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
             {"jsonrpc": "2.0", "method": "notifications/initialized"},
             {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
             {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "echo", "arguments": {"v": "hi"}}},
             {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "boom"}},
             {"jsonrpc": "2.0", "id": 5, "method": "nope"}]
    out = io.StringIO()
    server.serve(io.StringIO("\n".join(json.dumps(m) for m in lines) + "\nnot json\n"), out)
    answers = [json.loads(line) for line in out.getvalue().splitlines()]
    assert [a.get("id") for a in answers] == [1, 2, 3, 4, 5, None]  # the notification gets no answer
    assert answers[0]["result"]["protocolVersion"] == "2025-03-26" and answers[0]["result"]["instructions"] == "Use it well."
    assert [t["name"] for t in answers[1]["result"]["tools"]] == ["echo", "boom"]
    assert answers[2]["result"] == {"content": [{"type": "text", "text": "hi"}], "isError": False}
    assert answers[3]["result"]["isError"] and answers[3]["result"]["content"][0]["text"] == "not now"
    assert answers[4]["error"]["code"] == -32601 and answers[5]["error"]["code"] == -32700


# ── a session, with a fake browser ───────────────────────────────────────────────────────────

class FakeBrowser:
    def __init__(self, profile, start_url, domains, viewport, scale, redact, page_config):
        self.viewport, self.scale, self.redact, self.page_config = viewport, scale, redact, page_config
        self.current, self.calls, self.secret, self.closed = start_url, [], False, False

    def screenshot(self):
        import io

        image = Image.new("RGB", (round(self.viewport[0] * self.scale), round(self.viewport[1] * self.scale)), "white")
        out = io.BytesIO()
        image.save(out, "PNG")
        return out.getvalue()

    def click(self, x, y, button, count):
        self.calls.append(("click", x, y, button, count))

    def move(self, x, y):
        self.calls.append(("move", x, y))

    def drag(self, *points):
        self.calls.append(("drag", *points))

    def scroll(self, x, y, dx, dy):
        self.calls.append(("scroll", x, y, dx, dy))

    def type(self, text):
        self.calls.append(("type", text))

    def key(self, combo):
        self.calls.append(("key", combo))

    def wait(self, ms):
        self.calls.append(("wait", ms))

    def navigate(self, url):
        self.current = url
        self.calls.append(("navigate", url))

    def target_at(self, x, y):
        return {"role": "button", "name": "Guardar"}

    def focused_is_secret(self):
        return self.secret

    def url(self):
        return self.current

    def close(self):
        self.closed = True


@pytest.fixture
def allowed(course, browser, capsys, monkeypatch):  # noqa: F811
    root = course.parent.parent
    profile = {**PROFILE, "login_url": "https://sso.acme.example/login"}
    configure(root, profiles={"acme-admin": profile}, redact={"pixel_check": False})
    interface_asset(course, capsys)
    assert main(["capture", "login", "acme-admin"]) == 0
    assert main(["capture", "allow", "PWD", "U1-S2-M1", "--mode", "browser", "--profile", "acme-admin"]) == 0
    capsys.readouterr()
    return course


def test_a_session_needs_the_permission_and_a_capture_recipe(course, browser, capsys, monkeypatch):  # noqa: F811
    root = course.parent.parent
    project = find_project()
    with pytest.raises(mcpserver.ToolError, match="capture is turned off"):
        capture_session.start(project, "PWD", "U1-S2-M1", FakeBrowser)
    configure(root)
    prepare_asset(course, capsys)
    assert main(["media", "set", "PWD", "U1-S2-M1", "--depicts", "interface"]) == 0
    with pytest.raises(mcpserver.ToolError, match="not made from a capture"):
        capture_session.start(project, "PWD", "U1-S2-M1", FakeBrowser)
    assert main(["media", "set", "PWD", "U1-S2-M1", "--recipe", "screenshot", "--status", "scripted"]) == 0
    with pytest.raises(mcpserver.ToolError, match="no permission in force"):
        capture_session.start(project, "PWD", "U1-S2-M1", FakeBrowser)
    assert main(["capture", "allow", "PWD", "--mode", "desktop", "--window", "W"]) == 0
    monkeypatch.setattr(capture_session.redactmod, "reader", lambda *a: (_ for _ in ()).throw(redact.RedactError("no OCR")))
    with pytest.raises(mcpserver.ToolError, match="an OCR is needed"):
        capture_session.start(project, "PWD", "U1-S2-M1", FakeBrowser)


def test_the_coordinates_of_the_agent_are_those_of_what_it_sees(allowed):
    session = capture_session.start(find_project(), "PWD", "U1-S2-M1", FakeBrowser)
    with Image.open(__import__("io").BytesIO(session.screenshot())) as seen:
        assert seen.size == (1920, 1200)  # 1440x900 at 2x, made to fit 1920
    session.click(960, 600)
    assert session.backend.calls[-1] == ("click", 720.0, 450.0, "left", 1)
    assert session.steps[-1] == {"click": {"x": 720, "y": 450, "target": {"role": "button", "name": "Guardar"}}}
    with pytest.raises(mcpserver.ToolError, match="outside the screen"):
        session.click(5000, 10)
    with Image.open(__import__("io").BytesIO(session.zoom(0, 0, 480, 300))) as part:
        assert part.size == (1920, 1200)  # a quarter of the screen, four times closer


def test_a_session_never_types_a_secret_or_leaves_the_application(allowed):
    session = capture_session.start(find_project(), "PWD", "U1-S2-M1", FakeBrowser)
    session.backend.secret = True
    with pytest.raises(mcpserver.ToolError, match="password or a code"):
        session.type("hunter2")
    session.backend.secret = False
    session.type("12")
    with pytest.raises(mcpserver.ToolError, match="never leaves the application"):
        session.navigate("https://elsewhere.test/")
    session.navigate("/users?page=2")
    assert session.backend.current == "https://app.acme.example/users?page=2"
    assert session.steps[-2:] == [{"type": "12"}, {"navigate": "/users?page=2"}]
    session.key("ctrl+shift+a")
    assert session.backend.calls[-1] == ("key", "Control+Shift+A")


def test_the_page_gets_its_texts_back_with_invented_data_counted_once(allowed):
    session = capture_session.start(find_project(), "PWD", "U1-S2-M1", FakeBrowser)
    out = session.backend.redact(["Hola, Ana López", "ana@acme.example", "Hola, Ana López", "Guardar"])
    assert "Ana López" not in out[0] and out[0] == out[2] and "@example.com" in out[1] and out[3] == "Guardar"
    assert {k: len(v) for k, v in session.seen.items()} == {"name": 1, "email": 1}
    assert session.backend.page_config == {"selectors": [], "avatars": True, "visible": True}


def test_the_session_ends_when_the_permission_goes_or_the_login_page_appears(allowed):
    manager = capture_session.Manager(find_project(), FakeBrowser)
    tools = {tool.name: tool for tool in manager.tools()}
    content = tools["session_start"].run({"code": "PWD", "asset_id": "U1-S2-M1"})
    assert content[0]["type"] == "text" and content[1]["type"] == "image"
    with pytest.raises(mcpserver.ToolError, match="already a session"):
        tools["session_start"].run({"code": "PWD", "asset_id": "U1-S2-M1"})
    manager.session.backend.current = "https://sso.acme.example/login?next=/"
    backend = manager.session.backend
    with pytest.raises(mcpserver.ToolError, match="session of the profile acme-admin expired"):
        tools["left_click"].run({"x": 10, "y": 10})
    assert manager.session is None and backend.closed
    tools["session_start"].run({"code": "PWD", "asset_id": "U1-S2-M1"})
    assert main(["capture", "revoke", "PWD"]) == 0
    with pytest.raises(mcpserver.ToolError, match="no longer in force"):
        tools["screenshot"].run({})
    assert manager.session is None


def test_session_end_writes_the_steps_in_the_brief_and_waits_for_a_person(allowed, capsys):
    course_dir = allowed
    brief = course_dir / "media" / "scripts" / "U1-S2-M1.md"
    brief.parent.mkdir(parents=True, exist_ok=True)
    brief.write_text("# Change the minimum length\n\nShow where it is.\n\n```capture\nstart: /settings/security\n"
                     "mask: [{selector: .account-email}, {text: ACME-0042}]\n```\n\nEnd of the brief.\n", encoding="utf-8")
    manager = capture_session.Manager(find_project(), FakeBrowser)
    tools = {tool.name: tool for tool in manager.tools()}
    tools["session_start"].run({"code": "PWD", "asset_id": "U1-S2-M1"})
    assert manager.session.start_url == "https://app.acme.example/settings/security"
    assert manager.session.backend.page_config["selectors"] == [".account-email"]
    assert manager.session.backend.redact(["ref ACME-0042"]) != ["ref ACME-0042"]  # a text of the mask of the brief
    tools["left_click"].run({"x": 100, "y": 100})
    tools["record_start"].run({})
    tools["key"].run({"key": "enter"})
    tools["record_stop"].run({})
    assert "capture saved in courses/PWD/media/recordings/U1-S2-M1.png" in tools["save_shot"].run({})[0]["text"]
    end = tools["session_end"].run({"notes": "done"})[0]["text"]
    assert "waits for a person" in end and "coursekit capture replay PWD U1-S2-M1" in end
    text = brief.read_text(encoding="utf-8")
    assert text.startswith("# Change the minimum length") and text.rstrip().endswith("End of the brief.")
    block = capture_session.read_block({"_dir": course_dir}, "U1-S2-M1")
    assert block["profile"] == "acme-admin" and block["start"] == "/settings/security" and block["notes"] == "done"
    assert block["mask"] == [{"selector": ".account-email"}, {"text": "ACME-0042"}]
    assert [list(s)[0] for s in block["steps"]] == ["click", "record", "key", "record", "shot"]
    state = asset_capture(course_dir)
    assert state["state"] == "captured" and state["source"] == "session" and state["replay"] is True
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced", "--recipe", "screenshot"]) == 1  # a person first
    assert main(["capture", "approve", "PWD", "U1-S2-M1"]) == 0


def test_the_capture_server_is_registered_only_when_capture_is_on(course, capsys):  # noqa: F811
    root = course.parent.parent
    configure(root)
    assert main(["agents"]) == 0
    mcp = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["coursekit-capture"]
    assert mcp == {"type": "stdio", "command": "coursekit", "args": ["capture", "serve"]}
    oc = json.loads((root / "opencode.json").read_text(encoding="utf-8"))["mcp"]["coursekit-capture"]
    assert oc["command"] == ["coursekit", "capture", "serve"]
    assert '[mcp_servers."coursekit-capture"]' in (root / ".codex" / "config.toml").read_text(encoding="utf-8")
    configure(root, enabled=False)
    assert main(["agents"]) == 0
    assert "coursekit-capture" not in json.loads((root / ".mcp.json").read_text(encoding="utf-8")).get("mcpServers", {})
    assert "coursekit-capture" not in json.loads((root / "opencode.json").read_text(encoding="utf-8")).get("mcp", {})


def test_the_page_script_replaces_text_and_never_touches_what_can_be_edited(tmp_path):
    import subprocess
    from importlib import resources

    from coursekit import mediatools

    exe = mediatools.browser()
    if not exe:
        pytest.skip("no Chrome, Edge or Chromium")
    script = resources.files("coursekit.tools").joinpath("capture-dom.js").read_text(encoding="utf-8")
    page = tmp_path / "page.html"
    page.write_text(
        "<!doctype html><html><head><title>Ana López · panel</title><script>window.__ckConfig={selectors:['.secret'],avatars:true};"
        "window.__ckRedact=async t=>t.map(x=>x.replace(/Ana López/g,'Paula Ortega').replace(/ana@acme\\.example/g,'p@example.com'));"
        f"</script><script>{script}</script></head><body><p id=a>Hola, Ana López</p><span title='Ana López'>x</span>"
        "<input id=f value='ana@acme.example'><input id=g value='nada'><div contenteditable=true id=e>Para Ana López</div>"
        "<div class=secret id=s>s</div><img id=av class=user-avatar src=''><div id=host></div><script>"
        "document.getElementById('host').attachShadow({mode:'closed'}).innerHTML='<b>Ana López</b>';"
        "setTimeout(()=>{const p=document.createElement('p');p.id='late';p.textContent='Llega ana@acme.example';"
        "document.body.appendChild(p)},100);setTimeout(()=>{const h=document.getElementById('host');"
        "document.body.dataset.shadow=h.shadowRoot?h.shadowRoot.innerHTML:'none';document.body.dataset.pending=window.__ckPending;"
        "document.body.dataset.hidden=document.documentElement.className},600);</script></body></html>", encoding="utf-8")
    dom = subprocess.run([exe, "--headless=new", "--disable-gpu", "--virtual-time-budget=3000", "--dump-dom", page.as_uri()],
                         capture_output=True, text=True, encoding="utf-8", timeout=60).stdout
    assert "<title>Paula Ortega · panel</title>" in dom and '<p id="a">Hola, Paula Ortega</p>' in dom
    assert 'title="Paula Ortega"' in dom and "Llega p@example.com" in dom
    assert 'data-shadow="&lt;b&gt;Paula Ortega&lt;/b&gt;"' in dom  # a closed shadow root is reached too
    assert 'value="ana@acme.example" class="ck-blur-field"' in dom and 'id="g" value="nada">' in dom  # never the value
    assert ">Para Ana López</div>" in dom and 'id="e" class="ck-blur-field"' in dom
    assert 'class="secret ck-blur"' in dom and 'class="user-avatar ck-blur"' in dom
    assert 'data-pending="0"' in dom and 'data-hidden=""' in dom


# ── replay ───────────────────────────────────────────────────────────────────────────────────

from coursekit import capture_replay  # noqa: E402


class ReplayBrowser(FakeBrowser):
    """A fake browser that also finds elements by name and records frames."""

    elements = {("button", "Guardar"): (300.0, 200.0), ("label", "Longitud mínima"): (500.0, 260.0)}

    def __init__(self, *args):
        super().__init__(*args)
        self.recording = False

    def glide(self, x, y, ms):
        self.calls.append(("glide", x, y, ms))

    def locate(self, target):
        if target.get("role") and target.get("name"):
            return self.elements.get((target["role"], target["name"]))
        return self.elements.get(("label", target.get("label") or target.get("name")))

    def type_slowly(self, text, delay):
        self.calls.append(("type_slowly", text, delay))

    def start_recording(self):
        self.recording = True
        self.calls.append(("record", True))

    def stop_recording(self):
        import io

        self.recording = False
        self.calls.append(("record", False))
        frames = []
        for i, shade in enumerate((255, 200, 150)):
            out = io.BytesIO()
            Image.new("RGB", (64, 48), (shade, shade, shade)).save(out, "JPEG")
            frames.append((100.0 + i * 0.5, out.getvalue()))
        return [*frames, (102.0, b"")]


def write_steps(course_dir, steps):
    capture_session.write_block({"_dir": course_dir}, "U1-S2-M1", {"start": "/settings", "steps": steps})


def test_replay_finds_targets_by_name_first_and_at_the_pace_of_a_person(allowed, monkeypatch):
    configure(allowed.parent.parent, profiles={"acme-admin": PROFILE}, redact={"pixel_check": False},
              replay={"pause_ms": 5, "move_ms": 40, "type_delay_ms": 9})
    write_steps(allowed, [{"click": {"x": 10, "y": 10, "target": {"role": "button", "name": "Guardar"}}},
                          {"click": {"x": 11, "y": 12, "target": {"role": "button", "name": "Moved away"}}},
                          {"fill": {"label": "Longitud mínima", "value": "12"}}, {"key": "enter"}, {"shot": True}])
    result = capture_replay.replay(find_project(), "PWD", "U1-S2-M1", ReplayBrowser)
    assert result["video"] is None and [p.name for p in result["shots"]] == ["U1-S2-M1.png"]
    state = asset_capture(allowed)
    assert state["state"] == "captured" and state["source"] == "replay" and state["file"] == "media/recordings/U1-S2-M1.png"


def test_replay_moves_the_pointer_before_acting(allowed, monkeypatch):
    configure(allowed.parent.parent, profiles={"acme-admin": PROFILE}, redact={"pixel_check": False},
              replay={"pause_ms": 5, "move_ms": 40, "type_delay_ms": 9})
    seen = {}
    real_start = capture_session.start

    def start(*args, **kwargs):
        seen["session"] = real_start(*args, **kwargs)
        seen["cursor"] = seen["session"].backend.page_config.get("cursor")
        return seen["session"]

    monkeypatch.setattr(capture_replay.sessionmod, "start", start)
    write_steps(allowed, [{"click": {"x": 10, "y": 10, "target": {"role": "button", "name": "Guardar"}}},
                          {"click": {"x": 11, "y": 12, "target": {"role": "button", "name": "Moved away"}}},
                          {"fill": {"label": "Longitud mínima", "value": "12"}}, {"shot": True}])
    capture_replay.replay(find_project(), "PWD", "U1-S2-M1", ReplayBrowser)
    calls = [c for c in seen["session"].backend.calls if c[0] in ("glide", "click", "type_slowly", "key")]
    assert calls[:2] == [("glide", 300.0, 200.0, 40), ("click", 300.0, 200.0, "left", 1)]  # by its name
    assert calls[2:4] == [("glide", 11.0, 12.0, 40), ("click", 11.0, 12.0, "left", 1)]  # the name is gone: by position
    assert calls[4:] == [("glide", 500.0, 260.0, 40), ("click", 500.0, 260.0, "left", 1), ("key", "ControlOrMeta+A"),
                         ("type_slowly", "12", 9)]
    assert seen["cursor"] is True


def test_replay_stops_on_a_target_it_cannot_find_or_a_step_it_does_not_know(allowed):
    configure(allowed.parent.parent, profiles={"acme-admin": PROFILE}, redact={"pixel_check": False})
    write_steps(allowed, [{"click": {"label": "Nowhere"}}])
    with pytest.raises(capture_replay.ReplayError, match="step 1: .* is not found on screen"):
        capture_replay.replay(find_project(), "PWD", "U1-S2-M1", ReplayBrowser)
    write_steps(allowed, [{"dance": True}])
    with pytest.raises(capture_replay.ReplayError, match="step 1: .* is not a step"):
        capture_replay.replay(find_project(), "PWD", "U1-S2-M1", ReplayBrowser)
    write_steps(allowed, [{"wait": 10}])
    with pytest.raises(capture_replay.ReplayError, match="save nothing"):
        capture_replay.replay(find_project(), "PWD", "U1-S2-M1", ReplayBrowser)


def test_replay_needs_the_permission_too(allowed):
    write_steps(allowed, [{"shot": True}])
    assert main(["capture", "revoke", "PWD"]) == 0
    with pytest.raises(capture_replay.ReplayError, match="no permission in force"):
        capture_replay.replay(find_project(), "PWD", "U1-S2-M1", ReplayBrowser)


def test_replay_records_the_stretches_marked_as_a_video(allowed, capsys, monkeypatch):
    import shutil as sh

    if not sh.which("ffmpeg"):
        pytest.skip("ffmpeg is not installed")
    configure(allowed.parent.parent, profiles={"acme-admin": PROFILE}, redact={"pixel_check": False},
              replay={"pause_ms": 1, "move_ms": 1, "fps": 10})
    write_steps(allowed, [{"record": "start"}, {"click": {"label": "Longitud mínima"}}, {"record": "stop"},
                          {"record": "start"}, {"key": "enter"}])  # the last stretch records until the end
    monkeypatch.setattr(capture_session, "BrowserBackend", ReplayBrowser)
    capsys.readouterr()
    assert main(["capture", "replay", "PWD", "U1-S2-M1"]) == 0
    assert "U1-S2-M1: replayed; courses/PWD/media/recordings/U1-S2-M1.mp4" in capsys.readouterr().out
    video = allowed / "media" / "recordings" / "U1-S2-M1.mp4"
    assert video.stat().st_size > 0
    assert not list(video.parent.glob("*.part*"))
    probe = subprocess_duration(video)
    assert 3.5 <= probe <= 4.5  # two stretches of two seconds each
    assert asset_capture(allowed)["file"] == "media/recordings/U1-S2-M1.mp4"
    assert list((allowed.parent.parent / ".cache" / "capture" / "PWD" / "U1-S2-M1").glob("t*.png"))


def subprocess_duration(path):
    import shutil as sh
    import subprocess

    probe = sh.which("ffprobe")
    if not probe:
        pytest.skip("ffprobe is not installed")
    out = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


# ── a window of a desktop program ────────────────────────────────────────────────────────────

from coursekit import capture_macos, capture_window, capture_windows, capture_x11  # noqa: E402


class FakeWindow:
    """A window of 800 x 500 points on a Retina screen, with an email written at (100, 40) points."""

    def __init__(self, name):
        self.name, self.viewport, self.calls, self.secret = name, (800, 500), [], False

    def screenshot(self):
        import io

        image = Image.new("RGB", (1600, 1000), "white")
        image.paste((20, 20, 20), (200, 80, 600, 120))
        out = io.BytesIO()
        image.save(out, "PNG")
        return out.getvalue()

    def click(self, x, y, button, count):
        self.calls.append(("click", x, y))

    def glide(self, x, y, ms):
        self.calls.append(("glide", x, y))

    def locate(self, target):
        return None

    def wait(self, ms):
        pass

    def key(self, combo):
        self.calls.append(("key", combo))

    def focused_is_secret(self):
        return self.secret

    def target_at(self, x, y):
        return {"role": "button", "name": "OK"}

    def url(self):
        return ""

    def close(self):
        self.calls.append(("close",))


def window_reader(image):
    return [redact._line_from_words([("ana.lopez@acme.example", (200, 80, 400, 40))])]


@pytest.fixture
def desktop(course, capsys, monkeypatch):  # noqa: F811
    configure(course.parent.parent, redact={"faces": False, "pixels": "solid", "padding": 0})
    interface_asset(course, capsys)
    assert main(["capture", "allow", "PWD", "U1-S2-M1", "--mode", "desktop", "--window", "Password Manager"]) == 0
    monkeypatch.setattr(capture_session.redactmod, "reader", lambda choice, language: ("fake", window_reader))
    capsys.readouterr()
    return course


def test_a_desktop_window_is_covered_on_the_pixels_before_the_agent_sees_it(desktop):
    import io

    session = capture_session.start(find_project(), "PWD", "U1-S2-M1", FakeWindow)
    assert session.backend.name == "Password Manager"
    with Image.open(io.BytesIO(session.screenshot())) as seen:
        assert seen.size == (1600, 1000) and seen.getpixel((400, 100)) == (40, 40, 40) and seen.getpixel((10, 10)) == (255,) * 3
    session.click(800, 500)  # the pixels of the screenshot → points of the window
    assert session.backend.calls[-1] == ("click", 400.0, 250.0)
    with pytest.raises(mcpserver.ToolError, match="does not navigate"):
        session.navigate("/x")
    session.save_shot()
    out = session.end()
    block = capture_session.read_block({"_dir": desktop}, "U1-S2-M1")
    assert block["mode"] == "desktop" and block["window"] == "Password Manager" and block["window_size"] == {"width": 800, "height": 500}
    assert out["findings"] == {"email (pixels)": 1} and asset_capture(desktop)["engine"] == "pixels + fake"
    with Image.open(desktop / "media" / "recordings" / "U1-S2-M1.png") as saved:
        assert saved.getpixel((400, 100)) == (40, 40, 40)


def test_a_desktop_replay_never_keeps_a_video_it_could_not_cover(desktop, monkeypatch, tmp_path):
    import shutil as sh
    import subprocess

    ffmpeg = sh.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg is not installed")
    recorded = tmp_path / "screen.mp4"
    subprocess.run([ffmpeg, "-loglevel", "error", "-f", "lavfi", "-i", "color=c=white:s=64x48:d=1", "-pix_fmt", "yuv420p",
                    str(recorded)], check=True)

    class RecordingWindow(FakeWindow):
        def start_recording(self):
            pass

        def stop_recording(self):
            return recorded

    configure(desktop.parent.parent, redact={"faces": False, "pixels": "solid"}, replay={"pause_ms": 1, "move_ms": 1})
    write_steps(desktop, [{"record": "start"}, {"click": {"x": 10, "y": 20}}, {"record": "stop"}])
    monkeypatch.setattr(capture_replay.redactmod, "redact_video",
                        lambda *a, **k: (_ for _ in ()).throw(redact.RedactError("covering a video needs the capture extra")))
    with pytest.raises(capture_replay.ReplayError, match="needs the capture extra"):
        capture_replay.replay(find_project(), "PWD", "U1-S2-M1", RecordingWindow)
    assert not (desktop / "media" / "recordings" / "U1-S2-M1.mp4").exists()


def test_keys_and_windows_of_the_mac_are_understood():
    assert capture_macos.parse_combo("Control+Shift+A") == (0, 0x40000 | 0x20000)
    assert capture_macos.parse_combo("ControlOrMeta+A") == (0, 0x100000)
    assert capture_macos.parse_combo("A") == (0, 0x20000) and capture_macos.parse_combo("Enter") == (36, 0)
    with pytest.raises(mcpserver.ToolError, match="not a key"):
        capture_macos.parse_combo("Hyper+Q")
    windows = [{"id": 1, "pid": 9, "layer": 25, "bounds": (0, 0, 1000, 800)},  # an overlay of the system
               {"id": 2, "pid": 7, "layer": 0, "bounds": (50, 50, 100, 100)},  # another program, in front
               {"id": 3, "pid": 5, "layer": 101, "bounds": (0, 0, 10, 10)},  # a menu of ours
               {"id": 4, "pid": 5, "layer": 0, "bounds": (0, 0, 400, 300)}]
    assert [w["id"] for w in capture_macos.covering(windows, 5)] == [2, 3, 4]
    image = capture_window.paint_out(Image.new("RGB", (800, 600), "white"), (0, 0), 2, [(50, 50, 100, 100)])
    assert image.getpixel((150, 150)) == (24, 24, 24) and image.getpixel((90, 90)) == (255, 255, 255)


def test_the_windows_of_this_mac_can_be_listed():
    import sys

    if sys.platform != "darwin":
        pytest.skip("macOS only")
    windows = capture_macos.quartz().windows()
    assert all({"id", "owner", "pid", "title", "layer", "bounds"} <= set(w) for w in windows)
    assert set(capture_macos.permissions()) == {"screen", "accessibility"}


def test_doctor_says_what_capture_needs_only_when_the_project_captures(course, capsys):  # noqa: F811
    from coursekit import doctor

    project = find_project()
    assert doctor.capture_section(project) is None
    configure(course.parent.parent, modes=["browser"])
    labels = [c.label for c in doctor.capture_section(project).checks]
    assert any("Playwright" in label for label in labels) and any("OCR" in label for label in labels)
    assert not any("Accessibility" in label for label in labels)


def test_keys_of_windows_and_x11_are_understood():
    assert capture_windows.virtual_keys("Control+Shift+A") == [0x11, 0x10, ord("A")]
    assert capture_windows.virtual_keys("ControlOrMeta+A") == [0x11, ord("A")] and capture_windows.virtual_keys("Enter") == [0x0D]
    assert capture_windows.virtual_keys(";", scan=lambda ch: 0x1BA) == [0xBA]
    with pytest.raises(mcpserver.ToolError, match="not a key"):
        capture_windows.virtual_keys("Hyper+Q")
    assert capture_x11.xdotool_keys("Control+Shift+A") == "ctrl+shift+a"
    assert capture_x11.xdotool_keys("Enter") == "Return" and capture_x11.xdotool_keys("ControlOrMeta+-") == "ctrl+minus"
    assert capture_x11.shell_values("X=10\nY=20\nWIDTH=800\n") == {"X": "10", "Y": "20", "WIDTH": "800"}


def test_a_window_is_found_only_when_one_program_matches():
    every = [{"pid": 1, "owner": "Gestor", "title": "Bóveda — Gestor", "bounds": (0, 0, 800, 600)},
             {"pid": 1, "owner": "Gestor", "title": "Ajustes", "bounds": (0, 0, 400, 300)},
             {"pid": 2, "owner": "Notes", "title": "Gestor de tareas", "bounds": (0, 0, 800, 600)}]
    assert capture_window.one_program([w for w in every if capture_window.matches(w, "bóveda")], "bóveda", every)["pid"] == 1
    with pytest.raises(mcpserver.ToolError, match="several programs"):
        capture_window.one_program([w for w in every if capture_window.matches(w, "gestor")], "gestor", every)
    with pytest.raises(mcpserver.ToolError, match="no open window"):
        capture_window.one_program([], "nada", every)


def test_the_x11_backend_reads_what_xdotool_says(monkeypatch):
    """No X server here: xdotool answers from a table."""
    answers = {
        ("search", "--onlyvisible", "--name", "."): "11\n12\n",
        ("getwindowgeometry", "--shell", "11"): "WINDOW=11\nX=100\nY=50\nWIDTH=800\nHEIGHT=600\n",
        ("getwindowgeometry", "--shell", "12"): "WINDOW=12\nX=0\nY=0\nWIDTH=300\nHEIGHT=200\n",
        ("getwindowpid", "11"): "4242\n", ("getwindowpid", "12"): "77\n",
        ("getwindowname", "11"): "Gestor de contraseñas\n", ("getwindowname", "12"): "Terminal\n",
        ("getmouselocation", "--shell"): "X=150\nY=60\nSCREEN=0\nWINDOW=12\n",
    }
    calls = []

    def run(self, *args, check=True):
        calls.append(args)
        return answers.get(args, "")

    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)
    monkeypatch.setattr(capture_x11.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(capture_x11.X11Backend, "_run", run)
    backend = capture_x11.X11Backend("contraseñas")
    assert backend.window["id"] == "11" and backend.viewport == (800, 600)
    with pytest.raises(mcpserver.ToolError, match="not of the allowed program"):
        backend.click(50, 10, "left", 1)  # what is under the pointer is the terminal
    assert not any(a[0] == "mousedown" for a in calls)
    answers[("getmouselocation", "--shell")] = "WINDOW=11\n"
    backend.click(50, 10, "left", 2)
    assert [a for a in calls if a[0] in ("mousedown", "mouseup")] == [("mousedown", "1"), ("mouseup", "1")] * 2
    assert ("mousemove", "150", "60") in calls
    backend.key("Control+Shift+A")
    assert calls[-1] == ("key", "--clearmodifiers", "ctrl+shift+a")
    assert backend.record_args(backend.bounds())[0][-1] == ":0+100,50"
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    with pytest.raises(mcpserver.ToolError, match="Wayland"):
        capture_x11.X11Backend("contraseñas")


def test_replay_writes_when_and_where_each_click_and_point_happens(allowed, monkeypatch):
    import shutil as sh

    if not sh.which("ffmpeg"):
        pytest.skip("ffmpeg is not installed")
    configure(allowed.parent.parent, profiles={"acme-admin": PROFILE}, redact={"pixel_check": False},
              replay={"pause_ms": 1, "move_ms": 1, "fps": 10})
    clock = iter([100.0 + i * 0.25 for i in range(400)])
    monkeypatch.setattr(capture_replay.time, "time", lambda: next(clock))
    write_steps(allowed, [{"record": "start"}, {"point": {"label": "Longitud mínima", "note": "the minimum length"}},
                          {"click": {"role": "button", "name": "Guardar"}}, {"record": "stop"}])
    result = capture_replay.replay(find_project(), "PWD", "U1-S2-M1", ReplayBrowser)
    data = json.loads(result["events"].read_text(encoding="utf-8"))
    assert data["video"] == "U1-S2-M1.mp4" and (data["width"], data["height"]) == (1440, 900)
    point, click = data["events"]
    assert point["kind"] == "point" and point["label"] == "the minimum length" and (point["fx"], point["fy"]) == (0.3472, 0.2889)
    assert click["kind"] == "click" and click["label"] == "Guardar" and point["t"] < click["t"] <= data["duration"]


def test_the_agent_marks_a_place_without_clicking_it(allowed):
    manager = capture_session.Manager(find_project(), FakeBrowser)
    tools = {tool.name: tool for tool in manager.tools()}
    tools["session_start"].run({"code": "PWD", "asset_id": "U1-S2-M1"})
    assert tools["point"].run({"x": 960, "y": 600, "note": "the save button"}) == [{"type": "text", "text": "OK"}]
    assert manager.session.steps[-1] == {"point": {"x": 720, "y": 450, "target": {"role": "button", "name": "Guardar"},
                                                   "note": "the save button"}}
    assert not [c for c in manager.session.backend.calls if c[0] == "click"]


# ── the course itself: its html package or its review link in creator ────────────────────────

from tests.test_exelearning import edit_course  # noqa: E402


class StartBrowser(FakeBrowser):
    opened: list = []

    def __init__(self, profile, start_url, domains, *rest):
        super().__init__(profile, start_url, domains, *rest)
        StartBrowser.opened.append((start_url, list(domains)))


def course_capture(course_dir, capsys, start):
    configure(course_dir.parent.parent, redact={"pixel_check": False})
    interface_asset(course_dir, capsys)
    assert main(["capture", "allow", "PWD", "U1-S2-M1", "--mode", "browser", "--profile", "course"]) == 0  # no login
    capture_session.write_block({"_dir": course_dir}, "U1-S2-M1", {"start": start, "steps": []})
    capsys.readouterr()


def test_the_package_of_the_html_backend_is_served_on_this_machine(course, capsys):  # noqa: F811
    import urllib.request

    edit_course(course, lambda d: d.update(assembly={"backend": "html"}))
    course_capture(course, capsys, "unit:1")
    with pytest.raises(mcpserver.ToolError, match="unit 1 is not built: coursekit assemble build PWD --unit 1"):
        capture_session.start(find_project(), "PWD", "U1-S2-M1", StartBrowser)
    package = course / "assembly" / "html" / "unit-01"
    package.mkdir(parents=True)
    (package / "index.html").write_text("<h1>Contraseñas seguras</h1>", encoding="utf-8")
    session = capture_session.start(find_project(), "PWD", "U1-S2-M1", StartBrowser)
    url, domains = StartBrowser.opened[-1]
    assert url.startswith("http://127.0.0.1:") and url.endswith("/index.html") and domains == ["127.0.0.1"]
    with urllib.request.urlopen(url, timeout=5) as answer:  # noqa: S310 — the local server of the test
        assert "Contraseñas seguras" in answer.read().decode("utf-8")
    session.close()
    with pytest.raises(OSError):
        urllib.request.urlopen(url, timeout=2)  # noqa: S310 — it stopped with the session


def test_a_course_in_creator_is_recorded_from_the_review_link_of_its_unit(course, capsys):  # noqa: F811
    course_capture(course, capsys, "unit:1")
    with pytest.raises(mcpserver.ToolError, match="unit 1 has no review link in creator yet"):
        capture_session.start(find_project(), "PWD", "U1-S2-M1", StartBrowser)
    link = "https://creator.acme.example/review/u1-token"
    edit_course(course, lambda d: d["units"][0].update(links={"review": link}))
    capture_session.start(find_project(), "PWD", "U1-S2-M1", StartBrowser).close()
    assert StartBrowser.opened[-1] == (link, ["creator.acme.example"])
    capture_session.write_block({"_dir": course}, "U1-S2-M1", {"start": "unit:9", "steps": []})
    with pytest.raises(mcpserver.ToolError, match="unit:9 is not a unit of the course"):
        capture_session.start(find_project(), "PWD", "U1-S2-M1", StartBrowser)
    capture_session.write_block({"_dir": course}, "U1-S2-M1", {"start": "/settings", "steps": []})
    with pytest.raises(mcpserver.ToolError, match="needs start: unit:N"):
        capture_session.start(find_project(), "PWD", "U1-S2-M1", StartBrowser)


def test_a_profile_without_login_opens_with_no_session(course, browser, capsys):  # noqa: F811
    public = {"start_url": "https://docs.acme.example/", "allow_domains": ["docs.acme.example"], "login": False}
    configure(course.parent.parent, profiles={"docs": public})
    interface_asset(course, capsys)
    assert main(["capture", "login", "docs"]) == 1
    assert "needs no login" in capsys.readouterr().err and not browser
    assert main(["capture", "allow", "PWD", "U1-S2-M1", "--mode", "browser", "--profile", "docs"]) == 0
    assert main(["capture", "profiles"]) == 0
    assert "docs · — · https://docs.acme.example/ · no login" in capsys.readouterr().out


def test_the_plan_and_the_handoff_say_which_captures_wait_for_a_person(recording, capsys):
    from coursekit import handoff, media
    from coursekit.course import load as load_course

    course_dir = recording
    assert main(["capture", "redact", "PWD", "U1-S2-M1"]) == 0
    capsys.readouterr()
    assert main(["media", "plan", "PWD"]) == 0
    out = capsys.readouterr().out
    assert "waits for a person: coursekit capture review PWD U1-S2-M1" in out and "drop it in" not in out
    loaded = load_course(find_project(), "PWD")
    assert [a["id"] for a in handoff.captures_to_review(loaded)] == ["U1-S2-M1"]
    assert handoff._pending_media(loaded) == [] and handoff.awaiting_recordings(loaded) == []
    assert main(["capture", "reject", "PWD", "U1-S2-M1", "--note", "a name in the header"]) == 0
    capsys.readouterr()
    assert main(["media", "plan", "PWD"]) == 0
    assert "capture rejected (a name in the header): cover it again" in capsys.readouterr().out
    assert media.capture_waiting({"capture": asset_capture(course_dir), "status": "scripted"}) == "rejected"


def test_a_name_read_without_its_accents_is_still_a_name():
    assert kinds("Usuario: Lucia Munoz Pardo") == [("name", "Lucia Munoz Pardo")]


def test_apple_vision_reads_the_words_and_where_each_one_is():
    import sys

    if sys.platform != "darwin":
        pytest.skip("macOS only")
    pytest.importorskip("Vision")
    from PIL import ImageDraw, ImageFont

    image = Image.new("RGB", (1200, 160), "white")
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 36)
    ImageDraw.Draw(image).text((40, 50), "Lucía Muñoz · lucia@acme.example", fill="black", font=font)
    engine, read = redact.reader("auto", "es")
    assert engine == "vision"
    lines = read(image)
    assert any("Lucía Muñoz" in line.text for line in lines)
    boxes = redact.text_boxes(lines, RULES, pii.people("es"), [])
    assert {b.kind for b in boxes} == {"name", "email"}
    name = next(b for b in boxes if b.kind == "name")
    assert 30 <= name.x <= 60 and 40 <= name.y <= 70 and name.w < 300  # the name only, not the whole line
