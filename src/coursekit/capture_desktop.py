"""Desktop mode of `coursekit capture` on macOS: one window of a program, driven and captured with the permission of a person.

The person names the window when giving the permission (`coursekit capture allow CODE --mode desktop --window NAME`); the
session finds it among the windows on screen (by the name of the program or the title of the window: exactly one must
match). What the agent sees is only the area of that window, with the program brought to the front, and any window of
another program over it painted out; every screen is read on the pixels and its personal data covered before it is shown
(there is no page to clean here, so an OCR is required). A click or a key goes to the system only after checking that what
is under the pointer belongs to that program: nothing outside it can be clicked. A password field is never typed into.

It speaks to the system through its own libraries (CoreGraphics, Accessibility) with ctypes, and captures with the
`screencapture` and `ffmpeg` programs: no package is needed. The terminal that runs coursekit needs two permissions of
macOS (System Settings › Privacy & Security): Screen Recording and Accessibility.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import io
import re
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

FRAMEWORKS = "/System/Library/Frameworks"


class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


class CGSize(ctypes.Structure):
    _fields_ = [("width", ctypes.c_double), ("height", ctypes.c_double)]


class CGRect(ctypes.Structure):
    _fields_ = [("origin", CGPoint), ("size", CGSize)]


# ── the libraries of the system ──────────────────────────────────────────────────────────────

class _Quartz:
    """CoreGraphics, CoreFoundation and Accessibility through ctypes, loaded once."""

    def __init__(self):
        if sys.platform != "darwin":
            raise ToolError(t("capture", "desktop_macos_only"))
        self.cf = ctypes.CDLL(f"{FRAMEWORKS}/CoreFoundation.framework/CoreFoundation")
        self.cg = ctypes.CDLL(f"{FRAMEWORKS}/CoreGraphics.framework/CoreGraphics")
        self.ax = ctypes.CDLL(f"{FRAMEWORKS}/ApplicationServices.framework/ApplicationServices")
        vp, u32, i64 = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int64
        sig = {
            (self.cf, "CFArrayGetCount"): ([vp], ctypes.c_long),
            (self.cf, "CFArrayGetValueAtIndex"): ([vp, ctypes.c_long], vp),
            (self.cf, "CFDictionaryGetValue"): ([vp, vp], vp),
            (self.cf, "CFNumberGetValue"): ([vp, ctypes.c_int, vp], ctypes.c_bool),
            (self.cf, "CFStringGetCString"): ([vp, ctypes.c_char_p, ctypes.c_long, u32], ctypes.c_bool),
            (self.cf, "CFStringCreateWithCString"): ([vp, ctypes.c_char_p, u32], vp),
            (self.cf, "CFGetTypeID"): ([vp], ctypes.c_ulong),
            (self.cf, "CFStringGetTypeID"): ([], ctypes.c_ulong),
            (self.cf, "CFRelease"): ([vp], None),
            (self.cg, "CGWindowListCopyWindowInfo"): ([u32, u32], vp),
            (self.cg, "CGRectMakeWithDictionaryRepresentation"): ([vp, ctypes.POINTER(CGRect)], ctypes.c_bool),
            (self.cg, "CGPreflightScreenCaptureAccess"): ([], ctypes.c_bool),
            (self.cg, "CGMainDisplayID"): ([], u32),
            (self.cg, "CGDisplayBounds"): ([u32], CGRect),
            (self.cg, "CGDisplayPixelsWide"): ([u32], ctypes.c_size_t),
            (self.cg, "CGEventCreateMouseEvent"): ([vp, u32, CGPoint, u32], vp),
            (self.cg, "CGEventCreateKeyboardEvent"): ([vp, ctypes.c_uint16, ctypes.c_bool], vp),
            (self.cg, "CGEventKeyboardSetUnicodeString"): ([vp, ctypes.c_ulong, ctypes.POINTER(ctypes.c_uint16)], None),
            (self.cg, "CGEventCreateScrollWheelEvent2"): ([vp, u32, u32, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32], vp),
            (self.cg, "CGEventSetIntegerValueField"): ([vp, u32, i64], None),
            (self.cg, "CGEventSetFlags"): ([vp, ctypes.c_uint64], None),
            (self.cg, "CGEventPost"): ([u32, vp], None),
            (self.ax, "AXIsProcessTrusted"): ([], ctypes.c_bool),
            (self.ax, "AXUIElementCreateSystemWide"): ([], vp),
            (self.ax, "AXUIElementCopyElementAtPosition"): ([vp, ctypes.c_float, ctypes.c_float, ctypes.POINTER(vp)], ctypes.c_int32),
            (self.ax, "AXUIElementCopyAttributeValue"): ([vp, vp, ctypes.POINTER(vp)], ctypes.c_int32),
        }
        for (lib, name), (args, result) in sig.items():
            fn = getattr(lib, name)
            fn.argtypes, fn.restype = args, result
        self.key = {name: ctypes.c_void_p.in_dll(self.cg, name).value for name in (
            "kCGWindowNumber", "kCGWindowOwnerName", "kCGWindowName", "kCGWindowBounds", "kCGWindowLayer", "kCGWindowOwnerPID")}

    def cfstring(self, text: str):
        return self.cf.CFStringCreateWithCString(None, text.encode("utf-8"), 0x08000100)

    def string(self, ref) -> str:
        if not ref or self.cf.CFGetTypeID(ref) != self.cf.CFStringGetTypeID():
            return ""
        buffer = ctypes.create_string_buffer(4096)
        return buffer.value.decode("utf-8", "replace") if self.cf.CFStringGetCString(ref, buffer, 4096, 0x08000100) else ""

    def number(self, ref) -> int:
        value = ctypes.c_int64()
        return int(value.value) if ref and self.cf.CFNumberGetValue(ref, 4, ctypes.byref(value)) else 0

    def windows(self) -> list[dict]:
        """The windows on screen, front to back: number, program, pid, title, layer and bounds (points, top-left origin)."""
        listing = self.cg.CGWindowListCopyWindowInfo(1 | 16, 0)  # on screen only, without the desktop
        if not listing:
            return []
        out = []
        try:
            for i in range(self.cf.CFArrayGetCount(listing)):
                info = self.cf.CFArrayGetValueAtIndex(listing, i)

                def get(key, info=info):
                    return self.cf.CFDictionaryGetValue(info, self.key[key])

                rect = CGRect()
                bounds = get("kCGWindowBounds")
                if bounds:
                    self.cg.CGRectMakeWithDictionaryRepresentation(bounds, ctypes.byref(rect))
                out.append({"id": self.number(get("kCGWindowNumber")), "owner": self.string(get("kCGWindowOwnerName")),
                            "pid": self.number(get("kCGWindowOwnerPID")), "title": self.string(get("kCGWindowName")),
                            "layer": self.number(get("kCGWindowLayer")),
                            "bounds": (rect.origin.x, rect.origin.y, rect.size.width, rect.size.height)})
        finally:
            self.cf.CFRelease(listing)
        return out

    def post(self, event) -> None:
        if event:
            self.cg.CGEventPost(0, event)
            self.cf.CFRelease(event)

    def text(self, element, name: str) -> str:
        """A text attribute of an element of Accessibility ("" when it has none)."""
        value = self.attribute(element, name)
        if not value:
            return ""
        try:
            return self.string(value)
        finally:
            self.cf.CFRelease(value)

    def attribute(self, element, name: str):
        value = ctypes.c_void_p()
        attr = self.cfstring(name)
        try:
            err = self.ax.AXUIElementCopyAttributeValue(element, attr, ctypes.byref(value))
        finally:
            self.cf.CFRelease(attr)
        return value.value if err == 0 else None


_quartz: _Quartz | None = None


def quartz() -> _Quartz:
    global _quartz
    if _quartz is None:
        _quartz = _Quartz()
    return _quartz


def permissions() -> dict[str, bool]:
    """Whether the terminal has the two permissions of macOS that desktop capture needs."""
    q = quartz()
    return {"screen": bool(q.cg.CGPreflightScreenCaptureAccess()), "accessibility": bool(q.ax.AXIsProcessTrusted())}


def find_window(name: str) -> dict:
    """The one window whose program or title contains `name` (normal windows only, the frontmost when a program has several)."""
    wanted = name.strip().casefold()
    found = [w for w in quartz().windows() if w["layer"] == 0 and w["bounds"][2] > 40 and w["bounds"][3] > 40
             and (wanted in w["owner"].casefold() or wanted in w["title"].casefold())]
    programs = {w["pid"] for w in found}
    if len(programs) != 1:
        names = sorted({f"{w['owner']} — {w['title']}".rstrip(" —") for w in quartz().windows() if w["layer"] == 0})
        raise ToolError(t("capture", "window_not_found" if not found else "window_ambiguous", name=name,
                          windows="; ".join(names[:20]) or "—"))
    return found[0]  # front to back: the frontmost window of the program


# ── keys ─────────────────────────────────────────────────────────────────────────────────────

KEYCODES = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9, "b": 11, "q": 12, "w": 13, "e": 14,
    "r": 15, "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23, "=": 24, "9": 25, "7": 26, "-": 27,
    "8": 28, "0": 29, "]": 30, "o": 31, "u": 32, "[": 33, "i": 34, "p": 35, "l": 37, "j": 38, "'": 39, "k": 40, ";": 41,
    "\\": 42, ",": 43, "/": 44, "n": 45, "m": 46, ".": 47, "`": 50,
    "Enter": 36, "Tab": 48, "Space": 49, "Backspace": 51, "Escape": 53, "Delete": 117, "Home": 115, "End": 119,
    "PageUp": 116, "PageDown": 121, "ArrowLeft": 123, "ArrowRight": 124, "ArrowDown": 125, "ArrowUp": 126,
    **{f"F{n}": code for n, code in zip(range(1, 13), (122, 120, 99, 118, 96, 97, 98, 100, 101, 109, 103, 111), strict=True)},
}
FLAGS = {"Shift": 0x20000, "Control": 0x40000, "Alt": 0x80000, "Meta": 0x100000, "ControlOrMeta": 0x100000}


def parse_combo(combo: str) -> tuple[int, int]:
    """`Control+Shift+A` → (key code, flags)."""
    parts = combo.split("+")
    flags = 0
    for modifier in parts[:-1]:
        if modifier not in FLAGS:
            raise ToolError(t("capture", "bad_key", key=combo))
        flags |= FLAGS[modifier]
    key = parts[-1]
    code = KEYCODES.get(key, KEYCODES.get(key.lower()))
    if code is None:
        raise ToolError(t("capture", "bad_key", key=combo))
    if len(key) == 1 and key.isupper() and key.isalpha() and len(parts) == 1:
        flags |= FLAGS["Shift"]
    return code, flags


# ── the backend ──────────────────────────────────────────────────────────────────────────────

def covering(windows: list[dict], pid: int) -> list[dict]:
    """The windows that can be over the one of the program, front to back: the normal windows of every program, and every
    window of the program itself (its menus and dialogs). The layers of the system (the Dock, the menu bar, overlays the
    size of the screen) are left out: they are transparent where they show nothing."""
    return [w for w in windows if w["layer"] == 0 or w["pid"] == pid]


def paint_out(image: Image.Image, origin: tuple[float, float], scale: float, others: list[tuple]) -> Image.Image:
    """The capture of the area of the window with the windows of other programs over it painted out."""
    draw = ImageDraw.Draw(image)
    for x, y, w, h in others:
        box = ((x - origin[0]) * scale, (y - origin[1]) * scale, (x - origin[0] + w) * scale, (y - origin[1] + h) * scale)
        draw.rectangle(box, fill=(24, 24, 24))
    return image


class DesktopBackend:
    """One window of a program of the Mac. Coordinates are points inside the window (its top-left corner is 0, 0)."""

    def __init__(self, window_name: str):
        if not shutil.which("screencapture"):
            raise ToolError(t("capture", "desktop_macos_only"))
        granted = permissions()
        if not granted["screen"]:
            raise ToolError(t("capture", "need_screen_permission"))
        if not granted["accessibility"]:
            raise ToolError(t("capture", "need_accessibility_permission"))
        self.name = window_name
        self.window = find_window(window_name)
        self.viewport = (round(self.window["bounds"][2]), round(self.window["bounds"][3]))
        self._pointer = (self.viewport[0] / 2, self.viewport[1] / 2)
        self._ffmpeg: subprocess.Popen | None = None
        self._video: Path | None = None

    # where the window is now, and the program in front
    def _refresh(self) -> tuple[float, float, float, float]:
        current = next((w for w in quartz().windows() if w["id"] == self.window["id"]), None)
        if current is None:
            raise ToolError(t("capture", "window_gone", name=self.name))
        self.window = current
        return current["bounds"]

    def _front(self) -> None:
        script = f'tell application "System Events" to set frontmost of (first process whose unix id is {self.window["pid"]}) to true'
        subprocess.run(["osascript", "-e", script], capture_output=True, check=False)
        time.sleep(0.15)

    def _global(self, x: float, y: float) -> CGPoint:
        bx, by, bw, bh = self._refresh()
        if not (0 <= x <= bw and 0 <= y <= bh):
            raise ToolError(t("capture", "outside_screen", x=round(x), y=round(y)))
        return CGPoint(bx + x, by + y)

    def _ours_at(self, point: CGPoint) -> None:
        """What is under the pointer belongs to the program of the window (its menus and dialogs too), or nothing happens."""
        for w in covering(quartz().windows(), self.window["pid"]):
            x, y, ww, wh = w["bounds"]
            if x <= point.x < x + ww and y <= point.y < y + wh:
                if w["pid"] != self.window["pid"]:
                    raise ToolError(t("capture", "not_our_window", owner=w["owner"] or "?"))
                return

    def screenshot(self) -> bytes:
        self._front()
        bx, by, bw, bh = self._refresh()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "screen.png"
            done = subprocess.run(["screencapture", "-x", "-R", f"{bx:.0f},{by:.0f},{bw:.0f},{bh:.0f}", str(path)],
                                  capture_output=True, check=False)
            if done.returncode != 0 or not path.exists():
                raise ToolError(t("capture", "need_screen_permission"))
            image = Image.open(path)
            image.load()
        scale = image.width / bw
        above = []
        for w in covering(quartz().windows(), self.window["pid"]):  # front to back, until the window itself
            if w["id"] == self.window["id"]:
                break
            if w["pid"] != self.window["pid"]:
                above.append(w["bounds"])
        image = paint_out(image.convert("RGB"), (bx, by), scale, above)
        out = io.BytesIO()
        image.save(out, "PNG")
        return out.getvalue()

    def _mouse(self, kind: int, point: CGPoint, button: int = 0, clicks: int = 1) -> None:
        q = quartz()
        event = q.cg.CGEventCreateMouseEvent(None, kind, point, button)
        if clicks > 1:
            q.cg.CGEventSetIntegerValueField(event, 1, clicks)  # kCGMouseEventClickState
        q.post(event)

    def click(self, x, y, button, count) -> None:
        self._front()
        point = self._global(x, y)
        self._ours_at(point)
        down, up, which = (3, 4, 1) if button == "right" else (1, 2, 0)
        self._mouse(5, point)
        for n in range(1, count + 1):
            self._mouse(down, point, which, n)
            self._mouse(up, point, which, n)
        self._pointer = (x, y)
        time.sleep(0.3)

    def move(self, x, y) -> None:
        self._mouse(5, self._global(x, y))
        self._pointer = (x, y)

    def glide(self, x, y, ms) -> None:
        x0, y0 = self._pointer
        steps = max(1, int(ms) // 16)
        for i in range(1, steps + 1):
            self._mouse(5, self._global(x0 + (x - x0) * i / steps, y0 + (y - y0) * i / steps))
            time.sleep(0.016)
        self._pointer = (x, y)

    def drag(self, x1, y1, x2, y2) -> None:
        self._front()
        start, end = self._global(x1, y1), self._global(x2, y2)
        self._ours_at(start)
        self._ours_at(end)
        self._mouse(5, start)
        self._mouse(1, start)
        for i in range(1, 13):
            self._mouse(6, CGPoint(start.x + (end.x - start.x) * i / 12, start.y + (end.y - start.y) * i / 12))
            time.sleep(0.016)
        self._mouse(2, end)
        self._pointer = (x2, y2)

    def scroll(self, x, y, dx, dy) -> None:
        point = self._global(x, y)
        self._ours_at(point)
        self._mouse(5, point)
        q = quartz()
        q.post(q.cg.CGEventCreateScrollWheelEvent2(None, 0, 2, int(-dy), int(-dx), 0))  # pixels; positive goes up there
        time.sleep(0.3)

    def _key_event(self, code: int, flags: int, down: bool, text: str | None = None) -> None:
        q = quartz()
        event = q.cg.CGEventCreateKeyboardEvent(None, code, down)
        if flags:
            q.cg.CGEventSetFlags(event, flags)
        if text is not None:
            units = text.encode("utf-16-le")
            chars = (ctypes.c_uint16 * (len(units) // 2)).from_buffer_copy(units)
            q.cg.CGEventKeyboardSetUnicodeString(event, len(units) // 2, chars)
        q.post(event)

    def type(self, text) -> None:
        self.type_slowly(text, 20)

    def type_slowly(self, text, delay) -> None:
        self._front()
        for ch in text:
            self._key_event(0, 0, True, ch)
            self._key_event(0, 0, False, ch)
            time.sleep(max(0, delay) / 1000)

    def key(self, combo) -> None:
        self._front()
        code, flags = parse_combo(combo)
        self._key_event(code, flags, True)
        self._key_event(code, flags, False)
        time.sleep(0.3)

    def wait(self, ms) -> None:
        time.sleep(ms / 1000)

    def navigate(self, url) -> None:
        raise ToolError(t("capture", "desktop_no_navigate"))

    def url(self) -> str:
        return ""

    def _element(self, point: CGPoint | None = None):
        q = quartz()
        system = q.ax.AXUIElementCreateSystemWide()
        try:
            if point is None:
                return q.attribute(system, "AXFocusedUIElement")
            element = ctypes.c_void_p()
            err = q.ax.AXUIElementCopyElementAtPosition(system, point.x, point.y, ctypes.byref(element))
            return element.value if err == 0 else None
        finally:
            q.cf.CFRelease(system)

    def target_at(self, x, y) -> dict:
        q = quartz()
        element = self._element(self._global(x, y))
        if not element:
            return {}
        try:
            role = q.text(element, "AXRole").removeprefix("AX").lower()
            name = q.text(element, "AXTitle") or q.text(element, "AXDescription")
        finally:
            q.cf.CFRelease(element)
        return {k: v for k, v in (("role", role), ("name", name.strip()[:80])) if v}

    def focused_is_secret(self) -> bool:
        """A secure text field (a password), or a field whose name says it is a code. When it cannot be known: yes."""
        q = quartz()
        element = self._element()
        if not element:
            return True
        try:
            role, subrole = q.text(element, "AXRole"), q.text(element, "AXSubrole")
            hint = " ".join(q.text(element, a) for a in ("AXTitle", "AXDescription", "AXPlaceholderValue"))
        finally:
            q.cf.CFRelease(element)
        return role == "AXSecureTextField" or subrole == "AXSecureTextField" or bool(
            re.search(r"password|contraseña|passcode|one-time|otp|verification|código", hint, re.I))

    def locate(self, target: dict):
        return None  # on the desktop a replay goes by the position inside the window

    # ── the video of a replay: the screen recorded with ffmpeg, cut to the window ──

    def start_recording(self) -> None:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise ToolError(t("redact", "ffmpeg_missing"))
        q = quartz()
        display = q.cg.CGMainDisplayID()
        screen = q.cg.CGDisplayBounds(display)
        bx, by, bw, bh = self._refresh()
        if bx < screen.origin.x or by < screen.origin.y or bx + bw > screen.origin.x + screen.size.width \
                or by + bh > screen.origin.y + screen.size.height:
            raise ToolError(t("capture", "window_off_main_screen", name=self.name))
        scale = q.cg.CGDisplayPixelsWide(display) / screen.size.width
        listing = subprocess.run([ffmpeg, "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                                 capture_output=True, text=True, check=False).stderr
        index = next((m.group(1) for m in re.finditer(r"\[(\d+)\] Capture screen 0", listing)), None)
        if index is None:
            raise ToolError(t("capture", "need_screen_permission"))
        crop = f"crop={int(bw * scale) // 2 * 2}:{int(bh * scale) // 2 * 2}:{int((bx - screen.origin.x) * scale)}:" \
               f"{int((by - screen.origin.y) * scale)}"
        self._video = Path(tempfile.mkdtemp()) / "screen.mp4"
        self._ffmpeg = subprocess.Popen(
            [ffmpeg, "-y", "-loglevel", "error", "-f", "avfoundation", "-capture_cursor", "1", "-capture_mouse_clicks", "1",
             "-framerate", "30", "-i", f"{index}:none", "-vf", crop, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
             "-pix_fmt", "yuv420p", str(self._video)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
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
            process.send_signal(signal.SIGINT)
            process.wait(timeout=10)
        if not video.exists() or video.stat().st_size == 0:
            raise ToolError(t("capture", "replay_no_frames"))
        return video

    def close(self) -> None:
        if self._ffmpeg is not None:
            self._ffmpeg.kill()
            self._ffmpeg = None
