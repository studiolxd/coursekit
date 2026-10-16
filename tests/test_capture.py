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
