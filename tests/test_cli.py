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


def test_the_output_is_utf8_even_where_the_system_writes_cp1252(monkeypatch):
    import io
    import sys

    from coursekit import cli

    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252", newline="\n")  # the same line ends on every system
    monkeypatch.setattr(sys, "stdout", stream)
    cli._utf8_output()
    print("✔ ok › done")
    sys.stdout.flush()
    assert raw.getvalue().decode("utf-8") == "✔ ok › done\n"


@pytest.mark.parametrize("language", ["en", "es"])
def test_every_help_can_be_shown(language, monkeypatch):
    import argparse

    from coursekit.cli import build_parser

    monkeypatch.setenv("COURSEKIT_LANG", language)

    def walk(parser):
        parser.format_help()  # raises if a help text has a stray %
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for sub in action.choices.values():
                    walk(sub)

    walk(build_parser())
