import pytest

from coursekit import __version__
from coursekit.cli import main


def test_help_returns_zero(capsys):
    assert main(["help"]) == 0
    assert "coursekit" in capsys.readouterr().out


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out
