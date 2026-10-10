"""Tells the person when a newer coursekit is published on PyPI. It only informs: nothing is ever upgraded by itself.

At most once a day, when a command runs in a terminal, the latest version is asked of PyPI (a couple of seconds at most, any failure
is silent) and remembered in the per-machine store. `coursekit doctor` asks every time. `COURSEKIT_NO_UPDATE_CHECK=1` turns it off."""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request

from coursekit import __version__, store
from coursekit.i18n import t

PACKAGE = "slxd-coursekit"
URL = f"https://pypi.org/pypi/{PACKAGE}/json"
OFF_ENV = "COURSEKIT_NO_UPDATE_CHECK"
EVERY = 24 * 3600
TIMEOUT = 2.0
SKIP = {None, "help"}


def off() -> bool:
    return bool(os.environ.get(OFF_ENV))


def key(version: str) -> tuple:
    """Order of versions: the numbers, and a pre-release (`0.1.0.dev0`, `1.0rc1`) before its release."""
    numbers = tuple(int(n) for n in re.findall(r"\d+", re.split(r"[A-Za-z]", version, maxsplit=1)[0]))
    return numbers, 0 if re.search(r"[A-Za-z]", version) else 1


def newer(latest: str | None, current: str = __version__) -> bool:
    return bool(latest) and key(latest) > key(current)


def latest() -> str | None:
    """The latest version on PyPI, or None when it cannot be known (no network, unexpected answer)."""
    try:
        request = urllib.request.Request(URL, headers={"User-Agent": f"coursekit/{__version__}"})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 — a fixed https URL
            return str(json.load(response)["info"]["version"])
    except Exception:  # noqa: BLE001 — informing is optional: never fail because of it
        return None


def _cache():
    return store.home() / "update-check.json"


def _remembered() -> dict:
    try:
        return json.loads(_cache().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def known_latest(now: float | None = None) -> str | None:
    """The latest version, asking PyPI only when the last check is older than a day."""
    now = time.time() if now is None else now
    data = _remembered()
    if now - float(data.get("checked", 0) or 0) >= EVERY:
        found = latest()
        data = {"checked": now, "latest": found or data.get("latest")}
        try:
            _cache().parent.mkdir(parents=True, exist_ok=True)
            _cache().write_text(json.dumps(data), encoding="utf-8")
        except OSError:
            pass
    return data.get("latest")


def notice(command: str | None) -> str | None:
    """The line to print before the command, or None (off, not in a terminal, up to date, unknown)."""
    if off() or command in SKIP or not sys.stderr.isatty():
        return None
    found = known_latest()
    return t("updatecheck", "available", latest=found, current=__version__, package=PACKAGE) if newer(found) else None
