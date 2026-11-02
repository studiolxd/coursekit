"""Running the programs coursekit uses (ffmpeg, ffprobe, git, esbuild, uv…) and reading what they say.

`run` reads their output as UTF-8 always, with a replacement character where a program writes something else: without it, the
output is decoded with the encoding of the system (cp1252 in a console of Windows), and a file name with an accent in an error
of ffmpeg breaks the reading or comes out garbled. It calls `subprocess.run` through the module, so the tests that replace it
reach it.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any


def run(command: Sequence[str | Path], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """`subprocess.run` with the output as UTF-8 text. It does not raise for an exit code unless `check=True` is given: the
    caller looks at `returncode`."""
    kwargs.setdefault("check", False)
    return subprocess.run([str(part) for part in command], text=True, encoding="utf-8", errors="replace", **kwargs)
