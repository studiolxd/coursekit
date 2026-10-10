"""`coursekit handoff`: the whole process by itself, signing as "Coursekit Handoff"; the agents are played by a fake."""

import json
import re
import shutil
from pathlib import Path

import pytest
import yaml

from coursekit import agents, launch
from coursekit import assemble as assemblemod
from coursekit.cli import main
from coursekit.project import find_project
from tests.test_course_flow import ASSESSMENT, CONTENT, FIXTURES, write_course_rules

HANDOFF = "Coursekit Handoff <handoff@coursekit.local>"


def data(root) -> dict:
    return yaml.safe_load((root / "courses" / "PWD" / "course.yaml").read_text(encoding="utf-8"))


def set_status(root, status: str) -> None:
    path = root / "courses" / "PWD" / "course.yaml"
    path.write_text(re.sub(r"(?m)^status: .*$", f"status: {status}", path.read_text(encoding="utf-8"), count=1), encoding="utf-8")


class Agents:
    """What each agent command does on disk when it works; `skip` makes a command do nothing (it fails)."""

    def __init__(self, root, monkeypatch):
        self.root, self.calls, self.skip, self.reviews, self.fixing = root, [], {}, [], False
        self.produced_status, self.uploading = "uploaded", False
        monkeypatch.setattr(launch, "execute", self.execute)

    @property
    def course(self):
        return self.root / "courses" / "PWD"

    def execute(self, project, agent, text, headless, log_name):
        assert headless, "handoff never opens an interface"
        command, _, arguments = text.split("\n")[0].partition(" ")
        command = command.lstrip("/")
        self.calls.append(command)
        self.uploading = "already assembled" in text
        if self.skip.get(command, 0) > 0:
            self.skip[command] -= 1
            return 1, None, ""
        getattr(self, command.replace("-", "_"))(arguments)
        return 0, None, ""

    def new_course(self, arguments):
        assert "--no-material" in arguments and "--code PWD" in arguments
        self.existed = (self.course / "course.yaml").exists()  # handoff creates the course folders before the agent
        if not self.existed:
            assert main(["new", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
        write_course_rules(self.course)
        shutil.copy(FIXTURES / "matrix.json", self.course / "design" / "matrix.json")

    def approve_design(self, arguments):
        pass

    def write_unit(self, arguments):
        folder = self.course / "content" / "unit-01"
        content = folder / "content.md"
        if self.fixing:  # the writer fixes what the review found
            self.fixing = False
            text = content.read_text(encoding="utf-8").replace("40 palabras)*\n", "40 palabras)*\n\nextra\n", 1)
            content.write_text(text, encoding="utf-8")
        else:
            content.write_text(CONTENT, encoding="utf-8")
            (folder / "assessment.md").write_text(ASSESSMENT, encoding="utf-8")
        assert main(["verify", "PWD", "--unit", "1"]) == 0

    def review_unit(self, arguments):
        result = self.reviews.pop(0) if self.reviews else "ready"
        self.fixing = result == "not_ready"
        (self.course / "reviews").mkdir(exist_ok=True)
        (self.course / "reviews" / "unit-01-ai-review.md").write_text(
            f"# AI review\n> **Result:** x\n<!-- result: {result} -->\n", encoding="utf-8")
        assert main(["reviewed", "PWD", "1"]) == 0

    def define_theme(self, arguments):
        (self.root / "theme").mkdir(exist_ok=True)
        (self.root / "theme" / "tokens.json").write_text(json.dumps({"origin": {"source": "creator"}, "color": {}}), encoding="utf-8")

    def produce_media(self, arguments):
        path = self.course / "media" / "manifest.yaml"
        manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
        for asset in manifest["assets"]:
            asset["status"] = "uploaded" if self.uploading else self.produced_status
        path.write_text(yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")

    def assemble(self, arguments):
        set_status(self.root, "assembly")

    def deliver(self, arguments):
        set_status(self.root, "delivered")


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.delenv("COURSEKIT_PROJECT", raising=False)
    root = tmp_path / "demo"
    assert main(["init", str(root), "--yes", "--no-git"]) == 0
    monkeypatch.chdir(root)
    # nobody is the signer: handoff signs with its own identity
    monkeypatch.delenv("COURSEKIT_USER_NAME", raising=False)
    monkeypatch.delenv("COURSEKIT_USER_EMAIL", raising=False)
    return root


def test_the_whole_process_by_itself_signed_as_handoff(project, monkeypatch, capsys):
    fake = Agents(project, monkeypatch)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    out = capsys.readouterr().out
    assert fake.calls == ["new-course", "approve-design", "write-unit", "review-unit", "define-theme", "produce-media", "assemble",
                          "deliver"]
    assert fake.existed  # the course was created by handoff itself, then the design agent worked on it
    info = data(project)
    assert info["status"] == "delivered"
    assert [u["status"] for u in info["units"]] == ["approved"]
    approvals = info["approvals"]
    assert [a["gate"] for a in approvals] == ["design", "content"]
    assert all(a["by"] == HANDOFF and a["via"] == "handoff" for a in approvals)
    assert "handoff finished: PWD delivered" in out and "no person has reviewed this course" in out
    assert "Coursekit Handoff" in out


def test_a_person_signature_is_not_marked_as_handoff(project, monkeypatch):
    fake = Agents(project, monkeypatch)
    monkeypatch.setenv("COURSEKIT_USER_NAME", "Ana")
    monkeypatch.setenv("COURSEKIT_USER_EMAIL", "ana@example.com")
    fake.new_course("--no-material --code PWD")
    assert main(["approve", "design", "PWD", "--yes", "--no-commit"]) == 0
    assert data(project)["approvals"][0]["by"] == "Ana <ana@example.com>"
    assert "via" not in data(project)["approvals"][0]


def test_the_agents_cannot_run_handoff():
    assert "Bash(coursekit handoff:*)" in agents.DENY_CLAUDE
    assert "Bash(coursekit handoff:*)" in launch.CLAUDE_DENY
    assert agents.DENY_OPENCODE["*coursekit handoff*"] == "deny"
    reviewer = (Path(agents.__file__).parent / "agentkit" / "agents" / "reviewer.md").read_text(encoding="utf-8")
    assert '"*coursekit handoff*": deny' in reviewer


def test_it_stops_after_the_rounds_and_carries_on_from_where_it_was(project, monkeypatch, capsys):
    fake = Agents(project, monkeypatch)
    fake.skip["write-unit"] = 2  # the writer does nothing in both rounds (the default is 2)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 1
    err = capsys.readouterr().err
    assert "handoff stopped" in err and "unit 1 is not verified after the attempts" in err
    assert "coursekit handoff PWD" in err
    assert fake.calls.count("write-unit") == 2
    assert data(project)["status"] == "design_approved"
    fake.calls.clear()
    assert main(["handoff", "PWD"]) == 0  # the design is not asked for nor signed again
    assert fake.calls[0] == "write-unit" and "new-course" not in fake.calls
    assert [a["gate"] for a in data(project)["approvals"]] == ["design", "content"]
    assert data(project)["status"] == "delivered"


def test_a_not_ready_review_sends_the_unit_back_to_the_writer(project, monkeypatch, capsys):
    fake = Agents(project, monkeypatch)
    fake.reviews = ["not_ready"]
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    out = capsys.readouterr().out
    assert fake.calls[2:6] == ["write-unit", "review-unit", "write-unit", "review-unit"]
    assert 'the AI review says "not ready"' in out
    assert data(project)["status"] == "delivered"


def test_a_review_that_stays_not_ready_stops(project, monkeypatch, capsys):
    fake = Agents(project, monkeypatch)
    fake.reviews = ["not_ready", "not_ready"]
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD", "--rounds", "2"]) == 1
    assert 'still says "not ready" for unit 1' in capsys.readouterr().err
    assert data(project)["units"][0]["status"] != "approved"


def test_it_does_not_start_when_the_project_needs_the_client_review(project, monkeypatch, capsys):
    (project / "config").mkdir(exist_ok=True)
    (project / "config" / "delivery.yaml").write_text("client_review:\n  required: true\n", encoding="utf-8")
    fake = Agents(project, monkeypatch)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 1
    assert "requires the client review" in capsys.readouterr().err
    assert fake.calls == []  # nothing is created, signed nor written


def test_a_course_on_hold_is_not_touched(project, monkeypatch, capsys):
    fake = Agents(project, monkeypatch)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD", "--rounds", "1"]) == 0
    set_status(project, "on_hold")
    fake.calls.clear()
    assert main(["handoff", "PWD"]) == 1
    assert "on hold" in capsys.readouterr().err and fake.calls == []


def test_creating_needs_a_new_code_and_resuming_takes_no_creation_options(project, monkeypatch, capsys):
    fake = Agents(project, monkeypatch)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD", "--rounds", "1"]) == 0
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 1
    assert "already exists" in capsys.readouterr().err
    assert main(["handoff", "PWD", "--notes", "x"]) == 2
    assert "only apply when creating" in capsys.readouterr().err
    assert fake.calls.count("new-course") == 1


def test_the_rounds_come_from_the_rules(project, monkeypatch, capsys):
    (project / "config").mkdir(exist_ok=True)
    (project / "config" / "rules.yaml").write_text("handoff:\n  rounds: 1\n", encoding="utf-8")
    fake = Agents(project, monkeypatch)
    fake.skip["write-unit"] = 1
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 1
    assert fake.calls.count("write-unit") == 1


def test_it_waits_for_the_material_once_the_course_folders_exist(project, monkeypatch, capsys):
    fake = Agents(project, monkeypatch)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True, raising=False)
    prompts = []

    def enter(prompt):
        prompts.append(prompt)
        assert (project / "courses" / "PWD" / "brief" / "sources").is_dir() and fake.calls == []  # folders yes, agents not yet
        (project / "courses" / "PWD" / "brief" / "sources" / "guide.md").write_text("# Guide\n", encoding="utf-8")
        return ""

    monkeypatch.setattr("builtins.input", enter)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    out = capsys.readouterr().out
    assert len(prompts) == 1 and prompts[0].startswith("Press Enter to go on")
    assert "courses/PWD/brief/sources" in out and "courses/PWD/brief/links.md" in out and "courses/PWD/brief/notes.md" in out
    assert (project / "courses" / "PWD" / "brief" / "sources" / "guide.md").exists()
    assert fake.calls[0] == "new-course"


def test_no_pause_and_a_resume_never_wait(project, monkeypatch):
    fake = Agents(project, monkeypatch)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt: pytest.fail("it must not wait"))
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD", "--no-pause", "--rounds", "1"]) == 0
    assert main(["handoff", "PWD"]) == 0  # already delivered: nothing to wait for
    assert main(["handoff", "PWD", "--no-pause"]) == 2  # the option only makes sense when creating
    assert fake.calls.count("new-course") == 1


def test_a_step_refused_a_program_is_not_repeated(project, monkeypatch, capsys):
    fake = Agents(project, monkeypatch)
    log = project / "deliver.log"
    log.write_text("\n".join(json.dumps(e) for e in [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "1", "name": "Bash", "input": {"command": "curl -fL x"}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "1", "is_error": True,
                                                  "content": "This command requires approval"}]}},
    ]), encoding="utf-8")
    run = fake.execute

    def execute(project_, agent, text, headless, log_name):
        code, _, summary = run(project_, agent, text, headless, log_name)
        return (1, log, "needs curl") if text.startswith("/deliver") else (code, None, summary)

    monkeypatch.setattr(launch, "execute", execute)
    fake.skip["deliver"] = 2
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 1
    assert fake.calls.count("deliver") == 1  # the second round would be refused the same
    assert "tried to run curl" in capsys.readouterr().err


def test_the_media_is_uploaded_once_the_course_is_assembled_and_it_is_assembled_again(project, monkeypatch):
    fake = Agents(project, monkeypatch)
    fake.produced_status = "produced"  # they can only be uploaded to the content that the assembly creates
    monkeypatch.setattr(assemblemod, "unit_in_sync", lambda course_dir, n: fake.calls.count("assemble") >= 2)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    assert fake.calls[-5:] == ["produce-media", "assemble", "produce-media", "assemble", "deliver"]


def test_it_stops_when_the_media_cannot_be_uploaded(project, monkeypatch, capsys):
    fake = Agents(project, monkeypatch)
    fake.produced_status = "produced"
    run = fake.execute

    def execute(project_, agent, text, headless, log_name):
        if "already assembled" in text:
            fake.calls.append("produce-media")
            return 1, None, ""
        return run(project_, agent, text, headless, log_name)

    monkeypatch.setattr(launch, "execute", execute)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 1
    assert "still not uploaded to creator" in capsys.readouterr().err
    assert fake.calls.count("deliver") == 0


def test_media_marked_to_be_produced_again_is_produced_uploaded_and_assembled_again(project, monkeypatch):
    fake = Agents(project, monkeypatch)
    monkeypatch.setattr(assemblemod, "unit_in_sync", lambda course_dir, n: fake.calls.count("assemble") >= 2)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    path = fake.course / "media" / "manifest.yaml"
    manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest["assets"][0]["status"] = "scripted"  # what `coursekit media redo` leaves after the theme was changed
    path.write_text(yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")
    set_status(project, "assembly")
    fake.calls.clear()
    fake.produced_status = "produced"
    monkeypatch.setattr(assemblemod, "unit_in_sync", lambda course_dir, n: "assemble" in fake.calls)
    assert main(["handoff", "PWD"]) == 0
    assert fake.calls == ["produce-media", "produce-media", "assemble", "deliver"]


def test_a_delivered_course_is_reopened_after_its_content_was_edited(project, monkeypatch, capsys):
    fake = Agents(project, monkeypatch)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    assert main(["handoff", "PWD", "--new-version"]) == 0  # nothing edited: every unit stays approved, so it goes on from the media
    assert fake.calls[-1] == "deliver"
    content = fake.course / "content" / "unit-01" / "content.md"
    content.write_text(content.read_text(encoding="utf-8").replace("40 palabras)*\n", "40 palabras)*\n\nextra\n", 1), encoding="utf-8")
    fake.calls.clear()
    capsys.readouterr()
    assert main(["handoff", "PWD", "--new-version"]) == 0
    out = capsys.readouterr().out
    assert "reopened for a new version" in out and "carries on from 'ai_review'" in out
    assert fake.calls[0] == "review-unit" and fake.calls[-1] == "deliver"
    info = data(project)
    assert info["status"] == "delivered" and [u["status"] for u in info["units"]] == ["approved"]
    assert any(h.get("note") == "Reopened for a new version" and h["by"] == "Coursekit Handoff" for h in info["history"])


def test_only_a_delivered_course_can_be_reopened(project, monkeypatch, capsys):
    Agents(project, monkeypatch)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    set_status(project, "media")
    assert main(["handoff", "PWD", "--new-version"]) == 1
    assert "not delivered" in capsys.readouterr().err
    assert main(["handoff", "Otro curso", "1", "--new-version"]) == 2


def test_what_the_agents_record_is_signed_by_the_handoff(project, monkeypatch):
    fake = Agents(project, monkeypatch)
    seen = []
    run = fake.execute

    def execute(project_, agent, text, headless, log_name):
        seen.append(dict(launch.SESSION_ENV))
        return run(project_, agent, text, headless, log_name)

    monkeypatch.setattr(launch, "execute", execute)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    assert seen and all(e == {"COURSEKIT_USER_NAME": "Coursekit Handoff", "COURSEKIT_USER_EMAIL": "handoff@coursekit.local"} for e in seen)
    assert launch.SESSION_ENV == {}  # it does not leak to the next command


def test_the_session_environment_reaches_the_agent(project, monkeypatch):
    got = {}
    monkeypatch.setattr("subprocess.call", lambda args, **kw: got.update(env=kw["env"]) or 0)
    monkeypatch.setitem(launch.SESSION_ENV, "COURSEKIT_USER_NAME", "Someone")
    launch.execute(find_project(project), launch.Agent("writer", "claude", ""), "x", True, "t")
    assert got["env"]["COURSEKIT_USER_NAME"] == "Someone"


def test_an_assembly_that_stopped_before_recording_is_done_again_when_it_carries_on(project, monkeypatch):
    fake = Agents(project, monkeypatch)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    assembly = fake.course / "assembly"
    assembly.mkdir(exist_ok=True)
    (assembly / "unit-01.plan.json").write_text("{}", encoding="utf-8")
    (assembly / "unit-01.applied.json").write_text("{}", encoding="utf-8")
    state = {"synced": False}
    monkeypatch.setattr(assemblemod, "unit_in_sync", lambda course_dir, n: state["synced"] or fake.calls.count("assemble") >= 1)
    monkeypatch.setattr(assemblemod, "unit_checked", lambda course_dir, n: fake.calls.count("assemble") >= 1)
    set_status(project, "assembly")
    fake.calls.clear()
    assert main(["handoff", "PWD"]) == 0
    assert fake.calls == ["assemble", "deliver"]


def _recorded_unit(fake):
    """A unit whose plan is recorded as applied, as the assembly agent leaves it."""
    assert main(["assemble", "plan", "PWD", "--unit", "1"]) == 0
    plan = json.loads((fake.course / "assembly" / "unit-01.plan.json").read_text(encoding="utf-8"))
    for lesson in plan["lessons"]:
        ids = ",".join(f"b{i}" for i in range(len(lesson["bricks"])))
        assert main(["assemble", "applied", "PWD", "--unit", "1", "--lesson", lesson["key"], "--lesson-id", "L1", "--brick-ids", ids]) == 0
    assert main(["assemble", "applied", "PWD", "--unit", "1", "--content"]) == 0


def test_a_recorded_assembly_without_its_closing_checks_runs_them_before_delivering(project, monkeypatch, capsys):
    fake = Agents(project, monkeypatch)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    _recorded_unit(fake)
    capsys.readouterr()
    assert main(["assemble", "checked", "PWD", "--unit", "1"]) == 0
    assert "closing recorded" in capsys.readouterr().out
    # a change in the recorded bricks makes the checks pending again
    applied = fake.course / "assembly" / "unit-01.applied.json"
    state = json.loads(applied.read_text(encoding="utf-8"))
    first = next(iter(state["lessons"].values()))["bricks"][0]
    first["hash"] = "changed"
    applied.write_text(json.dumps(state), encoding="utf-8")
    assert not assemblemod.unit_checked(fake.course, 1)

    def assemble(arguments):
        fake.assembled = getattr(fake, "assembled", 0) + 1
        _recorded_unit(fake)
        assert main(["assemble", "checked", "PWD", "--unit", "1"]) == 0

    fake.assemble = assemble
    set_status(project, "assembly")
    fake.calls.clear()
    assert main(["handoff", "PWD"]) == 0
    assert fake.calls == ["assemble", "deliver"]


def test_it_stops_when_the_closing_checks_cannot_be_done(project, monkeypatch, capsys):
    fake = Agents(project, monkeypatch)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    _recorded_unit(fake)
    set_status(project, "assembly")
    fake.calls.clear()
    assert main(["handoff", "PWD"]) == 1
    assert "closing checks" in capsys.readouterr().err
    assert "deliver" not in fake.calls


def test_checked_refuses_what_is_not_in_sync_with_the_plan(project, monkeypatch, capsys):
    fake = Agents(project, monkeypatch)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    _recorded_unit(fake)
    applied = fake.course / "assembly" / "unit-01.applied.json"
    state = json.loads(applied.read_text(encoding="utf-8"))
    next(iter(state["lessons"].values()))["bricks"][0]["hash"] = "changed"
    applied.write_text(json.dumps(state), encoding="utf-8")
    capsys.readouterr()
    assert main(["assemble", "checked", "PWD", "--unit", "1"]) == 1
    assert "does not match the plan" in capsys.readouterr().err


def test_checking_an_unchanged_assembly_moves_a_reopened_course_to_assembly(project, monkeypatch):
    fake = Agents(project, monkeypatch)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    _recorded_unit(fake)
    set_status(project, "media")  # reopened: nothing to apply, so nothing is recorded but the closing
    assert main(["assemble", "checked", "PWD", "--unit", "1"]) == 0
    assert data(project)["status"] == "assembly"
