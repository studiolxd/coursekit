"""The images of the reference material (`brief/`), so that the real material that already exists reaches the course: the
captures of a manual, the figures of the official documentation, the screenshots a person left.

- The images of the documents are extracted when `coursekit brief` converts them: from Word, PowerPoint and Excel (they carry
  them inside) and from PDF with `pdfimages` (poppler), when it is installed. They go to `brief/text/media/<document>/`, as the
  images of an eXeLearning package do. Icons and decorations (small images) are left out.
- The pages of a website keep their images in `brief/text/web/<site>/assets/` (web2md downloads them), with the alternative
  text the page gives them.
- `brief/images.md` lists all of them, with where each comes from, its size and its text, and whether it looks like a capture
  of a screen. The writer names one in "how it is made" and the media agent adopts it (`coursekit media adopt`).

Only the brief is read: what is in it is either the material of the client or official documentation the design or the writer
added (and a person confirmed or the review approved)."""

from __future__ import annotations

import re
import shutil
import subprocess
import zipfile
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from coursekit.i18n import t_in

IMAGES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff")
OFFICE_MEDIA = ("word/media/", "ppt/media/", "xl/media/")
MIN_SIDE = 200  # px: smaller ones are icons, bullets or decorations
LIST = "images.md"


def _size(path: Path) -> tuple[int, int] | None:
    try:
        with Image.open(path) as image:
            return image.size
    except (UnidentifiedImageError, OSError):
        return None


def _keep(path: Path) -> bool:
    size = _size(path)
    if size is None or min(size) < MIN_SIDE:
        path.unlink(missing_ok=True)
        return False
    return True


def extract(src: Path, out: Path) -> list[Path]:
    """The images of a document (Word, PowerPoint, Excel, PDF) in `out`, without the small ones. Nothing for another kind, or
    for a PDF when `pdfimages` is not installed."""
    shutil.rmtree(out, ignore_errors=True)
    found: list[Path] = []
    ext = src.suffix.lower()
    if ext in (".docx", ".pptx", ".xlsx"):
        try:
            with zipfile.ZipFile(src) as package:
                for name in package.namelist():
                    if name.startswith(OFFICE_MEDIA) and name.lower().endswith(IMAGES):
                        out.mkdir(parents=True, exist_ok=True)
                        target = out / Path(name).name
                        target.write_bytes(package.read(name))
                        if _keep(target):
                            found.append(target)
        except zipfile.BadZipFile:
            return []
    elif ext == ".pdf" and shutil.which("pdfimages"):
        out.mkdir(parents=True, exist_ok=True)
        subprocess.run(["pdfimages", "-png", "-p", str(src), str(out / "page")], capture_output=True, check=False, timeout=300)
        found = [p for p in sorted(out.glob("*.png")) if _keep(p)]
    if out.is_dir() and not any(out.iterdir()):
        out.rmdir()
    return found


def screen_like(path: Path) -> bool:
    """Whether an image looks like a capture of a screen: a screen's proportions and few colours (flat areas of an interface,
    not a photograph)."""
    try:
        with Image.open(path) as image:
            width, height = image.size
            if not (1.2 <= width / max(height, 1) <= 2.4) or width < 600:
                return False
            sample = image.convert("RGB").resize((160, max(1, round(160 * height / width))))
            colours = sample.getcolors(maxcolors=4096)
            return colours is not None and len(colours) < 1200
    except (UnidentifiedImageError, OSError):
        return False


def _web_alts(site: Path) -> dict[str, str]:
    """The alternative text the pages of a website give each of their images (`![alt](assets/x.png)`)."""
    alts: dict[str, str] = {}
    for page in site.rglob("*.md"):
        for alt, ref in re.findall(r"!\[([^\]]*)\]\(([^)\s]+)\)", page.read_text(encoding="utf-8", errors="replace")):
            if alt.strip():
                alts.setdefault(Path(ref).name, alt.strip())
    return alts


def catalog(brief: Path) -> list[dict]:
    """Every image of the brief: what a person left in sources/, the images of the documents and packages, those of the
    websites. Each with its file (from the course folder), its origin, its size, its text and whether it looks like a capture."""
    rows: list[dict] = []

    def add(path: Path, origin: str, text: str = "") -> None:
        size = _size(path)
        if size is None:
            return
        rows.append({"file": path.relative_to(brief.parent).as_posix(), "origin": origin, "width": size[0], "height": size[1],
                     "text": text, "screen": screen_like(path)})

    sources = brief / "sources"
    if sources.is_dir():
        for path in sorted(p for p in sources.rglob("*") if p.suffix.lower() in IMAGES and not p.name.startswith(".")):
            add(path, "source", path.stem.replace("_", " ").replace("-", " "))
    media = brief / "text" / "media"
    if media.is_dir():
        for folder in sorted(p for p in media.iterdir() if p.is_dir()):
            for path in sorted(p for p in folder.rglob("*") if p.suffix.lower() in IMAGES):
                add(path, "document", folder.name)
    web = brief / "text" / "web"
    if web.is_dir():
        for site in sorted(p for p in web.iterdir() if p.is_dir()):
            alts = _web_alts(site)
            for path in sorted(p for p in (site / "assets").rglob("*") if p.suffix.lower() in IMAGES) if (site / "assets").is_dir() else []:
                if min(_size(path) or (0, 0)) >= MIN_SIDE:
                    add(path, "web", alts.get(path.name, site.name))
    return rows


def write_list(brief: Path, lang: str) -> int:
    """`brief/images.md`: the images of the brief, for the writer and the media agent. Returns how many there are."""
    rows = catalog(brief)
    path = brief / LIST
    if not rows:
        path.unlink(missing_ok=True)
        return 0

    def say(key: str, **values: object) -> str:
        return t_in(lang, "brief", key, **values)

    out = [say("images_title"), "", say("images_intro"), "", say("images_header"), "|---|---|---|---|---|"]
    for row in rows:
        out.append(f"| `{row['file']}` | {say('images_origin_' + row['origin'])} | {row['width']}×{row['height']} | "
                   f"{say('answer_yes') if row['screen'] else '—'} | {row['text'].replace('|', '/')} |")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return len(rows)
