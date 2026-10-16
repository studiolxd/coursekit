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
