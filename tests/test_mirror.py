"""The catalog and the mirror folder after a command: cheap, silent when nothing changed and deferred in agent sessions."""

import os
import shutil

import openpyxl
import pytest
import yaml

from coursekit import catalog, commands, launch
from coursekit import course as coursemod
from coursekit.cli import main
from coursekit.project import find_project
from tests.test_assemble import course  # noqa: F401 — project with a course
from tests.test_exelearning import edit_course


@pytest.fixture
def mirror(course, tmp_path, monkeypatch):  # noqa: F811
    folder = tmp_path / "shared"
    folder.mkdir()
    root = course.parent.parent
    data = yaml.safe_load((root / "project.yaml").read_text(encoding="utf-8")) or {}
    data["mirror"] = {"provider": "folder", "url": ""}
    (root / "project.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    monkeypatch.setenv("MIRROR_DIR", str(folder))
    return folder


def second_course(project_root):
    assert main(["new", "Otro curso", "1", "--code", "TWO"]) == 0
    return project_root / "courses" / "TWO"


def test_the_catalog_is_written_once_and_again_only_when_its_data_change(course):  # noqa: F811
    project = find_project()
    output = project.root / "courses" / "catalog.xlsx"
    assert catalog.build(project, output)[2] is True and output.is_file()
    stamp = output.stat().st_mtime_ns
    assert catalog.build(project, output)[2] is False and output.stat().st_mtime_ns == stamp  # nothing changed: nothing written
    edit_course(course, lambda d: d.update(title="Un título nuevo"))
    courses, units, written = catalog.build(project, output)
    assert written is True and courses == 1
    assert openpyxl.load_workbook(output).worksheets[0].cell(row=2, column=2).value == "Un título nuevo"
    assert catalog.build(project, output, force=True)[2] is True  # asked for: always
    output.unlink()
    assert catalog.build(project, output)[2] is True  # a file that is gone is written again


def test_only_the_course_that_changed_is_read_again(course, monkeypatch):  # noqa: F811
    root = course.parent.parent
    other = second_course(root)
    project = find_project()
    output = root / "courses" / "catalog.xlsx"
    loaded = []
    real = coursemod.load

    def counting(p, name, *a, **k):
        loaded.append(os.path.basename(str(name)))
        return real(p, name, *a, **k)

    monkeypatch.setattr(catalog.coursemod, "load", counting)
    shutil.rmtree(project.cache_dir / "catalog", ignore_errors=True)  # `new` already built it
    catalog.build(project, output)
    assert sorted(loaded) == ["PWD", "TWO"]
    loaded.clear()
    catalog.build(project, output)
    assert loaded == []  # a build costs what changed, not the number of courses
    edit_course(other, lambda d: d.update(title="Cambiado"))
    catalog.build(project, output)
    assert loaded == ["TWO"]
    loaded.clear()
    (course / "content" / "unit-01" / "content.md").write_text("# nuevo\n", encoding="utf-8")  # a unit changed
    catalog.build(project, output)
    assert loaded == ["PWD"]


def touch_asset(*extra):
    assert main(["media", "extract", "PWD"]) == 0
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "scripted", *extra]) == 0


def test_after_a_command_nothing_is_said_when_nothing_changed(mirror, capsys):
    touch_asset()
    first = capsys.readouterr().out
    assert "published" in first  # the first time the course goes to the folder
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "scripted"]) == 0  # the same again
    second = capsys.readouterr().out
    assert "wrote" not in second and "published" not in second and "catalog" not in second.lower()
    assert (mirror / catalog.file_name(find_project())).is_file()
    # asked for, it says what it did
    assert main(["publish"]) == 0
    assert "unchanged" in capsys.readouterr().out


def test_agent_sessions_leave_the_mirror_to_who_started_them(mirror, capsys, monkeypatch):
    monkeypatch.setenv("COURSEKIT_MIRROR", "deferred")
    touch_asset()
    assert not list(mirror.iterdir())  # nothing was published by the command of the agent
    monkeypatch.delenv("COURSEKIT_MIRROR")
    assert launch.session_env()["COURSEKIT_MIRROR"] == "deferred"  # what the sessions without an interface start with
    calls = []
    monkeypatch.setattr(commands, "_mirror", lambda project, code: calls.append(code))
    monkeypatch.setattr(launch, "execute", lambda *a, **k: (0, None, ""))
    assert main(["run", "produce-media", "PWD", "--headless"]) == 0
    assert calls == ["PWD"]  # once, when the session ends


def test_verify_without_update_does_not_touch_the_mirror(course, monkeypatch):  # noqa: F811
    calls = []
    monkeypatch.setattr(commands, "_mirror", lambda project, code: calls.append(code))
    main(["verify", "PWD", "--unit", "1", "--no-update"])
    assert calls == []
    main(["verify", "PWD", "--unit", "1"])
    assert calls == ["PWD"]
