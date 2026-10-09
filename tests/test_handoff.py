"""`coursekit handoff`: the whole process by itself, signing as "Coursekit Handoff"; the agents are played by a fake."""

import json
import re
import shutil
from pathlib import Path

import pytest
import yaml

from coursekit import agents, launch
from coursekit.cli import main
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
        monkeypatch.setattr(launch, "execute", self.execute)

    @property
    def course(self):
        return self.root / "courses" / "PWD"

    def execute(self, project, agent, text, headless, log_name):
        assert headless, "handoff never opens an interface"
        command, _, arguments = text.split("\n")[0].partition(" ")
        command = command.lstrip("/")
        self.calls.append(command)
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
            asset["status"] = "uploaded"
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
