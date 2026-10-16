"""Desktop mode of `coursekit capture` on macOS (see `capture_window` for what every system shares).

It speaks to the system through its own libraries (CoreGraphics, CoreFoundation, Accessibility) with ctypes, and captures
with the `screencapture` and `ffmpeg` programs: no package is needed. Coordinates are points. The terminal that runs
coursekit needs two permissions of macOS (System Settings › Privacy & Security): Screen Recording and Accessibility. When
the focused field cannot be known, nothing is typed.
"""

from __future__ import annotations

import ctypes
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image

from coursekit.capture_window import Bounds, WindowBackend, one_program, paint_out
from coursekit.i18n import t
from coursekit.mcpserver import ToolError

__all__ = ["MacBackend", "covering", "paint_out", "parse_combo", "permissions", "quartz"]

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
            raise ToolError(t("capture", "desktop_unsupported", system=sys.platform))
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
    from coursekit.capture_window import matches

    every = [w for w in quartz().windows() if w["layer"] == 0]
    found = [w for w in every if w["bounds"][2] > 40 and w["bounds"][3] > 40 and matches(w, name)]
    return one_program(found, name, every)


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


class MacBackend(WindowBackend):
    """One window of a program of the Mac. Coordinates are points inside the window (its top-left corner is 0, 0)."""

    when_unknown_secret = True

    def __init__(self, window_name: str):
        if not shutil.which("screencapture"):
            raise ToolError(t("capture", "desktop_unsupported", system=sys.platform))
        granted = permissions()
        if not granted["screen"]:
            raise ToolError(t("capture", "need_screen_permission"))
        if not granted["accessibility"]:
            raise ToolError(t("capture", "need_accessibility_permission"))
        self._held: str | None = None
        super().__init__(window_name)

    def find(self, name: str) -> dict:
        return find_window(name)

    def bounds(self) -> Bounds:
        current = next((w for w in quartz().windows() if w["id"] == self.window["id"]), None)
        if current is None:
            raise ToolError(t("capture", "window_gone", name=self.name))
        self.window = current
        return current["bounds"]

    def front(self) -> None:
        script = f'tell application "System Events" to set frontmost of (first process whose unix id is {self.window["pid"]}) to true'
        subprocess.run(["osascript", "-e", script], capture_output=True, check=False)
        time.sleep(0.15)

    def owner_at(self, x, y):
        for w in covering(quartz().windows(), self.window["pid"]):
            wx, wy, ww, wh = w["bounds"]
            if wx <= x < wx + ww and wy <= y < wy + wh:
                return w["pid"], w["owner"]
        return None

    def grab(self, area: Bounds) -> Image.Image:
        bx, by, bw, bh = area
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "screen.png"
            done = subprocess.run(["screencapture", "-x", "-R", f"{bx:.0f},{by:.0f},{bw:.0f},{bh:.0f}", str(path)],
                                  capture_output=True, check=False)
            if done.returncode != 0 or not path.exists():
                raise ToolError(t("capture", "need_screen_permission"))
            image = Image.open(path)
            image.load()
        return image

    def others_above(self) -> list[Bounds]:
        above = []
        for w in covering(quartz().windows(), self.window["pid"]):  # front to back, until the window itself
            if w["id"] == self.window["id"]:
                break
            if w["pid"] != self.window["pid"]:
                above.append(w["bounds"])
        return above

    def _mouse(self, kind: int, x: float, y: float, button: int = 0, clicks: int = 1) -> None:
        q = quartz()
        event = q.cg.CGEventCreateMouseEvent(None, kind, CGPoint(x, y), button)
        if clicks > 1:
            q.cg.CGEventSetIntegerValueField(event, 1, clicks)  # kCGMouseEventClickState
        q.post(event)

    def mouse_move(self, x, y) -> None:
        dragged = {"left": 6, "right": 7}.get(self._held or "")
        self._mouse(dragged or 5, x, y, 1 if self._held == "right" else 0)

    def mouse_button(self, button, down, x, y, clicks=1) -> None:
        kind = {("left", True): 1, ("left", False): 2, ("right", True): 3, ("right", False): 4}[(button, down)]
        self._mouse(kind, x, y, 1 if button == "right" else 0, clicks)
        self._held = button if down else None

    def wheel(self, x, y, dx, dy) -> None:
        q = quartz()
        q.post(q.cg.CGEventCreateScrollWheelEvent2(None, 0, 2, int(-dy), int(-dx), 0))  # pixels; positive goes up there

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

    def type_text(self, text, delay_ms) -> None:
        for ch in text:
            self._key_event(0, 0, True, ch)
            self._key_event(0, 0, False, ch)
            time.sleep(delay_ms / 1000)

    def press(self, combo) -> None:
        code, flags = parse_combo(combo)
        self._key_event(code, flags, True)
        self._key_event(code, flags, False)

    def _element(self, point: tuple[float, float] | None = None):
        q = quartz()
        system = q.ax.AXUIElementCreateSystemWide()
        try:
            if point is None:
                return q.attribute(system, "AXFocusedUIElement")
            element = ctypes.c_void_p()
            err = q.ax.AXUIElementCopyElementAtPosition(system, point[0], point[1], ctypes.byref(element))
            return element.value if err == 0 else None
        finally:
            q.cf.CFRelease(system)

    def element_at(self, x, y) -> dict:
        q = quartz()
        element = self._element((x, y))
        if not element:
            return {}
        try:
            role = q.text(element, "AXRole").removeprefix("AX").lower()
            name = q.text(element, "AXTitle") or q.text(element, "AXDescription")
        finally:
            q.cf.CFRelease(element)
        return {k: v for k, v in (("role", role), ("name", name.strip()[:80])) if v}

    def focused_secret(self) -> bool | None:
        """A secure text field (a password), or a field whose name says it is a code; None when it cannot be known."""
        q = quartz()
        element = self._element()
        if not element:
            return None
        try:
            role, subrole = q.text(element, "AXRole"), q.text(element, "AXSubrole")
            hint = " ".join(q.text(element, a) for a in ("AXTitle", "AXDescription", "AXPlaceholderValue"))
        finally:
            q.cf.CFRelease(element)
        return role == "AXSecureTextField" or subrole == "AXSecureTextField" or bool(
            re.search(r"password|contraseña|passcode|one-time|otp|verification|código", hint, re.I))

    def record_args(self, area: Bounds) -> tuple[list[str], str]:
        """The main screen with avfoundation, cut to the window (it must be entirely on that screen)."""
        q = quartz()
        display = q.cg.CGMainDisplayID()
        screen = q.cg.CGDisplayBounds(display)
        bx, by, bw, bh = area
        if bx < screen.origin.x or by < screen.origin.y or bx + bw > screen.origin.x + screen.size.width \
                or by + bh > screen.origin.y + screen.size.height:
            raise ToolError(t("capture", "window_off_main_screen", name=self.name))
        scale = q.cg.CGDisplayPixelsWide(display) / screen.size.width
        listing = subprocess.run([shutil.which("ffmpeg"), "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                                 capture_output=True, text=True, check=False).stderr
        index = next((m.group(1) for m in re.finditer(r"\[(\d+)\] Capture screen 0", listing)), None)
        if index is None:
            raise ToolError(t("capture", "need_screen_permission"))
        crop = f"crop={int(bw * scale) // 2 * 2}:{int(bh * scale) // 2 * 2}:{int((bx - screen.origin.x) * scale)}:" \
               f"{int((by - screen.origin.y) * scale)}"
        return ["-f", "avfoundation", "-capture_cursor", "1", "-capture_mouse_clicks", "1", "-framerate", "30", "-i",
                f"{index}:none"], crop
