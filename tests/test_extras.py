import importlib.util

from coursekit import brief, doctor, extras


def installed_only(monkeypatch, modules):
    """Only the extras whose modules are in `modules` look installed, whatever this environment really has."""
    real = importlib.util.find_spec
    extra_modules = {m for names in extras.EXTRAS.values() for m in names}

    def find_spec(name, *a):
        if name in extra_modules:
            return object() if name in modules else None
        return real(name, *a)

    monkeypatch.setattr(importlib.util, "find_spec", find_spec)


def test_the_install_command_keeps_the_extras_already_installed(monkeypatch):
    installed_only(monkeypatch, {"markitdown"})
    assert extras.installed() == ["docs"]
    assert extras.install_command("capture") == 'uv tool install --force "slxd-coursekit[docs,capture]"'
    installed_only(monkeypatch, set())
    assert extras.install_command("capture") == 'uv tool install --force "slxd-coursekit[capture]"'


def test_brief_without_the_docs_extra_names_the_command(monkeypatch, tmp_path):
    installed_only(monkeypatch, set())
    monkeypatch.setitem(__import__("sys").modules, "markitdown", None)  # the import fails, as without the extra
    text, problem = brief.markitdown(tmp_path / "manual.pdf")
    assert text is None
    assert problem == ("markitdown_missing", {"command": 'uv tool install --force "slxd-coursekit[docs]"'})


def test_doctor_asks_for_the_docs_extra_only_when_there_are_documents_to_convert(monkeypatch, tmp_path):
    installed_only(monkeypatch, set())
    monkeypatch.delenv("COURSEKIT_PROJECT", raising=False)
    monkeypatch.setenv("COURSEKIT_NO_UPDATE_CHECK", "1")
    (tmp_path / "project.yaml").write_text("name: Demo\n", encoding="utf-8")
    sources = tmp_path / "brief" / "sources"
    sources.mkdir(parents=True)
    (sources / "notes.md").write_text("# Notes\n", encoding="utf-8")
    (sources / "diagram.png").write_bytes(b"png")
    monkeypatch.chdir(tmp_path)
    from coursekit.project import find_project

    def markitdown_check():
        return next(c for c in doctor.collect(find_project())[0].checks if "MarkItDown" in c.label)

    assert markitdown_check().status == "info"  # text and images need no extra
    (sources / "manual.pdf").write_bytes(b"%PDF")
    check = markitdown_check()
    assert check.status == "missing" and check.hint == 'uv tool install --force "slxd-coursekit[docs]"'


def test_doctor_warns_of_several_opencv_packages(monkeypatch):
    from importlib import metadata

    present = {"opencv-python", "opencv-python-headless"}

    def distribution(name):
        if name not in present:
            raise metadata.PackageNotFoundError(name)
        return object()

    monkeypatch.setattr(metadata, "distribution", distribution)
    assert doctor.opencv_distributions() == ["opencv-python", "opencv-python-headless"]
