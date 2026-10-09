"""The per-machine store: workspaces installed once and linked, the record of what setup installed, and `coursekit uninstall`.
No tool is ever installed for real: npm and uv are replaced by fakes."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from coursekit import setup, store
from coursekit.cli import main
from coursekit.project import find_project

REAL_RUN = subprocess.run


class Fakes:
    """npm creates node_modules; uv records what it was asked and lists the tools it 'has'."""

    def __init__(self, monkeypatch, tools=()):
        self.calls: list[list[str]] = []
        self.installed = set(tools)
        self.fail_npm = False
        monkeypatch.setattr(subprocess, "run", self.run)
        monkeypatch.setattr(setup.shutil, "which", lambda name: f"/fake/{name}" if name in ("npm", "uv", "brew") else None)
        monkeypatch.setattr(store.shutil, "which", lambda name: f"/fake/{name}" if name in ("npm", "uv", "brew") else None)

    def run(self, args, **kwargs):
        name = Path(str(args[0])).name
        if name not in ("npm", "uv", "brew"):
            return REAL_RUN(args, **kwargs)
        self.calls.append([name, *map(str, args[1:])])

        class Done:
            returncode = 0
            stdout = ""

        done = Done()
        if name == "npm":
            if self.fail_npm:
                done.returncode = 1
            else:
                (Path(kwargs["cwd"]) / "node_modules" / ".bin").mkdir(parents=True, exist_ok=True)
        elif name == "uv" and args[1:3] == ["tool", "list"]:
            done.stdout = "".join(f"{tool} v1.0\n- {tool}\n" for tool in sorted(self.installed))
        elif name == "uv" and args[1:3] == ["tool", "install"]:
            self.installed.add(str(args[-1]))
        elif name == "uv" and args[1:3] == ["tool", "uninstall"]:
            self.installed.discard(str(args[-1]))
        return done

    def npm_installs(self) -> int:
        return sum(1 for call in self.calls if call[0] == "npm" and call[1] == "install")


@pytest.fixture
def project(tmp_path, monkeypatch):
    for key in ("COURSEKIT_PROJECT", "COURSEKIT_USER_NAME", "COURSEKIT_USER_EMAIL"):
        monkeypatch.delenv(key, raising=False)
    root = tmp_path / "p1"
    assert main(["init", str(root), "--yes", "--no-git"]) == 0
    monkeypatch.chdir(root)
    return find_project(root)


@pytest.fixture
def user_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setenv("SHELL", "/bin/zsh")
    return home


# ── where the store is ───────────────────────────────────────────────────────────────────────


def test_the_store_can_be_moved_with_an_environment_variable(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSEKIT_HOME", str(tmp_path / "elsewhere"))
    assert store.home() == tmp_path / "elsewhere"


@pytest.mark.skipif(os.name == "nt", reason="the folder of the user's data differs on Windows")
def test_the_default_place_follows_the_system(user_home, monkeypatch):
    monkeypatch.delenv("COURSEKIT_HOME")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    assert store.home() == user_home / "Library" / "Application Support" / "coursekit"
    monkeypatch.setattr(sys, "platform", "linux")
    assert store.home() == user_home / ".local" / "share" / "coursekit"
    monkeypatch.setenv("XDG_DATA_HOME", str(user_home / "data"))
    assert store.home() == user_home / "data" / "coursekit"


def test_sizes_are_readable():
    assert store.human(512) == "512 B" and store.human(1500) == "1.5 KB" and store.human(2_500_000) == "2.5 MB"


# ── workspaces installed once ────────────────────────────────────────────────────────────────


def package_json(folder: Path, deps: str = "a") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "package.json"
    path.write_text(json.dumps({"name": "w", "dependencies": {deps: "1"}}), encoding="utf-8")
    return path


def test_a_workspace_is_installed_once_per_package_json(tmp_path, monkeypatch):
    fakes = Fakes(monkeypatch)
    said = []
    first = store.ensure_workspace("remotion", package_json(tmp_path / "a"), said.append)
    again = store.ensure_workspace("remotion", package_json(tmp_path / "b"), said.append)  # the same dependencies
    assert first == again and (first / "node_modules").is_dir() and fakes.npm_installs() == 1
    other = store.ensure_workspace("remotion", package_json(tmp_path / "c", deps="other"), said.append)
    assert other != first and fakes.npm_installs() == 2
    assert store.registry()["workspaces"] == [first.name, other.name]
    assert "once for every project" in said[0]


def test_the_lock_file_is_part_of_the_key(tmp_path):
    manifest = package_json(tmp_path / "a")
    plain = store.workspace_key(manifest)
    (tmp_path / "a" / "package-lock.json").write_text("{}", encoding="utf-8")
    assert store.workspace_key(manifest) != plain


def test_a_failed_install_leaves_nothing_behind(tmp_path, monkeypatch):
    fakes = Fakes(monkeypatch)
    fakes.fail_npm = True
    assert store.ensure_workspace("remotion", package_json(tmp_path / "a"), lambda m: None) is None
    assert not list(store.workspaces_dir().glob("*")) and store.registry()["workspaces"] == []


def test_without_npm_there_is_no_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(store.shutil, "which", lambda name: None)
    said = []
    assert store.ensure_workspace("remotion", package_json(tmp_path / "a"), said.append) is None
    assert said


def test_node_modules_is_linked_kept_or_replaced(tmp_path, monkeypatch):
    Fakes(monkeypatch)
    workspace = store.ensure_workspace("remotion", package_json(tmp_path / "w"), lambda m: None)
    project_dir = tmp_path / "project" / "tools" / "remotion"
    project_dir.mkdir(parents=True)
    assert store.link_node_modules(project_dir, workspace) == "linked"
    assert (project_dir / "node_modules" / ".bin").is_dir()  # it reaches what the workspace installed
    assert (project_dir / "node_modules").resolve() == (workspace / "node_modules").resolve()
    assert store.link_node_modules(project_dir, workspace) == "linked"  # again: nothing changes
    other = store.ensure_workspace("remotion", package_json(tmp_path / "w2", deps="other"), lambda m: None)
    assert store.link_node_modules(project_dir, other) == "linked"  # a link to another workspace is replaced
    assert (project_dir / "node_modules").resolve() == (other / "node_modules").resolve()

    own = tmp_path / "own"
    (own / "node_modules").mkdir(parents=True)
    assert store.link_node_modules(own, workspace) == "kept"  # a real folder is the project's own install


def test_a_link_that_cannot_be_made_is_reported(tmp_path, monkeypatch):
    Fakes(monkeypatch)
    workspace = store.ensure_workspace("remotion", package_json(tmp_path / "w"), lambda m: None)
    monkeypatch.setattr(store, "_make_link", lambda link, target: False)
    folder = tmp_path / "x"
    folder.mkdir()
    assert store.link_node_modules(folder, workspace) == "failed"


# ── setup uses it ────────────────────────────────────────────────────────────────────────────


def test_two_projects_share_one_install_of_remotion(project, tmp_path, monkeypatch):
    fakes = Fakes(monkeypatch)
    said = []
    setup.remotion(project, said.append)
    second = tmp_path / "p2"
    assert main(["init", str(second), "--yes", "--no-git"]) == 0
    setup.remotion(find_project(second), said.append)
    assert fakes.npm_installs() == 1  # the second project downloads nothing
    first_modules = (project.root / "tools" / "remotion" / "node_modules").resolve()
    assert first_modules == (second / "tools" / "remotion" / "node_modules").resolve()
    assert (project.root / "tools" / "remotion" / "src").is_dir() and (second / "tools" / "remotion" / "src").is_dir()
    assert any("shared from" in line for line in said)


def test_without_a_link_the_project_installs_its_own(project, monkeypatch):
    fakes = Fakes(monkeypatch)
    monkeypatch.setattr(store, "_make_link", lambda link, target: False)
    said = []
    setup.remotion(project, said.append)
    target = project.root / "tools" / "remotion"
    assert (target / "node_modules").is_dir() and not (target / "node_modules").is_symlink()
    assert fakes.npm_installs() == 2  # the store one and the project's own


def test_a_project_with_its_own_install_keeps_it(project, monkeypatch):
    Fakes(monkeypatch)
    target = project.root / "tools" / "remotion"
    setup.remotion(project, lambda m: None)  # creates the sources and the link
    (target / "node_modules").unlink()
    (target / "node_modules").mkdir()
    said = []
    setup.remotion(project, said.append)
    assert not (target / "node_modules").is_symlink() and any("its own node_modules" in line for line in said)


def test_the_project_ignores_node_modules(project):
    assert "node_modules/" in (project.root / ".gitignore").read_text(encoding="utf-8")


def test_setup_records_what_it_installs(project, user_home, monkeypatch):
    fakes = Fakes(monkeypatch)
    monkeypatch.setattr(setup, "IS_WINDOWS", False)
    setup.media_tools(lambda m: None)
    assert set(store.registry()["uv_tools"]) == {"piper-tts", "stable-ts"}
    assert fakes.installed == {"piper-tts", "stable-ts"}

    def fake_retrieve(url, target):
        Path(target).write_text("voice", encoding="utf-8")

    monkeypatch.setattr(setup.urllib.request, "urlretrieve", fake_retrieve)
    monkeypatch.setattr(setup, "voices_dir", lambda: user_home / "voices")
    monkeypatch.delenv("PIPER_VOICE", raising=False)
    setup.piper_voice(project, lambda m: None)
    assert len(store.registry()["files"]) == 2 and all(Path(f).exists() for f in store.registry()["files"])

    assert setup.persist_user_env("NODE_EXTRA_CA_CERTS", "/certs/corp.pem")
    assert store.registry()["shell_lines"] == [{"file": str(user_home / ".zshrc"), "name": "NODE_EXTRA_CA_CERTS"}]
    assert "export NODE_EXTRA_CA_CERTS=" in (user_home / ".zshrc").read_text(encoding="utf-8")


# ── uninstall ────────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def installed(project, user_home, monkeypatch):
    """A machine where setup has installed everything."""
    fakes = Fakes(monkeypatch)
    monkeypatch.setattr(setup, "IS_WINDOWS", False)
    (user_home / ".zshrc").write_text("export PATH=$PATH:/x\n", encoding="utf-8")
    setup.persist_user_env("NODE_EXTRA_CA_CERTS", "/certs/corp.pem")
    setup.persist_user_env("UV_NATIVE_TLS", "1")
    setup.remotion(project, lambda m: None)
    setup.media_tools(lambda m: None)
    voices = user_home / "voices"
    voices.mkdir()
    (voices / "es_ES-sharvard-medium.onnx").write_text("voice", encoding="utf-8")
    store.record("files", str(voices / "es_ES-sharvard-medium.onnx"))
    store.record("system", {"manager": "brew", "packages": ["ffmpeg", "vhs"]})
    return fakes


def test_uninstall_dry_run_shows_everything_and_removes_nothing(installed, user_home, capsys):
    assert main(["uninstall", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "Node dependencies shared by the projects" in out and "remotion-" in out
    assert "piper-tts (installed by coursekit setup)" in out and "stable-ts" in out
    assert "es_ES-sharvard-medium.onnx" in out and "2 coursekit block(s)" in out
    assert "brew uninstall ffmpeg vhs" in out
    assert "uv tool uninstall slxd-coursekit" in out
    assert list(store.workspaces_dir().glob("*")) and installed.installed == {"piper-tts", "stable-ts"}
    assert "NODE_EXTRA_CA_CERTS" in (user_home / ".zshrc").read_text(encoding="utf-8")


def test_uninstall_without_a_terminal_and_without_yes_keeps_everything(installed, capsys, monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert main(["uninstall"]) == 0
    assert "left as it is" in capsys.readouterr().out
    assert list(store.workspaces_dir().glob("*")) and installed.installed


def test_uninstall_yes_removes_what_coursekit_installed_and_nothing_else(installed, project, user_home, capsys):
    assert main(["uninstall", "--yes"]) == 0
    out = capsys.readouterr().out
    assert not store.home().exists()  # the workspaces and the record
    assert installed.installed == set()
    assert not (user_home / "voices").exists()
    assert (user_home / ".zshrc").read_text(encoding="utf-8") == "export PATH=$PATH:/x\n"  # the rest of the file is intact
    assert "removed 1 dependency folder(s)" in out and "removed piper-tts" in out and "removed 2 block(s)" in out
    assert "brew uninstall ffmpeg vhs" in out  # system packages are only listed
    assert (project.root / "project.yaml").exists() and (project.root / "tools" / "remotion" / "src").is_dir()  # projects untouched


def test_uninstall_asks_group_by_group(installed, monkeypatch, capsys):
    answers = iter([False, True, True, True, True])  # keep the workspaces, remove the rest
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("coursekit.init.confirm", lambda question, default=True: next(answers))
    assert main(["uninstall"]) == 0
    assert list(store.workspaces_dir().glob("*")) and installed.installed == set()


def test_uninstall_with_nothing_installed(user_home, monkeypatch, capsys):
    Fakes(monkeypatch)
    assert main(["uninstall", "--dry-run"]) == 0
    assert "Nothing installed by coursekit outside the projects" in capsys.readouterr().out


def test_a_tool_that_is_installed_but_not_recorded_is_asked_about(user_home, monkeypatch, capsys):
    fakes = Fakes(monkeypatch, tools={"piper-tts"})
    assert main(["uninstall", "--dry-run"]) == 0
    assert "piper-tts (detected" in capsys.readouterr().out
    assert fakes.installed == {"piper-tts"}


# ── doctor ───────────────────────────────────────────────────────────────────────────────────


def test_doctor_shows_the_store_and_a_broken_link(project, monkeypatch, capsys):
    Fakes(monkeypatch)
    setup.remotion(project, lambda m: None)
    assert main(["doctor"]) in (0, 1)
    out = capsys.readouterr().out
    assert "coursekit store" in out and "Remotion dependencies (tools/remotion/node_modules)" in out
    import shutil

    shutil.rmtree(store.workspaces_dir())  # the link now points at nothing
    assert main(["doctor"]) in (0, 1)
    assert "missing Remotion dependencies" in capsys.readouterr().out.replace("  ", " ")
