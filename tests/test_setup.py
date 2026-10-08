import subprocess

import pytest

from coursekit import doctor, setup
from coursekit.cli import main
from coursekit.project import find_project


@pytest.fixture
def project(tmp_path, monkeypatch):
    for key in ("COURSEKIT_PROJECT", "COURSEKIT_USER_NAME", "COURSEKIT_USER_EMAIL", "NODE_EXTRA_CA_CERTS"):
        monkeypatch.delenv(key, raising=False)
    root = tmp_path / "demo"
    assert main(["init", str(root), "--yes"]) == 0  # with git
    monkeypatch.chdir(root)
    return root


def test_set_env_value_keeps_the_rest(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comment\nA=1\nCOURSEKIT_USER_NAME=\nB=2 # note\n", encoding="utf-8")
    setup.set_env_value(env, "COURSEKIT_USER_NAME", "Ana Pérez")
    setup.set_env_value(env, "NEW_KEY", "x")
    assert env.read_text(encoding="utf-8") == '# comment\nA=1\nCOURSEKIT_USER_NAME="Ana Pérez"\nB=2 # note\nNEW_KEY=x\n'


def test_setup_with_identity_flags(project, capsys):
    assert main(["setup", "--yes", "--name", "Ana Pérez", "--email", "ana@example.com"]) == 0
    out = capsys.readouterr().out
    assert "you sign as Ana Pérez <ana@example.com>" in out
    env = (project / ".env").read_text(encoding="utf-8")
    assert 'COURSEKIT_USER_NAME="Ana Pérez"' in env and "COURSEKIT_USER_EMAIL=ana@example.com" in env
    assert "WRITER_AGENT" in env  # copied from .env.example
    hooks = subprocess.run(["git", "config", "--get", "core.hooksPath"], cwd=project, capture_output=True, text=True).stdout
    assert hooks.strip() == ".githooks"


def test_setup_without_identity_and_without_terminal(project, capsys):
    assert main(["setup", "--yes"]) == 0
    assert "missing: identity to sign approvals" in capsys.readouterr().out
    assert main(["setup", "--identity", "--yes"]) == 1


def test_identity_is_asked_with_the_git_suggestion(project, monkeypatch):
    p = find_project(project)
    monkeypatch.setattr(setup.identity, "suggested", lambda: setup.identity.Identity("Git Name", "git@example.com"))
    asked = []

    def ask(question, default):
        asked.append(default)
        return default

    who = setup.setup_identity(p, lambda m: None, ask)
    assert str(who) == "Git Name <git@example.com>"
    assert asked == ["Git Name", "git@example.com"]


def test_network_certificate_from_project(project, tmp_path, monkeypatch):
    cert = tmp_path / "corp.pem"
    cert.write_text("cert", encoding="utf-8")
    text = (project / "project.yaml").read_text(encoding="utf-8").replace("ca_bundles: []", f"ca_bundles: ['{cert.as_posix()}']")
    (project / "project.yaml").write_text(text, encoding="utf-8")
    p = find_project(project)
    assert setup.ca_bundle(p) == cert
    said = []
    persisted = []
    monkeypatch.setattr(setup, "persist_user_env", lambda k, v: persisted.append((k, v)) or True)
    setup.network(p, said.append, lambda q: True)
    assert ("NODE_EXTRA_CA_CERTS", str(cert)) in persisted
    checks = {c.label: c.status for s in doctor.collect(p) for c in s.checks}
    assert checks[f"corporate CA certificate: NODE_EXTRA_CA_CERTS ({cert})"] == "ok"


def test_doctor_reports(project, capsys):
    assert main(["setup", "--yes", "--name", "Ana", "--email", "ana@example.com"]) == 0
    capsys.readouterr()
    assert main(["doctor"]) == 0
    out = capsys.readouterr().out
    for title in ("Base", "Agent tools", "Network", "Mirror folder", "Media"):
        assert title in out
    assert "ok      signing identity: Ana <ana@example.com>" in out
    assert "ok      git hooks" in out


def test_hooks_are_executable_and_refresh_agents(project):
    import os

    hook = project / ".githooks" / "post-merge"
    assert "coursekit agents" in hook.read_text(encoding="utf-8")
    if os.name != "nt":
        assert os.access(hook, os.X_OK)
