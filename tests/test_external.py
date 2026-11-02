import subprocess
import sys

from coursekit import external


def test_the_output_is_read_as_utf8_whatever_the_system_encoding(tmp_path):
    script = tmp_path / "say.py"
    script.write_text("import sys\nsys.stdout.buffer.write('Contraseñas: año, cañón\\n'.encode('utf-8'))\nsys.exit(3)\n",
                      encoding="utf-8")
    done = external.run([sys.executable, script], capture_output=True)
    assert done.stdout == "Contraseñas: año, cañón\n"
    assert done.returncode == 3  # no exception for an exit code


def test_bytes_that_are_not_utf8_become_a_replacement_character(tmp_path):
    script = tmp_path / "latin.py"
    script.write_text("import sys\nsys.stdout.buffer.write('a\\xf1o'.encode('latin-1'))\n", encoding="utf-8")
    assert external.run([sys.executable, script], capture_output=True).stdout == "a�o"


def test_it_goes_through_subprocess_run_so_tests_can_replace_it(monkeypatch):
    seen = {}
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: seen.update(cmd=cmd, **kw))
    external.run(["ffmpeg", tmp := __import__("pathlib").Path("a b.mp4")], capture_output=True, check=True)
    assert seen["cmd"] == ["ffmpeg", str(tmp)] and seen["encoding"] == "utf-8" and seen["check"] is True
