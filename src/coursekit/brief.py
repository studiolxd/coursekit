"""`coursekit brief`: prepare the reference material (brief/) of a course or of the project.

The person drops files of any format in brief/sources/, lists web documentation in
brief/links.md and writes indications in brief/notes.md. This converts all of it to Markdown in
brief/text/ and writes brief/index.md, which is what the design, writing and review agents read:

    sources/<path>      -> text/files/<path>.md   (MarkItDown)
    links.md (URLs)     -> text/web/<site>/       (web2md.js, Node)

Only new or changed files are converted; URLs are downloaded once (refresh downloads them again).
Images are listed for the agents to open directly; audio and video need a transcript.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import subprocess
from importlib import resources
from pathlib import Path

from coursekit.lang import format_number
from coursekit.util import sha256_file

WEB2MD = Path(str(resources.files("coursekit.tools").joinpath("web2md.js")))


def fmt(number: int) -> str:
    return format_number(number, "es")


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


def markitdown(src: Path) -> tuple[str | None, str | None]:
    try:
        from markitdown import MarkItDown
    except ImportError:
        return None, "falta MarkItDown (coursekit setup)"
    try:
        return MarkItDown().convert(str(src)).text_content or "", None
    except Exception as exc:  # noqa: BLE001 — any converter error is reported per file
        return None, f"no se pudo convertir: {type(exc).__name__}: {str(exc)[:200]}"


def text_path(out_root: Path, rel: str) -> Path:
    """text/files/<rel>.md, without doubling the extension of Markdown sources."""
    return out_root / (rel if Path(rel).suffix.lower() in (".md", ".markdown") else f"{rel}.md")


def convert_files(brief: Path, state: dict) -> tuple[list[dict], int]:
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
            row["notes"].append(f"pesa {size_mb:.0f} MB: mejor fuera de git (enlace o transcripción)")
        if ext in IMAGES:
            row["kind"] = "imagen"
            rows.append(row)
            continue
        if ext in AUDIO_VIDEO:
            row["kind"] = "audio/vídeo"
            row["notes"].append("sin transcripción: añade un .vtt/.txt con el texto")
            rows.append(row)
            continue
        row["kind"] = "documento"
        present.add(rel)
        target = text_path(out_root, rel)
        digest = sha256_file(src)
        current[rel] = digest
        if previous.get(rel) != digest or not target.exists():
            if ext in COPY:
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
        if row["words"] < MIN_WORDS:
            row["notes"].append("casi sin texto: ¿escaneado? necesita OCR")
        rows.append(row)
    # Remove conversions of files that are no longer in sources/.
    for rel in set(previous) - present:
        text_path(out_root, rel).unlink(missing_ok=True)
    if out_root.exists():
        for folder in sorted((d for d in out_root.rglob("*") if d.is_dir()), key=lambda d: len(d.parts), reverse=True):
            if not any(folder.iterdir()):
                folder.rmdir()
    state["files"] = current
    return rows, failed


def download_links(brief: Path, state: dict, refresh: bool, log=None) -> tuple[list[dict], int]:
    web_root = brief / "text" / "web"
    previous = state.get("web", {})
    current, rows, failed = {}, [], 0
    links = parse_links(brief / "links.md")
    node = shutil.which("node")
    for url, note in links:
        slug = site_slug(url)
        folder = web_root / slug
        info = dict(previous.get(slug, {}), url=url)
        if refresh or not folder.exists():
            if node is None:
                failed += 1
                rows.append({"url": url, "note": note, "folder": None, "pages": 0, "words": 0,
                             "downloaded": None, "notes": ["falta Node (nodejs.org)"]})
                continue
            if folder.exists():
                shutil.rmtree(folder)
            if log:
                log(f"descargando {url} …")
            proc = subprocess.run([node, str(WEB2MD), url, "--out", str(folder)],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace")
            info["downloaded"] = dt.date.today().isoformat()
            info["errors"] = proc.returncode != 0
        pages = [p for p in folder.rglob("*.md") if p.name != "README.md"] if folder.exists() else []
        notes = ["algunas páginas fallaron (coursekit brief --refresh)"] if info.get("errors") else []
        if folder.exists() and not pages:
            notes.append("no se extrajo texto (¿web con JavaScript?)")
        rows.append({"url": url, "note": note, "folder": folder.relative_to(brief).as_posix() if folder.exists() else None,
                     "pages": len(pages), "words": sum(words(p.read_text(encoding="utf-8")) for p in pages),
                     "downloaded": info.get("downloaded"), "notes": notes})
        current[slug] = info
    for slug in set(previous) - set(current):
        shutil.rmtree(web_root / slug, ignore_errors=True)
    state["web"] = current
    return rows, failed


def cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def write_index(brief: Path, code: str, files: list[dict], webs: list[dict], general: str | None = None) -> None:
    notes_text = strip_frontmatter(re.sub(r"<!--.*?-->", "", (brief / "notes.md").read_text(encoding="utf-8"), flags=re.S))
    has_notes = words(re.sub(r"^#.*$", "", notes_text, flags=re.M)) > 0
    docs = [f for f in files if f["kind"] == "documento"]
    total = sum(f["words"] for f in docs) + sum(w["words"] for w in webs)
    out = [
        f"# Material de referencia — {code}",
        "",
        "> Generado por `coursekit brief`. No lo edites: cambia `sources/`, `links.md` o `notes.md` y",
        "> vuelve a ejecutarlo. Agentes: leed este índice, luego `notes.md` y abrid en `text/` solo",
        "> lo que toque a vuestra tarea. Los originales de `sources/` solo para imágenes.",
        "",
        f"Actualizado: {dt.date.today().isoformat()} · {len(docs)} documentos · {len(webs)} webs · "
        f"{fmt(total)} palabras · indicaciones en `notes.md`: {'sí' if has_notes else 'no'}",
        "",
    ]
    if general:
        out += [f"Material general del proyecto: `{general}` (léelo también).", ""]
    if docs:
        out += ["## Documentos", "", "| Documento | Texto | Palabras | Avisos |", "|---|---|---:|---|"]
        out += [f"| {cell(f['title'])} (`{cell(f['source'])}`) | " + (f"`{f['text']}`" if f["text"] else "—")
                + f" | {fmt(f['words'])} | {cell('; '.join(f['notes']))} |" for f in docs]
        out.append("")
    if webs:
        out += ["## Webs", "", "| URL | Nota | Texto | Páginas | Palabras | Descargada | Avisos |", "|---|---|---|---:|---:|---|---|"]
        out += [f"| {w['url']} | {cell(w['note'])} | " + (f"`{w['folder']}/` (índice: `README.md`)" if w["folder"] else "—")
                + f" | {w['pages']} | {fmt(w['words'])} | {w['downloaded'] or '—'} | {cell('; '.join(w['notes']))} |" for w in webs]
        out.append("")
    other = [f for f in files if f["kind"] != "documento"]
    if other:
        out += ["## Imágenes, audio y vídeo", "", "Sin texto: las imágenes se abren directamente desde `sources/`.", "",
                "| Fichero | Tipo | Avisos |", "|---|---|---|"]
        out += [f"| `{cell(f['source'])}` | {f['kind']} | {cell('; '.join(f['notes']))} |" for f in other]
        out.append("")
    if not (docs or webs or other):
        out += ["Sin material todavía: deja ficheros en `sources/` o URLs en `links.md`.", ""]
    (brief / "index.md").write_text("\n".join(out), encoding="utf-8")


def build(brief: Path, title: str, refresh: bool = False, general: str | None = None, log=None) -> dict:
    """Convert sources and links of one brief folder and write its index. Returns a summary."""
    (brief / "sources").mkdir(parents=True, exist_ok=True)
    state_path = brief / "text" / STATE
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    files, failed_files = convert_files(brief, state)
    webs, failed_webs = download_links(brief, state, refresh, log)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not (brief / "notes.md").exists():
        (brief / "notes.md").write_text("", encoding="utf-8")
    write_index(brief, title, files, webs, general)
    documents = [f for f in files if f["kind"] == "documento"]
    return {
        "documents": len([f for f in documents if f["text"]]),
        "webs": len(webs),
        "media": len(files) - len(documents),
        "notes": [(item.get("source") or item.get("url"), note) for item in [*files, *webs] for note in item["notes"]],
        "failed": failed_files + failed_webs,
    }
