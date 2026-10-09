"""A unit can be reviewed by a person instead of the AI, and a project can skip the AI review altogether."""

import yaml

from coursekit.cli import main
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture


def data(course_dir) -> dict:
    return yaml.safe_load((course_dir / "course.yaml").read_text(encoding="utf-8"))


def rule(course_dir, text: str) -> None:
    folder = course_dir.parent.parent / "config"
    folder.mkdir(exist_ok=True)
    (folder / "rules.yaml").write_text(text, encoding="utf-8")


def test_by_default_the_ai_review_is_needed(course, capsys):  # noqa: F811
    assert main(["verify", "PWD"]) == 0
    assert data(course)["units"][0]["status"] == "verified"
    assert main(["reviewed", "PWD", "1"]) == 1
    assert "missing reviews/unit-01-ai-review.md" in capsys.readouterr().err
    assert main(["approve", "content", "PWD", "--unit", "1", "--yes", "--no-commit"]) == 1
    assert "needs its review first" in capsys.readouterr().err


def test_a_person_can_record_their_own_review(course, capsys):  # noqa: F811
    assert main(["verify", "PWD"]) == 0
    capsys.readouterr()
    assert main(["reviewed", "PWD", "1", "--by", "Eva Reviewer", "--note", "read with the trainer"]) == 0
    assert "unit 1: reviewed by Eva Reviewer" in capsys.readouterr().out
    info = data(course)
    unit = info["units"][0]
    assert unit["status"] == "reviewed"
    review = unit["review"]
    assert (review["kind"], review["by"], review["note"]) == ("human", "Eva Reviewer", "read with the trainer")
    assert unit["reviewed_parts"]  # fingerprints: what changes afterwards is noticed, as with the AI review
    assert info["history"][-1]["by"] == "Eva Reviewer" and "reviewed by Eva Reviewer" in info["history"][-1]["note"]
    assert not (course / "reviews" / "unit-01-ai-review.md").exists()

    assert main(["approve", "content", "PWD", "--unit", "1", "--yes", "--no-commit"]) == 0  # no AI report is asked for
    assert data(course)["units"][0]["status"] == "approved"
    assert data(course)["units"][0]["review"]["kind"] == "human"


def test_content_edited_after_a_person_review_goes_back(course, capsys):  # noqa: F811
    assert main(["verify", "PWD"]) == 0
    assert main(["reviewed", "PWD", "1", "--by", "Eva"]) == 0
    content = course / "content" / "unit-01" / "content.md"
    content.write_text(content.read_text(encoding="utf-8") + "\nUna frase más.\n", encoding="utf-8")
    capsys.readouterr()
    assert main(["verify", "PWD"]) == 0
    unit = data(course)["units"][0]
    assert unit["status"] == "verified" and "review" not in unit  # back to verified: it needs a new review


def test_the_report_and_the_note_belong_to_the_review_of_a_person(course, tmp_path, capsys):  # noqa: F811
    assert main(["verify", "PWD"]) == 0
    capsys.readouterr()
    assert main(["reviewed", "PWD", "1", "--note", "x"]) == 2
    assert "--note and --report need --by" in capsys.readouterr().err
    assert main(["reviewed", "PWD", "1", "--by", "Eva", "--report", "reviews/nothing.md"]) == 1
    assert "does not exist" in capsys.readouterr().err
    outside = tmp_path / "notes.md"
    outside.write_text("notes\n", encoding="utf-8")
    assert main(["reviewed", "PWD", "1", "--by", "Eva", "--report", str(outside)]) == 1
    assert "must be inside the folder of course PWD" in capsys.readouterr().err
    (course / "reviews").mkdir(exist_ok=True)
    (course / "reviews" / "eva.md").write_text("notes\n", encoding="utf-8")
    assert main(["reviewed", "PWD", "1", "--by", "Eva", "--report", "reviews/eva.md"]) == 0
    assert data(course)["units"][0]["review"]["report"] == "reviews/eva.md"


def test_skipping_the_ai_review_makes_a_verified_unit_reviewed(course, capsys):  # noqa: F811
    rule(course, "review:\n  ai: skip\n")
    assert main(["verify", "PWD"]) == 0
    out = capsys.readouterr().out
    assert "AI review skipped" in out
    info = data(course)
    assert info["units"][0]["status"] == "reviewed" and info["units"][0]["review"]["kind"] == "skipped"
    assert info["status"] == "editorial_review"  # no ai_review phase
    assert main(["approve", "content", "PWD", "--unit", "1", "--yes", "--no-commit"]) == 0
    assert data(course)["units"][0]["status"] == "approved"
    assert data(course)["status"] == "media"


def test_a_verified_unit_can_be_signed_when_the_project_skips_the_ai_review(course, capsys):  # noqa: F811
    assert main(["verify", "PWD", "--no-update"]) == 0  # still 'writing' or 'pending'
    assert main(["verify", "PWD"]) == 0  # verified, with the AI review required
    rule(course, "review:\n  ai: skip\n")
    assert main(["approve", "content", "PWD", "--unit", "1", "--yes", "--no-commit"]) == 0


def test_a_review_rule_with_a_wrong_value_is_reported(course, capsys):  # noqa: F811
    rule(course, "review:\n  ai: maybe\n")
    capsys.readouterr()
    assert main(["verify", "PWD"]) == 1
    assert "rules › review › ai is 'maybe': use 'required' or 'skip'" in capsys.readouterr().err


def test_agents_are_denied_the_review_of_a_person():
    from coursekit import agents

    assert "Bash(coursekit reviewed*--by*)" in agents.DENY_CLAUDE
    assert agents.DENY_OPENCODE["*coursekit reviewed*--by*"] == "deny"
