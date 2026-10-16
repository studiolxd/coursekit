"""Desktop mode of `coursekit capture` on Windows (see `capture_window` for what every system shares).

It speaks to the system through user32, dwmapi and kernel32 with ctypes, grabs the screen with Pillow and records it with the
`gdigrab` input of ffmpeg: no package is needed, and no permission of the system either. Coordinates are physical pixels
(the process declares itself aware of the scale of each screen). The focused field is a password when it is a classic edit
box with the password style; in other kinds of programs it cannot be known, and typing is not refused.
"""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes

from PIL import Image

from coursekit.capture_window import Bounds, WindowBackend, matches, one_program
from coursekit.i18n import t
from coursekit.mcpserver import ToolError

VK = {"Enter": 0x0D, "Tab": 0x09, "Space": 0x20, "Backspace": 0x08, "Escape": 0x1B, "Delete": 0x2E, "Home": 0x24,
      "End": 0x23, "PageUp": 0x21, "PageDown": 0x22, "ArrowLeft": 0x25, "ArrowUp": 0x26, "ArrowRight": 0x27,
      "ArrowDown": 0x28, **{f"F{n}": 0x6F + n for n in range(1, 13)}}
MODIFIERS = {"Shift": 0x10, "Control": 0x11, "Alt": 0x12, "Meta": 0x5B, "ControlOrMeta": 0x11}


def virtual_keys(combo: str, scan=None) -> list[int]:
    """`Control+Shift+A` → the virtual keys to hold, in order (the last one is the key). `scan` gives the key of a symbol."""
    parts = combo.split("+")
    keys = []
    for modifier in parts[:-1]:
        if modifier not in MODIFIERS:
            raise ToolError(t("capture", "bad_key", key=combo))
        keys.append(MODIFIERS[modifier])
    key = parts[-1]
    if key in VK:
        keys.append(VK[key])
    elif len(key) == 1 and (key.isalpha() or key.isdigit()) and key.isascii():
        keys.append(ord(key.upper()))
    elif len(key) == 1 and scan is not None and scan(key) >= 0:
        keys.append(scan(key) & 0xFF)
    else:
        raise ToolError(t("capture", "bad_key", key=combo))
    return keys


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_size_t)]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT), ("hi", _HARDWAREINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


class _GUITHREADINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD), ("hwndActive", wintypes.HWND),
                ("hwndFocus", wintypes.HWND), ("hwndCapture", wintypes.HWND), ("hwndMenuOwner", wintypes.HWND),
                ("hwndMoveSize", wintypes.HWND), ("hwndCaret", wintypes.HWND), ("rcCaret", wintypes.RECT)]


MOUSE = {("left", True): 0x0002, ("left", False): 0x0004, ("right", True): 0x0008, ("right", False): 0x0010}
KEYEVENTF_KEYUP, KEYEVENTF_UNICODE, MOUSEEVENTF_WHEEL, MOUSEEVENTF_HWHEEL = 0x0002, 0x0004, 0x0800, 0x1000


class _Win:
    """user32, dwmapi and kernel32, loaded once."""

    def __init__(self):
        if sys.platform != "win32":
            raise ToolError(t("capture", "desktop_unsupported", system=sys.platform))
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.dwm = ctypes.WinDLL("dwmapi")
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        try:  # coordinates in physical pixels on every screen
            self.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (AttributeError, OSError):
            self.user32.SetProcessDPIAware()
        self.user32.WindowFromPoint.argtypes = [wintypes.POINT]
        self.user32.WindowFromPoint.restype = wintypes.HWND
        self.user32.GetAncestor.restype = wintypes.HWND
        self.user32.GetWindow.restype = wintypes.HWND
        self.user32.VkKeyScanW.restype = ctypes.c_short

    def windows(self) -> list[dict]:
        """The visible top-level windows, front to back."""
        out = []
        proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def each(hwnd, _):
            if self.user32.IsWindowVisible(hwnd) and not self.user32.IsIconic(hwnd) and not self.cloaked(hwnd):
                out.append(self.describe(hwnd))
            return True

        self.user32.EnumWindows(proc(each), 0)
        return [w for w in out if w["bounds"][2] > 0 and w["bounds"][3] > 0]

    def cloaked(self, hwnd) -> bool:
        value = wintypes.DWORD()
        self.dwm.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(value), ctypes.sizeof(value))  # DWMWA_CLOAKED
        return bool(value.value)

    def describe(self, hwnd) -> dict:
        length = self.user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buffer, length + 1)
        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return {"id": int(hwnd), "pid": int(pid.value), "owner": self.program(pid.value), "title": buffer.value,
                "bounds": self.rect(hwnd)}

    def rect(self, hwnd) -> Bounds:
        rect = wintypes.RECT()
        if self.dwm.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect)) != 0:  # without the shadow
            self.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return float(rect.left), float(rect.top), float(rect.right - rect.left), float(rect.bottom - rect.top)

    def program(self, pid: int) -> str:
        handle = self.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ""
        try:
            size = wintypes.DWORD(1024)
            buffer = ctypes.create_unicode_buffer(size.value)
            if not self.kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                return ""
            name = buffer.value.replace("\\", "/").rsplit("/", 1)[-1]
            return name[:-4] if name.lower().endswith(".exe") else name
        finally:
            self.kernel32.CloseHandle(handle)

    def send(self, *inputs: _INPUT) -> None:
        array = (_INPUT * len(inputs))(*inputs)
        self.user32.SendInput(len(inputs), array, ctypes.sizeof(_INPUT))


_win: _Win | None = None


def win() -> _Win:
    global _win
    if _win is None:
        _win = _Win()
    return _win


def _mouse_input(flags: int, data: int = 0) -> _INPUT:
    return _INPUT(type=0, u=_INPUTUNION(mi=_MOUSEINPUT(0, 0, data & 0xFFFFFFFF, flags, 0, 0)))


def _key_input(vk: int = 0, scan: int = 0, flags: int = 0) -> _INPUT:
    return _INPUT(type=1, u=_INPUTUNION(ki=_KEYBDINPUT(vk, scan, flags, 0, 0)))


class WindowsBackend(WindowBackend):
    """One window of a program of Windows. Coordinates are physical pixels inside the window."""

    def find(self, name: str) -> dict:
        every = win().windows()
        found = [w for w in every if w["bounds"][2] > 40 and w["bounds"][3] > 40 and matches(w, name)]
        return one_program(found, name, every)

    def bounds(self) -> Bounds:
        w = win()
        if not w.user32.IsWindow(self.window["id"]):
            raise ToolError(t("capture", "window_gone", name=self.name))
        self.window["bounds"] = w.rect(self.window["id"])
        return self.window["bounds"]

    def front(self) -> None:
        w, hwnd = win(), self.window["id"]
        if w.user32.IsIconic(hwnd):
            w.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        if w.user32.GetForegroundWindow() != hwnd:
            w.send(_key_input(0x12), _key_input(0x12, flags=KEYEVENTF_KEYUP))  # an Alt lets a program bring another forward
            w.user32.SetForegroundWindow(hwnd)
            time.sleep(0.15)

    def owner_at(self, x, y):
        w = win()
        hwnd = w.user32.WindowFromPoint(wintypes.POINT(int(x), int(y)))
        if not hwnd:
            return None
        root = w.user32.GetAncestor(hwnd, 2) or hwnd  # GA_ROOT
        found = w.describe(root)
        return found["pid"], found["owner"]

    def grab(self, area: Bounds) -> Image.Image:
        from PIL import ImageGrab

        w = win()
        left, top = w.user32.GetSystemMetrics(76), w.user32.GetSystemMetrics(77)  # the origin of the virtual screen
        screen = ImageGrab.grab(all_screens=True)
        x, y, width, height = area
        return screen.crop((int(x - left), int(y - top), int(x - left + width), int(y - top + height)))

    def others_above(self) -> list[Bounds]:
        w, above = win(), []
        hwnd = w.user32.GetWindow(self.window["id"], 3)  # GW_HWNDPREV: the windows in front of it
        while hwnd:
            if w.user32.IsWindowVisible(hwnd) and not w.user32.IsIconic(hwnd) and not w.cloaked(hwnd):
                found = w.describe(hwnd)
                if found["pid"] != self.window["pid"] and found["bounds"][2] > 0:
                    above.append(found["bounds"])
            hwnd = w.user32.GetWindow(hwnd, 3)
        return above

    def mouse_move(self, x, y) -> None:
        win().user32.SetCursorPos(int(x), int(y))

    def mouse_button(self, button, down, x, y, clicks=1) -> None:
        win().user32.SetCursorPos(int(x), int(y))
        win().send(_mouse_input(MOUSE[(button, down)]))

    def wheel(self, x, y, dx, dy) -> None:
        if dy:
            win().send(_mouse_input(MOUSEEVENTF_WHEEL, int(-dy)))  # positive goes up there
        if dx:
            win().send(_mouse_input(MOUSEEVENTF_HWHEEL, int(dx)))

    def type_text(self, text, delay_ms) -> None:
        units = text.encode("utf-16-le")
        for i in range(0, len(units), 2):
            code = int.from_bytes(units[i:i + 2], "little")
            win().send(_key_input(scan=code, flags=KEYEVENTF_UNICODE),
                       _key_input(scan=code, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
            time.sleep(delay_ms / 1000)

    def press(self, combo) -> None:
        keys = virtual_keys(combo, lambda ch: win().user32.VkKeyScanW(ord(ch)))
        win().send(*[_key_input(vk) for vk in keys], *[_key_input(vk, flags=KEYEVENTF_KEYUP) for vk in reversed(keys)])

    def focused_secret(self) -> bool | None:
        w = win()
        thread = w.user32.GetWindowThreadProcessId(self.window["id"], None)
        info = _GUITHREADINFO(cbSize=ctypes.sizeof(_GUITHREADINFO))
        if not w.user32.GetGUIThreadInfo(thread, ctypes.byref(info)) or not info.hwndFocus:
            return None
        name = ctypes.create_unicode_buffer(64)
        w.user32.GetClassNameW(info.hwndFocus, name, 64)
        if name.value.lower() not in ("edit", "richedit20w", "richedit50w"):
            return None
        return bool(w.user32.GetWindowLongW(info.hwndFocus, -16) & 0x20)  # GWL_STYLE, ES_PASSWORD

    def record_args(self, area: Bounds) -> tuple[list[str], str]:
        x, y, width, height = area
        return ["-f", "gdigrab", "-framerate", "30", "-draw_mouse", "1", "-offset_x", str(int(x)), "-offset_y", str(int(y)),
                "-video_size", f"{int(width) // 2 * 2}x{int(height) // 2 * 2}", "-i", "desktop"], ""
