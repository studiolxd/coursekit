"""Terminal mode of `coursekit capture`: a shell in a pseudo-terminal of its own, driven by the agent and recorded as it goes.

No window of the person is touched: coursekit starts the shell of a stage (`capture_stage`) in a `pty`, writes what the agent
types and reads what comes out. A terminal emulator in the process (`pyte`) keeps the screen from that output: the agent reads
its text (`read_screen`) or sees it drawn (`screenshot`, with Pillow and a monospaced font of the system). Drawing the real
output of the real program is what any terminal does: nothing of the interface is invented.

Every piece of output is covered before it reaches the emulator: the personal data of `capture.yaml › redact` and, also, the
user, the home folder, the name of the machine and the values of the variables that look like secrets are replaced in the
text (never inside the escape sequences). So what the model sees, the images, the `.cast` and the video are covered; the
original is not kept. When it ends, the screen of every moment is read again and what still looks like personal data goes to
the review as a warning.

The whole session is one recording (asciicast v2, what asciinema writes and its player reads). When it ends it is cut to the
stretches between `record_start` and `record_stop` (what came before is played at once, so the screen starts as it was), the
pauses of the model are shortened to `terminal.idle_limit`, and it becomes `media/recordings/<id>.cast`, the video
`<id>.mp4` drawn frame by frame with its `<id>.events.json` (the places the narration names, for the zooms), or both.
"""

from __future__ import annotations

import codecs
import hashlib
import io
import itertools
import json
import os
import re
import select
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from coursekit.i18n import t
from coursekit.mcpserver import ToolError

# an escape sequence: CSI, OSC (ended by BEL or ST), DCS/SOS/PM/APC (ended by ST), or a two-character one
ESCAPE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[PX^_][^\x1b]*\x1b\\|(?![\[\]PX^_])[ -/]*[0-~])")
SECRET_PROMPT = re.compile(r"pass(word|phrase|code)|contrase(ñ|n)a|token|secret|clave", re.I)
SECRET_NAME = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL", re.I)
KEYS = {"enter": "\r", "return": "\r", "tab": "\t", "escape": "\x1b", "esc": "\x1b", "backspace": "\x7f", "space": " ",
        "up": "\x1b[A", "down": "\x1b[B", "right": "\x1b[C", "left": "\x1b[D", "home": "\x1b[H", "end": "\x1b[F",
        "pageup": "\x1b[5~", "pagedown": "\x1b[6~", "delete": "\x1b[3~", "insert": "\x1b[2~",
        "arrowup": "\x1b[A", "arrowdown": "\x1b[B", "arrowright": "\x1b[C", "arrowleft": "\x1b[D",
        **{f"f{n}": code for n, code in zip(range(1, 13), ("\x1bOP", "\x1bOQ", "\x1bOR", "\x1bOS", "\x1b[15~", "\x1b[17~",
                                                              "\x1b[18~", "\x1b[19~", "\x1b[20~", "\x1b[21~", "\x1b[23~",
                                                              "\x1b[24~"), strict=True)}}
ANSI = ("black", "red", "green", "brown", "blue", "magenta", "cyan", "white")  # the names pyte gives the 8 colors
# the block elements (U+2580–U+259F), drawn as rectangles of the cell (left, top, right, bottom, as fractions) so the logos and
# the bars of a TUI have no seams between cells; the shades are the whole cell at a share of the color
_Q = {"ul": (0, 0, .5, .5), "ur": (.5, 0, 1, .5), "ll": (0, .5, .5, 1), "lr": (.5, .5, 1, 1)}
BLOCKS = {"\u2580": [(0, 0, 1, .5)], "\u2584": [(0, .5, 1, 1)], "\u2588": [(0, 0, 1, 1)], "\u258c": [(0, 0, .5, 1)],
          "\u2590": [(.5, 0, 1, 1)], "\u2594": [(0, 0, 1, .125)], "\u2595": [(.875, 0, 1, 1)],
          **{chr(0x2580 + n): [(0, 1 - n / 8, 1, 1)] for n in range(1, 8)},
          **{chr(0x2588 + n): [(0, 0, (8 - n) / 8, 1)] for n in range(1, 8)},
          **{ch: [_Q[q] for q in quads.split()] for ch, quads in (
              ("\u2596", "ll"), ("\u2597", "lr"), ("\u2598", "ul"), ("\u2599", "ul ll lr"), ("\u259a", "ul lr"),
              ("\u259b", "ul ur ll"), ("\u259c", "ul ur lr"), ("\u259d", "ur"), ("\u259e", "ur ll"), ("\u259f", "ur ll lr"))}}
BLOCKS |= {"\u2502": [(.4375, 0, .5625, 1)], "\u2503": [(.375, 0, .625, 1)], "\u2579": [(.375, 0, .625, .5)],
           "\u257b": [(.375, .5, .625, 1)], "\u2500": [(0, .47, 1, .53)], "\u2501": [(0, .44, 1, .56)]}  # straight lines
SHADES = {"\u2591": .25, "\u2592": .5, "\u2593": .75}
FONTS = ("/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/SFNSMono.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
         "/usr/share/fonts/TTF/DejaVuSansMono.ttf", "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf")
FALLBACK_FONTS = ("/System/Library/Fonts/Apple Symbols.ttf", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/noto/NotoSansSymbols2-Regular.ttf")


def supported() -> bool:
    """The terminal mode needs a pseudo-terminal (macOS and Linux)."""
    return os.name == "posix"


def emulator_available() -> bool:
    try:
        import pyte  # noqa: F401
    except ImportError:
        return False
    return True


def key_bytes(combo: str) -> str:
    """What a key or a combination sends to the terminal: `Enter`, `ctrl+c`, `shift+tab`, `alt+b`, `F2`…"""
    parts = [p.strip().lower() for p in str(combo).replace(" ", "").split("+") if p.strip()]
    if not parts:
        raise ToolError(t("capture", "terminal_bad_key", key=combo))
    *mods, name = parts
    mods = {"control" if m in ("ctrl", "control") else "alt" if m in ("alt", "option", "meta") else m for m in mods}
    if name == "tab" and "shift" in mods:
        return "\x1b[Z"
    if name in KEYS:
        base = KEYS[name]
    elif len(name) == 1:
        base = name.upper() if "shift" in mods else name
    else:
        raise ToolError(t("capture", "terminal_bad_key", key=combo))
    if "control" in mods:
        if len(base) != 1 or not ("@" <= base.upper() <= "_" or base == "?"):
            raise ToolError(t("capture", "terminal_bad_key", key=combo))
        base = "\x7f" if base == "?" else chr(ord(base.upper()) & 0x1F)
    if "alt" in mods:
        base = "\x1b" + base
    return base


def cover_text(text: str, cover) -> str:
    """The output with its personal data replaced in the text only: the escape sequences go through as they are."""
    out, last = [], 0
    for match in ESCAPE.finditer(text):
        if match.start() > last:
            out.append(cover(text[last:match.start()]))
        out.append(match.group(0))
        last = match.end()
    if last < len(text):
        out.append(cover(text[last:]))
    return "".join(out)


def safe_cut(text: str) -> int:
    """Where the output can be cut without leaving an escape sequence or a word in two (the rest waits for more output)."""
    escape = text.rfind("\x1b")
    if escape != -1 and not ESCAPE.match(text, escape):
        return escape  # an escape sequence still coming
    cut = max(text.rfind(c) for c in " \n\r\t\x1b\x07")
    if cut == -1:
        return 0 if len(text) < 256 else len(text)
    if text[cut] == "\x1b":
        match = ESCAPE.match(text, cut)
        return match.end() if match else cut
    return cut + 1


def secret_terms(env: dict[str, str]) -> list[str]:
    """What is always hidden in a terminal of this machine: who and where (user, home, machine) and the secret values."""
    import getpass
    import socket

    terms = [str(Path.home()), getpass.getuser(), socket.gethostname().split(".")[0]]
    for key in ("user.name", "user.email"):
        done = subprocess.run(["git", "config", "--global", key], capture_output=True, text=True, check=False)
        terms.append(done.stdout.strip())
    terms += [value for name, value in env.items() if SECRET_NAME.search(name) and len(value) >= 6]
    return sorted({term for term in terms if len(term.strip()) >= 3}, key=len, reverse=True)


# ── the terminal ─────────────────────────────────────────────────────────────────────────────

class Terminal:
    """A program in a pseudo-terminal: its screen, kept by an emulator, and its output with the time it came out."""

    def __init__(self, argv: list[str], cwd: Path, env: dict[str, str], cols: int, rows: int, cover=lambda text: text):
        import fcntl
        import pty
        import struct
        import termios

        import pyte

        self.cols, self.rows, self.cover = cols, rows, cover
        self.screen = pyte.Screen(cols, rows)
        self.stream = pyte.Stream(self.screen)
        self.lock = threading.Lock()
        self.events: list[tuple[float, str]] = []  # (seconds from the start, covered output)
        self.marks: list[tuple[float, dict]] = []  # record start/stop, points, chapters
        self.typed: list[float] = []  # when something was sent: the output right after it is its echo, never sped up
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self._held = ""
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        self.master = master
        self.started = time.monotonic()
        try:
            self.process = subprocess.Popen(argv, stdin=slave, stdout=slave, stderr=slave, cwd=str(cwd), env=env,
                                            start_new_session=True, close_fds=True)
        except OSError as exc:
            os.close(master)
            raise ToolError(t("capture", "terminal_failed", reason=str(exc))) from None
        finally:
            os.close(slave)
        self._stop = threading.Event()
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()

    def now(self) -> float:
        return time.monotonic() - self.started

    def _read(self) -> None:
        while not self._stop.is_set():
            ready, _, _ = select.select([self.master], [], [], 0.05)
            if not ready:
                self._flush(everything=True)
                continue
            try:
                data = os.read(self.master, 65536)
            except OSError:
                data = b""
            if not data:
                self._flush(everything=True)
                break
            self._held += self._decoder.decode(data)
            self._flush()

    def _flush(self, everything: bool = False) -> None:
        if not self._held:
            return
        cut = len(self._held) if everything else safe_cut(self._held)
        if cut <= 0:
            return
        text, self._held = self._held[:cut], self._held[cut:]
        covered = cover_text(text, self.cover)
        with self.lock:
            self.stream.feed(covered)
            self.events.append((round(self.now(), 4), covered))

    def send(self, data: str) -> None:
        if self.process.poll() is not None:
            raise ToolError(t("capture", "terminal_ended"))
        self.typed.append(self.now())
        os.write(self.master, data.encode("utf-8"))

    def type(self, text: str, delay_ms: int) -> None:
        for ch in text:
            self.send(ch)
            time.sleep(max(0, delay_ms) / 1000)

    def mark(self, kind: str, **data) -> None:
        self.marks.append((round(self.now(), 4), {"kind": kind, **data}))

    def lines(self) -> list[str]:
        with self.lock:
            return list(self.screen.display)

    def text(self) -> str:
        return "\n".join(line.rstrip() for line in self.lines()).rstrip("\n")

    def cursor_line(self) -> str:
        with self.lock:
            return self.screen.display[self.screen.cursor.y]

    def snapshot(self) -> Snapshot:
        with self.lock:
            return Snapshot.of(self.screen)

    def wait_for(self, text: str, timeout_ms: int) -> bool:
        end = time.monotonic() + max(0, timeout_ms) / 1000
        while True:
            if text in self.text():
                return True
            if time.monotonic() >= end or self.process.poll() is not None:
                return text in self.text()
            time.sleep(0.1)

    def close(self) -> None:
        if self.process.poll() is None:
            for sig in (signal.SIGHUP, signal.SIGKILL):
                try:
                    os.killpg(self.process.pid, sig)
                except (ProcessLookupError, PermissionError):
                    break
                try:
                    self.process.wait(timeout=2)
                    break
                except subprocess.TimeoutExpired:
                    continue
        self._stop.set()
        self._reader.join(timeout=2)
        self._flush(everything=True)
        try:
            os.close(self.master)
        except OSError:
            pass


@dataclass
class Snapshot:
    """The screen at one moment: each cell as (character, foreground, background, bold, reverse), and the cursor."""

    cells: list[list[tuple]]
    cursor: tuple[int, int] | None

    @classmethod
    def of(cls, screen) -> Snapshot:
        rows = []
        for y in range(screen.lines):
            line = screen.buffer[y]
            rows.append([(c.data, c.fg, c.bg, c.bold, c.reverse) for c in (line[x] for x in range(screen.columns))])
        cursor = None if screen.cursor.hidden else (screen.cursor.x, screen.cursor.y)
        return cls(rows, cursor)

    def key(self) -> str:
        return hashlib.sha256(repr((self.cells, self.cursor)).encode("utf-8")).hexdigest()


# ── drawing it ───────────────────────────────────────────────────────────────────────────────

def find_font(configured: str = "") -> str | None:
    """The monospaced font the screen is drawn with: the one of `terminal.font`, else the first of the system found."""
    for path in ([configured] if configured else []) + list(FONTS):
        if path and Path(path).expanduser().is_file():
            return str(Path(path).expanduser())
    if sys.platform.startswith("linux"):
        done = subprocess.run(["fc-match", "-f", "%{file}", "monospace"], capture_output=True, text=True, check=False) \
            if _which("fc-match") else None
        if done and done.stdout.strip() and Path(done.stdout.strip()).is_file():
            return done.stdout.strip()
    return None


def _which(name: str) -> bool:
    import shutil

    return shutil.which(name) is not None


class Painter:
    """Draws a snapshot of the screen as an image, with the palette of `capture.yaml › terminal`."""

    def __init__(self, cols: int, rows: int, width: int, font_path: str, palette: dict):
        self.cols, self.rows = cols, rows
        self.pad = max(8, width // 80)
        probe = ImageFont.truetype(font_path, 100)
        ratio = probe.getlength("M") / 100
        size = max(8, int((width - 2 * self.pad) / cols / ratio))
        self.font = ImageFont.truetype(font_path, size)
        try:
            self.bold = ImageFont.truetype(font_path, size, index=1) if font_path.endswith(".ttc") else self.font
        except OSError:
            self.bold = self.font
        self.fallbacks = [ImageFont.truetype(p, size) for p in FALLBACK_FONTS if Path(p).is_file()]
        self.cell_w = self.font.getlength("M")
        ascent, descent = self.font.getmetrics()
        self.cell_h = ascent + descent
        content = (round(2 * self.pad + cols * self.cell_w), round(2 * self.pad + rows * self.cell_h))
        # a frame of 16:9 (the one of a video), the screen in its middle on its own background: no bands when it is shown
        self.size = (max(content[0], round(content[1] * 16 / 9)), max(content[1], round(content[0] * 9 / 16)))
        self.offset = ((self.size[0] - content[0]) / 2 + self.pad, (self.size[1] - content[1]) / 2 + self.pad)
        self.background = _rgb(palette.get("background"), (255, 255, 255))
        self.foreground = _rgb(palette.get("foreground"), (0, 0, 0))
        colors = list(palette.get("ansi") or [])
        self.ansi = {name: _rgb(colors[i] if i < len(colors) else None, (0, 0, 0)) for i, name in enumerate(ANSI)}
        self.ansi |= {f"bright{name}": _rgb(colors[i + 8] if i + 8 < len(colors) else None, self.ansi[name])
                      for i, name in enumerate(ANSI)}
        self._glyphs: dict[str, ImageFont.FreeTypeFont] = {}

    def color(self, value: str, default: tuple[int, int, int]) -> tuple[int, int, int]:
        if value == "default":
            return default
        if value in self.ansi:
            return self.ansi[value]
        return _rgb(value, default)

    def _ink(self, font, ch: str) -> bytes:
        image = Image.new("L", (round(self.cell_w * 2), self.cell_h))
        ImageDraw.Draw(image).text((0, 0), ch, font=font, fill=255)
        return image.tobytes()

    def _has(self, font, ch: str) -> bool:
        """Whether the font draws the character (and not the box of a missing one)."""
        return self._ink(font, ch) != self._ink(font, "\U0010fffd")

    def _font_for(self, ch: str, bold: bool):
        font = self.bold if bold else self.font
        if ch.isascii():
            return font
        if ch not in self._glyphs:
            self._glyphs[ch] = font if self._has(font, ch) else next((f for f in self.fallbacks if self._has(f, ch)), font)
        return self._glyphs[ch]

    def cell_box(self, x: int, y: int) -> tuple[float, float, float, float]:
        left, top = self.offset[0] + x * self.cell_w, self.offset[1] + y * self.cell_h
        return left, top, left + self.cell_w, top + self.cell_h

    def paint(self, shot: Snapshot) -> Image.Image:
        from collections import Counter

        styled = [[self._colors(cell, shot.cursor == (x, y)) for x, cell in enumerate(row)] for y, row in enumerate(shot.cells)]
        ground = Counter(back for row in styled for _, back in row).most_common(1)  # what the program paints the screen with
        base = ground[0][0] if ground else self.background
        image = Image.new("RGB", self.size, base)
        draw = ImageDraw.Draw(image)
        for y, row in enumerate(shot.cells):
            for x, (ch, *_style) in enumerate(row):
                front, back = styled[y][x]
                left, top, right, bottom = self.cell_box(x, y)
                if back != base:
                    wide = x + 1 < len(row) and row[x + 1][0] == ""
                    draw.rectangle((left, top, right + (self.cell_w if wide else 0), bottom), fill=back)
                if ch in BLOCKS:
                    for a, b, c, d in BLOCKS[ch]:
                        draw.rectangle((left + a * self.cell_w, top + b * self.cell_h, left + c * self.cell_w - 1,
                                        top + d * self.cell_h - 1), fill=front)
                elif ch in SHADES:
                    share = SHADES[ch]
                    draw.rectangle((left, top, right - 1, bottom - 1),
                                   fill=tuple(round(f * share + k * (1 - share)) for f, k in zip(front, back, strict=True)))
                elif ch and ch != " ":
                    draw.text((left, top), ch, font=self._font_for(ch, _style[2]), fill=front)
        return image

    def _colors(self, cell: tuple, cursor: bool) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        _, fg, bg, _, reverse = cell
        front, back = self.color(fg, self.foreground), self.color(bg, self.background)
        if reverse != cursor:  # the cursor is drawn as the cell reversed
            front, back = back, front
        return front, back

    def png(self, shot: Snapshot) -> bytes:
        out = io.BytesIO()
        self.paint(shot).save(out, "PNG")
        return out.getvalue()


def _rgb(value, default: tuple[int, int, int]) -> tuple[int, int, int]:
    text = str(value or "").lstrip("#")
    if re.fullmatch(r"[0-9a-fA-F]{6}", text):
        return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
    return default


# ── the recording ────────────────────────────────────────────────────────────────────────────

@dataclass
class Cut:
    """The recording cut and shortened: its output, its points (with the new times) and how long it lasts."""

    events: list[tuple[float, str]]
    points: list[tuple[float, dict]] = field(default_factory=list)
    duration: float = 0.0


def stretches(marks: list[tuple[float, dict]], end: float) -> list[tuple[float, float]]:
    """The recorded stretches (between record start and stop); the whole session when there are none."""
    out, start = [], None
    for at, mark in marks:
        if mark["kind"] == "record" and mark.get("on") and start is None:
            start = at
        elif mark["kind"] == "record" and not mark.get("on") and start is not None:
            out.append((start, at))
            start = None
    if start is not None:
        out.append((start, end))
    return out or [(0.0, end)]


def hurry(events: list[tuple[float, str]], marks: list[tuple[float, dict]], typed: list[float], end: float, cols: int, rows: int,
          limit: float, cells: int) -> tuple[list[tuple[float, str]], list[tuple[float, dict]], float]:
    """The waits of a program sped up, never cut: a stretch where only a few cells change (a spinner, a counter, the dots of a
    model thinking) and nothing was typed plays in `limit` seconds at most, every frame of it kept, faster. Returns the
    output, the marks and the end on the new times."""
    import bisect

    import pyte

    if limit <= 0 or not events:
        return events, marks, end
    screen = pyte.Screen(cols, rows)
    stream = pyte.Stream(screen)
    before = list(screen.display)
    minor = []
    for at, data in events:
        stream.feed(data)
        now = list(screen.display)
        # a wide character (an emoji, a CJK letter) fills two cells and one character: lines of different lengths
        changed = sum(1 for a, b in zip(before, now, strict=True) for x, y in itertools.zip_longest(a, b) if x != y)
        k = bisect.bisect_right(typed, at)
        echo = k > 0 and at - typed[k - 1] <= 0.3  # the program writes back what was typed
        minor.append(changed <= cells and not echo)
        before = now
    waits, i = [], 0
    while i < len(events):
        if not minor[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(events) and minor[j + 1]:
            j += 1
        start, stop = events[i][0], events[j + 1][0] if j + 1 < len(events) else end  # until something real happens
        if stop - start > limit:
            waits.append((start, stop))
        i = j + 1

    def moved(t: float) -> float:
        gained = 0.0
        for start, stop in waits:
            if t >= stop:
                gained += (stop - start) - limit
            elif t > start:
                return round(start - gained + (t - start) * limit / (stop - start), 4)
            else:
                break
        return round(t - gained, 4)

    return [(moved(at), data) for at, data in events], [(moved(at), mark) for at, mark in marks], moved(end)


def cut(events: list[tuple[float, str]], marks: list[tuple[float, dict]], end: float, idle_limit: float) -> Cut:
    """Keeps the recorded stretches: what came before the first one is played at once, what came between two is joined,
    what came after the last one is left out, and every pause longer than `idle_limit` is shortened to it."""
    kept = stretches(marks, end)
    items = sorted([(at, 0, data) for at, data in events] + [(at, 1, mark) for at, mark in marks if mark["kind"] in ("point", "chapter")],
                   key=lambda item: (item[0], item[1]))
    out, points, new, last, index = [], [], 0.0, None, 0
    for at, kind, data in items:
        while index < len(kept) and at > kept[index][1]:
            if last is not None:
                new += min(idle_limit, kept[index][1] - last)  # the end of the stretch holds a moment
            last, index = None, index + 1
        if index >= len(kept):
            break
        start, _ = kept[index]
        if at >= start:
            previous = start if last is None else last
            new += min(idle_limit, max(0.0, at - previous))
            last = at
        (out if kind == 0 else points).append((round(new, 4), data))
    if index < len(kept) and last is not None:
        new += min(idle_limit, max(0.0, kept[index][1] - last))
    return Cut(out, points, round(max(new, 0.0), 4))


def cast_text(recording: Cut, cols: int, rows: int, palette: dict, title: str = "") -> str:
    """The recording as an asciicast v2 file (what asciinema writes and its player reads), with the palette it was drawn with."""
    header = {"version": 2, "width": cols, "height": rows, "timestamp": int(time.time()),
              "env": {"TERM": "xterm-256color", "SHELL": "/bin/bash"}}
    if palette.get("ansi"):
        header["theme"] = {"fg": palette.get("foreground"), "bg": palette.get("background"),
                           "palette": ":".join(palette["ansi"][:16])}
    if title:
        header["title"] = title
    lines = [json.dumps(header, ensure_ascii=False)]
    chapters = [(at, 1, mark["label"]) for at, mark in recording.points if mark.get("kind") == "chapter"]
    lines += [json.dumps([at, "m" if kind else "o", data], ensure_ascii=False)  # "m": a marker, where the player can pause
              for at, kind, data in sorted([(at, 0, data) for at, data in recording.events] + chapters, key=lambda e: (e[0], e[1]))]
    if recording.events and recording.duration > recording.events[-1][0]:
        lines.append(json.dumps([recording.duration, "o", ""]))  # the last screen holds until the end
    return "\n".join(lines) + "\n"


def frames(recording: Cut, cols: int, rows: int, painter: Painter, fps: int) -> list[tuple[float, bytes]]:
    """The recording drawn: a frame each time the screen changes (at most `fps` a second), and the empty last one (its end)."""
    import pyte

    screen = pyte.Screen(cols, rows)
    stream = pyte.Stream(screen)
    out: list[tuple[float, bytes]] = []
    seen = None
    slots: dict[int, list[str]] = {}
    for at, data in recording.events:
        slots.setdefault(int(at * fps), []).append(data)
    for slot in sorted(slots):
        for data in slots[slot]:
            stream.feed(data)
        shot = Snapshot.of(screen)
        key = shot.key()
        if key != seen:
            out.append((slot / fps, painter.png(shot)))
            seen = key
    if not out:
        out.append((0.0, painter.png(Snapshot.of(screen))))
    out.append((max(recording.duration, out[-1][0] + 1 / fps), b""))
    return out


def screens(recording: Cut, cols: int, rows: int, every: float) -> list[tuple[float, Snapshot, list[str]]]:
    """The screen every `every` seconds of the recording (and at its end): to read it again and to sample the review."""
    import pyte

    screen = pyte.Screen(cols, rows)
    stream = pyte.Stream(screen)
    out, next_at = [], 0.0
    for at, data in recording.events:
        while at > next_at:
            out.append((next_at, Snapshot.of(screen), list(screen.display)))
            next_at += every
        stream.feed(data)
    out.append((recording.duration, Snapshot.of(screen), list(screen.display)))
    return out


# ── the backend of a capture session ─────────────────────────────────────────────────────────

class TerminalBackend:
    """What a capture session drives in terminal mode: the shell of the stage, its screen drawn by the painter."""

    def __init__(self, workspace, cols: int, rows: int, painter: Painter, type_delay_ms: int, cover):
        self.workspace, self.painter, self.type_delay_ms = workspace, painter, type_delay_ms
        self.viewport = painter.size
        self.term = Terminal(workspace.argv, workspace.folder, workspace.env, cols, rows, cover)
        self.term.wait_for("$", 3000)  # the prompt

    def screenshot(self) -> bytes:
        return self.painter.png(self.term.snapshot())

    def screen_text(self) -> str:
        return self.term.text()

    def _no_pointer(self, *args) -> None:
        raise ToolError(t("capture", "terminal_no_pointer"))

    click = move = drag = scroll = _no_pointer

    def type(self, text: str) -> None:
        self.term.type(text, self.type_delay_ms)
        time.sleep(0.15)

    def key(self, combo: str) -> None:
        self.term.send(key_bytes(combo))
        time.sleep(0.25)

    def wait(self, ms: int) -> None:
        time.sleep(max(0, ms) / 1000)

    def wait_for(self, text: str, timeout_ms: int) -> bool:
        return self.term.wait_for(text, timeout_ms)

    def navigate(self, url: str) -> None:
        raise ToolError(t("capture", "terminal_no_navigate"))

    def cell_at(self, x: float, y: float) -> tuple[int, int]:
        col = int((x - self.painter.offset[0]) // self.painter.cell_w)
        row = int((y - self.painter.offset[1]) // self.painter.cell_h)
        return max(0, min(self.term.cols - 1, col)), max(0, min(self.term.rows - 1, row))

    def target_at(self, x: float, y: float) -> dict:
        col, row = self.cell_at(x, y)
        line = self.term.lines()[row]
        words = [m for m in re.finditer(r"\S+", line) if m.start() <= col < m.end()]
        return {"cell": [row, col], **({"text": words[0].group(0)[:80]} if words else {})}

    def find_box(self, text: str, until: str = "") -> tuple[float, float, float, float, str] | None:
        """The box of the first place the text is on screen (in the pixels of the screenshot) or, with `until`, of the lines from
        it to the first one after it that has `until` (from the first letter of any of them to the last), and the tone of its
        background: `dark` or `light`."""
        lines = self.term.lines()
        start = next(((row, line.find(text)) for row, line in enumerate(lines) if text and text in line), None)
        if start is None:
            return None
        row, col = start
        cells = [(row, col, col + len(text))]
        if until:
            end = next((r for r in range(row, len(lines)) if until in lines[r]), None)
            if end is None:
                return None
            cells = [(r, len(lines[r]) - len(lines[r].lstrip()), len(lines[r].rstrip())) for r in range(row, end + 1)
                     if lines[r].strip()]
        left, top, _, _ = self.painter.cell_box(min(c[1] for c in cells), cells[0][0])
        _, _, right, bottom = self.painter.cell_box(max(c[2] for c in cells) - 1, cells[-1][0])
        shot = self.term.snapshot()
        grounds = [self.painter._colors(shot.cells[r][c], False)[1] for r, a, b in cells for c in range(a, b)]
        light = sum(0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in grounds) / max(1, len(grounds))
        return left, top, right, bottom, "dark" if light < 128 else "light"

    def mark(self, kind: str, **data) -> None:
        self.term.mark(kind, **data)

    def focused_is_secret(self) -> bool:
        return bool(SECRET_PROMPT.search(self.term.cursor_line()))

    def url(self) -> str:
        return ""

    def close(self) -> None:
        self.term.close()


def finish(backend: TerminalBackend, asset_id: str, recipe: str, recordings: Path, review: Path, cfg: dict, rules: dict,
           who, terms: list[str], part: str = "") -> dict:
    """The end of a terminal session: the recording cut and written as the resource needs it (`.cast` for a terminal demo,
    `.mp4` and its events for a video), the review sampled, and what still looks like personal data, as warnings."""
    from coursekit import pii

    backend.close()
    term, painter = backend.term, backend.painter
    terminal = dict(cfg.get("terminal") or {})
    events, marks, end = hurry(term.events, term.marks, term.typed, term.now(), term.cols, term.rows,
                               float(terminal.get("busy_limit") or 0), int(terminal.get("busy_cells") or 0))
    recording = cut(events, marks, end, float(terminal.get("idle_limit") or 2))
    out: dict = {"file": None, "warnings": [], "frames": 0}
    every = max(1.0, recording.duration / 40)
    review.mkdir(parents=True, exist_ok=True)
    leftovers: set[str] = set()
    for n, (at, shot, lines) in enumerate(screens(recording, term.cols, term.rows, every)):
        for line in lines:
            for finding in pii.find(line, {**rules, "names": False}, who, terms):
                leftovers.add(f"{finding.kind} ({at:.0f} s)")
        if recipe in ("asciinema", "screen-recording"):
            painter.paint(shot).save(review / f"t{part + '-' if part else ''}{n:04d}.00.png")
            out["frames"] += 1
    out["warnings"] += [t("capture", "terminal_leftover", where=item) for item in sorted(leftovers)]
    recordings.mkdir(parents=True, exist_ok=True)
    if recipe == "asciinema":
        target = recordings / f"{asset_id}.cast"
        target.write_text(cast_text(recording, term.cols, term.rows, dict(terminal.get("palette") or {})), encoding="utf-8",
                          newline="\n")
        out["file"] = target
    elif recipe == "screen-recording":
        from coursekit import capture_replay

        fps = int((cfg.get("replay") or {}).get("fps") or 30)
        video = recordings / f"{asset_id}.mp4"
        try:
            capture_replay.encode(frames(recording, term.cols, term.rows, painter, fps), video, fps)
        except capture_replay.ReplayError as exc:
            raise ToolError(str(exc)) from None
        width, height = painter.size
        events = []
        for at, mark in recording.points:
            if mark.get("kind") != "point":
                continue
            event = {"t": at, "kind": "point", "fx": round(mark["x"] / width, 4), "fy": round(mark["y"] / height, 4)}
            if mark.get("label"):
                event["label"] = mark["label"]
            if mark.get("box"):  # the whole of what it shows: the zoom keeps it in the frame and marks it
                x, y, w, h = mark["box"]
                event.update(box=[round(x / width, 4), round(y / height, 4), round(w / width, 4), round(h / height, 4)],
                             shape=mark.get("shape") or "round", tone=mark.get("tone") or "light")
            events.append(event)
        data = {"video": video.name, "width": width, "height": height, "duration": recording.duration, "events": events}
        capture_replay.events_path(video).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                                                     newline="\n")
        out["file"] = video
    return out
