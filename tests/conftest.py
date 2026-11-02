import os
import shutil
from pathlib import Path

import pytest

from coursekit import i18n, store


@pytest.fixture(autouse=True)
def no_npm(monkeypatch):
    """The suite never installs anything: npm is not found for the store unless a test brings its own fake."""
    real = shutil.which
    monkeypatch.setattr(store.shutil, "which", lambda name, *args, **kwargs: None if name == "npm" else real(name, *args, **kwargs))


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path_factory):
    """coursekit loads .env files into os.environ: restore it after every test. Messages in English unless a test says otherwise."""
    saved = dict(os.environ)
    os.environ["COURSEKIT_LANG"] = "en"
    os.environ["COURSEKIT_NO_UPDATE_CHECK"] = "1"  # the suite never asks PyPI
    os.environ["COURSEKIT_NO_REFRESH"] = "1"  # a test that wants the refresh removes it
    os.environ["COURSEKIT_HOME"] = str(tmp_path_factory.mktemp("coursekit-home"))  # never the real store of the machine
    i18n.use(None)
    yield
    i18n.use(None)
    os.environ.clear()
    os.environ.update(saved)


@pytest.fixture(autouse=True)
def no_misconceptions(request, monkeypatch):
    """The sample courses of the suite predate the common errors (design/misconceptions.yaml): the suite starts without them
    (`misconceptions.per_objective: 0`); the tests of the feature set the rule in their course."""
    from coursekit import config

    if request.node.get_closest_marker("real_defaults"):
        return
    real = config.package_defaults

    def defaults(name):
        data = real(name)
        if name == "rules":
            data.setdefault("misconceptions", {})["per_objective"] = 0
            data.setdefault("content", {})["visual_sections"] = []  # the sample units predate it: tested in test_visuals
            data["content"]["visual_decision"] = False
        return data

    monkeypatch.setattr(config, "package_defaults", defaults)


@pytest.fixture
def agent_tool(monkeypatch):
    """The AI tools are found on the machine (CI has none): for the tests that build the command line of a session."""
    from coursekit import launch

    real = launch.shutil.which
    monkeypatch.setattr(launch.shutil, "which", lambda name, *args, **kwargs: real(name, *args, **kwargs) or f"/fake/{name}")


@pytest.fixture
def make_project(tmp_path, monkeypatch):
    """Makes a project with `coursekit init --yes` in tmp_path/<folder> and enters it. Nobody signs unless `signer` is given
    (a name and an email, written to the .env of the project). `options` go to init; `clear` names more variables to unset."""
    from coursekit.cli import main

    def make(*options: str, folder: str = "demo", signer: tuple[str, str] | None = None, git: bool = False, clear=()):
        for key in ("COURSEKIT_PROJECT", "COURSEKIT_USER_NAME", "COURSEKIT_USER_EMAIL", *clear):
            monkeypatch.delenv(key, raising=False)
        root = tmp_path / folder
        assert main(["init", str(root), "--yes", *([] if git else ["--no-git"]), *options]) == 0
        monkeypatch.chdir(root)
        if signer:
            (root / ".env").write_text(f"COURSEKIT_USER_NAME={signer[0]}\nCOURSEKIT_USER_EMAIL={signer[1]}\n", encoding="utf-8")
        return root

    return make


@pytest.fixture
def make_course():
    """Makes a course with `coursekit new` in the current project. With `approve`, the sample design (fixtures/matrix.json) is
    approved; `prepare(course_dir)` runs before, to change the course first (its rules, say)."""
    from coursekit.cli import main

    def make(root: Path, title: str = "Contraseñas seguras", code: str = "PWD", approve: bool = False, prepare=None) -> Path:
        assert main(["new", title, "1", "--code", code]) == 0
        course_dir = root / "courses" / code
        if prepare:
            prepare(course_dir)
        if approve:
            shutil.copy(Path(__file__).parent / "fixtures" / "matrix.json", course_dir / "design" / "matrix.json")
            assert main(["approve", "design", code, "--yes", "--no-commit"]) == 0
        return course_dir

    return make
