"""`coursekit brief`: prepare the reference material (brief/) of a course or of the project.

The person drops files of any format in brief/sources/, lists web documentation in
brief/links.md and writes indications in brief/notes.md. This converts all of it to Markdown in
brief/text/ and writes brief/index.md, which is what the design, writing and review agents read:

    sources/<path>      -> text/files/<path>.md   (MarkItDown)
    links.md (URLs)     -> text/web/<site>/       (web2md.js, Node; a link to a PDF or an Office file, with MarkItDown)

Only new or changed files are converted; URLs are downloaded once (refresh downloads them again).
Images are listed for the agents to open directly; audio and video need a transcript.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from importlib import resources
from pathlib import Path

from coursekit import config as configmod
from coursekit import exelearning, i18n
from coursekit.lang import format_number
from coursekit.util import USER_AGENT, sha256_file

WEB2MD = Path(str(resources.files("coursekit.tools").joinpath("web2md.js")))
BLOCKED = re.compile(r"^BLOCKED\t(\S+)", re.M)  # what web2md says of a page that answered empty or with a check against robots
RENDERED = re.compile(r"^RENDERED\t(\S+)", re.M)  # ...and of one it read in the browser of the machine instead
PAGES_FAILED = re.compile(r"^\d+ errores\.$", re.M)


def fmt(number: int, lang: str) -> str:
    return format_number(number, lang)


def note(key: str, **values: object) -> tuple[str, dict]:
    """A warning about a file, kept as a key so it can be shown in any language."""
    return key, values


def render(item: tuple[str, dict], lang: str) -> str:
    key, values = item
    return i18n.t_in(lang, "brief", f"note_{key}", **values)


STATE = ".state.json"
COPY = {".md", ".markdown", ".txt"}
IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tif", ".tiff", ".heic"}
AUDIO_VIDEO = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
MAX_MB = 20
MIN_WORDS = 20  # below this, a converted document probably had no text layer (scanned PDF)
LINK = re.compile(r"^\s*(?:[-*+]\s+)?<?(https?://[^\s>]+)>?\s*(?:[—–-]+\s*(.*))?$")  # bullet optional


def words(text: str) -> int:
    return len(re.findall(r"\w+", strip_frontmatter(text)))


def strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            return text[end + 4:]
    return text


def title_of(text: str, fallback: str) -> str:
    m = re.search(r"^title:\s*\"?(.+?)\"?\s*$", text[:2000], re.M) or re.search(r"^#\s+(.+)$", strip_frontmatter(text), re.M)
    return m.group(1).strip() if m else fallback


def parse_links(path: Path) -> list[tuple[str, str]]:
    if not path.exists():
        return []
    text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
    found = []
    for line in text.splitlines():
        m = LINK.match(line)
        if m:
            found.append((m.group(1), (m.group(2) or "").strip()))
    return found


def site_slug(url: str) -> str:
    return re.sub(r"[^\w]+", "-", re.sub(r"^https?://", "", url)).strip("-")


def markitdown(src: Path) -> tuple[str | None, tuple[str, dict] | None]:
    try:
        from markitdown import MarkItDown
    except ImportError:
        return None, note("markitdown_missing")
    try:
        return MarkItDown().convert(str(src)).text_content or "", None
    except Exception as exc:  # noqa: BLE001 — any converter error is reported per file
        return None, note("convert_failed", error=f"{type(exc).__name__}: {str(exc)[:200]}")


def text_path(out_root: Path, rel: str) -> Path:
    """text/files/<rel>.md, without doubling the extension of Markdown sources."""
    return out_root / (rel if Path(rel).suffix.lower() in (".md", ".markdown") else f"{rel}.md")


EXELEARNING = {".elp"}
REPORT = "import-report.md"


def exe_convert(src: Path, rel: str, brief: Path, target: Path, options: dict):
    """A package of eXeLearning as Markdown (its images go to text/media/<name>/): (text, error, report)."""
    media = brief / "text" / "media" / re.sub(r"[^\w.-]+", "-", rel).strip("-")
    shutil.rmtree(media, ignore_errors=True)
    try:
        body, report = exelearning.convert(src, media, Path(os.path.relpath(media, target.parent)).as_posix(),
                                           options.get("rules") or [], options.get("language") or "es", options.get("forbidden"))
    except exelearning.ExeError as exc:
        return None, note("convert_failed", error=str(exc)), None
    return body, None, report


def convert_files(brief: Path, state: dict, options: dict | None = None) -> tuple[list[dict], int]:
    options = options or {}
    sources, out_root = brief / "sources", brief / "text" / "files"
    previous = state.get("files", {})
    current, present, rows, failed = {}, set(), [], 0
    today = dt.date.today().isoformat()
    def visible(p: Path) -> bool:
        return p.is_file() and not any(part.startswith(".") for part in p.relative_to(sources).parts)

    for src in sorted(p for p in sources.rglob("*") if visible(p)):
        rel = src.relative_to(sources).as_posix()
        ext = src.suffix.lower()
        size_mb = src.stat().st_size / 1_000_000
        row = {"source": f"sources/{rel}", "text": None, "title": src.stem, "words": 0, "notes": []}
        if size_mb > MAX_MB:
            row["notes"].append(note("heavy", mb=f"{size_mb:.0f}"))
        if ext in IMAGES:
            row["kind"] = "image"
            rows.append(row)
            continue
        if ext in AUDIO_VIDEO:
            row["kind"] = "media"
            row["notes"].append(note("no_transcript"))
            rows.append(row)
            continue
        row["kind"] = "document"
        present.add(rel)
        target = text_path(out_root, rel)
        digest = sha256_file(src)
        if ext in EXELEARNING:  # what a package becomes depends on the rules of the import and on what is forbidden
            digest += ":" + hashlib.sha256(json.dumps([options.get("rules"), options.get("forbidden"), options.get("language")],
                                                      sort_keys=True, default=str).encode("utf-8")).hexdigest()[:12]
        current[rel] = digest
        if previous.get(rel) != digest or not target.exists():
            if ext in EXELEARNING:
                body, error, report = exe_convert(src, rel, brief, target, options)
                if report is not None:
                    state.setdefault("exe", {})[rel] = dataclasses.asdict(report)
            elif ext in COPY:
                body, error = src.read_text(encoding="utf-8", errors="replace"), None
            else:
                body, error = markitdown(src)
            if error:
                current.pop(rel)
                failed += 1
                row["notes"].append(error)
                rows.append(row)
                continue
            body = strip_frontmatter(body).strip() + "\n"
            front = (f"---\ntitle: {json.dumps(title_of(body, src.stem), ensure_ascii=False)}\n"
                     f"source: {json.dumps(row['source'], ensure_ascii=False)}\nconverted: {today}\n"
                     f"words: {words(body)}\n---\n\n")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(front + body, encoding="utf-8")
        text = target.read_text(encoding="utf-8")
        row.update(text=target.relative_to(brief).as_posix(), title=title_of(text, src.stem), words=words(text))
        if ext in EXELEARNING and rel in state.get("exe", {}):
            row["notes"] += [note("exe_report"), *exelearning.summary_notes(exelearning.Report(**state["exe"][rel]))]
        if row["words"] < MIN_WORDS:
            row["notes"].append(note("no_text"))
        rows.append(row)
    # Remove conversions of files that are no longer in sources/.
    for rel in set(previous) - present:
        text_path(out_root, rel).unlink(missing_ok=True)
        if Path(rel).suffix.lower() in EXELEARNING:
            shutil.rmtree(brief / "text" / "media" / re.sub(r"[^\w.-]+", "-", rel).strip("-"), ignore_errors=True)
            state.get("exe", {}).pop(rel, None)
    if out_root.exists():
        for folder in sorted((d for d in out_root.rglob("*") if d.is_dir()), key=lambda d: len(d.parts), reverse=True):
            if not any(folder.iterdir()):
                folder.rmdir()
    state["files"] = current
    return rows, failed


def write_import_report(brief: Path, state: dict, lang: str) -> None:
    """`brief/import-report.md`: what the conversion of the eXeLearning packages left out or did not understand."""
    path = brief / REPORT
    saved = state.get("exe") or {}
    if not saved:
        path.unlink(missing_ok=True)
        return
    reports = [(f"sources/{rel}", exelearning.Report(**data)) for rel, data in sorted(saved.items())]
    path.write_text(exelearning.render_report(reports, lang), encoding="utf-8", newline="\n")


def browser_args(log=None) -> list[str]:
    """`--browser` and `--playwright` for web2md: the Chrome or Edge of the machine and the store workspace with playwright-core
    (installed the first time a blocked page needs it). Empty when there is no browser or the workspace cannot be installed."""
    from coursekit import store
    from coursekit.htmlkit.build import template_dir
    from coursekit.htmlkit.playcheck import find_browser

    browser = find_browser()
    if not browser:
        return []
    workspace = store.ensure_workspace("html-checker", template_dir() / "checker" / "package.json", log or (lambda m: None))
    return ["--browser", browser, "--playwright", str(workspace)] if workspace else []


def _web2md(node: str, url: str, folder: Path, extra: list[str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([node, str(WEB2MD), url, "--out", str(folder), *(extra or [])],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


DOCUMENT_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


def fetch_document(url: str) -> tuple[bytes, str] | None:
    """The file behind a link when it is a document (PDF, Word, PowerPoint, Excel) and not a web page: its bytes and its
    extension, by the type the server says or, when it says only "binary", by the extension of the address. None otherwise."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            kind = resp.headers.get_content_type()
            suffix = DOCUMENT_TYPES.get(kind)
            if suffix is None and kind in ("application/octet-stream", "binary/octet-stream", "application/download"):
                found = Path(urllib.parse.urlparse(resp.url).path).suffix.lower()
                suffix = found if found in DOCUMENT_TYPES.values() else None
            return (resp.read(), suffix) if suffix else None
    except (OSError, ValueError):  # unreachable or not HTTP: web2md tries it and says what happened
        return None


def save_document(url: str, body: bytes, suffix: str, folder: Path) -> tuple[str, dict] | None:
    """A downloaded document as Markdown in its folder of text/web/, as the files of sources/ are. A warning when it has no text."""
    folder.mkdir(parents=True, exist_ok=True)
    name = Path(urllib.parse.urlparse(url).path).stem or "document"
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"{name}{suffix}"
        src.write_bytes(body)
        text, problem = markitdown(src)
    if problem:
        return problem
    if not (text or "").strip():
        return note("document_no_text")
    (folder / f"{name}.md").write_text(f"<!-- {url} -->\n\n{text.strip()}\n", encoding="utf-8", newline="\n")
    return None


def download_links(brief: Path, state: dict, refresh: bool, log=None, links: list[tuple[str, str]] | None = None
                   ) -> tuple[list[dict], int]:
    """Each link of links.md (or the `links` given) as Markdown in text/web/<site>/: a Storybook read whole from its manifests,
    a link to a document (PDF, Office) with MarkItDown, any other site with web2md."""
    from coursekit import storybook

    web_root = brief / "text" / "web"
    previous = state.get("web", {})
    current, rows, failed = {}, [], 0
    links = parse_links(brief / "links.md") if links is None else links
    node = shutil.which("node")
    for url, comment in links:
        slug = site_slug(url)
        folder = web_root / slug
        info = dict(previous.get(slug, {}), url=url)
        root = storybook.detect(url) if refresh or not folder.exists() else info.get("storybook")
        if root and (refresh or not folder.exists()):
            if folder.exists():
                shutil.rmtree(folder)
            if log:
                log(i18n.t("brief", "downloading_storybook", url=url))
            done = storybook.download(root, folder)
            info.update(downloaded=dt.date.today().isoformat(), errors=False, storybook=root,
                        files=[p.relative_to(brief).as_posix() for p in done["files"]], manifests=done["manifests"])
        elif (refresh or not folder.exists()) and (document := fetch_document(url)) is not None:
            info.pop("storybook", None)
            if folder.exists():
                shutil.rmtree(folder)
            if log:
                log(i18n.t("brief", "downloading", url=url))
            problem = save_document(url, *document, folder)
            info.update(downloaded=dt.date.today().isoformat(), document=document[1].lstrip("."), blocked=[], rendered=0,
                        errors=False, problem=list(problem) if problem else None)
        elif refresh or not folder.exists():
            info.pop("storybook", None)
            info.pop("document", None)
            info.pop("problem", None)
            if node is None:
                failed += 1
                rows.append({"url": url, "note": comment, "folder": None, "pages": 0, "words": 0,
                             "downloaded": None, "notes": [note("node_missing")]})
                continue
            if folder.exists():
                shutil.rmtree(folder)
            if log:
                log(i18n.t("brief", "downloading", url=url))
            proc = _web2md(node, url, folder)
            if BLOCKED.search(proc.stderr or ""):  # empty or a check against robots: again, in the browser of the machine
                extra = browser_args(log)
                if extra:
                    if log:
                        log(i18n.t("brief", "rendering", url=url))
                    shutil.rmtree(folder, ignore_errors=True)
                    proc = _web2md(node, url, folder, extra)
            said = proc.stderr or ""
            info["downloaded"] = dt.date.today().isoformat()
            info["blocked"] = BLOCKED.findall(said)
            info["rendered"] = len(RENDERED.findall(said))
            info["errors"] = bool(PAGES_FAILED.search(said)) or (proc.returncode != 0 and not info["blocked"])
        pages = [p for p in folder.rglob("*.md") if p.name != "README.md"] if folder.exists() else []
        notes = [note("pages_failed")] if info.get("errors") else []
        if info.get("blocked"):
            notes.append(note("pages_blocked", count=len(info["blocked"]), pages=", ".join(info["blocked"][:3])))
        if info.get("rendered"):
            notes.append(note("pages_rendered", count=info["rendered"]))
        if info.get("storybook"):
            notes.append(note("storybook" if info.get("manifests") else "storybook_index_only"))
        if info.get("document"):
            notes.append(note("document", kind=info["document"].upper()))
        if info.get("problem"):
            notes.append(tuple(info["problem"]))
        elif folder.exists() and not pages and not info.get("blocked"):
            notes.append(note("no_web_text"))
        rows.append({"url": url, "note": comment, "folder": folder.relative_to(brief).as_posix() if folder.exists() else None,
                     "pages": len(pages), "words": sum(words(p.read_text(encoding="utf-8")) for p in pages),
                     "downloaded": info.get("downloaded"), "notes": notes})
        current[slug] = info
    for slug in set(previous) - set(current):
        shutil.rmtree(web_root / slug, ignore_errors=True)
    state["web"] = current
    return rows, failed


def cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def write_index(brief: Path, code: str, files: list[dict], webs: list[dict], general: str | None, lang: str) -> None:
    def say(key: str, **values: object) -> str:
        return i18n.t_in(lang, "brief", key, **values)

    def warnings(row: dict) -> str:
        return cell("; ".join(render(n, lang) for n in row["notes"]))

    notes_text = strip_frontmatter(re.sub(r"<!--.*?-->", "", (brief / "notes.md").read_text(encoding="utf-8"), flags=re.S))
    has_notes = words(re.sub(r"^#.*$", "", notes_text, flags=re.M)) > 0
    docs = [f for f in files if f["kind"] == "document"]
    total = sum(f["words"] for f in docs) + sum(w["words"] for w in webs)
    out = [
        say("index_title", code=code),
        "",
        *say("index_generated").rstrip("\n").split("\n"),
        "",
        say("index_updated", date=dt.date.today().isoformat(), documents=len(docs), webs=len(webs), words=fmt(total, lang),
            notes=say("answer_yes" if has_notes else "answer_no")),
        "",
    ]
    if general:
        out += [say("index_general", general=general), ""]
    if docs:
        out += [say("section_documents"), "", say("header_documents"), "|---|---|---:|---|"]
        out += [f"| {cell(f['title'])} (`{cell(f['source'])}`) | " + (f"`{f['text']}`" if f["text"] else "—")
                + f" | {fmt(f['words'], lang)} | {warnings(f)} |" for f in docs]
        out.append("")
    if webs:
        out += [say("section_webs"), "", say("header_webs"), "|---|---|---|---:|---:|---|---|"]
        out += [f"| {w['url']} | {cell(w['note'])} | " + (say("web_text_index", folder=w["folder"]) if w["folder"] else "—")
                + f" | {w['pages']} | {fmt(w['words'], lang)} | {w['downloaded'] or '—'} | {warnings(w)} |" for w in webs]
        out.append("")
    other = [f for f in files if f["kind"] != "document"]
    if other:
        out += [say("section_other"), "", say("other_intro"), "", say("header_other"), "|---|---|---|"]
        out += [f"| `{cell(f['source'])}` | {say('kind_' + f['kind'])} | {warnings(f)} |" for f in other]
        out.append("")
    if not (docs or webs or other):
        out += [say("index_empty"), ""]
    (brief / "index.md").write_text("\n".join(out), encoding="utf-8")


def build(brief: Path, title: str, refresh: bool = False, general: str | None = None, log=None, language: str = "es",
          importing: dict | None = None, forbidden: dict | None = None) -> dict:
    """Convert sources and links of one brief folder and write its index in `language` (the content's). Returns a summary."""
    (brief / "sources").mkdir(parents=True, exist_ok=True)
    state_path = brief / "text" / STATE
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    options = {"rules": (importing if importing is not None else configmod.package_defaults("import")).get("idevices"),
               "language": language, "forbidden": forbidden}
    files, failed_files = convert_files(brief, state, options)
    webs, failed_webs = download_links(brief, state, refresh, log)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not (brief / "notes.md").exists():
        (brief / "notes.md").write_text("", encoding="utf-8")
    write_import_report(brief, state, language)
    write_index(brief, title, files, webs, general, language)
    documents = [f for f in files if f["kind"] == "document"]
    return {
        "documents": len([f for f in documents if f["text"]]),
        "webs": len(webs),
        "media": len(files) - len(documents),
        "notes": [(item.get("source") or item.get("url"), render(n, i18n.language())) for item in [*files, *webs] for n in item["notes"]],
        "failed": failed_files + failed_webs,
    }
