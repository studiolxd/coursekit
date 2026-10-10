"""The notice of a newer coursekit: once a day, only in a terminal, silent on any failure, never upgrades anything."""

import json
import sys

import pytest

from coursekit import doctor, store, updatecheck
from coursekit.cli import main
from coursekit.project import find_project


@pytest.fixture(autouse=True)
def on(monkeypatch):
    monkeypatch.delenv(updatecheck.OFF_ENV)
    monkeypatch.setattr(sys.stderr, "isatty", lambda: True, raising=False)


def test_versions_are_compared_by_their_numbers_and_a_pre_release_comes_first():
    assert updatecheck.newer("0.1.3", "0.1.2") and updatecheck.newer("0.2.0", "0.1.9") and updatecheck.newer("0.10.0", "0.9.0")
    assert updatecheck.newer("0.1.0", "0.1.0.dev0") and not updatecheck.newer("0.1.0.dev0", "0.1.0")
    assert not updatecheck.newer("0.1.2", "0.1.2") and not updatecheck.newer(None, "0.1.2")


def test_a_newer_version_is_announced_once_a_day(monkeypatch):
    asked = []
    monkeypatch.setattr(updatecheck, "latest", lambda: asked.append(1) or "99.0.0")
    first = updatecheck.notice("status")
    assert "99.0.0 is available" in first and "uv tool upgrade slxd-coursekit" in first
    assert updatecheck.notice("status") == first and len(asked) == 1  # remembered, not asked again
    data = json.loads((store.home() / "update-check.json").read_text(encoding="utf-8"))
    data["checked"] -= updatecheck.EVERY + 1
    (store.home() / "update-check.json").write_text(json.dumps(data), encoding="utf-8")
    updatecheck.notice("status")
    assert len(asked) == 2


def test_nothing_is_said_when_up_to_date_offline_off_or_without_a_terminal(monkeypatch):
    monkeypatch.setattr(updatecheck, "latest", lambda: "0.0.1")
    assert updatecheck.notice("status") is None
    monkeypatch.setattr(updatecheck, "latest", lambda: None)
    (store.home() / "update-check.json").unlink()
    assert updatecheck.notice("status") is None  # no network: silent
    monkeypatch.setattr(updatecheck, "latest", lambda: "99.0.0")
    (store.home() / "update-check.json").unlink()
    assert updatecheck.notice("help") is None
    monkeypatch.setattr(sys.stderr, "isatty", lambda: False, raising=False)
    assert updatecheck.notice("status") is None  # logs and scripts stay clean
    monkeypatch.setattr(sys.stderr, "isatty", lambda: True, raising=False)
    monkeypatch.setenv(updatecheck.OFF_ENV, "1")
    assert updatecheck.notice("status") is None


def test_the_notice_comes_before_the_command(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(updatecheck, "latest", lambda: "99.0.0")
    monkeypatch.delenv("COURSEKIT_PROJECT", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stderr, "isatty", lambda: True, raising=False)  # the stream capsys installed
    main(["status"])
    assert "99.0.0 is available" in capsys.readouterr().err


def test_a_network_failure_is_not_an_error(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr(updatecheck.urllib.request, "urlopen", boom)
    assert updatecheck.latest() is None


def test_doctor_always_asks_and_says_it(monkeypatch, tmp_path):
    monkeypatch.delenv("COURSEKIT_PROJECT", raising=False)
    assert main(["init", str(tmp_path / "demo"), "--yes", "--no-git"]) == 0
    monkeypatch.chdir(tmp_path / "demo")
    monkeypatch.setattr(updatecheck, "latest", lambda: "99.0.0")
    text = doctor.render(doctor.collect(find_project()))
    assert "latest published version: 99.0.0" in text and "uv tool upgrade slxd-coursekit" in text
