"""Command line entry point: `coursekit <command> [args]`."""

from __future__ import annotations

import argparse
import sys

from coursekit import __version__

COMMANDS: dict[str, str] = {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coursekit",
        description="AI-assisted e-learning course production.",
    )
    parser.add_argument("--version", action="version", version=f"coursekit {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.add_parser("help", help="show this help")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in (None, "help"):
        parser.print_help()
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
