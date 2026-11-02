import json

import yaml

from coursekit import commands, verify
from coursekit.cli import main
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture


def unit_status(course_dir):
    return yaml.safe_load((course_dir / "course.yaml").read_text(encoding="utf-8"))["units"][0].get("status")


def test_the_families_of_the_parser_are_those_of_verify():
    assert commands.VERIFY_FAMILIES == verify.FAMILIES


def test_json_gives_each_finding_with_its_family(course, capsys):  # noqa: F811
    assert main(["verify", "PWD", "--json", "--no-update"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["code"] == "PWD" and data["ok"] is True and data["filtered"] is False
    unit = data["units"][0]
    assert unit["n"] == 1 and unit["summary"]["words"] > 0 and unit["errors"] == []
    families = {w["family"] for w in unit["warnings"]}
    assert families and families <= set(verify.FAMILIES)
    assert {"words", "activities"} <= families  # sections above their minimum; no closing reflection


def test_only_and_ignore_filter_the_families_and_leave_the_status_alone(course, capsys):  # noqa: F811
    before = unit_status(course)
    assert main(["verify", "PWD", "--only", "words", "--json"]) == 0
    only = json.loads(capsys.readouterr().out)
    assert only["filtered"] is True and {w["family"] for w in only["units"][0]["warnings"]} == {"words"}
    assert main(["verify", "PWD", "--ignore", "words,activities", "--json"]) == 0
    ignored = json.loads(capsys.readouterr().out)
    assert not {w["family"] for w in ignored["units"][0]["warnings"]} & {"words", "activities"}
    assert unit_status(course) == before  # a partial view never marks a unit as verified
    assert main(["verify", "PWD", "--only", "words"]) == 0
    out = capsys.readouterr().out
    assert "[words]" in out and "[activities]" not in out and "status of the units does not change" in out


def test_an_unknown_family_is_refused(course, capsys):  # noqa: F811
    assert main(["verify", "PWD", "--only", "spelling"]) == 1
    assert "unknown family: spelling" in capsys.readouterr().err


def test_an_error_names_its_family_and_fails(course, capsys):  # noqa: F811
    (course / "content" / "unit-01" / "assessment.md").unlink()
    assert main(["verify", "PWD", "--json", "--no-update"]) == 1
    errors = json.loads(capsys.readouterr().out)["units"][0]["errors"]
    assert {"family": "structure", "message": "assessment.md is missing"} in errors or any(
        e["family"] == "structure" and "assessment.md" in e["message"] for e in errors)
    assert main(["verify", "PWD", "--ignore", "structure", "--no-update"]) == 0


def test_status_doctor_and_media_check_as_json(course, capsys):  # noqa: F811
    assert main(["status", "--json"]) == 0
    overview = json.loads(capsys.readouterr().out)
    assert overview[0]["code"] == "PWD" and overview[0]["design_signed"]["by"].startswith("Ana")
    assert main(["status", "PWD", "--json"]) == 0
    detail = json.loads(capsys.readouterr().out)
    assert detail["units"][0]["n"] == 1 and detail["design"]["problem"] is None and detail["next_step"]
    assert main(["doctor", "--json"]) == 0
    sections = json.loads(capsys.readouterr().out)
    assert sections[0]["checks"] and {c["status"] for s in sections for c in s["checks"]} <= {"ok", "missing", "info"}
    assert main(["media", "check", "PWD", "--json"]) == 0  # no audio or video yet: nothing to check
    assert json.loads(capsys.readouterr().out) == {"ok": True, "fixed": [], "findings": []}
