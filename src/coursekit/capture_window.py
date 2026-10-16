"""Desktop mode of `coursekit capture`: one window of a program, driven and captured with the permission of a person.

The person names the window when giving the permission (`coursekit capture allow CODE --mode desktop --window NAME`); the
session finds it among the windows on screen (by the name of the program or the title of the window: the windows of exactly
one program must match). What the agent sees is only the area of that window, with the program brought to the front and the
windows of other programs over it painted out where the system says where they are; every screen is read on the pixels and
its personal data covered before it is shown (there is no page to clean here, so an OCR is required). A click, a drag or a
scroll goes to the system only after checking that what is under the pointer belongs to that program: nothing outside it
can be clicked. A password field is never typed into.

What is common lives here (`WindowBackend`); each system says how to find a window, grab its area, move the mouse, press keys
and record the screen: `capture_macos` (CoreGraphics and Accessibility through ctypes), `capture_windows` (user32 through
ctypes) and `capture_x11` (`xdotool`, Linux with X11; Wayland does not let a program drive another). The coordinates of a
backend are inside the window (its top-left corner is 0, 0), in the units of its system: points on macOS, pixels elsewhere.
"""

from __future__ import annotations

import io
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw

from coursekit.i18n import t
from coursekit.mcpserver import ToolError

Bounds = tuple[float, float, float, float]  # x, y, width, height, on the whole screen


def paint_out(image: Image.Image, origin: tuple[float, float], scale: float, others: list[tuple]) -> Image.Image:
    """The capture of the area of the window with the windows of other programs over it painted out."""
    draw = ImageDraw.Draw(image)
    for x, y, w, h in others:
        box = ((x - origin[0]) * scale, (y - origin[1]) * scale, (x - origin[0] + w) * scale, (y - origin[1] + h) * scale)
        draw.rectangle(box, fill=(24, 24, 24))
    return image


def one_program(found: list[dict], name: str, every: list[dict]) -> dict:
    """The window of the one program that matches `name` (the first, the frontmost); an error that lists them otherwise."""
    if len({w["pid"] for w in found}) != 1:
        names = sorted({f"{w['owner']} — {w['title']}".rstrip(" —") for w in every if w.get("owner") or w.get("title")})
        raise ToolError(t("capture", "window_not_found" if not found else "window_ambiguous", name=name,
                          windows="; ".join(names[:20]) or "—"))
    return found[0]


def matches(window: dict, name: str) -> bool:
    wanted = name.strip().casefold()
    return bool(wanted) and (wanted in window["owner"].casefold() or wanted in window["title"].casefold())


class WindowBackend:
    """One window of a program. A system implements the hooks below; the rest is the same everywhere."""

    when_unknown_secret = False  # whether typing is refused when the focused field cannot be known

    def __init__(self, window_name: str):
        self.name = window_name
        self.window = self.find(window_name)
        self.viewport = (round(self.window["bounds"][2]), round(self.window["bounds"][3]))
        self._pointer = (self.viewport[0] / 2, self.viewport[1] / 2)
        self._ffmpeg: subprocess.Popen | None = None
        self._video: Path | None = None

    # ── what each system says ──

    def find(self, name: str) -> dict:  # {"id", "pid", "owner", "title", "bounds"}
        raise NotImplementedError

    def bounds(self) -> Bounds:  # where the window is now (window_gone when it was closed)
        raise NotImplementedError

    def front(self) -> None:
        raise NotImplementedError

    def owner_at(self, x: float, y: float) -> tuple[int, str] | None:  # the program of what is under a point of the screen
        raise NotImplementedError

    def grab(self, area: Bounds) -> Image.Image:
        raise NotImplementedError

    def others_above(self) -> list[Bounds]:  # the windows of other programs over this one
        return []

    def mouse_move(self, x: float, y: float) -> None:
        raise NotImplementedError

    def mouse_button(self, button: str, down: bool, x: float, y: float, clicks: int = 1) -> None:
        raise NotImplementedError

    def wheel(self, x: float, y: float, dx: float, dy: float) -> None:  # dy > 0 goes down
        raise NotImplementedError

    def type_text(self, text: str, delay_ms: int) -> None:
        raise NotImplementedError

    def press(self, combo: str) -> None:  # `Control+Shift+A`, `Enter`
        raise NotImplementedError

    def focused_secret(self) -> bool | None:  # None: it cannot be known
        return None

    def element_at(self, x: float, y: float) -> dict:
        return {}

    def record_args(self, area: Bounds) -> tuple[list[str], str]:
        """The input of ffmpeg that records the screen, and the filter that cuts it to that area ("" when it is cut already)."""
        raise NotImplementedError

    # ── the same everywhere ──

    def _global(self, x: float, y: float) -> tuple[float, float]:
        bx, by, bw, bh = self.bounds()
        if not (0 <= x <= bw and 0 <= y <= bh):
            raise ToolError(t("capture", "outside_screen", x=round(x), y=round(y)))
        return bx + x, by + y

    def _ours_at(self, point: tuple[float, float]) -> None:
        found = self.owner_at(*point)
        if found is not None and found[0] != self.window["pid"]:
            raise ToolError(t("capture", "not_our_window", owner=found[1] or "?"))

    def screenshot(self) -> bytes:
        self.front()
        area = self.bounds()
        image = self.grab(area).convert("RGB")
        image = paint_out(image, area[:2], image.width / area[2], self.others_above())
        out = io.BytesIO()
        image.save(out, "PNG")
        return out.getvalue()

    def click(self, x, y, button, count) -> None:
        self.front()
        point = self._global(x, y)
        self._ours_at(point)
        self.mouse_move(*point)
        for n in range(1, count + 1):
            self.mouse_button(button, True, *point, n)
            self.mouse_button(button, False, *point, n)
        self._pointer = (x, y)
        time.sleep(0.3)

    def move(self, x, y) -> None:
        self.mouse_move(*self._global(x, y))
        self._pointer = (x, y)

    def glide(self, x, y, ms) -> None:
        x0, y0 = self._pointer
        steps = max(1, int(ms) // 16)
        for i in range(1, steps + 1):
            self.mouse_move(*self._global(x0 + (x - x0) * i / steps, y0 + (y - y0) * i / steps))
            time.sleep(0.016)
        self._pointer = (x, y)

    def drag(self, x1, y1, x2, y2) -> None:
        self.front()
        start, end = self._global(x1, y1), self._global(x2, y2)
        self._ours_at(start)
        self._ours_at(end)
        self.mouse_move(*start)
        self.mouse_button("left", True, *start)
        for i in range(1, 13):
            self.mouse_move(start[0] + (end[0] - start[0]) * i / 12, start[1] + (end[1] - start[1]) * i / 12)
            time.sleep(0.016)
        self.mouse_button("left", False, *end)
        self._pointer = (x2, y2)

    def scroll(self, x, y, dx, dy) -> None:
        point = self._global(x, y)
        self._ours_at(point)
        self.mouse_move(*point)
        self.wheel(*point, dx, dy)
        time.sleep(0.3)

    def type(self, text) -> None:
        self.type_slowly(text, 20)

    def type_slowly(self, text, delay) -> None:
        self.front()
        self.type_text(text, max(0, int(delay)))

    def key(self, combo) -> None:
        self.front()
        self.press(combo)
        time.sleep(0.3)

    def wait(self, ms) -> None:
        time.sleep(ms / 1000)

    def navigate(self, url) -> None:
        raise ToolError(t("capture", "desktop_no_navigate"))

    def url(self) -> str:
        return ""

    def target_at(self, x, y) -> dict:
        return self.element_at(*self._global(x, y))

    def focused_is_secret(self) -> bool:
        secret = self.focused_secret()
        return self.when_unknown_secret if secret is None else secret

    def locate(self, target: dict):
        return None  # on the desktop a replay goes by the position inside the window

    def start_recording(self) -> None:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise ToolError(t("redact", "ffmpeg_missing"))
        self.front()
        source, crop = self.record_args(self.bounds())
        filters = ",".join(f for f in (crop, "scale=trunc(iw/2)*2:trunc(ih/2)*2") if f)
        self._video = Path(tempfile.mkdtemp()) / "screen.mp4"
        self._ffmpeg = subprocess.Popen(
            [ffmpeg, "-y", "-loglevel", "error", *source, "-vf", filters, "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(self._video)],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        time.sleep(0.8)  # the recording starts

    def stop_recording(self) -> Path:
        """The video recorded since `start_recording` (an MP4 of the area of the window)."""
        process, video = self._ffmpeg, self._video
        self._ffmpeg = self._video = None
        if process is None or video is None:
            raise ToolError(t("capture", "replay_no_frames"))
        try:
            process.communicate(b"q", timeout=15)
        except subprocess.TimeoutExpired:
            process.send_signal(signal.CTRL_C_EVENT if sys.platform == "win32" else signal.SIGINT)
            process.wait(timeout=10)
        if not video.exists() or video.stat().st_size == 0:
            raise ToolError(t("capture", "replay_no_frames"))
        return video

    def close(self) -> None:
        if self._ffmpeg is not None:
            self._ffmpeg.kill()
            self._ffmpeg = None


def make_backend(window_name: str) -> WindowBackend:
    """The backend of this system for a window."""
    if sys.platform == "darwin":
        from coursekit.capture_macos import MacBackend

        return MacBackend(window_name)
    if sys.platform == "win32":
        from coursekit.capture_windows import WindowsBackend

        return WindowsBackend(window_name)
    if sys.platform.startswith("linux"):
        from coursekit.capture_x11 import X11Backend

        return X11Backend(window_name)
    raise ToolError(t("capture", "desktop_unsupported", system=sys.platform))
