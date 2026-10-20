"""`coursekit media gallery`: every media resource of a course on one page, with where it goes and what it was made from.

Each resource of `media/manifest.yaml` is a card: the produced file in place (image, video, audio, PDF, or the same embedded player
the learner gets for terminal demos and simulations), or a `pending` box when there is no file yet; the unit and section it belongs
to (and the line of its placeholder in `content.md`); and everything coursekit holds about how it was made: description, how it is
made, specifications, alternative text, the script, the transcript, the subtitles, the text of the session, the capture state.

The page is plain HTML with relative links, so it opens from disk. With `--serve` a local server (127.0.0.1) shows it, watches the
manifest and the folders of the course, and builds the page again when something changes: the page asks for `version.json` every
second and reloads itself, keeping the filters it had.
"""

from __future__ import annotations

import html
import json
import os
import re
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

from coursekit import course as coursemod
from coursekit.i18n import t
from coursekit.preview import RANGE_RE, Server

IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
VIDEOS = {".mp4", ".webm", ".mov"}
AUDIOS = {".mp3", ".wav", ".ogg", ".m4a"}
PLACEHOLDER = re.compile(r"^> \*\*\[[^\]]*\]\*\*\s*$")
TITLE_LINE = re.compile(r"^> \*\*[^*]+:\*\*\s*(.*?)\s*$")


class GalleryError(Exception):
    pass


def gallery_dir(course: dict) -> Path:
    """Where the page is written: .cache/media/<CODE>/resources/ (the video gallery has its own folder, `gallery/`)."""
    return course["_project"].cache_dir / "media" / course["code"] / "resources"


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip() if path.is_file() else ""
    except (OSError, UnicodeDecodeError):
        return ""


def _section_titles(course: dict, n: int) -> dict[int, str]:
    tokens = coursemod.tokens(course)
    text = _read(coursemod.unit_dir(course["_dir"], n) / "content.md")
    heading = re.compile(rf"^## {re.escape(tokens['section'])} (\d+)\s*[—-]\s*(.+?)\s*(?:\*\(.*\)\*)?\s*$", re.M)
    return {int(m.group(1)): m.group(2) for m in heading.finditer(text)}


def _placeholder_lines(course: dict, n: int) -> dict[str, int]:
    """The line of each media placeholder of the unit, by its title: the marker line, `> **[RECURSO ...]**`."""
    lines = _read(coursemod.unit_dir(course["_dir"], n) / "content.md").split("\n")
    found: dict[str, int] = {}
    for i in range(1, len(lines)):
        m = TITLE_LINE.match(lines[i])
        if m and PLACEHOLDER.match(lines[i - 1]):
            found.setdefault(m.group(1), i)  # 1-based line of the marker (the line before the title, index i - 1)
    return found


def _texts(course: dict, asset: dict) -> list[tuple[str, str]]:
    """What coursekit holds about the resource, as (label key, text), in the order it is shown. Empty ones are left out."""
    media = course["_dir"] / "media"
    asset_id = str(asset["id"])
    files = media / "files"
    capture = asset.get("capture") or {}
    state = ""
    if capture.get("state"):
        state = t("mediagallery", "capture_state", state=capture["state"], by=capture.get("by") or "—", engine=capture.get("engine") or "—")
        for warning in capture.get("warnings") or []:
            state += f"\n· {warning}"
    anchors = "\n".join(f"· {a.get('label')}" for a in asset.get("anchors") or [] if isinstance(a, dict))
    points = "\n".join(f"· {p}" for p in asset.get("points") or [])
    session = _read(files / f"{asset_id}.txt") or _read(media / "recordings" / f"{asset_id}.txt")
    found = [
        ("description", str(asset.get("description") or "")),
        ("how", str(asset.get("how") or "")),
        ("specs", str(asset.get("specs") or "")),
        ("alt", str(asset.get("alt") or "")),
        ("script", _read(media / "scripts" / f"{asset_id}.md")),
        ("video_script", _read(media / "scripts" / f"{asset_id}.video.yaml")),
        ("scenes", _read(media / "scripts" / f"{asset_id}.scenes.yaml")),
        ("transcript", _read(files / f"{asset_id}.transcript.txt") or str(asset.get("transcript") or "")),
        ("audio_description", _read(files / f"{asset_id}.descriptions.vtt")),
        ("subtitles", _read(files / f"{asset_id}.vtt")),
        ("session", session),
        ("body", str(asset.get("body") or "")),
        ("points", points or anchors),
        ("capture", state),
    ]
    return [(key, text.strip()) for key, text in found if text and text.strip()]


def collect(course: dict) -> list[dict]:
    """One entry per resource of the manifest: where it goes, its file (or that it is pending) and its texts."""
    manifest = course["_dir"] / "media" / "manifest.yaml"
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) if manifest.exists() else None
    assets = (data or {}).get("assets") or []
    tokens = coursemod.tokens(course)
    unit_titles = {int(u["n"]): u.get("title") or "" for u in course.get("units") or []}
    sections: dict[int, dict[int, str]] = {}
    lines: dict[int, dict[str, int]] = {}
    out = []
    for asset in assets:
        unit = int(asset["unit"]) if str(asset.get("unit") or "").isdigit() else 0
        section = int(asset["section"]) if str(asset.get("section") or "").isdigit() else 0
        if unit and unit not in sections:
            sections[unit] = _section_titles(course, unit)
            lines[unit] = _placeholder_lines(course, unit)
        rel = str(asset.get("file") or "")
        path = course["_dir"] / rel if rel else None
        out.append({
            "id": str(asset["id"]),
            "type": str(asset.get("type") or ""),
            "type_word": tokens["media_types"].get(str(asset.get("type") or ""), str(asset.get("type") or "")),
            "title": str(asset.get("title") or ""),
            "unit": unit, "unit_title": unit_titles.get(unit, ""),
            "section": section, "section_title": sections.get(unit, {}).get(section, ""),
            "line": lines.get(unit, {}).get(str(asset.get("title") or "")),
            "status": str(asset.get("status") or ""),
            "recipe": str(asset.get("recipe") or ""),
            "depicts": str(asset.get("depicts") or ""),
            "path": path if path and path.is_file() else None,
            "missing": bool(path and not path.is_file()),
            "pending": str(asset.get("status") or "") == "pending" or not (path and path.is_file()),
            "texts": _texts(course, asset),
            "downloads": [d for d in asset.get("downloads") or [] if isinstance(d, dict) and d.get("file")],
        })
    return out


def _rel(course: dict, path: Path) -> str:
    return html.escape(Path(os.path.relpath(path, gallery_dir(course))).as_posix(), quote=True)


def _preview(course: dict, entry: dict) -> str:
    path = entry["path"]
    if path is None:
        key = "missing_file" if entry["missing"] else "pending_box"
        return f'<div class="pending">{html.escape(t("mediagallery", key))}</div>'
    suffix = path.suffix.lower()
    src = _rel(course, path)
    name = html.escape(path.name)
    if suffix in IMAGES:
        return f'<a href="{src}"><img loading="lazy" src="{src}" alt=""></a>'
    if suffix in VIDEOS:
        tracks = ""
        language = coursemod.language(course)
        subtitles = path.with_suffix(".vtt")
        if subtitles.is_file():
            label = html.escape(t("mediagallery", "subtitles"))
            tracks += f'<track kind="subtitles" srclang="{language}" label="{label}" src="{_rel(course, subtitles)}" default>'
        described = path.with_name(f"{path.stem}.descriptions.vtt")
        if described.is_file():
            label = html.escape(t("mediagallery", "audio_description"))
            tracks += f'<track kind="descriptions" srclang="{language}" label="{label}" src="{_rel(course, described)}">'
        return f'<video controls preload="metadata" src="{src}">{tracks}</video>'
    if suffix in AUDIOS:
        return f'<audio controls preload="metadata" src="{src}"></audio>'
    if suffix == ".pdf":
        return f'<iframe class="doc" loading="lazy" src="{src}" title="{name}"></iframe>'
    if suffix in (".html", ".htm"):  # the player of a terminal demo or a simulation: the one the learner gets
        kind = "player" if entry["type"] == "terminal_demo" else "embed"
        return f'<iframe class="{kind}" loading="lazy" src="{src}" title="{name}"></iframe>'
    return f'<a href="{src}">{name}</a>'


def _raw_links(course: dict, entry: dict) -> str:
    """Links to the files behind the resource: the recording of a terminal demo, the downloads of a job aid."""
    media = course["_dir"] / "media"
    found = []
    for suffix in (".cast", ".mp3", ".json"):
        for path in sorted((media / "files").glob(f"{entry['id']}{suffix}")):
            found.append(path)
    found += [course["_dir"] / d["file"] for d in entry["downloads"] if (course["_dir"] / d["file"]).is_file()]
    return " · ".join(f'<a href="{_rel(course, p)}">{html.escape(p.name)}</a>' for p in found)


def _card(course: dict, entry: dict) -> str:
    done = not entry["pending"]
    where = (t("mediagallery", "where", unit=entry["unit"], unit_title=entry["unit_title"], section=entry["section"],
               section_title=entry["section_title"]) if entry["unit"] else t("mediagallery", "no_place"))
    if entry["line"]:
        where += " · " + t("mediagallery", "placeholder_line", line=entry["line"])
    meta = " · ".join(html.escape(v) for v in (entry["type_word"], entry["recipe"], entry["depicts"]) if v)
    badge = t("mediagallery", "done" if done else "pending")
    blocks = "".join(
        f'<details><summary>{html.escape(t("mediagallery", key))}</summary><pre>{html.escape(text)}</pre></details>'
        for key, text in entry["texts"])
    raw = _raw_links(course, entry)
    haystack = " ".join([entry["id"], entry["title"], entry["unit_title"], entry["section_title"], *(text for _, text in entry["texts"])])
    return (f'<article class="card {"done" if done else "todo"}" data-unit="{entry["unit"]}" data-type="{html.escape(entry["type"])}" '
            f'data-state="{"done" if done else "pending"}" data-text="{html.escape(haystack.lower(), quote=True)}" '
            f'id="{html.escape(entry["id"])}">'
            f'<header><h3>{html.escape(entry["id"])} — {html.escape(entry["title"])}</h3>'
            f'<span class="badge">{html.escape(badge)}{" · " + html.escape(entry["status"]) if entry["status"] else ""}</span></header>'
            f'<p class="where">{html.escape(where)}</p><p class="meta">{meta}</p>'
            + (f'<p class="stale">{html.escape(t("mediagallery", "stale"))}</p>' if entry["pending"] and entry["path"] else "")
            + f'<div class="media">{_preview(course, entry)}</div>'
            + (f'<p class="raw">{raw}</p>' if raw else "") + blocks + "</article>")


STYLE = """
body{font-family:system-ui,sans-serif;margin:0;background:#fafafa;color:#1b1b1b}
header.top{position:sticky;top:0;background:#fff;border-bottom:1px solid #ccc;padding:12px 24px;z-index:2}
header.top h1{font-size:20px;margin:0 0 4px}.summary{margin:0 0 8px;color:#444}
.filters{display:flex;flex-wrap:wrap;gap:8px}.filters select,.filters input{font:inherit;padding:4px 6px}
main{padding:16px 24px}h2{margin:32px 0 8px;font-size:18px;border-bottom:1px solid #ccc}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:16px}
.card{scroll-margin-top:120px;background:#fff;border:1px solid #ccc;padding:12px}.card.todo{border-style:dashed}
.card header{display:flex;justify-content:space-between;gap:8px;align-items:baseline}.card h3{font-size:15px;margin:0}
.badge{font-size:12px;border:1px solid #888;padding:1px 6px;white-space:nowrap}.card.todo .badge{background:#ffe9a8}
.where{margin:6px 0 0;font-weight:600;font-size:13px}.meta,.raw{margin:2px 0 8px;font-size:12px;color:#555}
.media img,.media video{max-width:100%;max-height:420px;display:block;margin:0 auto;border:1px solid #ddd}
.media audio{width:100%}.media iframe{width:100%;border:1px solid #ddd}.media iframe.doc{height:420px}
.media iframe.player{height:760px}.media iframe.embed{height:520px}
.stale{margin:4px 0;font-size:12px;color:#7a5b00;background:#fff8e1;padding:4px 6px}
.pending{padding:32px 8px;text-align:center;color:#7a5b00;background:#fff8e1;border:1px dashed #c9a227}
details{margin-top:6px}summary{cursor:pointer;font-size:13px;font-weight:600}
pre{white-space:pre-wrap;word-break:break-word;font-size:12px;background:#f3f3f3;padding:8px;max-height:320px;overflow:auto}
.hidden{display:none}
"""

SCRIPT = """
const $ = (s) => document.querySelector(s);
const saved = JSON.parse(sessionStorage.getItem('ck-gallery') || '{}');
for (const id of ['unit', 'type', 'state', 'q']) if (saved[id] !== undefined) $('#' + id).value = saved[id];
function apply() {
  const f = {unit: $('#unit').value, type: $('#type').value, state: $('#state').value, q: $('#q').value.toLowerCase()};
  sessionStorage.setItem('ck-gallery', JSON.stringify(f));
  let shown = 0;
  for (const c of document.querySelectorAll('.card')) {
    const ok = (!f.unit || c.dataset.unit === f.unit) && (!f.type || c.dataset.type === f.type)
      && (!f.state || c.dataset.state === f.state) && (!f.q || c.dataset.text.includes(f.q));
    c.classList.toggle('hidden', !ok); if (ok) shown++;
  }
  for (const g of document.querySelectorAll('section.group')) g.classList.toggle('hidden', !g.querySelector('.card:not(.hidden)'));
  $('#shown').textContent = shown;
}
for (const id of ['unit', 'type', 'state', 'q']) $('#' + id).addEventListener('input', apply);
apply();
if (location.protocol.startsWith('http')) {
  let version = null;
  setInterval(async () => {
    try {
      const v = (await (await fetch('version.json', {cache: 'no-store'})).json()).version;
      if (version !== null && v !== version) { sessionStorage.setItem('ck-scroll', String(scrollY)); location.reload(); }
      version = v;
    } catch (e) { /* the server is not there: nothing to do */ }
  }, 1000);
  const y = sessionStorage.getItem('ck-scroll'); if (y) { scrollTo(0, Number(y)); sessionStorage.removeItem('ck-scroll'); }
}
"""


def render(course: dict, entries: list[dict]) -> str:
    done = sum(1 for e in entries if not e["pending"])
    units = sorted({e["unit"] for e in entries if e["unit"]})
    types = sorted({(e["type"], e["type_word"]) for e in entries})
    unit_names = {e["unit"]: e["unit_title"] for e in entries}
    options = lambda items: "".join(f'<option value="{html.escape(str(v))}">{html.escape(label)}</option>' for v, label in items)  # noqa: E731
    groups = []
    keys = sorted({(e["unit"], e["section"]) for e in entries})
    for unit, section in keys:
        cards = [e for e in entries if (e["unit"], e["section"]) == (unit, section)]
        head = (t("mediagallery", "where", unit=unit, unit_title=unit_names.get(unit, ""), section=section,
                  section_title=cards[0]["section_title"]) if unit else t("mediagallery", "no_place"))
        groups.append(f'<section class="group"><h2>{html.escape(head)}</h2><div class="grid">'
                      + "".join(_card(course, e) for e in cards) + "</div></section>")
    body = "".join(groups) or f'<p>{html.escape(t("mediagallery", "empty"))}</p>'
    return (f'<!doctype html><html lang="{coursemod.language(course)}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{html.escape(t("mediagallery", "title", code=course["code"]))}</title><style>{STYLE}</style></head><body>'
            f'<header class="top"><h1>{html.escape(t("mediagallery", "title", code=course["code"]))}</h1>'
            f'<p class="summary">{html.escape(t("mediagallery", "summary", total=len(entries), done=done, pending=len(entries) - done))}'
            f' · <span id="shown">{len(entries)}</span> {html.escape(t("mediagallery", "shown"))}</p>'
            f'<div class="filters"><select id="unit"><option value="">{html.escape(t("mediagallery", "all_units"))}</option>'
            + options((u, t("mediagallery", "unit_option", unit=u, unit_title=unit_names.get(u, ""))) for u in units)
            + f'</select><select id="type"><option value="">{html.escape(t("mediagallery", "all_types"))}</option>'
            + options(types) + f'</select><select id="state"><option value="">{html.escape(t("mediagallery", "all_states"))}</option>'
            f'<option value="done">{html.escape(t("mediagallery", "done"))}</option>'
            f'<option value="pending">{html.escape(t("mediagallery", "pending"))}</option></select>'
            f'<input id="q" type="search" placeholder="{html.escape(t("mediagallery", "search"))}"></div></header>'
            f"<main>{body}</main><script>{SCRIPT}</script></body></html>")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def build(course: dict) -> Path:
    """Write the page (and a version.json for the live mode) and give its path."""
    folder = gallery_dir(course)
    page = folder / "index.html"
    _write(page, render(course, collect(course)))
    if not (folder / "version.json").exists():
        _write(folder / "version.json", json.dumps({"version": 1}))
    return page


def watched(course: dict) -> list[Path]:
    root = course["_dir"]
    media = root / "media"
    return [media / "manifest.yaml", media / "files", media / "recordings", media / "scripts", media / "src",
            root / "content", root / "course.yaml"]


def stamp(paths: list[Path]) -> tuple:
    """When each file (or each file inside a folder) last changed, to tell the server that something moved."""
    out = []
    for path in paths:
        files = [path] if path.is_file() else ([p for p in path.rglob("*") if p.is_file()] if path.is_dir() else [])
        for f in files:
            try:
                stat = f.stat()
            except OSError:
                continue
            out.append((f.as_posix(), stat.st_mtime_ns, stat.st_size))
    return tuple(sorted(out))


def _handler(course: dict, state: dict):
    """Serves the page and what the cards point at, and nothing else of the project: the gallery folder and `media/` and
    `content/` of the course (not `.env`, not other courses). It answers Range requests: audio and video need them to seek."""
    folder = gallery_dir(course).resolve()
    allowed = [folder, (course["_dir"] / "media").resolve(), (course["_dir"] / "content").resolve()]
    base = course["_project"].root.resolve()

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A002 - the signature of the standard library
            pass

        def _send(self, body: bytes, kind: str, status: HTTPStatus = HTTPStatus.OK) -> None:
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
                pass

        def do_HEAD(self):  # noqa: N802
            self.do_GET()

        def do_GET(self):  # noqa: N802
            import mimetypes

            path = unquote(urlsplit(self.path).path)
            if path == "/version.json":
                self._send(json.dumps(state).encode("utf-8"), "application/json")
                return
            target = (folder / "index.html") if path in ("/", "/index.html") else (base / path.lstrip("/")).resolve()
            if not any(target.is_relative_to(a) for a in allowed) or not target.is_file():
                self._send(b"not found", "text/plain; charset=utf-8", HTTPStatus.NOT_FOUND)
                return
            kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if kind.startswith("text/") or kind in ("application/javascript", "image/svg+xml", "application/json"):
                kind += "; charset=utf-8"
            self._send(target.read_bytes(), kind)

    return Handler


def serve(course: dict, reload, port: int = 8767, open_browser: bool = True, say=print) -> int:
    """Serve the page on 127.0.0.1 (the port asked for, else a free one) until Ctrl+C, building it again when the course changes.
    `reload` gives the course read anew."""
    build(course)
    state = {"version": 1}
    stop = threading.Event()

    def watch() -> None:
        current = reload()
        before = stamp(watched(current))
        while not stop.wait(1):
            try:
                current = reload()
                now = stamp(watched(current))
            except Exception:  # a file half written: next second
                continue
            if now == before:
                continue
            try:
                build(current)
                state["version"] += 1
                say(t("mediagallery", "updated", time=time.strftime("%H:%M:%S")))
            except Exception as exc:  # the page keeps the last good build and the next save fixes it
                say(t("commands", "error_line", text=exc))
            before = stamp(watched(current))

    handler = _handler(course, state)
    try:
        server = Server(("127.0.0.1", port), handler)
    except OSError:
        server = Server(("127.0.0.1", 0), handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    say(t("mediagallery", "serving", url=url))
    say(t("mediagallery", "watching"))
    threading.Thread(target=watch, daemon=True).start()
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()
    return 0
