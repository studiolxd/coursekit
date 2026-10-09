"""Fixes found auditing the documentation against the code."""

import urllib.error
import urllib.request

import pytest
import yaml

from coursekit import mediatools
from coursekit.assemble import Syntax, directive_brick
from coursekit.cli import main
from coursekit.lang import tokens
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture


def data(course_dir) -> dict:
    return yaml.safe_load((course_dir / "course.yaml").read_text(encoding="utf-8"))


def test_a_new_sync_keeps_how_a_unit_was_reviewed(course, capsys):  # noqa: F811
    assert main(["verify", "PWD"]) == 0
    assert main(["reviewed", "PWD", "1", "--by", "Eva Reviewer", "--note", "read with the trainer"]) == 0
    assert main(["sync", "PWD"]) == 0
    unit = data(course)["units"][0]
    assert unit["status"] == "reviewed" and unit["review"]["kind"] == "human" and unit["review"]["by"] == "Eva Reviewer"


def test_signing_a_design_again_keeps_the_progress_of_the_units(course, capsys):  # noqa: F811
    assert main(["verify", "PWD"]) == 0
    assert data(course)["status"] == "ai_review"
    assert main(["approve", "design", "PWD", "--yes", "--no-commit"]) == 0
    info = data(course)
    assert info["units"][0]["status"] == "verified" and info["status"] == "ai_review"  # it does not go back to design_approved


def test_sync_does_not_overwrite_a_written_assessment(course, capsys):  # noqa: F811
    content = course / "content" / "unit-01" / "content.md"
    assessment = course / "content" / "unit-01" / "assessment.md"
    before = assessment.read_text(encoding="utf-8")
    content.unlink()  # the content is regenerated, the written assessment stays
    assert main(["sync", "PWD"]) == 0
    assert assessment.read_text(encoding="utf-8") == before


def test_the_position_under_a_point_of_a_labelled_graphic_is_read():
    syntax = Syntax(tokens("en"))
    ctx = {"registry": {"labelled-graphic": {"brick": "LABELLED_GRAPHIC"}}, "syntax": syntax, "media_by_title": {}, "warnings": []}
    body = ["image: Anatomy", "", "#### Start", "position: 30,40", "The first part.", "", "#### End", "The last part."]
    brick = directive_brick("labelled-graphic", body, ctx)
    first, second = brick["items"] if "items" in brick else brick["data"]["items"]
    assert (first["x"], first["y"]) == (30.0, 40.0)
    assert second["y"] == 50  # the automatic position


def test_a_missing_program_or_a_failed_api_is_a_message_not_a_traceback(tmp_path, monkeypatch, capsys):
    def missing(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(mediatools.subprocess, "run", missing)
    with pytest.raises(mediatools.ToolError, match="ffmpeg is not installed"):
        mediatools.to_mp3(tmp_path / "a.wav", tmp_path / "a.mp3")

    def refused(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(mediatools.urllib.request, "urlopen", refused)
    with pytest.raises(mediatools.ToolError, match="api.elevenlabs.io answered 401 Unauthorized"):
        mediatools.fetch(urllib.request.Request("https://api.elevenlabs.io/v1/x"))


def test_signing_a_design_again_after_assembly_keeps_the_status(course, capsys):  # noqa: F811
    path = course / "course.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("status: design_approved", "status: assembly", 1), encoding="utf-8")
    assert data(course)["status"] == "assembly"
    assert main(["approve", "design", "PWD", "--yes", "--no-commit"]) == 0
    assert data(course)["status"] == "assembly"
