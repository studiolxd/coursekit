"""The fix report of the handoff (reviews/unit-NN-fix.md): what to fix and nothing else, and the stop when a round ends
with the findings of the round before."""

from coursekit import fixes
from coursekit.cli import main
from tests.test_handoff import Agents, data, project  # noqa: F401 - fixture

REVIEW = """# AI review
> **Result:** x
<!-- result: {result} -->

## Findings
| # | Section | Criterion | Severity | Finding | Action (applied / proposed) |
|---|---|---|---|---|---|
| 1 | Apartado 2 | Alignment | blocking | The example does not apply objective U1.1 | proposed: rewrite it with a work account |
| 2 | Apartado 2 | Accuracy | `blocking` | A wrong figure | applied: fixed to 14 characters |
| 3 | Apartado 3 | Style | minor | A typo | applied |
"""


class Reviewed(Agents):
    """The reviewer writes a findings table; the texts the agents get are kept."""

    def __init__(self, root, monkeypatch):
        super().__init__(root, monkeypatch)
        self.texts = []

    def execute(self, where, agent, text, headless, log_name):
        self.texts.append(text)
        return super().execute(where, agent, text, headless, log_name)

    def review_unit(self, arguments):
        super().review_unit(arguments)
        report = self.course / "reviews" / "unit-01-ai-review.md"
        result = "not_ready" if "not_ready" in report.read_text(encoding="utf-8") else "ready"
        report.write_text(REVIEW.format(result=result), encoding="utf-8")


def test_only_open_blocking_findings_are_read(tmp_path):
    course = {"_dir": tmp_path, "code": "PWD"}
    (tmp_path / "reviews").mkdir()
    (tmp_path / "reviews" / "unit-01-ai-review.md").write_text(REVIEW.format(result="not_ready"), encoding="utf-8")
    assert fixes.review_findings(course, 1) == [
        fixes.Finding("review", "Apartado 2 · Alignment: The example does not apply objective U1.1")]


def test_the_fingerprint_ignores_order_and_line_numbers(tmp_path):
    a = [fixes.Finding("verify", "content.md:12: unknown directive"), fixes.Finding("review", "x")]
    b = [fixes.Finding("review", "x"), fixes.Finding("verify", "content.md:15: unknown directive")]
    assert fixes.fingerprint(a) == fixes.fingerprint(b) != fixes.fingerprint(a[:1])
    course = {"_dir": tmp_path, "code": "PWD"}
    path = fixes.write(course, 1, a, 2)
    text = path.read_text(encoding="utf-8")
    assert "# Fix only this — PWD · unit 1 (round 2)" in text and "and nothing else" in text
    assert "## Errors of coursekit verify\n\n1. content.md:12: unknown directive" in text
    assert "## Blocking findings of the review not applied\n\n1. x" in text
    assert fixes.previous_fingerprint(course, 1) == fixes.fingerprint(a)


def test_the_writer_gets_only_what_failed_and_the_report_goes_when_it_passes(project, monkeypatch, capsys):  # noqa: F811
    fake = Reviewed(project, monkeypatch)
    fake.reviews = ["not_ready"]
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    out = capsys.readouterr().out
    assert "unit 1: 1 item(s) to fix in courses/PWD/reviews/unit-01-fix.md" in out
    fix_text = next(text for text in fake.texts if "fix ONLY what `courses/PWD/reviews/unit-01-fix.md` lists" in text)
    assert fix_text.startswith("/write-unit")
    assert not (fake.course / "reviews" / "unit-01-fix.md").exists()  # the unit passed: nothing left to fix
    assert data(project)["status"] == "delivered"


def test_the_same_findings_twice_stop_the_handoff(project, monkeypatch, capsys):  # noqa: F811
    fake = Reviewed(project, monkeypatch)
    fake.reviews = ["not_ready", "not_ready", "not_ready"]
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD", "--rounds", "3"]) == 1
    err = capsys.readouterr().err
    assert "unit 1 still has the same 1 problem(s) after fixing it" in err and "reviews/unit-01-fix.md" in err
    assert fake.calls.count("write-unit") == 2  # the first write and one fix: not a third round on the same thing
    report = (fake.course / "reviews" / "unit-01-fix.md").read_text(encoding="utf-8")
    assert "The example does not apply objective U1.1" in report


def test_an_html_package_that_fails_its_check_stops_before_delivering(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import pytest

    from coursekit import handoff
    from coursekit.htmlkit import playcheck

    course = {"_dir": tmp_path / "courses" / "PWD", "code": "PWD", "units": [{"n": 1}, {"n": 2}]}
    logged = []
    ctx = handoff.Context(SimpleNamespace(root=tmp_path), "PWD", 2, logged.append, lambda: None)
    monkeypatch.setattr(playcheck, "check", lambda c, unit, browser=None, say=print: playcheck.CheckResult(
        unit["n"], errors=["U2-S1: accessibility, color-contrast"] if unit["n"] == 2 else [], warnings=["no browser"]))
    with pytest.raises(handoff.HandoffError) as stop:
        handoff._check_packages(ctx, course)
    assert "found 1 error(s), listed in courses/PWD/reviews/package-check.md" in str(stop.value)
    report = (course["_dir"] / "reviews" / "package-check.md").read_text(encoding="utf-8")
    assert "## Unit 2\n\n1. U2-S1: accessibility, color-contrast" in report and "## Unit 1" not in report
    assert any("no browser" in line for line in logged)
    monkeypatch.setattr(playcheck, "check", lambda c, unit, browser=None, say=print: playcheck.CheckResult(unit["n"]))
    handoff._check_packages(ctx, course)
    assert not (course["_dir"] / "reviews" / "package-check.md").exists()
