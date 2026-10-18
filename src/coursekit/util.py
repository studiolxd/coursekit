"""Small shared helpers."""

from __future__ import annotations

import hashlib
import io
import os
import re
import subprocess
import sys
import threading
import time
import unicodedata
from contextlib import contextmanager
from pathlib import Path

import yaml
from ruamel.yaml import YAML

from coursekit import __version__

# Sent with every download and upload: the services behind Cloudflare refuse the default one of Python (error 1010, a 403).
USER_AGENT = f"coursekit/{__version__}"


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def roundtrip_yaml() -> YAML:
    """YAML loader/dumper that keeps comments and key order (for course.yaml edits)."""
    ry = YAML()
    ry.preserve_quotes = True
    ry.width = 100
    ry.indent(mapping=2, sequence=4, offset=2)
    return ry


def edit_yaml(path: Path):
    """Context-free helper: load a YAML file for round-trip editing. Returns (yaml, data)."""
    ry = roundtrip_yaml()
    return ry, ry.load(path.read_text(encoding="utf-8"))


def save_yaml(ry: YAML, data, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        ry.dump(data, fh)


def save_yaml_atomic(ry: YAML, data, path: Path) -> None:
    """Like save_yaml, but whoever reads the file meanwhile sees the old one or the new one, never half of it."""
    buffer = io.StringIO()
    ry.dump(data, buffer)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(buffer.getvalue(), encoding="utf-8", newline="\n")
    for attempt in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:  # Windows: another process has the file open for a moment
            if attempt == 19:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(0.1)


class LockTimeout(Exception):
    pass


_held: dict[str, list] = {}  # lock files this process holds: [thread lock, depth, open file]
_held_guard = threading.Lock()


@contextmanager
def file_lock(path: Path, timeout: float = 120):
    """An exclusive lock between processes (agents in parallel) on a lock file next to what it protects. Reentrant in the same
    thread; the system frees it if the process dies. LockTimeout when another process keeps it longer than `timeout`."""
    key = str(path.resolve())
    with _held_guard:
        entry = _held.setdefault(key, [threading.RLock(), 0, None])
    entry[0].acquire()
    try:
        if entry[1] == 0:
            path.parent.mkdir(parents=True, exist_ok=True)
            fh = path.open("a+b")
            deadline = time.monotonic() + timeout
            while True:
                try:
                    if sys.platform == "win32":
                        import msvcrt

                        fh.seek(0)
                        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        fh.close()
                        raise LockTimeout(path.as_posix()) from None
                    time.sleep(0.1)
            entry[2] = fh
        entry[1] += 1
        try:
            yield
        finally:
            entry[1] -= 1
            if entry[1] == 0:
                fh = entry[2]
                entry[2] = None
                if sys.platform == "win32":
                    import msvcrt

                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                fh.close()  # closing it frees the flock
    finally:
        entry[0].release()


def render(text: str, **values: object) -> str:
    """Replace {key} tokens without touching other braces (YAML inline maps)."""
    for key, value in values.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def slugify(text: str, limit: int = 48) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:limit]


def character_asset_id(name: str) -> str:
    """Id of the portrait asset of a character of a dialogue (`Daniel` -> `CHAR-DANIEL`): one per character in the whole course."""
    return "CHAR-" + slugify(name).upper()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str, cwd: Path | None = None) -> str:
    try:
        # git prints UTF-8 on every platform; the locale encoding (cp1252 on Windows) would garble it.
        out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, encoding="utf-8", errors="replace", check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""
