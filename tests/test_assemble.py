import json
from pathlib import Path

import pytest
import yaml

from coursekit.cli import main
from tests.test_course_flow import ASSESSMENT, CONTENT, FIXTURES, write_course_rules


@pytest.fixture
def course(make_project, make_course):
    root = make_project(signer=("Ana", "ana@example.com"))
    course_dir = make_course(root, approve=True, prepare=write_course_rules)
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
    assert evaluation["type"] == "evaluation"
    assert evaluation["quiz"] == {"passingGrade": 50, "maxAttempts": 2, "courseWeight": 1, "shuffleQuestions": True}


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


def test_the_structure_category_and_its_conditional_are_not_new_directives(course, tmp_path, capsys):
    """The catalog gained a category, `structure`, with CONDITIONAL: the assembly builds it from :::if, so it is not reported
    as a brick to turn into a directive, and a category coursekit does not know is read like any other."""
    from coursekit import config
    from coursekit.project import find_project

    registry = config.effective("directives", find_project()).value
    every = sorted({d["brick"] for d in registry["directives"].values()} | set(registry["not_directives"]))
    catalog = {"structuredContent": {"categories": [
        {"category": "collection", "types": [{"type": b, "whenToUse": "x"} for b in every if b != "CONDITIONAL"]},
        {"category": "structure", "types": [{"type": "CONDITIONAL", "whenToUse": "adaptive content"}]}]}}
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    capsys.readouterr()
    assert main(["directives", "check", str(path)]) == 0, capsys.readouterr().out
    assert "CONDITIONAL" not in capsys.readouterr().out


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


def test_the_language_of_a_code_block_for_creator_is_never_auto():
    from coursekit.assemble import code_language

    assert code_language("bash", ["ls"]) == "bash" and code_language("yaml", ["a: 1"]) == "yaml"
    assert code_language("powershell", ["Get-Date"]) == "powershell" and code_language("pwsh", ["x"]) == "powershell"
    assert code_language("text", ["/assemble PWD"]) == "shell" and code_language("console", ["x"]) == "shell"
    assert code_language("text", ["coursekit status PWD", "", "git status"]) == "shell"
    assert code_language("", ["$ pwd"]) == "shell" and code_language("terminal", ["x"]) == "shell"
    assert code_language("text", ["ok      .env", "coursekit 0.1.0"]) == "plaintext"  # an output, not only commands
    assert code_language("text", ["Estado: delivered"]) == "plaintext" and code_language("text", []) == "plaintext"
    assert code_language("diff", ["+a"]) == "diff" and code_language("patch", ["+a"]) == "diff"
    assert code_language("dockerfile", ["FROM x"]) == "dockerfile" and code_language("http", ["GET /"]) == "http"
    assert code_language("TS", ["let a = 1"]) == "typescript" and code_language("jsx", ["<A />"]) == "javascript"
    assert code_language("toml", ["a = 1"]) == "plaintext" and code_language("mermaid", ["graph TD"]) == "plaintext"
    assert code_language("toml", ["a = 1"], ["toml"]) == "toml"  # a language creator adds later (rules › assembly)


def test_a_terminal_session_is_shell_and_an_output_is_plain_text():
    from coursekit.assemble import code_language

    assert code_language("text", ["daniel@mac ~ % pwd", "/Users/daniel"]) == "shell"
    assert code_language("text", ["ana@portatil-ana ~ %"]) == "shell"
    assert code_language("text", [r"PS C:\Users\ana> coursekit", "coursekit : error"]) == "shell"
    assert code_language("text", ["$ pwd", "/home/ana"]) == "shell"
    assert code_language("text", ["Estado: delivered", "Montaje: backend creator"]) == "plaintext"


def test_the_plan_fits_the_text_to_the_single_line_fields_of_creator():
    from coursekit import assemble

    question = {"type": "SINGLE_CHOICE", "data": {
        "content": {"question": assemble.inline("Which command shows `git status`? See [docs](https://example.com)"),
                    "feedback_correct": assemble.inline("`git status` lists the changes")},
        "items": [{"content": assemble.inline("Run `git status` **now**"), "isCorrect": True},
                  {"content": assemble.inline("Run *nothing*"), "isCorrect": False}]}}
    adaptive = {"type": "CONDITIONAL", "data": {"branches": [{"condition": "x", "bricks": [
        {"type": "MATCH", "data": {"items": [{"left": assemble.inline("`ls`"), "right": assemble.inline("lists files")}]}}]}],
        "else": []}}
    warnings = assemble.creator_fields([question, adaptive], "u1-s1")
    data = question["data"]
    assert data["items"][0]["content"] == "<p>Run git status <strong>now</strong></p>"
    assert data["items"][1]["content"] == "<p>Run <em>nothing</em></p>"
    assert data["content"]["question"] == "<p>Which command shows <code>git status</code>? See docs</p>"
    assert "<code>git status</code>" in data["content"]["feedback_correct"]
    assert adaptive["data"]["branches"][0]["bricks"][0]["data"]["items"][0]["left"] == "<p>ls</p>"
    assert len(warnings) == 3 and all(w.startswith("u1-s1: ") for w in warnings)
    assert any("SINGLE_CHOICE › items[].content" in w and "Run git status now" in w for w in warnings)
    assert assemble.creator_fields([question], "u1-s1") == []


def choice_shuffle(course_dir) -> list[bool]:
    from coursekit import assemble
    from coursekit import course as coursemod
    from coursekit.project import find_project

    data = coursemod.load(find_project(course_dir), "PWD")
    plan, errors, _ = assemble.build_plan(data, data["units"][0])
    assert not errors
    return [b["data"]["properties"]["shuffleOptions"] for lesson in plan["lessons"] for b in lesson["bricks"]
            if b["type"] == "SINGLE_CHOICE"]


def test_the_options_are_shuffled_in_the_practice_and_the_tests_unless_the_course_or_the_question_says_no(course):
    assert choice_shuffle(course) == [True, True]  # the practice of section 2, the test
    data_path = course / "course.yaml"
    data = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    data["delivery"] = {"shuffle_options": {"assessment": False}}
    data_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    assert choice_shuffle(course) == [True, False]
    content = course / "content" / "unit-01" / "content.md"
    content.write_text(CONTENT.replace("objetivo: U1.2\n", "objetivo: U1.2\nbarajar: no\n", 1), encoding="utf-8")
    assert choice_shuffle(course) == [False, False]
    assessment = course / "content" / "unit-01" / "assessment.md"
    assessment.write_text(ASSESSMENT.replace("objetivo: U1.1\n", "objetivo: U1.1\nbarajar: sí\n", 1), encoding="utf-8")
    assert choice_shuffle(course) == [False, True]


def test_the_shuffle_key_takes_yes_or_no_and_only_goes_in_questions_with_options():
    from coursekit import assemble
    from coursekit import course as coursemod

    ctx = assemble.context({"language": "es", "units": []}, assets={})
    ctx["registry"] = {"single-choice": {"brick": "SINGLE_CHOICE", "role": "question"},
                       "true-false": {"brick": "TRUE_FALSE", "role": "question"}}
    options = ["pregunta: ¿Cuál?", "- [x] Larga", "- [ ] Corta"]
    assert assemble.directive_brick("single-choice", ["barajar: Si", *options], ctx)["data"]["properties"]["shuffleOptions"]
    with pytest.raises(assemble.PlanError, match="'barajar:' lleva 'sí' o 'no'|'barajar:' takes 'sí' or 'no'"):
        assemble.directive_brick("single-choice", ["barajar: quizá", *options], ctx)
    with pytest.raises(assemble.PlanError, match="single-choice"):
        assemble.directive_brick("true-false", ["barajar: no", "pregunta: ¿Sí?", "respuesta: verdadero"], ctx)
    assert coursemod.tokens({"language": "en"})["directive_keys"]["shuffle"] == "shuffle"


def test_the_questions_of_a_test_are_shuffled_unless_the_course_says_no(course, capsys):
    def quiz():
        assert main(["assemble", "plan", "PWD", "--unit", "1"]) == 0
        plan = json.loads((course / "assembly" / "unit-01.plan.json").read_text(encoding="utf-8"))
        return next(lesson["quiz"] for lesson in plan["lessons"] if lesson["type"] == "evaluation")

    assert quiz()["shuffleQuestions"] is True
    data_path = course / "course.yaml"
    data = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    data["delivery"] = {"shuffle_questions": False}
    data_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    assert quiz()["shuffleQuestions"] is False
