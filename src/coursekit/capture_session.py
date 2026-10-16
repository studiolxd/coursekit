"""A capture session: an agent drives a real application and coursekit captures it, with the personal data already replaced.

The MCP server of coursekit (`coursekit capture serve`) holds one session at a time. A session starts only for a resource
that shows an interface and has the permission of a person in force (`coursekit capture allow`); the permission is checked
again before every action, so taking it back (`revoke`) or letting it expire stops the agent.

Browser mode: the browser of the machine opens with the profile of the application (the session a person logged in with),
the page is cleaned before it is shown (`tools/capture-dom.js` asks `pii.replace` for every text on screen) and, with
`redact › pixel_check`, every screenshot is also read on the pixels and what is still there is covered. So whatever the
model sees, and the captures saved, never hold real data. Navigation outside `allow_domains` is blocked, typing into a
password or a one-time-code field is refused, and landing on the `login_url` of the profile ends the session (a person logs
in again: the agent never does).

Every action is written down: the targets of the clicks by role and name (not only by position), so `coursekit capture
replay` can repeat it. `session_end` writes the steps in the `capture` block of the brief (media/scripts/<id>.md), the
capture to media/recordings/<id>.png and leaves it waiting for a person (`coursekit capture review`, `approve`).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Protocol
from urllib.parse import urljoin, urlsplit

import yaml
from PIL import Image

from coursekit import capture as capturemod
from coursekit import course as coursemod
from coursekit import pii
from coursekit import redact as redactmod
from coursekit.i18n import t
from coursekit.mcpserver import ToolError

RECIPES = ("screenshot", "screen-recording")


class SessionGone(ToolError):
    """The permission was taken back or expired, or the session of the profile expired: the capture session ends."""
BLOCK_RE = re.compile(r"^```capture[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)


# ── the capture block of the brief ───────────────────────────────────────────────────────────

def brief_file(course: dict, asset_id: str) -> Path:
    return course["_dir"] / "media" / "scripts" / f"{asset_id}.md"


def read_block(course: dict, asset_id: str) -> dict:
    """The `capture` block of the brief of a resource ({} when there is none)."""
    path = brief_file(course, asset_id)
    match = BLOCK_RE.search(path.read_text(encoding="utf-8")) if path.exists() else None
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise ToolError(t("capture", "bad_block", path=path.name, error=str(exc).splitlines()[0])) from None
    return data if isinstance(data, dict) else {}


def write_block(course: dict, asset_id: str, block: dict) -> Path:
    """Writes the `capture` block of the brief, in place of the one it had (or at the end)."""
    path = brief_file(course, asset_id)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    body = yaml.safe_dump(block, allow_unicode=True, sort_keys=False, width=120)
    fenced = f"```capture\n{body}```\n"
    if BLOCK_RE.search(text):
        text = BLOCK_RE.sub(lambda _: fenced.rstrip("\n"), text, count=1)
    else:
        text = text.rstrip("\n") + ("\n\n" if text.strip() else "") + fenced
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


# ── what a backend does ──────────────────────────────────────────────────────────────────────

class Backend(Protocol):
    viewport: tuple[int, int]  # css pixels

    def screenshot(self) -> bytes: ...
    def click(self, x: float, y: float, button: str, count: int) -> None: ...
    def move(self, x: float, y: float) -> None: ...
    def drag(self, x1: float, y1: float, x2: float, y2: float) -> None: ...
    def scroll(self, x: float, y: float, dx: float, dy: float) -> None: ...
    def type(self, text: str) -> None: ...
    def key(self, combo: str) -> None: ...
    def wait(self, ms: int) -> None: ...
    def navigate(self, url: str) -> None: ...
    def target_at(self, x: float, y: float) -> dict: ...
    def focused_is_secret(self) -> bool: ...
    def url(self) -> str: ...
    def close(self) -> None: ...


def domain_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def normalize_key(combo: str) -> str:
    """`ctrl+shift+a` → `Control+Shift+A` (the names Playwright uses)."""
    names = {"ctrl": "Control", "control": "Control", "cmd": "Meta", "command": "Meta", "meta": "Meta", "alt": "Alt",
             "option": "Alt", "shift": "Shift", "enter": "Enter", "return": "Enter", "esc": "Escape", "escape": "Escape",
             "tab": "Tab", "space": "Space", "backspace": "Backspace", "delete": "Delete", "up": "ArrowUp",
             "down": "ArrowDown", "left": "ArrowLeft", "right": "ArrowRight", "pageup": "PageUp", "pagedown": "PageDown",
             "home": "Home", "end": "End"}
    parts = [p.strip() for p in str(combo).replace(" ", "").split("+") if p.strip()]
    return "+".join(names.get(p.lower(), p.upper() if len(p) == 1 else p[:1].upper() + p[1:]) for p in parts)


# ── the session ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Session:
    project: object
    course: dict
    asset_id: str
    grant: dict
    backend: Backend
    rules: dict
    max_edge: int
    start_url: str
    allow_domains: list[str]
    login_url: str = ""
    steps: list[dict] = field(default_factory=list)
    shots: list[Path] = field(default_factory=list)
    seen: dict[str, set[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    redactor: redactmod.Redactor | None = None
    started_at: str = ""
    server: object | None = None  # the local server of the package of the course, when it is what is recorded
    _scale: float = 1.0  # model pixels → css pixels

    # the agent sees the screen at most `max_edge` wide or tall: these are its coordinates
    def _to_css(self, x: float, y: float) -> tuple[float, float]:
        cx, cy = x * self._scale, y * self._scale
        w, h = self.backend.viewport
        if not (0 <= cx <= w and 0 <= cy <= h):
            raise ToolError(t("capture", "outside_screen", x=round(x), y=round(y)))
        return cx, cy

    def close(self) -> None:
        """Closes the browser (or the window) and the local server, if there is one."""
        try:
            if self.backend is not None:
                self.backend.close()
        finally:
            if self.server is not None:
                self.server.shutdown()
                self.server = None

    def check(self) -> None:
        """Before every action: the permission is still in force and the session of the profile has not expired."""
        grant = capturemod.active_grant(self.project, self.course["code"], self.asset_id)
        if grant is None:
            raise SessionGone(t("capture", "grant_gone", code=self.course["code"]))
        if self.login_url and self.backend.url().startswith(self.login_url):
            raise SessionGone(t("capture", "session_expired", name=self.grant.get("profile") or ""))

    def note_texts(self, texts: list[str], who: pii.People, terms: list[str]) -> list[str]:
        """What the page asks: each text with its personal data replaced (and the kinds found, counted once per value)."""
        out = []
        for text in texts:
            text = str(text or "")
            for finding in pii.find(text, self.rules, who, terms, strict=True):
                value = text[finding.start:finding.end]
                self.seen.setdefault(finding.kind, set()).add(hashlib.sha256(value.encode("utf-8")).hexdigest()[:16])
            out.append(pii.replace(text, self.rules, who, terms))
        return out

    def frame(self) -> Image.Image:
        """The screen as it is, cleaned, at full size (and covered on the pixels with `pixel_check`)."""
        image = Image.open(io.BytesIO(self.backend.screenshot()))
        image.load()
        if self.redactor is not None:
            boxes = self.redactor.boxes(image)
            if boxes:
                found = self.redactor.report.findings  # the most seen at once on one screen, kind by kind
                for kind, n in Counter(b.kind for b in boxes).items():
                    found[kind] = max(found[kind], n)
                image = redactmod.cover(image, boxes, self.redactor.style, self.redactor.margin)
        width = self.backend.viewport[0]
        fit = min(1.0, self.max_edge / max(image.size))
        self._scale = width / (image.width * fit)
        return image

    def _model_image(self, image: Image.Image) -> bytes:
        fit = min(1.0, self.max_edge / max(image.size))
        if fit < 1:
            image = image.resize((round(image.width * fit), round(image.height * fit)), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        image.convert("RGB").save(out, "PNG")
        return out.getvalue()

    def screenshot(self) -> bytes:
        self.check()
        return self._model_image(self.frame())

    def zoom(self, x: float, y: float, w: float, h: float) -> bytes:
        self.check()
        image = self.frame()
        factor = image.width / (self.backend.viewport[0] / self._scale)  # model pixels → image pixels
        box = (max(0, round(x * factor)), max(0, round(y * factor)), min(image.width, round((x + w) * factor)),
               min(image.height, round((y + h) * factor)))
        if box[2] <= box[0] or box[3] <= box[1]:
            raise ToolError(t("capture", "outside_screen", x=round(x), y=round(y)))
        part = image.crop(box)
        grow = min(4.0, self.max_edge / max(part.size))
        part = part.resize((max(1, round(part.width * grow)), max(1, round(part.height * grow))), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        part.convert("RGB").save(out, "PNG")
        return out.getvalue()

    def click(self, x: float, y: float, button: str = "left", count: int = 1) -> None:
        self.check()
        cx, cy = self._to_css(x, y)
        target = self.backend.target_at(cx, cy)
        self.backend.click(cx, cy, button, count)
        step = {"x": round(cx), "y": round(cy)}
        if target:
            step["target"] = target
        if button != "left":
            step["button"] = button
        if count != 1:
            step["count"] = count
        self.steps.append({"click": step})

    def point(self, x: float, y: float, note: str = "") -> None:
        """Marks a place of the screen without touching it: on replay it is written down, for a zoom of the video."""
        self.check()
        cx, cy = self._to_css(x, y)
        step = {"x": round(cx), "y": round(cy)}
        target = self.backend.target_at(cx, cy)
        if target:
            step["target"] = target
        if note.strip():
            step["note"] = note.strip()
        self.steps.append({"point": step})

    def move(self, x: float, y: float) -> None:
        self.check()
        cx, cy = self._to_css(x, y)
        self.backend.move(cx, cy)
        self.steps.append({"move": {"x": round(cx), "y": round(cy)}})

    def drag(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self.check()
        a, b = self._to_css(x1, y1), self._to_css(x2, y2)
        self.backend.drag(*a, *b)
        self.steps.append({"drag": {"from": [round(a[0]), round(a[1])], "to": [round(b[0]), round(b[1])]}})

    def scroll(self, x: float, y: float, dx: float, dy: float) -> None:
        self.check()
        cx, cy = self._to_css(x, y)
        self.backend.scroll(cx, cy, dx, dy)
        self.steps.append({"scroll": {"x": round(cx), "y": round(cy), "dx": round(dx), "dy": round(dy)}})

    def type(self, text: str) -> None:
        self.check()
        if self.backend.focused_is_secret():
            raise ToolError(t("capture", "secret_field"))
        self.backend.type(text)
        self.steps.append({"type": text})

    def key(self, combo: str) -> None:
        self.check()
        combo = normalize_key(combo)
        self.backend.key(combo)
        self.steps.append({"key": combo})

    def wait(self, ms: int) -> None:
        self.check()
        ms = max(0, min(int(ms), 10000))
        self.backend.wait(ms)
        self.steps.append({"wait": ms})

    def navigate(self, url: str) -> None:
        self.check()
        if self.grant.get("mode") == "desktop":
            raise ToolError(t("capture", "desktop_no_navigate"))
        full = urljoin(self.backend.url() or self.start_url, url)
        if not capturemod.domain_allowed(domain_of(full), self.allow_domains):
            raise ToolError(t("capture", "domain_blocked", host=domain_of(full) or url))
        self.backend.navigate(full)
        parts = urlsplit(full)
        self.steps.append({"navigate": parts.path + (f"?{parts.query}" if parts.query else "")})

    def save_shot(self) -> Path:
        self.check()
        image = self.frame()
        target = self.course["_dir"] / "media" / "recordings" / f"{self.asset_id}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(target)
        sheet = capturemod.review_dir(self.course, self.asset_id)
        sheet.mkdir(parents=True, exist_ok=True)
        copy = sheet / f"t{len(self.shots):04d}.00.png"
        image.convert("RGB").save(copy)
        self.shots.append(copy)
        self.steps.append({"shot": True})
        return target

    def record(self, on: bool) -> None:
        self.check()
        self.steps.append({"record": "start" if on else "stop"})

    def end(self, notes: str = "") -> dict:
        """Writes the steps in the brief and leaves the capture waiting for a person."""
        try:
            size = {"width": self.backend.viewport[0], "height": self.backend.viewport[1]}
            if self.grant.get("mode") == "desktop":
                block = {"mode": "desktop", "window": self.grant.get("window"), "window_size": size, "steps": self.steps}
            else:
                block = {"mode": "browser", "profile": self.grant.get("profile"), "start": urlsplit(self.start_url).path or "/",
                         "viewport": size, "steps": self.steps}
            previous = read_block(self.course, self.asset_id)
            if previous.get("mask"):
                block["mask"] = previous["mask"]
            if notes.strip():
                block["notes"] = notes.strip()
            brief = write_block(self.course, self.asset_id, block)
            findings = {kind: len(values) for kind, values in sorted(self.seen.items())}
            if self.redactor is not None:
                for kind, n in self.redactor.report.findings.items():
                    findings[f"{kind} (pixels)"] = n
            recorded = any(s.get("record") for s in self.steps)
            if not self.shots and not recorded:
                return {"brief": brief, "findings": findings, "file": None}
            engine = "pixels" if self.grant.get("mode") == "desktop" else "page"
            report = {"engine": engine + (f" + {self.redactor.report.engine}" if self.redactor else ""), "findings": findings,
                      "warnings": self.warnings, "frames": len(self.shots), "samples": []}
            review = capturemod.write_review(self.course, self.asset_id, report)
            ry, path, data, asset = capturemod.find_asset(self.course, self.asset_id)
            previous_state = dict(asset.get("capture") or {})
            asset["capture"] = {"state": "captured", "source": "session", "engine": report["engine"], "at": _now(),
                                "findings": findings, "warnings": self.warnings,
                                "file": f"media/recordings/{self.asset_id}.png" if self.shots else None,
                                "masks": previous_state.get("masks"), "replay": recorded or None}
            capturemod.save_manifest(ry, path, data)
            return {"brief": brief, "findings": findings, "file": asset["capture"]["file"], "review": review,
                    "replay": recorded}
        finally:
            self.close()


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


# ── starting one ─────────────────────────────────────────────────────────────────────────────

def start(project, code: str, asset_id: str, backend_factory=None, cursor: bool = False) -> Session:
    cfg = capturemod.settings(project)
    if not cfg.get("enabled"):
        raise ToolError(t("capture", "not_enabled"))
    course = coursemod.load(project, code)
    try:
        _, _, _, asset = capturemod.find_asset(course, asset_id)
    except capturemod.CaptureError as exc:
        raise ToolError(str(exc)) from None
    if asset.get("recipe") not in RECIPES:
        raise ToolError(t("capture", "bad_recipe", id=asset_id, recipes=", ".join(RECIPES)))
    grant = capturemod.active_grant(project, course["code"], asset_id)
    if grant is None:
        raise ToolError(t("capture", "no_grant", code=course["code"], id=asset_id))
    if grant["mode"] == "desktop":
        return _start_desktop(project, cfg, course, asset, asset_id, grant, backend_factory)
    try:
        profile = capturemod.profile_config(cfg, grant["profile"])
    except capturemod.CaptureError as exc:
        raise ToolError(str(exc)) from None
    if not capturemod.ready(project, grant["profile"], profile):
        raise ToolError(t("capture", "not_logged_in", name=grant["profile"]))
    block = read_block(course, asset_id)
    start_url, domains, server = resolve_start(course, profile, str(block.get("start") or ""))
    profile = {**profile, "allow_domains": [*profile["allow_domains"], *domains]}
    if not capturemod.domain_allowed(domain_of(start_url), profile["allow_domains"]):
        if server:
            server.shutdown()
        raise ToolError(t("capture", "domain_blocked", host=domain_of(start_url)))
    viewport = block.get("viewport") or {}
    size = (int(viewport.get("width") or 1440), int(viewport.get("height") or 900))
    rules, who, terms = _rules(cfg, course, asset, block)
    selectors = [*(rules.get("selectors") or []), *(str(m["selector"]) for m in block.get("mask") or []
                                                      if isinstance(m, dict) and m.get("selector"))]
    session = Session(project, course, asset_id, grant, None, rules, int((cfg.get("screenshot") or {}).get("max_edge") or 1920),
                      start_url, profile["allow_domains"], profile["login_url"], started_at=_now(), server=server)
    if rules.get("pixel_check"):
        try:
            session.redactor = _redactor(rules, course, who, terms)
            session.warnings += session.redactor.report.warnings
        except redactmod.RedactError:
            session.warnings.append(t("capture", "pixel_check_off"))
    device = float((cfg.get("screenshot") or {}).get("device_scale") or 1)
    session._scale = 1 / (device * min(1.0, session.max_edge / (max(size) * device)))
    factory = backend_factory or BrowserBackend
    try:
        session.backend = factory(capturemod._private_dir(capturemod.profile_dir(project, grant["profile"])), start_url,
                                  profile["allow_domains"], size, device, lambda texts: session.note_texts(texts, who, terms),
                                  {"selectors": selectors, "avatars": True, **({"cursor": True} if cursor else {})})
    except Exception:
        if server:
            server.shutdown()
        raise
    return session


def resolve_start(course: dict, profile: dict, start: str):
    """Where a session opens: (address, domains it adds, the local server it started, if any).

    `unit:N` (optionally followed by a path) is the course itself: with the html backend, the package of unit N
    (`assembly/html/unit-NN/`) served on this machine; with creator, the review link of unit N. Anything else is a path
    joined to the `start_url` of the profile."""
    match = re.fullmatch(r"unit:(\d+)(/.*)?", start.strip())
    if not match:
        if profile.get("builtin"):
            raise ToolError(t("capture", "course_needs_unit"))
        return (urljoin(profile["start_url"], start) if start else profile["start_url"]), [], None
    n, rest = int(match.group(1)), (match.group(2) or "").lstrip("/")
    if not any(int(u.get("n", 0)) == n for u in course.get("units") or []):
        raise ToolError(t("capture", "bad_unit", start=start))
    if coursemod.backend(course) == "html":
        folder = course["_dir"] / "assembly" / "html" / f"unit-{n:02d}"
        if not (folder / "index.html").exists():
            raise ToolError(t("capture", "no_package", n=n, code=course["code"]))
        server = serve_folder(folder)
        return f"http://127.0.0.1:{server.server_address[1]}/{rest or 'index.html'}", ["127.0.0.1"], server
    link = next((((u.get("links") or {}).get("review") or "") for u in course.get("units") or [] if int(u.get("n", 0)) == n), "")
    if not link:
        raise ToolError(t("capture", "no_review_link", n=n))
    return (urljoin(link, rest) if rest else link), [domain_of(link)], None


def serve_folder(folder: Path):
    """A quiet HTTP server of a folder on 127.0.0.1 (a free port), in a thread; `shutdown()` stops it."""
    import functools
    import http.server
    import threading

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args) -> None:
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(folder)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _rules(cfg: dict, course: dict, asset: dict, block: dict) -> tuple[dict, pii.People, list[str]]:
    """What is replaced or covered, who replaces it, and the texts always hidden in this resource."""
    rules = dict(cfg.get("redact") or {})
    terms = [str(m) for m in (asset.get("capture") or {}).get("masks") or []]
    terms += [str(m.get("text")) for m in block.get("mask") or [] if isinstance(m, dict) and m.get("text")]
    return rules, pii.people(coursemod.language(course)), terms


def _redactor(rules: dict, course: dict, who: pii.People, terms: list[str]) -> redactmod.Redactor:
    engine, read = redactmod.reader(str(rules.get("ocr") or "auto"), coursemod.language(course))
    return redactmod.Redactor(rules, who, terms, read, engine)


def _start_desktop(project, cfg, course, asset, asset_id, grant, backend_factory) -> Session:
    """A window of a program: there is no page to clean, so every screen is covered on the pixels and an OCR is required."""
    block = read_block(course, asset_id)
    rules, who, terms = _rules(cfg, course, asset, block)
    try:
        redactor = _redactor(rules, course, who, terms)
    except redactmod.RedactError:
        raise ToolError(t("capture", "desktop_needs_ocr")) from None
    if backend_factory is None:
        from coursekit.capture_window import make_backend as backend_factory
    session = Session(project, course, asset_id, grant, None, rules, int((cfg.get("screenshot") or {}).get("max_edge") or 1920),
                      "", [], started_at=_now(), redactor=redactor, warnings=list(redactor.report.warnings))
    session.backend = backend_factory(str(grant["window"]))
    session.frame()  # the scale of the screen of the window (a Retina screen has two pixels per point)
    return session


# ── the browser ──────────────────────────────────────────────────────────────────────────────

TARGET_JS = """([x, y]) => {
  let el = document.elementFromPoint(x, y);
  while (el && el.shadowRoot) { const inner = el.shadowRoot.elementFromPoint(x, y); if (!inner || inner === el) break; el = inner; }
  if (!el) return null;
  const hit = el.closest('button,a,input,select,textarea,summary,label,[role],[onclick],[tabindex]') || el;
  const implicit = {BUTTON: 'button', A: 'link', SELECT: 'combobox', TEXTAREA: 'textbox', SUMMARY: 'button'};
  let role = hit.getAttribute('role') || implicit[hit.tagName] || '';
  if (hit.tagName === 'INPUT') role = ({checkbox: 'checkbox', radio: 'radio', submit: 'button', button: 'button'})[hit.type] || 'textbox';
  let label = '';
  if (hit.labels && hit.labels.length) label = hit.labels[0].innerText.trim();
  const name = (hit.getAttribute('aria-label') || label || hit.innerText || hit.value || hit.getAttribute('title') ||
                hit.getAttribute('placeholder') || '').trim().replace(/\\s+/g, ' ').slice(0, 80);
  const out = {};
  if (role) out.role = role;
  if (name) out.name = name;
  if (label && label !== name) out.label = label;
  return out;
}"""

SECRET_JS = """() => {
  let el = document.activeElement;
  while (el && el.shadowRoot && el.shadowRoot.activeElement) el = el.shadowRoot.activeElement;
  if (!el) return false;
  const hint = [el.name, el.id, el.getAttribute && el.getAttribute('autocomplete')].join(' ');
  return el.type === 'password' || /one-time-code|otp|totp|2fa|mfa|passcode|verification/i.test(hint);
}"""


class BrowserBackend:
    """The Chrome, Edge or Chromium of the machine, visible, with the profile of the application."""

    def __init__(self, profile: Path, start_url: str, allow_domains: list[str], viewport: tuple[int, int], scale: float,
                 redact, page_config: dict):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ToolError(t("capture", "playwright_missing")) from None
        from coursekit.htmlkit.playcheck import find_browser

        executable = find_browser()
        if not executable:
            raise ToolError(t("capture", "no_browser"))
        self.viewport = viewport
        self.allow_domains = allow_domains
        self.scale = scale
        self._frames: list[tuple[float, bytes]] = []
        self._cdp = None
        self._pointer = (0.0, 0.0)
        self._pw = sync_playwright().start()
        try:
            self.context = self._pw.chromium.launch_persistent_context(
                str(profile), executable_path=executable, headless=False, viewport={"width": viewport[0], "height": viewport[1]},
                device_scale_factor=scale)
            self.context.expose_function("__ckRedact", redact)
            self.context.add_init_script(script=f"window.__ckConfig = {json.dumps(page_config)};")
            self.context.add_init_script(path=str(resources.files("coursekit.tools").joinpath("capture-dom.js")))
            if page_config.get("cursor"):
                self.context.add_init_script(path=str(resources.files("coursekit.tools").joinpath("capture-cursor.js")))
            self.context.route("**/*", self._guard)
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            self.navigate(start_url)
        except Exception:
            self.close()
            raise

    def _guard(self, route) -> None:
        request = route.request
        if request.is_navigation_request() and request.frame.parent_frame is None \
                and not capturemod.domain_allowed(domain_of(request.url), self.allow_domains):
            route.abort("blockedbyclient")
        else:
            route.continue_()

    def _settle(self) -> None:
        from playwright.sync_api import Error as PlaywrightError

        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            self.page.wait_for_function("window.__ckPending === 0", timeout=15000)
        except PlaywrightError:
            raise ToolError(t("capture", "page_not_clean")) from None

    def screenshot(self) -> bytes:
        self._settle()
        return self.page.screenshot(type="png")

    def click(self, x, y, button, count) -> None:
        self.page.mouse.click(x, y, button=button, click_count=count)
        self._pointer = (x, y)
        self._settle()

    def move(self, x, y) -> None:
        self.page.mouse.move(x, y, steps=8)

    def drag(self, x1, y1, x2, y2) -> None:
        self.page.mouse.move(x1, y1)
        self.page.mouse.down()
        self.page.mouse.move(x2, y2, steps=12)
        self.page.mouse.up()
        self._settle()

    def scroll(self, x, y, dx, dy) -> None:
        self.page.mouse.move(x, y)
        self.page.mouse.wheel(dx, dy)
        self.page.wait_for_timeout(300)

    def type(self, text) -> None:
        self.page.keyboard.type(text, delay=20)

    def key(self, combo) -> None:
        self.page.keyboard.press(combo)
        self._settle()

    def type_slowly(self, text, delay) -> None:
        self.page.keyboard.type(text, delay=delay)

    def wait(self, ms) -> None:
        self.page.wait_for_timeout(ms)

    def navigate(self, url) -> None:
        from playwright.sync_api import Error as PlaywrightError

        try:
            self.page.goto(url, wait_until="domcontentloaded")
        except PlaywrightError as exc:
            raise ToolError(t("capture", "browser_failed", reason=str(exc).splitlines()[0])) from None
        self._settle()

    # ── what only the replay uses ──

    def glide(self, x, y, ms) -> None:
        """Moves the pointer to (x, y) in about `ms` milliseconds, so the video shows it travel."""
        x0, y0 = self._pointer
        steps = max(1, int(ms) // 16)
        for i in range(1, steps + 1):
            self.page.mouse.move(x0 + (x - x0) * i / steps, y0 + (y - y0) * i / steps)
            self.page.wait_for_timeout(16)
        self._pointer = (x, y)

    def locate(self, target: dict) -> tuple[float, float] | None:
        """The centre of the element a step names (by role and name, by label or by text), when there is exactly one."""
        from playwright.sync_api import Error as PlaywrightError

        candidates = []
        if target.get("role") and target.get("name"):
            candidates.append(self.page.get_by_role(target["role"], name=target["name"], exact=True))
        for text in (target.get("label"), target.get("name")):
            if text:
                candidates += [self.page.get_by_label(text, exact=True), self.page.get_by_text(text, exact=True)]
        for locator in candidates:
            try:
                visible = [item for item in locator.all() if item.is_visible()]
                if len(visible) == 1:
                    visible[0].scroll_into_view_if_needed(timeout=3000)
                    box = visible[0].bounding_box()
                    if box:
                        return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            except PlaywrightError:
                continue
        return None

    def start_recording(self) -> None:
        self._cdp = self.context.new_cdp_session(self.page)
        self._cdp.on("Page.screencastFrame", self._frame)
        self._cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "everyNthFrame": 1,
                                                "maxWidth": round(self.viewport[0] * self.scale),
                                                "maxHeight": round(self.viewport[1] * self.scale)})

    def _frame(self, event: dict) -> None:
        import base64

        self._frames.append((float(event["metadata"]["timestamp"]), base64.b64decode(event["data"])))
        try:
            self._cdp.send("Page.screencastFrameAck", {"sessionId": event["sessionId"]})
        except Exception:  # noqa: BLE001 — the screencast may already be stopping
            pass

    def stop_recording(self) -> list[tuple[float, bytes]]:
        """The frames recorded since `start_recording`, with the time each one appeared, and the time it stopped."""
        import time

        self.page.wait_for_timeout(300)  # the last frames
        self._cdp.send("Page.stopScreencast")
        frames, self._frames = self._frames, []
        frames.append((time.time(), b""))  # when it stopped: the last frame lasts until then
        self._cdp.detach()
        self._cdp = None
        return frames

    def target_at(self, x, y) -> dict:
        return self.page.evaluate(TARGET_JS, [x, y]) or {}

    def focused_is_secret(self) -> bool:
        return bool(self.page.evaluate(SECRET_JS))

    def url(self) -> str:
        return self.page.url

    def close(self) -> None:
        try:
            self.context.close()
        except Exception:  # noqa: BLE001 — closing must never fail the end of a session
            pass
        try:
            self._pw.stop()
        except Exception:  # noqa: BLE001
            pass


# ── the MCP server ───────────────────────────────────────────────────────────────────────────

INSTRUCTIONS = (
    "Captures of a real application for the course resources that show an interface. Start with session_start(code, "
    "asset_id): it only works when a person allowed it (coursekit capture allow). Follow the brief of the resource "
    "(media/scripts/<id>.md): look with screenshot, act with the other tools (coordinates are those of the last screenshot), "
    "save the final capture with save_shot, mark the stretches of a video with record_start and record_stop, and finish "
    "with session_end. Personal data is already replaced on screen: never try to see the real data, never log in or type "
    "a password (a person does it), and stop if a tool says the permission or the session is gone."
)


class Manager:
    """The tools of the server, around the one session there can be at a time."""

    def __init__(self, project, backend_factory=None):
        self.project, self.factory, self.session = project, backend_factory, None

    def _current(self) -> Session:
        if self.session is None:
            raise ToolError(t("capture", "no_session_started"))
        return self.session

    def _guarded(self, action):
        """Runs an action; when the permission or the profile session is gone, the session ends with it."""
        try:
            return action()
        except SessionGone:
            if self.session is not None:
                self.session.close()
                self.session = None
            raise

    def tools(self) -> list:
        from coursekit.mcpserver import Tool, image, schema, text

        num, string = {"type": "number"}, {"type": "string"}
        xy = {"x": num, "y": num}

        def start_tool(args):
            if self.session is not None:
                raise ToolError(t("capture", "session_running", id=self.session.asset_id))
            self.session = start(self.project, str(args["code"]), str(args["asset_id"]), self.factory)
            s = self.session
            notes = [t("capture", "session_started", id=s.asset_id, url=s.start_url, domains=", ".join(s.allow_domains))]
            notes += s.warnings
            return [text("\n".join(notes)), image(s.screenshot())]

        def act(fn, *names, shot=True):
            def run(args):
                values = [args[n] for n in names]
                self._guarded(lambda: fn(self._current())(*values))
                return [image(self._guarded(lambda: self._current().screenshot()))] if shot else [text("OK")]
            return run

        def end_tool(args):
            s = self._current()
            self.session = None
            out = s.end(str(args.get("notes") or ""))
            root = self.project.root
            lines = [t("capture", "session_ended", brief=out["brief"].relative_to(root).as_posix(),
                       found=", ".join(f"{k} {n}" for k, n in out["findings"].items()) or t("capture", "review_nothing"))]
            if out.get("file"):
                lines.append(t("capture", "session_waits", file=out["file"], code=s.course["code"], id=s.asset_id))
            if out.get("replay"):
                lines.append(t("capture", "session_replay", code=s.course["code"], id=s.asset_id))
            return [text("\n".join(lines))]

        return [
            Tool("session_start", "Start capturing a resource of a course (needs the permission of a person). Returns the "
                 "first screenshot.", schema({"code": string, "asset_id": string}, ["code", "asset_id"]), start_tool),
            Tool("screenshot", "The screen now, with personal data replaced.", schema(),
                 lambda a: [image(self._guarded(lambda: self._current().screenshot()))]),
            Tool("zoom", "A closer look at a region of the last screenshot (its coordinates).",
                 schema({**xy, "width": num, "height": num}, ["x", "y", "width", "height"]),
                 lambda a: [image(self._guarded(lambda: self._current().zoom(a["x"], a["y"], a["width"], a["height"])))]),
            Tool("left_click", "Click at a point of the screenshot.", schema(xy, ["x", "y"]),
                 act(lambda s: lambda x, y: s.click(x, y), "x", "y")),
            Tool("double_click", "Double click at a point.", schema(xy, ["x", "y"]),
                 act(lambda s: lambda x, y: s.click(x, y, count=2), "x", "y")),
            Tool("right_click", "Right click at a point.", schema(xy, ["x", "y"]),
                 act(lambda s: lambda x, y: s.click(x, y, button="right"), "x", "y")),
            Tool("point", "Mark a place of the screen without clicking it, where the video should zoom when the narration names it "
                 "(say what it is in note).", schema({**xy, "note": string}, ["x", "y"]),
                 lambda a: [self._guarded(lambda: self._current().point(a["x"], a["y"], str(a.get("note") or ""))) or text("OK")]),
            Tool("mouse_move", "Move the pointer to a point (hover).", schema(xy, ["x", "y"]),
                 act(lambda s: s.move, "x", "y")),
            Tool("drag", "Drag from one point to another.", schema({"x1": num, "y1": num, "x2": num, "y2": num},
                 ["x1", "y1", "x2", "y2"]), act(lambda s: s.drag, "x1", "y1", "x2", "y2")),
            Tool("scroll", "Scroll at a point: dy > 0 goes down, dx > 0 goes right (pixels).",
                 schema({**xy, "dx": num, "dy": num}, ["x", "y", "dx", "dy"]), act(lambda s: s.scroll, "x", "y", "dx", "dy")),
            Tool("type", "Type text into the focused field (never a password or a code).", schema({"text": string}, ["text"]),
                 act(lambda s: s.type, "text")),
            Tool("key", "Press a key or a combination, e.g. Enter, Tab, ctrl+a.", schema({"key": string}, ["key"]),
                 act(lambda s: s.key, "key")),
            Tool("wait", "Wait some milliseconds (at most 10000).", schema({"ms": num}, ["ms"]), act(lambda s: s.wait, "ms")),
            Tool("navigate", "Open an address of the application (relative to the current one, or full on its domains).",
                 schema({"url": string}, ["url"]), act(lambda s: s.navigate, "url")),
            Tool("save_shot", "Save the screen as it is now as the capture of the resource.", schema(),
                 lambda a: [text(t("capture", "shot_saved", path=self._guarded(lambda: self._current().save_shot())
                                   .relative_to(self.project.root).as_posix()))]),
            Tool("record_start", "Mark where the video of the resource starts (it is recorded on replay).", schema(),
                 act(lambda s: lambda: s.record(True), shot=False)),
            Tool("record_stop", "Mark where the video of the resource stops.", schema(),
                 act(lambda s: lambda: s.record(False), shot=False)),
            Tool("session_end", "Finish: the steps go to the brief and the capture waits for a person to review it.",
                 schema({"notes": string}), end_tool),
        ]


def serve(project) -> None:
    from coursekit import __version__
    from coursekit.mcpserver import Server

    Server("coursekit-capture", __version__, Manager(project).tools(), INSTRUCTIONS).serve()
