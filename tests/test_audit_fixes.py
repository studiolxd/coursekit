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


def test_the_quiz_takes_its_weight_pass_mark_and_attempts_from_the_design(course, capsys):  # noqa: F811
    import json

    matrix = course / "design" / "matrix.json"
    graph = json.loads(matrix.read_text(encoding="utf-8"))
    graph["actividadesEvaluacion"][0].update({"peso": 3, "notaAprobado": 70, "intentosMax": 0})
    matrix.write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")
    assert main(["approve", "design", "PWD", "--yes", "--no-commit"]) == 0
    assert main(["assemble", "plan", "PWD", "--unit", "1"]) == 0
    plan = json.loads((course / "assembly" / "unit-01.plan.json").read_text(encoding="utf-8"))
    quiz = next(lesson["quiz"] for lesson in plan["lessons"] if lesson["type"] == "evaluation")
    assert quiz == {"passingGrade": 70, "maxAttempts": 0, "courseWeight": 3}  # 0 attempts: unlimited, as in creator


def test_the_quiz_falls_back_to_the_course_grading_when_the_design_gives_nothing(course, capsys):  # noqa: F811
    import json

    assert main(["assemble", "plan", "PWD", "--unit", "1"]) == 0
    plan = json.loads((course / "assembly" / "unit-01.plan.json").read_text(encoding="utf-8"))
    quiz = next(lesson["quiz"] for lesson in plan["lessons"] if lesson["type"] == "evaluation")
    assert quiz == {"passingGrade": 50, "maxAttempts": 2, "courseWeight": 1}


def test_a_change_only_in_the_grading_of_a_test_is_a_diff(course, capsys):  # noqa: F811
    import json

    assert main(["assemble", "plan", "PWD", "--unit", "1"]) == 0
    assert main(["assemble", "link", "PWD", "--unit", "1", "--content-id", "c-1"]) == 0
    plan_path = course / "assembly" / "unit-01.plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    for i, lesson in enumerate(plan["lessons"]):
        ids = ",".join(f"b{i}-{j}" for j in range(len(lesson["bricks"])))
        args = ["--lesson", lesson["key"], "--lesson-id", f"l{i}", "--brick-ids", ids]
        assert main(["assemble", "applied", "PWD", "--unit", "1", *args]) == 0
    assert main(["assemble", "applied", "PWD", "--unit", "1", "--content"]) == 0
    capsys.readouterr()
    assert main(["assemble", "diff", "PWD", "--unit", "1"]) == 0
    assert {lesson["action"] for lesson in json.loads(capsys.readouterr().out)["lessons"]} == {"unchanged"}

    matrix = course / "design" / "matrix.json"
    graph = json.loads(matrix.read_text(encoding="utf-8"))
    graph["actividadesEvaluacion"][0]["notaAprobado"] = 80
    matrix.write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")
    assert main(["approve", "design", "PWD", "--yes", "--no-commit"]) == 0
    assert main(["assemble", "plan", "PWD", "--unit", "1"]) == 0
    capsys.readouterr()
    assert main(["assemble", "diff", "PWD", "--unit", "1"]) == 0
    lessons = {lesson["key"]: lesson for lesson in json.loads(capsys.readouterr().out)["lessons"]}
    assert lessons["U1-E1.1"]["action"] == "update"
    assert lessons["U1-E1.1"]["ops"] == [{"op": "update_quiz", "quiz": {"passingGrade": 80, "maxAttempts": 2, "courseWeight": 1}}]
    assert lessons["U1-S1"]["action"] == "unchanged"
