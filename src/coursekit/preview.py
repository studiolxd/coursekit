"""`coursekit preview`: play the units of an html course with a simulated LMS.

A local server shows a page that holds the SCORM 1.2 and 2004 APIs (`API`, `API_1484_11`) and the unit in an iframe, so the
package finds its LMS as it would on a real platform. What the unit sends is kept in the browser (localStorage): closing
and reopening resumes where it was. A panel shows the tracking live, and the unit reloads when it is built again.
"""

from __future__ import annotations

import json
import mimetypes
import re
import threading
import webbrowser
from collections.abc import Callable
from html import escape
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from urllib.parse import unquote, urlsplit

from coursekit import course as coursemod
from coursekit import delivery as deliverymod
from coursekit.i18n import t

Say = Callable[[str], None]

RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")

# The texts of the panel, from lang/messages/preview.yaml.
PANEL_TEXTS = ("panel_title", "unit", "standard", "status", "completion", "success", "score", "location", "progress",
               "entry", "exit", "session_time", "suspend_data", "chars", "interactions", "interaction_id", "response",
               "result", "weighting", "none", "calls", "errors", "reopen", "reset", "reloaded",
               "not_built", "hide", "show")


def units_dir(course: dict) -> Path:
    return course["_dir"] / "assembly" / "html"


def unit_dir(course: dict, n: int) -> Path:
    return units_dir(course) / f"unit-{n:02d}"


def stamp(course: dict, n: int) -> float:
    """When the unit was last built (0 if it is not)."""
    index = unit_dir(course, n) / "index.html"
    return index.stat().st_mtime if index.exists() else 0.0


def page(course: dict, units: list[dict], first: int) -> str:
    template = resources.files("coursekit.templates.html").joinpath("preview.html").read_text(encoding="utf-8")
    standard = deliverymod.settings(course)["export"]["standard"]
    config = {
        "course": course["code"],
        "standard": "2004" if standard == "scorm_2004" else "1.2",
        "first": first,
        "units": [{"n": u["n"], "title": u.get("title") or "", "built": stamp(course, u["n"]) > 0} for u in units],
        "texts": {key: t("preview", key) for key in PANEL_TEXTS},
    }
    data = json.dumps(config, ensure_ascii=False).replace("</", "<\\/")
    return (template.replace("__LANG__", escape(coursemod.language(course)))
            .replace("__TITLE__", escape(f"{course['code']} · {t('preview', 'panel_title')}"))
            .replace("__CONFIG__", data))


def handler_for(course: dict, units: list[dict], first: int):
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A002 - the signature of the standard library
            pass

        def _send(self, body: bytes, kind: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            # audio and video ask for parts (Range): without them the browser gives up on the file
            part = RANGE_RE.match(self.headers.get("Range") or "") if status == HTTPStatus.OK else None
            size = len(body)
            if part:
                first = int(part.group(1) or 0)
                last = min(int(part.group(2)) if part.group(2) else size - 1, size - 1)
                if first >= size or first > last:
                    self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                body = body[first:last + 1]
                status = HTTPStatus.PARTIAL_CONTENT
            try:
                self.send_response(status)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Accept-Ranges", "bytes")
                if part:
                    self.send_header("Content-Range", f"bytes {first}-{last}/{size}")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass  # the browser stopped wanting it (a reload, a media element that moved on)

        def do_HEAD(self):  # noqa: N802
            self.do_GET()

        def do_GET(self):  # noqa: N802
            path = unquote(urlsplit(self.path).path)
            if path == "/favicon.ico":
                self._send(b"", "image/x-icon", HTTPStatus.NO_CONTENT)
                return
            if path in ("/", "/index.html"):
                self._send(page(course, units, first).encode("utf-8"), "text/html; charset=utf-8")
                return
            if path == "/__ck/lms.js":
                body = resources.files("coursekit.templates.html").joinpath("lms.js").read_bytes()
                self._send(body, "text/javascript; charset=utf-8")
                return
            if path == "/__ck/stamps":
                body = json.dumps({str(u["n"]): stamp(course, u["n"]) for u in units})
                self._send(body.encode("utf-8"), "application/json")
                return
            parts = path.strip("/").split("/", 2)
            if len(parts) >= 2 and parts[0] == "unit" and parts[1].isdigit():
                base = unit_dir(course, int(parts[1])).resolve()
                target = (base / (parts[2] if len(parts) == 3 and parts[2] else "index.html")).resolve()
                if target.is_relative_to(base) and target.is_file():
                    kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
                    if kind.startswith("text/") or kind in ("application/javascript", "image/svg+xml"):
                        kind += "; charset=utf-8"
                    self._send(target.read_bytes(), kind)
                    return
            self._send(b"not found", "text/plain; charset=utf-8", HTTPStatus.NOT_FOUND)

    return Handler


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 128  # a page asks for many images at once: the default queue (5) refuses connections


def serve(course: dict, units: list[dict], first: int, port: int = 8765) -> ThreadingHTTPServer:
    """The preview server on 127.0.0.1 (the port asked for, else a free one); call `serve_forever` on it."""
    handler = handler_for(course, units, first)
    try:
        return Server(("127.0.0.1", port), handler)
    except OSError:
        return Server(("127.0.0.1", 0), handler)


def run(course: dict, units: list[dict], first: int, port: int, open_browser: bool, say: Say = print) -> int:
    server = serve(course, units, first, port)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    say(t("preview", "serving", url=url))
    say(t("preview", "stop_hint"))
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
