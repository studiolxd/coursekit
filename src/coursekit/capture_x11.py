"""Desktop mode of `coursekit capture` on Linux with X11 (see `capture_window` for what every system shares).

It drives the windows with the `xdotool` program, grabs the screen with Pillow and records it with the `x11grab` input of
ffmpeg. Wayland does not let one program read or drive the windows of another: there, desktop capture is refused. The
windows of other programs over the one captured are not known here (the program is brought to the front first), and the
focused field cannot be known, so typing is not refused.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from PIL import Image

from coursekit.capture_window import Bounds, WindowBackend, matches, one_program
from coursekit.i18n import t
from coursekit.mcpserver import ToolError

KEYS = {"Enter": "Return", "Tab": "Tab", "Space": "space", "Backspace": "BackSpace", "Escape": "Escape", "Delete": "Delete",
        "Home": "Home", "End": "End", "PageUp": "Prior", "PageDown": "Next", "ArrowLeft": "Left", "ArrowUp": "Up",
        "ArrowRight": "Right", "ArrowDown": "Down", **{f"F{n}": f"F{n}" for n in range(1, 13)}}
MODIFIERS = {"Shift": "shift", "Control": "ctrl", "Alt": "alt", "Meta": "super", "ControlOrMeta": "ctrl"}
SYMBOLS = {" ": "space", "-": "minus", "=": "equal", ",": "comma", ".": "period", "/": "slash", ";": "semicolon",
           "'": "apostrophe", "[": "bracketleft", "]": "bracketright", "\\": "backslash", "`": "grave"}


def xdotool_keys(combo: str) -> str:
    """`Control+Shift+A` → `ctrl+shift+a` (the names xdotool uses)."""
    parts = combo.split("+")
    out = []
    for modifier in parts[:-1]:
        if modifier not in MODIFIERS:
            raise ToolError(t("capture", "bad_key", key=combo))
        out.append(MODIFIERS[modifier])
    key = parts[-1]
    if key in KEYS:
        out.append(KEYS[key])
    elif len(key) == 1 and key.isascii() and key.isalnum():
        out.append(key.lower() if len(parts) > 1 else key)
    elif key in SYMBOLS:
        out.append(SYMBOLS[key])
    else:
        raise ToolError(t("capture", "bad_key", key=combo))
    return "+".join(out)


def shell_values(text: str) -> dict[str, str]:
    """The `KEY=value` lines that `xdotool ... --shell` prints."""
    return dict(re.findall(r"^(\w+)=(.*)$", text, re.M))


class X11Backend(WindowBackend):
    """One window of a program of an X11 session. Coordinates are pixels inside the window."""

    def __init__(self, window_name: str):
        if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or (os.environ.get("WAYLAND_DISPLAY")
                                                                           and not os.environ.get("DISPLAY")):
            raise ToolError(t("capture", "wayland_unsupported"))
        if not os.environ.get("DISPLAY"):
            raise ToolError(t("capture", "desktop_unsupported", system="linux without DISPLAY"))
        self.xdotool = shutil.which("xdotool")
        if not self.xdotool:
            raise ToolError(t("capture", "xdotool_missing"))
        super().__init__(window_name)

    def _run(self, *args: str, check: bool = True) -> str:
        done = subprocess.run([self.xdotool, *args], capture_output=True, text=True, encoding="utf-8", check=False)
        if check and done.returncode != 0:
            raise ToolError(t("capture", "window_gone", name=self.name))
        return done.stdout

    def _describe(self, wid: str) -> dict | None:
        geometry = shell_values(self._run("getwindowgeometry", "--shell", wid, check=False))
        if not geometry.get("WIDTH"):
            return None
        pid = self._run("getwindowpid", wid, check=False).strip()
        program = Path(f"/proc/{pid}/comm").read_text(encoding="utf-8").strip() if pid.isdigit() and \
            Path(f"/proc/{pid}/comm").exists() else ""
        title = self._run("getwindowname", wid, check=False).strip()
        return {"id": wid, "pid": int(pid) if pid.isdigit() else 0, "owner": program, "title": title,
                "bounds": (float(geometry["X"]), float(geometry["Y"]), float(geometry["WIDTH"]), float(geometry["HEIGHT"]))}

    def find(self, name: str) -> dict:
        ids = self._run("search", "--onlyvisible", "--name", ".", check=False).split()
        every = [w for w in (self._describe(i) for i in ids) if w]
        found = [w for w in every if w["bounds"][2] > 40 and w["bounds"][3] > 40 and matches(w, name)]
        return one_program(found, name, every)

    def bounds(self) -> Bounds:
        current = self._describe(self.window["id"])
        if current is None:
            raise ToolError(t("capture", "window_gone", name=self.name))
        self.window["bounds"] = current["bounds"]
        return current["bounds"]

    def front(self) -> None:
        self._run("windowactivate", "--sync", self.window["id"], check=False)
        time.sleep(0.15)

    def owner_at(self, x, y):
        self.mouse_move(x, y)  # X11 says which window is under the pointer, not under any point
        where = shell_values(self._run("getmouselocation", "--shell", check=False))
        wid = where.get("WINDOW")
        if not wid:
            return None
        if wid == str(self.window["id"]):
            return self.window["pid"], self.window["owner"]
        pid = self._run("getwindowpid", wid, check=False).strip()
        if not pid.isdigit():
            return None  # the frame of the window manager or the desktop: it has no program
        found = self._describe(wid)
        return int(pid), found["owner"] if found else ""

    def grab(self, area: Bounds) -> Image.Image:
        from PIL import ImageGrab

        x, y, width, height = area
        return ImageGrab.grab(bbox=(int(x), int(y), int(x + width), int(y + height)))

    def mouse_move(self, x, y) -> None:
        self._run("mousemove", str(int(x)), str(int(y)), check=False)

    def mouse_button(self, button, down, x, y, clicks=1) -> None:
        self.mouse_move(x, y)
        self._run("mousedown" if down else "mouseup", "3" if button == "right" else "1", check=False)

    def wheel(self, x, y, dx, dy) -> None:
        for amount, (less, more) in ((dy, ("4", "5")), (dx, ("6", "7"))):
            notches = round(abs(amount) / 50)
            if notches:
                self._run("click", "--repeat", str(notches), more if amount > 0 else less, check=False)

    def type_text(self, text, delay_ms) -> None:
        self._run("type", "--delay", str(int(delay_ms)), "--", text, check=False)

    def press(self, combo) -> None:
        self._run("key", "--clearmodifiers", xdotool_keys(combo), check=False)

    def record_args(self, area: Bounds) -> tuple[list[str], str]:
        x, y, width, height = area
        return ["-f", "x11grab", "-framerate", "30", "-draw_mouse", "1", "-video_size", f"{int(width) // 2 * 2}x{int(height) // 2 * 2}",
                "-i", f"{os.environ.get('DISPLAY', ':0')}+{int(x)},{int(y)}"], ""
