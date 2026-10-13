"""Adaptive blocks as creator takes them: several branches (:::elif), texts in the conditions, the result of a simulation
(grade, score, maxScore, ending, kind) as variables, reserved names, and creator's limits."""

import json
import shutil
import subprocess
from importlib import resources
from pathlib import Path

import pytest

from coursekit import simulation as simmod
from coursekit import verify as verifymod
from coursekit.htmlkit import playcheck, render
from tests.test_decision_based import SCENARIO

BLOCK = ["intro", ":::if call.risk >= 3", "rama uno", ":::elif call.kind == \"good\"", "rama dos", ":::else", "neutra", ":::"]


def test_elif_branches_are_read_in_order():
    blocks, problems = simmod.scan_conditionals(BLOCK)
    assert problems == [] and [c for _, c in blocks[0].branches] == ["call.risk >= 3", 'call.kind == "good"']
    assert simmod.adaptive_lines(BLOCK) == {2, 3, 4, 5, 6, 8}  # the branches with a condition and the fences
    _, problems = simmod.scan_conditionals([":::if a.x", "x", ":::else", "y", ":::elif a.y", "z", ":::"])
    assert (5, "elif_after_else") in problems
    _, problems = simmod.scan_conditionals([":::elif a.y", "z"])
    assert (1, "elif_without_if") in problems


def test_the_plan_and_the_page_carry_every_branch():
    from coursekit import assemble

    ctx = {"errors": [], "warnings": []}
    branches, other, end = assemble.conditional_parts(BLOCK, 1)
    assert [(c, part) for c, part in branches] == [("call.risk >= 3", ["rama uno"]), ('call.kind == "good"', ["rama dos"])]
    assert other == ["neutra"] and end == 7
    def text(words):
        return {"type": "TEXT", "meta": {}, "data": {"content": {"content": f"<p>{words}</p>"}}}

    brick = {"type": "CONDITIONAL", "meta": {}, "data": {
        "branches": [{"condition": "a.x > 1", "bricks": [text("uno")]}, {"condition": 'a.kind == "good"', "bricks": [text("dos")]}],
        "else": [text("neutra")]}}
    assert len(ctx["errors"]) == 0 and len(assemble.branch_bricks(brick)) == 3
    assert assemble.conditions(brick) == ["a.x > 1", 'a.kind == "good"']
    html = render.conditional(brick, render.Ctx({}, "U1-S1"))
    assert html.count('class="ck-if"') == 2 and 'data-condition="a.kind == &quot;good&quot;"' in html and '<div class="ck-else">' in html


def test_texts_are_compared_only_for_equality_in_python_and_in_the_player(tmp_path):
    env = {"call.kind": "good", "call.grade": 80}
    assert simmod.test('call.kind == "good" && call.grade >= 50', env) and simmod.test('call.kind != "bad"', env)
    for bad in ('call.kind < "good"', '"good"', '"a" + 1', '-"x"'):
        with pytest.raises(simmod.ExpressionError):
            simmod.parse_expression(bad)
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    source = Path(str(resources.files("coursekit.templates.html"))) / "player" / "expr.js"
    shutil.copy(source, tmp_path / "expr.mjs")
    cases = [['call.kind == "good" && call.grade >= 50', env], ['call.kind != "good"', env], ['call.ending == "fin_malo"', {}]]
    (tmp_path / "run.mjs").write_text(
        "import { test, parse } from './expr.mjs';\n"
        f"const cases = {json.dumps(cases)};\n"
        "const fails = (c) => { try { parse(c); return false; } catch (e) { return true; } };\n"
        "const bad = ['call.kind < \"good\"', '\"good\"', '\"a\" + 1'].map(fails);\n"
        "console.log(JSON.stringify([cases.map(([c, env]) => test(c, env)), bad]));\n",
        encoding="utf-8")
    out = json.loads(subprocess.run([node, "run.mjs"], cwd=tmp_path, capture_output=True, text=True, check=True).stdout)
    assert out == [[simmod.test(c, e) for c, e in cases], [True, True, True]]


def test_the_result_fields_are_reserved_and_readable():
    reserved = SCENARIO.splitlines()[1:-1]
    reserved = [line.replace("state: {risk: 0, trust: 2, called: false}", "state: {risk: 0, trust: 2, called: false, grade: 0}")
                for line in reserved]
    assert any("variable 'grade' has a reserved name" in e for e in simmod.parse("scenario", reserved, "x").errors)
    sim = simmod.parse("scenario", SCENARIO.splitlines()[1:-1], "x")
    runs = {"call": {"a": "safe", "e": {"risk": 0}, "s": 2, "d": 1}}
    env = playcheck.adaptive_env(runs, {"call": sim})
    assert env["call.kind"] == "good" and env["call.grade"] == 100 and env["call.ending"] == "safe" and env["call.maxScore"] == 2
    assert playcheck.adaptive_branch(["call.risk >= 3", 'call.kind == "good"'], runs, {"call": sim}) == 1
    assert playcheck.adaptive_branch(['call.kind == "good"'], {"call": {**runs["call"], "d": 0}}, {"call": sim}) == -1


def test_verify_keeps_the_blocks_within_creators_limits():
    report = verifymod.Report()
    sims = [(1, "content.md", 1, "call", simmod.variable_types({"risk": 0}), False),
            (1, "content.md", 4, "inner", simmod.variable_types({"x": 0}), True)]
    lines = ["sim", ':::if call.kind == "good" && inner.x > 0', "a", "inner sim", ":::else", "b", ":::"]
    assert verifymod.check_adaptive(Path("content.md"), lines, 1, sims, report) == 1
    text = "\n".join(report.errors)
    assert "simulation 'inner' is inside a branch: it cannot be scored there" in text
    assert "reads 'inner.x', of a simulation inside the block itself" in text
    report = verifymod.Report()
    long = ":::if " + " || ".join(["call.risk > 1"] * 40)
    many = [":::if call.risk > 0"] + [x for i in range(10) for x in (f":::elif call.risk > {i + 1}", "x")] + [":::else", "y", ":::"]
    verifymod.check_adaptive(Path("assessment.md"), [long, "a", ":::else", "b", ":::"] + many, 1, sims[:1], report)
    text = "\n".join(report.errors)
    assert "cannot go in a test" in text and "characters; at most 500" in text and "11 branches with a condition; at most 10" in text


def test_conditions_follow_creators_grammar_and_types():
    assert simmod.test("call.risk < 3 == true", {"call.risk": 2})  # equality above the relations
    assert simmod.test('call.ending == "say \\"no\\""', {"call.ending": 'say "no"'})  # escapes \" and \\
    with pytest.raises(simmod.ExpressionError):
        simmod.parse_expression("1 < call.risk < 3")  # comparisons do not chain
    report = verifymod.Report()
    sims = [(1, "content.md", 1, "call", simmod.variable_types({"risk": 0, "called": False}), False)]
    for condition in ('call.kind == 3', '!call.kind', 'call.called + 1', 'call.risk', 'call.grade >= 50 && call.called'):
        verifymod.check_adaptive(Path("content.md"), ["sim", f":::if {condition}", "a", ":::else", "b", ":::"], 1, sims, report)
    text = "\n".join(report.errors)
    assert "'==' compares str with num" in text and "'!' needs bool and gets str" in text
    assert "'+' needs num and gets bool" in text and "the condition gives num" in text
    assert len(report.errors) == 4


def test_the_package_sends_its_variables_in_state_vars():
    source = (Path(str(resources.files("coursekit.templates.html"))) / "player" / "embedsim.js").read_text(encoding="utf-8")
    assert "vars: run.env" in source and "saved.vars || saved.e" in source
