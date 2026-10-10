import json
import shutil
from pathlib import Path

import pytest
import yaml

from coursekit.cli import main
from tests.test_course_flow import ASSESSMENT, CONTENT, FIXTURES, write_course_rules


@pytest.fixture
def course(tmp_path, monkeypatch):
    monkeypatch.delenv("COURSEKIT_PROJECT", raising=False)
    root = tmp_path / "demo"
    assert main(["init", str(root), "--yes", "--no-git"]) == 0
    monkeypatch.chdir(root)
    (root / ".env").write_text("COURSEKIT_USER_NAME=Ana\nCOURSEKIT_USER_EMAIL=ana@example.com\n", encoding="utf-8")
    assert main(["new", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    course_dir = root / "courses" / "PWD"
    write_course_rules(course_dir)
    shutil.copy(FIXTURES / "matrix.json", course_dir / "design" / "matrix.json")
    assert main(["approve", "design", "PWD", "--yes", "--no-commit"]) == 0
    (course_dir / "content" / "unit-01" / "content.md").write_text(CONTENT, encoding="utf-8")
    (course_dir / "content" / "unit-01" / "assessment.md").write_text(ASSESSMENT, encoding="utf-8")
    return course_dir


def diff(capsys) -> dict:
    capsys.readouterr()
    assert main(["assemble", "diff", "PWD", "--unit", "1"]) == 0
    return json.loads(capsys.readouterr().out)


def test_plan_bricks(course, capsys):
    assert main(["assemble", "plan", "PWD", "--unit", "1"]) == 0
    assert "4 lessons" in capsys.readouterr().out
    plan = json.loads((course / "assembly" / "unit-01.plan.json").read_text(encoding="utf-8"))
    assert plan["content_title"] == "Contraseñas seguras"  # single unit: the course title
    keys = [lesson["key"] for lesson in plan["lessons"]]
    assert keys == ["U1-S1", "U1-S2", "U1-S3", "U1-E1.1"]
    s2 = [b["type"] for b in plan["lessons"][1]["bricks"]]
    assert "ACCORDION" in s2 and "SINGLE_CHOICE" in s2
    note = next(b for b in plan["lessons"][1]["bricks"] if b["type"] == "NOTE")
    assert "Recurso multimedia — Infografía: Anatomía de una contraseña" in note["data"]["content"]["title"]
    assert "<strong>Descripción:</strong>" in note["data"]["content"]["content"]
    evaluation = plan["lessons"][3]
    assert evaluation["type"] == "evaluation" and evaluation["quiz"] == {"passingGrade": 50, "maxAttempts": 2, "courseWeight": 1}


def test_apply_cycle(course, capsys):
    assert main(["assemble", "plan", "PWD", "--unit", "1"]) == 0
    assert main(["assemble", "link", "PWD", "--unit", "1", "--content-id", "c-1"]) == 0
    assert main(["assemble", "plan", "PWD", "--unit", "1"]) == 0
    d = diff(capsys)
    assert d["content_id"] == "c-1"
    assert d["content"]["action"] == "rename"
    assert {lesson["action"] for lesson in d["lessons"]} == {"create"}
    # the person approved the unit: course in media, ready to assemble
    data_path = course / "course.yaml"
    data = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    data["status"] = "media"
    data["units"][0]["status"] = "approved"
    data_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    plan = json.loads((course / "assembly" / "unit-01.plan.json").read_text(encoding="utf-8"))
    for i, lesson in enumerate(plan["lessons"]):
        ids = ",".join(f"b{i}-{j}" for j in range(len(lesson["bricks"])))
        args = ["--lesson", lesson["key"], "--lesson-id", f"l{i}", "--brick-ids", ids]
        assert main(["assemble", "applied", "PWD", "--unit", "1", *args]) == 0
    capsys.readouterr()
    assert main(["assemble", "applied", "PWD", "--unit", "1", "--content"]) == 0
    assert "course: media -> assembly" in capsys.readouterr().out
    d = diff(capsys)
    assert d["content"]["action"] == "unchanged"
    assert {lesson["action"] for lesson in d["lessons"]} == {"unchanged"}
    # an edit becomes a minimal update
    content = course / "content" / "unit-01" / "content.md"
    content.write_text(content.read_text(encoding="utf-8").replace("Más larga es mejor.", "Cuanto más larga, mejor."), encoding="utf-8")
    assert main(["assemble", "plan", "PWD", "--unit", "1"]) == 0
    d = diff(capsys)
    s2 = next(lesson for lesson in d["lessons"] if lesson["key"] == "U1-S2")
    assert s2["action"] == "update"
    assert [op["op"] for op in s2["ops"]] == ["update"]
    assert s2["ops"][0]["type"] == "ACCORDION"


def test_applied_needs_matching_brick_count(course, capsys):
    assert main(["assemble", "plan", "PWD", "--unit", "1"]) == 0
    capsys.readouterr()
    assert main(["assemble", "applied", "PWD", "--unit", "1", "--lesson", "U1-S1", "--lesson-id", "l", "--brick-ids", "x,y"]) == 1
    assert "brick ids but the plan has" in capsys.readouterr().err


def test_verify_reports_assembly_errors(course, capsys):
    content = course / "content" / "unit-01" / "content.md"
    bad = content.read_text(encoding="utf-8").replace("- [x] tres-palabras-largas-juntas", "- [ ] tres-palabras-largas-juntas")
    content.write_text(bad, encoding="utf-8")
    capsys.readouterr()
    assert main(["verify", "PWD", "--no-update"]) == 1
    assert "assembly: U1-S2: :::single-choice needs exactly one correct option" in capsys.readouterr().out


def test_directives_check(course, tmp_path, capsys):
    catalog = {"categories": [{"category": "collection", "types": [
        {"type": "ACCORDION", "whenToUse": "x"}, {"type": "BRAND_NEW", "whenToUse": "something new"}]}]}
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    capsys.readouterr()
    assert main(["directives", "check", str(path)]) == 1
    out = capsys.readouterr().out
    assert "NEW     BRAND_NEW [collection] something new" in out
    assert "REMOVED TABS (in directive 'tabs')" in out


def test_english_course_plan(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("COURSEKIT_PROJECT", raising=False)
    root = tmp_path / "en"
    assert main(["init", str(root), "--yes", "--no-git", "--language", "en"]) == 0
    monkeypatch.chdir(root)
    (root / ".env").write_text("COURSEKIT_USER_NAME=Ann\nCOURSEKIT_USER_EMAIL=ann@example.com\n", encoding="utf-8")
    assert main(["new", "Strong passwords", "1", "--code", "EN1"]) == 0
    course_dir = root / "courses" / "EN1"
    matrix = json.loads((FIXTURES / "matrix.json").read_text(encoding="utf-8"))
    for node in matrix["nodos"]:
        names = {"Introducción y objetivos": "Introduction and objectives", "Resumen": "Summary"}
        node["titulo"] = names.get(node["titulo"], node["titulo"])
    (course_dir / "design" / "matrix.json").write_text(json.dumps(matrix), encoding="utf-8")
    assert main(["approve", "design", "EN1", "--yes", "--no-commit"]) == 0
    skeleton = (course_dir / "content" / "unit-01" / "content.md").read_text(encoding="utf-8")
    assert "## Section 1 — Introduction and objectives *(min. 1,000 words)*" in skeleton
    text = skeleton + "\n> **[MEDIA ASSET — Infographic]**\n> **Title:** A chart\n> **Description:** d\n"
    (course_dir / "content" / "unit-01" / "content.md").write_text(text, encoding="utf-8")
    assert main(["assemble", "plan", "EN1", "--unit", "1"]) == 0
    plan = json.loads((course_dir / "assembly" / "unit-01.plan.json").read_text(encoding="utf-8"))
    note = next(b for lesson in plan["lessons"] for b in lesson["bricks"] if b["type"] == "NOTE")
    assert note["data"]["content"]["title"] == "<p>Media asset — Infographic: A chart</p>"
    assert Path(course_dir / "assembly").is_dir()


def test_panel_directive_without_panels_is_an_error(course, capsys):
    content = course / "content" / "unit-01" / "content.md"
    content.write_text(content.read_text(encoding="utf-8").replace("#### Longitud", "## Longitud"), encoding="utf-8")
    capsys.readouterr()
    assert main(["verify", "PWD", "--no-update"]) == 1
    assert ":::accordion has no panels" in capsys.readouterr().out


def test_the_language_of_a_code_block_for_creator():
    from coursekit.assemble import code_language

    assert code_language("bash", ["ls"]) == "bash" and code_language("yaml", ["a: 1"]) == "yaml"
    assert code_language("powershell", ["Get-Date"]) == "bash" and code_language("pwsh", ["x"]) == "bash"
    assert code_language("text", ["/assemble PWD"]) == "bash"
    assert code_language("text", ["coursekit status PWD", "", "git status"]) == "bash"
    assert code_language("", ["$ pwd"]) == "bash"
    assert code_language("text", ["ok      .env", "coursekit 0.1.0"]) == "auto"  # an output, not only commands
    assert code_language("text", ["Estado: delivered"]) == "auto"
    assert code_language("text", []) == "auto"


def test_the_languages_creator_adds_are_used_once_they_are_listed():
    from coursekit.assemble import code_language

    new = ["plaintext", "shell", "powershell", "diff", "dockerfile", "http"]
    assert code_language("text", ["Estado: delivered"], new) == "plaintext" and code_language("", ["ok  .env"], new) == "plaintext"
    assert code_language("text", ["/assemble PWD"], new) == "shell" and code_language("console", ["x"], new) == "shell"
    assert code_language("terminal", ["x"], new) == "shell" and code_language("shell", ["x"], new) == "shell"
    assert code_language("powershell", ["x"], new) == "powershell" and code_language("pwsh", ["x"], new) == "powershell"
    assert code_language("diff", ["+a"], new) == "diff" and code_language("patch", ["+a"], new) == "diff"
    assert code_language("dockerfile", ["FROM x"], new) == "dockerfile" and code_language("http", ["GET /"], new) == "http"
    assert code_language("bash", ["ls"], new) == "bash"
    # not listed yet: creator would reject them
    assert code_language("diff", ["+a"]) == "auto" and code_language("http", ["GET /"]) == "auto"
    assert code_language("console", ["x"]) == "bash" and code_language("text", ["Estado: x"]) == "auto"


def test_a_terminal_session_is_shell_and_an_output_is_plain_text():
    from coursekit.assemble import code_language

    new = ["plaintext", "shell", "powershell", "diff", "dockerfile", "http"]
    assert code_language("text", ["daniel@mac ~ % pwd", "/Users/daniel"], new) == "shell"
    assert code_language("text", ["ana@portatil-ana ~ %"], new) == "shell"
    assert code_language("text", [r"PS C:\Users\ana> coursekit", "coursekit : error"], new) == "shell"
    assert code_language("text", ["$ pwd", "/home/ana"], new) == "shell"
    assert code_language("text", ["daniel@mac ~ % pwd"]) == "bash"  # creator without `shell`
    assert code_language("text", ["Estado: delivered", "Montaje: backend creator"], new) == "plaintext"
