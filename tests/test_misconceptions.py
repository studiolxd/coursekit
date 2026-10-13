"""The common errors of a course (design/misconceptions.yaml): signed with the design, pointed at by the distractors (‹id›)
and the decisions of the simulations (`error: id`), checked by verify and never shown to the learner."""

import shutil

import pytest

from coursekit import course as coursemod
from coursekit import misconceptions as misconmod
from coursekit import simulation as simmod
from coursekit.cli import main
from coursekit.project import find_project
from tests.test_course_flow import ASSESSMENT, CONTENT, FIXTURES, project, write_course_rules  # noqa: F401 - fixture

ERRORS = """U1.1:
  short: Pensar que ocho caracteres bastan si llevan símbolos
  year: Cambiar solo el año de la contraseña de siempre
U1.2:
  name: Usar el nombre de la mascota porque nadie lo sabe
"""

TAGGED = CONTENT.replace("- [ ] 1234\n", "- [ ] 1234 ‹name›\n")
TAGGED_ASSESSMENT = ASSESSMENT.replace("- [ ] 4\n", "- [ ] 4 ‹short›\n- [ ] La de siempre con 2026 ‹year›\n")


@pytest.fixture
def course_dir(project):  # noqa: F811
    (project / ".env").write_text("COURSEKIT_USER_NAME=Ana\nCOURSEKIT_USER_EMAIL=ana@example.com\n", encoding="utf-8")
    assert main(["new", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    folder = project / "courses" / "PWD"
    write_course_rules(folder)
    path = folder / "course.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("misconceptions: {per_objective: 0}", "misconceptions: {per_objective: 1}"),
                    encoding="utf-8")
    shutil.copy(FIXTURES / "matrix.json", folder / "design" / "matrix.json")
    return folder


def test_tags_are_read_and_removed():
    assert misconmod.strip_tag("La de siempre ‹year›") == ("La de siempre", "year")
    assert misconmod.strip_tag("Un ‹entrecomillado› en medio") == ("Un ‹entrecomillado› en medio", None)
    assert misconmod.strip_tag("Sin marca") == ("Sin marca", None)


def test_the_design_needs_its_common_errors_and_signs_them(course_dir, capsys):
    assert main(["approve", "design", "PWD", "--yes", "--no-commit"]) == 1
    assert "design/misconceptions.yaml is missing" in capsys.readouterr().err
    errors = course_dir / "design" / "misconceptions.yaml"
    errors.write_text("U1.1:\n  short: Ocho caracteres bastan\n  Bad-Id: x\nU9.9:\n  other: y\n", encoding="utf-8")
    assert main(["approve", "design", "PWD", "--yes", "--no-commit"]) == 1
    err = capsys.readouterr().err
    assert "invalid error id 'Bad-Id'" in err and "objective U9.9 is not in the design" in err
    assert "U1.2 has 0 common error(s) and the design asks for at least 1" in err
    errors.write_text(ERRORS, encoding="utf-8")
    assert main(["approve", "design", "PWD", "--yes", "--no-commit"]) == 0
    assert "common errors: design/misconceptions.yaml, 3 (signed with the design)" in capsys.readouterr().out
    course = coursemod.load(find_project(), "PWD")
    assert coursemod.approval_problem(course) is None
    errors.write_text(ERRORS + "  more: otro\n", encoding="utf-8")
    assert "misconceptions.yaml changed after the approval" in coursemod.approval_problem(coursemod.load(find_project(), "PWD"))


def test_verify_checks_that_every_error_is_shown_and_known(course_dir, capsys):
    (course_dir / "design" / "misconceptions.yaml").write_text(ERRORS, encoding="utf-8")
    assert main(["approve", "design", "PWD", "--yes", "--no-commit"]) == 0
    unit = course_dir / "content" / "unit-01"
    (unit / "content.md").write_text(CONTENT, encoding="utf-8")
    (unit / "assessment.md").write_text(ASSESSMENT, encoding="utf-8")
    capsys.readouterr()
    assert main(["verify", "PWD", "--no-update"]) == 1
    out = capsys.readouterr().out
    for eid in ("short", "year", "name"):
        assert f"the common error ‹{eid}›" in out
    assert "1 distractor(s) without the common error they represent" in out

    (unit / "content.md").write_text(TAGGED, encoding="utf-8")
    (unit / "assessment.md").write_text(TAGGED_ASSESSMENT, encoding="utf-8")
    capsys.readouterr()
    assert main(["verify", "PWD", "--no-update"]) == 0, capsys.readouterr().out

    (unit / "assessment.md").write_text(TAGGED_ASSESSMENT.replace("- [x] 14", "- [x] 14 ‹short›").replace("‹year›", "‹typo›"),
                                        encoding="utf-8")
    capsys.readouterr()
    assert main(["verify", "PWD", "--no-update"]) == 1
    out = capsys.readouterr().out
    assert "the right option carries the error ‹short›" in out and "error ‹typo› is not in design/misconceptions.yaml" in out


def test_without_the_file_verify_only_warns(course_dir, capsys):
    path = course_dir / "course.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("misconceptions: {per_objective: 1}", "misconceptions: {per_objective: 0}"),
                    encoding="utf-8")
    assert main(["approve", "design", "PWD", "--yes", "--no-commit"]) == 0
    path.write_text(path.read_text(encoding="utf-8").replace("misconceptions: {per_objective: 0}", "misconceptions: {per_objective: 2}"),
                    encoding="utf-8")
    unit = course_dir / "content" / "unit-01"
    (unit / "content.md").write_text(CONTENT, encoding="utf-8")
    (unit / "assessment.md").write_text(ASSESSMENT, encoding="utf-8")
    capsys.readouterr()
    assert main(["verify", "PWD", "--no-update"]) == 0
    assert "the design lists no common errors" in capsys.readouterr().out


def test_the_learner_never_sees_the_tags(course_dir):
    from coursekit import assemble

    (course_dir / "design" / "misconceptions.yaml").write_text(ERRORS, encoding="utf-8")
    assert main(["approve", "design", "PWD", "--yes", "--no-commit"]) == 0
    unit_dir = course_dir / "content" / "unit-01"
    (unit_dir / "content.md").write_text(TAGGED, encoding="utf-8")
    (unit_dir / "assessment.md").write_text(TAGGED_ASSESSMENT, encoding="utf-8")
    course = coursemod.load(find_project(), "PWD")
    plan, errors, _ = assemble.build_plan(course, course["units"][0])
    assert not errors
    text = repr(plan)
    assert "‹" not in text and "La de siempre con 2026" in text and "1234" in text


def test_a_decision_says_which_error_it_represents():
    body = ["id: x", "title: T", "state: {a: 0}", "scenes:", "  s:", "    text: S", "    choices:",
            "      - {text: Bien, goto: e, score: 1}", "      - {text: Mal, goto: e, score: -1, error: reuse}",
            "      - {text: Raro, goto: e, error: Not-An-Id}", "  e: {text: E, ending: good, debriefing: D}"]
    sim = simmod.parse("scenario", body, "x")
    assert any("'error' must be the id of a common error" in e for e in sim.errors)
    sim = simmod.parse("scenario", body[:-2] + [body[-1]], "x")
    assert not sim.errors
    uses = misconmod.Uses()
    misconmod.simulation_uses(sim, uses)
    assert uses.used == {"reuse": ["x.s"]} and uses.untagged == []
    from coursekit import paths

    assert "‹reuse›" in paths._changes(sim.data["scenes"]["s"]["choices"][1])
