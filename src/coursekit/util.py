"""Small shared helpers."""

from __future__ import annotations

import hashlib
import re
import subprocess
import unicodedata
from pathlib import Path

import yaml
from ruamel.yaml import YAML


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


def render(text: str, **values: object) -> str:
    """Replace {key} tokens without touching other braces (YAML inline maps)."""
    for key, value in values.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def slugify(text: str, limit: int = 48) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:limit]


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
