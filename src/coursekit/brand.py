"""The brand material of a project (theme/branding/) or of a course (courses/<CODE>/theme/branding/): the folder, the fonts the
media are made with, and the conversion of what a person leaves there (`coursekit brand`)."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from coursekit import config as configmod
from coursekit import i18n
from coursekit.i18n import t
from coursekit.project import Project

FONTS_SHEET = Path("fonts") / "fonts.css"
FONT_TYPES = {".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf", ".otf": "font/otf"}


class BrandError(Exception):
    pass


def folder(project: Project, course: dict | None = None) -> Path:
    """The brand folder of a course when it has one of its own, else the project's."""
    if course is not None:
        own = course["_dir"] / "theme" / "branding"
        if own.is_dir() and any(p for p in own.iterdir() if not p.name.startswith(".")):
            return own
    return project.theme_dir / "branding"


def fonts_stylesheet(project: Project, course: dict | None = None) -> Path | None:
    """The stylesheet with the @font-face rules of the brand that every resource made on this machine is drawn with (a video,
    an SVG exported as PNG): media.yaml › fonts, a path from the project; `auto` (the default) is theme/branding/fonts/fonts.css
    of the course, else of the project, when it exists; null, none."""
    value = configmod.effective("media", project, course).value.get("fonts", "auto")
    if value in (None, "", "none", False):
        return None
    if str(value) != "auto":
        return project.root / str(value)
    for base in ([course["_dir"] / "theme" / "branding"] if course is not None else []) + [project.theme_dir / "branding"]:
        if (base / FONTS_SHEET).is_file():
            return base / FONTS_SHEET
    return None


def inline_fonts(sheet: Path, root: Path) -> tuple[str, list[str]]:
    """A stylesheet of @font-face rules with each font file inside as data (so what draws with it needs no file and no
    network), and the families it declares. Its files must be inside the project."""
    name = sheet.relative_to(root).as_posix() if sheet.is_relative_to(root) else sheet.as_posix()
    if not sheet.is_file():
        raise BrandError(t("video", "fonts_missing", path=name))
    css = re.sub(r"/\*.*?\*/", "", sheet.read_text(encoding="utf-8"), flags=re.S)

    def inline(match: re.Match) -> str:
        ref = match.group(2).strip()
        if ref.startswith("data:"):
            return match.group(0)
        if re.match(r"^[a-z]+:", ref, re.I) or ref.startswith("//"):
            raise BrandError(t("video", "font_remote", url=ref, path=name))
        file = (sheet.parent / ref.split("?")[0].split("#")[0]).resolve()
        if not file.is_file() or root.resolve() not in file.parents:
            raise BrandError(t("video", "font_file_missing", file=ref, path=name))
        kind = FONT_TYPES.get(file.suffix.lower(), "application/octet-stream")
        return f'url("data:{kind};base64,{base64.b64encode(file.read_bytes()).decode()}")'

    css = re.sub(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)""", inline, css)
    families = sorted({f.strip().strip("'\"") for f in re.findall(r"font-family\s*:\s*([^;}]+)", css)})
    if not families:
        raise BrandError(t("video", "fonts_empty", path=name))
    return css, families


# ── `coursekit brand`: what a person leaves in the brand folder, ready for the agents ──────────────────

DOCUMENTS = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".odt", ".odp", ".html", ".htm", ".md", ".markdown", ".txt", ".rtf",
             ".epub"}
FONT_FILES = {".woff2", ".woff", ".ttf", ".otf"}
IMAGES = {".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico"}
LOGO_WORDS = ("logo", "logotipo", "logotype", "logomark", "isotipo", "isologo", "imagotipo", "brandmark", "wordmark")
GENERATED = "/* Written by coursekit brand from the fonts of the brand folder. Leave your own @font-face sheet in sources/. */"
ICON_FOLDERS = {"icons", "iconos", "icon", "glyphs", "glifos"}
TOKEN_FILES = {"tokens", "design-tokens", "variables", "theme", "colors", "colours"}  # what a package keeps its tokens in
ARCHIVES = (".tgz", ".tar.gz", ".zip")
NPM_URL = re.compile(r"^https?://(?:www\.)?npmjs\.com/package/((?:@[^/?#]+/)?[^/?#]+)(?:/v/([^/?#]+))?", re.I)
NPM_REGISTRY = "https://registry.npmjs.org"
GOOGLE_SUBSETS = ("latin", "latin-ext")
MAX_TEXT = 200_000  # characters of a token file copied into the text


def course_folder(course: dict) -> Path:
    return course["_dir"] / "theme" / "branding"


def target_folder(project: Project, course: dict | None) -> Path:
    """Where `coursekit brand` works: the folder of the course with --course, else the project's."""
    return course_folder(course) if course is not None else project.theme_dir / "branding"


def prepare(base: Path, lang: str) -> None:
    """The folders and the two files a person fills (links.md with its two parts, notes.md), when they are missing."""
    (base / "sources").mkdir(parents=True, exist_ok=True)
    if not (base / "links.md").exists():
        (base / "links.md").write_text(i18n.t_in(lang, "brand", "links_template"), encoding="utf-8", newline="\n")
    if not (base / "notes.md").exists():
        (base / "notes.md").write_text(i18n.t_in(lang, "brand", "notes_template"), encoding="utf-8", newline="\n")


def style_headings() -> set[str]:
    return {i18n.t_in(code, "brand", "links_style_heading").strip("# ").lower() for code in ("es", "en")}


def illustration_headings() -> set[str]:
    return {i18n.t_in(code, "brand", "links_illustrations_heading").strip("# ").lower() for code in ("es", "en")}


def parse_links(path: Path) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str]]]:
    """(links whose content is read, links whose style is observed, sources of illustrations): by the heading they are under,
    in either language; a link under any other heading, or under none, is read."""
    from coursekit import brief

    if not path.exists():
        return [], [], []
    found_by = {"content": [], "style": [], "illustrations": []}
    section = "content"
    text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
    style, illustrations = style_headings(), illustration_headings()
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            title = line.strip("# \t").lower()
            section = "style" if title in style else "illustrations" if title in illustrations else "content"
            continue
        found = brief.LINK.match(line)
        if found:
            found_by[section].append((found.group(1), (found.group(2) or "").strip()))
    return found_by["content"], found_by["style"], found_by["illustrations"]


REFERENCES = 6  # previews of a source of illustrations kept in style/ (a preview costs no download)


def _illustration_sources(base: Path, links: list[tuple[str, str]], refresh: bool) -> list[dict]:
    """The sources of illustrations in illustration-sources.json, each with the id of its author on Magnific and a few previews
    of its work in style/. A link that is not the page of an author on Magnific is kept as a reference only."""
    from coursekit import illustrations

    known = {s["url"]: s for s in illustrations.load(base)}
    sources = []
    for url, comment in links:
        source = {"url": url, "note": comment, "provider": None, "author": None, "author_id": None, "error": None}
        slug = illustrations.author_of(url)
        if slug:
            source.update(provider="magnific", author=slug)
            if url in known and known[url].get("author_id") and not refresh:
                source["author_id"] = known[url]["author_id"]
            else:
                try:
                    source["author_id"] = illustrations.resolve(slug)
                    if source["author_id"] is None:
                        source["error"] = i18n.t("illustrations", "author_not_found", author=slug)
                    else:
                        _previews(base, source)
                except illustrations.IllustrationError as exc:
                    source["error"] = str(exc)
        sources.append(source)
    path = base / illustrations.SOURCES
    if sources:
        path.write_text(json.dumps(sources, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        path.unlink(missing_ok=True)
    return sources


def _previews(base: Path, source: dict) -> None:
    from coursekit import illustrations

    found = illustrations.get("resources", {"term": "illustration", "filters[author]": source["author_id"], "limit": REFERENCES})
    style = base / "style"
    style.mkdir(parents=True, exist_ok=True)
    for item in (found.get("data") or [])[:REFERENCES]:
        url = ((item.get("image") or {}).get("source") or {}).get("url")
        if url:
            (style / f"source-{source['author']}-{item['id']}.jpg").write_bytes(illustrations.fetch(url))


def _words(name: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9]+", name.lower()) if w]


def _classify(path: Path, base: Path | None = None) -> str:
    ext = path.suffix.lower()
    parts = {p.lower() for p in (path.relative_to(base).parts[:-1] if base else ())}
    if path.name.lower().endswith(ARCHIVES):
        return "archive"
    if ext == ".svg" and parts & ICON_FOLDERS:
        return "icon"
    if ext in FONT_FILES:
        return "font"
    if ext == ".css":
        return "font_sheet" if "@font-face" in path.read_text(encoding="utf-8", errors="replace") else "tokens"
    if ext == ".json":
        return "tokens"
    if path.stem.lower().startswith(("license", "licence", "ofl", "licencia")):
        return "licence"
    if ext in IMAGES:
        return "logo" if set(_words(path.stem)) & set(LOGO_WORDS) else "image"
    if ext in DOCUMENTS:
        return "document"
    return "other"


def _family_of(path: Path) -> tuple[str, str, str]:
    """(family, style, weight) of a font file from its name, e.g. acme-sans-italic-700.woff2: a guess the index says to check."""
    words = re.split(r"[-_ ]+", path.stem)
    style = "italic" if any(w.lower() in ("italic", "it", "oblique") for w in words) else "normal"
    weight = next((w for w in words if re.fullmatch(r"[1-9]00", w)), None)
    named = {"thin": "100", "light": "300", "regular": "400", "medium": "500", "semibold": "600", "bold": "700", "black": "900"}
    weight = weight or next((named[w.lower()] for w in words if w.lower() in named), "1 1000")
    skip = {"italic", "it", "oblique", "normal", "latin", "ext", "variable", "vf", *named}
    family = " ".join(w.capitalize() for w in words if w.lower() not in skip and not re.fullmatch(r"[1-9]00|wght|opsz", w.lower()))
    return family or path.stem, style, weight


def _google_fonts(urls: list[str], fonts_dir: Path, known: set[str] = frozenset()) -> list[dict]:
    """The font files of some Google Fonts stylesheets (open licences), in fonts/<family>/, and their @font-face rules."""
    from coursekit import storybook

    rules = []
    for url in urls:
        css = (storybook.get(url) or b"").decode("utf-8", "replace")
        for subset, block in re.findall(r"(?:/\*\s*([\w-]+)\s*\*/\s*)?@font-face\s*\{([^}]*)\}", css):
            if subset and subset not in GOOGLE_SUBSETS:  # the alphabets of the courses, not every one Google serves
                continue
            family = re.search(r"font-family:\s*['\"]?([^;'\"]+)", block)
            src = re.search(r"url\(([^)]+)\)", block)
            if not family or not src:
                continue
            name = family.group(1).strip()
            if name in known:  # the brand already brings its files
                continue
            body = storybook.get(src.group(1).strip("'\""))
            if body is None:
                continue
            folder = fonts_dir / storybook.slug(name)
            folder.mkdir(parents=True, exist_ok=True)
            style = (re.search(r"font-style:\s*([^;]+)", block) or [None, "normal"])[1].strip()
            file = folder / f"{storybook.slug(name)}-{style}-{subset or 'all'}.woff2"
            file.write_bytes(body)
            (folder / "LICENSE.txt").write_text(i18n.t_in("en", "brand", "google_licence", family=name), encoding="utf-8")
            kept = re.sub(r"\s*src:[^;]+;", "", block).strip()
            rules.append({"family": name, "origin": "google", "css": f"@font-face {{\n  {kept}\n  src: url('./{folder.name}/{file.name}')"
                          " format('woff2');\n}"})
    return rules


def _font_rules(base: Path, found: dict[str, list[Path]], google: list[str]) -> list[dict]:
    """The @font-face rules of the brand: a sheet left in sources/ (its files copied next to it in fonts/), font files left
    alone (their family guessed from the name), then the Google Fonts the brand uses; the first one of a family wins."""
    fonts_dir = base / "fonts"
    rules: list[dict] = []
    for sheet in found.get("font_sheet", []):
        css = re.sub(r"/\*.*?\*/", "", sheet.read_text(encoding="utf-8", errors="replace"), flags=re.S)
        for ref in re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", css):
            source = (sheet.parent / ref).resolve()
            if source.is_file() and base.resolve() in source.parents:  # sources/, or a package unpacked in text/archives/
                target = fonts_dir / source.relative_to(sheet.parent.resolve())
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
        for block in re.findall(r"@font-face\s*\{[^}]*\}", css):
            family = re.search(r"font-family:\s*['\"]?([^;'\"]+)", block)
            rules.append({"family": family.group(1).strip() if family else "?", "origin": "sheet", "css": block})
    sheet_files = {p.resolve() for s in found.get("font_sheet", []) for p in s.parent.rglob("*")}
    for file in found.get("font", []):
        if file.resolve() in sheet_files:
            continue
        family, style, weight = _family_of(file)
        target = fonts_dir / storybook_slug(family) / file.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(file.read_bytes())
        kind = {".woff2": "woff2", ".woff": "woff", ".ttf": "truetype", ".otf": "opentype"}[file.suffix.lower()]
        rules.append({"family": family, "origin": "file", "css": f"@font-face {{\n  font-family: '{family}';\n  font-style: {style};\n"
                      f"  font-weight: {weight};\n  src: url('./{target.parent.name}/{file.name}') format('{kind}');\n}}"})
    for licence in found.get("licence", []):
        near = [r for r in rules if r["origin"] == "file"]
        if near:
            (fonts_dir / licence.name).write_bytes(licence.read_bytes())
    known = {r["family"] for r in rules}
    rules += _google_fonts(google, fonts_dir, known) if google else []
    return rules


def storybook_slug(text: str) -> str:
    from coursekit import storybook

    return storybook.slug(text)


def _visible(sources: Path) -> list[Path]:
    return sorted(p for p in sources.rglob("*") if p.is_file() and not any(part.startswith(".") for part in p.relative_to(sources).parts))


def _document(src: Path, rel: str, base: Path, state: dict) -> dict:
    """A document of sources/ as Markdown in text/files/ (converted again only when it changed)."""
    from coursekit import brief
    from coursekit.util import sha256_file

    target = brief.text_path(base / "text" / "files", rel)
    digest = sha256_file(src)
    row = {"source": f"sources/{rel}", "text": None, "words": 0, "notes": []}
    if state.get(rel) != digest or not target.exists():
        if src.suffix.lower() in brief.COPY:
            body, error = src.read_text(encoding="utf-8", errors="replace"), None
        else:
            body, error = brief.markitdown(src)
        if error:
            row["notes"].append(error)
            return row
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"---\nsource: sources/{rel}\n---\n\n" + brief.strip_frontmatter(body).strip() + "\n", encoding="utf-8")
    state[rel] = digest
    text = target.read_text(encoding="utf-8")
    row.update(text=target.relative_to(base).as_posix(), words=brief.words(text))
    return row


def _copy(src: Path, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / src.name
    target.write_bytes(src.read_bytes())
    return target


def build(project: Project, course: dict | None = None, refresh: bool = False, log=None) -> dict:
    """Read what a person left in the brand folder (sources/, links.md, notes.md): documents and pages as Markdown in text/,
    a whole Storybook, the style observed on a website, the fonts (fonts/fonts.css), logos (logo/), token files (tokens/), and
    the index of all of it (index.md) that the agents read first. Returns a summary."""
    from coursekit import brief
    from coursekit import course as coursemod

    base = target_folder(project, course)
    lang = coursemod.language(course) if course is not None else str(configmod.project_data(project).get("content_language") or "es")
    prepare(base, lang)
    state_path = base / "text" / ".state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    found: dict[str, list[Path]] = {}
    for src in _visible(base / "sources"):
        found.setdefault(_classify(src, base / "sources"), []).append(src)
    for archive in found.get("archive", []):  # a brand kit or the package of a design system: only what the media use
        for kind, files in _unpack(archive, base).items():
            found.setdefault(kind, []).extend(files)
    content, style, illustration_links = parse_links(base / "links.md")
    packages = [_package(url, comment, base, state.setdefault("packages", {}), refresh) for url, comment in content if NPM_URL.match(url)]
    content = [(url, comment) for url, comment in content if not NPM_URL.match(url)]
    for package in packages:  # a package of npm named in links.md: as if its .tgz were in sources/
        if package.get("file"):
            for kind, files in _unpack(base / package["file"], base).items():
                found.setdefault(kind, []).extend(files)
    documents = [_document(src, src.relative_to(base / "sources").as_posix(), base, state.setdefault("files", {}))
                 for src in found.get("document", [])]
    for src in found.get("tokens", []):
        _copy(src, base / "tokens")
        text = src.read_text(encoding="utf-8", errors="replace")[:MAX_TEXT]
        target = base / "text" / "tokens" / f"{src.name}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"---\nsource: {src.relative_to(base).as_posix()}\n---\n\n```{src.suffix[1:]}\n{text}\n```\n", encoding="utf-8")
    icons = [_copy(src, base / "icons") for src in found.get("icon", [])]
    logos = [_copy(src, base / "logo") for src in found.get("logo", []) if src.suffix.lower() in IMAGES]
    webs, failed = brief.download_links(base, state, refresh, log, links=content)
    google: list[str] = []
    for info in (state.get("web") or {}).values():
        if info.get("storybook"):
            google += [u for u in storybook_fonts(info["storybook"])]
            logos += [_copy(base / f, base / "logo") for f in info.get("files") or []
                      if set(_words(Path(f).stem)) & set(LOGO_WORDS) and (base / f).is_file()]
    observed = []
    for url, comment in style:
        row = observe(url, base, refresh, log)
        row["note"] = comment
        observed.append(row)
        google += row.get("google") or []
        failed += 1 if row.get("error") else 0
    sources = _illustration_sources(base, illustration_links, refresh)
    failed += sum(1 for s in sources if s.get("error")) + sum(1 for p in packages if p.get("error"))
    rules = _font_rules(base, found, sorted(set(google)))
    sheet = base / FONTS_SHEET
    notes = []
    if rules and (not sheet.exists() or sheet.read_text(encoding="utf-8").startswith(GENERATED)):
        sheet.parent.mkdir(parents=True, exist_ok=True)
        sheet.write_text(GENERATED + "\n\n" + "\n\n".join(r["css"] for r in rules) + "\n", encoding="utf-8", newline="\n")
    elif rules:
        notes.append(i18n.t_in(lang, "brand", "sheet_kept", path=FONTS_SHEET.as_posix()))
    have = {r["family"].lower() for r in rules}
    missing = sorted({f for row in observed for f in row.get("families") or [] if f.lower() not in have})
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_index(base, lang, documents, webs, observed, rules, missing, logos, found, notes, icons, sources, packages)
    return {"folder": base, "documents": len(documents), "webs": len(webs), "observed": len(observed),
            "fonts": sorted({r["family"] for r in rules}), "missing_fonts": missing, "logos": len(logos), "icons": len(icons),
            "failed": failed}


def npm_fetch(url: str) -> bytes:
    """What the registry of npm serves (the tests stand in for it)."""
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "coursekit", "Accept": "application/json, application/octet-stream"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def _package(url: str, note: str, base: Path, state: dict, refresh: bool) -> dict:
    """A package of npm named in links.md (https://www.npmjs.com/package/<name>, or …/v/<version> for one version): its .tgz
    from the registry into packages/, downloaded again only when the version changes. A private package is not reached."""
    import urllib.error
    import urllib.parse

    name, pinned = NPM_URL.match(url).groups()
    row = {"url": url, "note": note, "name": name, "version": pinned, "file": None, "error": None}
    try:
        meta = json.loads(npm_fetch(f"{NPM_REGISTRY}/{urllib.parse.quote(name, safe='@')}"))
        version = pinned or (meta.get("dist-tags") or {}).get("latest")
        tarball = (((meta.get("versions") or {}).get(version) or {}).get("dist") or {}).get("tarball")
        if not tarball:
            row["error"] = i18n.t("brand", "package_no_version", name=name, version=version or "latest")
            return row
        target = base / "packages" / f"{name.lstrip('@').replace('/', '-')}-{version}.tgz"
        if refresh or not target.exists() or state.get(url) != version:
            target.parent.mkdir(parents=True, exist_ok=True)
            for old in target.parent.glob(f"{name.lstrip('@').replace('/', '-')}-*.tgz"):
                old.unlink()
            target.write_bytes(npm_fetch(tarball))
        state[url] = version
        row.update(version=version, file=target.relative_to(base).as_posix())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        row["error"] = i18n.t("brand", "package_failed", name=name, reason=getattr(exc, "reason", exc))
    return row


def _unpack(archive: Path, base: Path) -> dict[str, list[Path]]:
    """The files of a brand kit (.zip) or of the package of a design system (.tgz) the media use: @font-face sheets and font
    files, icons (a folder icons/ or glyphs/), logos and token files; never its code. Unpacked into text/archives/<name>/."""
    import shutil
    import tarfile
    import zipfile

    name = re.sub(r"(\.tar)?\.(tgz|gz|zip)$", "", archive.name, flags=re.I)
    out = base / "text" / "archives" / name
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    keep = FONT_FILES | IMAGES | {".css", ".json", ".txt", ""}
    wanted = lambda member: Path(member).suffix.lower() in keep and "node_modules" not in member  # noqa: E731
    if archive.name.lower().endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            for member in zf.namelist():
                target = (out / member).resolve()
                if member.endswith("/") or not wanted(member) or out.resolve() not in target.parents:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(member))
    else:
        with tarfile.open(archive) as tf:
            members = [m for m in tf.getmembers() if m.isfile() and wanted(m.name)]
            tf.extractall(out, members=members, filter="data")
    found: dict[str, list[Path]] = {}
    for file in sorted(p for p in out.rglob("*") if p.is_file()):
        kind = _classify(file, out)
        if kind == "tokens" and file.stem.lower() not in TOKEN_FILES:
            continue  # a package.json, the stylesheet of a component: not the tokens of the brand
        if kind == "image" or kind == "document" or kind == "other":
            continue
        found.setdefault(kind, []).append(file)
    return found


def storybook_fonts(root: str) -> list[str]:
    from coursekit import storybook

    return storybook.font_links(root)


def _cell(text: object) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def write_index(base: Path, lang: str, documents: list[dict], webs: list[dict], observed: list[dict], rules: list[dict],
                missing: list[str], logos: list[Path], found: dict[str, list[Path]], notes: list[str],
                icons: list[Path] | None = None, sources: list[dict] | None = None, packages: list[dict] | None = None) -> None:
    from coursekit import brief

    def say(key: str, **values) -> str:
        return i18n.t_in(lang, "brand", key, **values)

    rel = lambda p: p.relative_to(base).as_posix()  # noqa: E731
    notes_text = re.sub(r"<!--.*?-->", "", (base / "notes.md").read_text(encoding="utf-8"), flags=re.S)
    has_notes = brief.words(re.sub(r"(?m)^#.*$", "", notes_text)) > 0
    out = [say("index_title"), "", say("index_intro"), "", say("index_notes", answer=say("yes" if has_notes else "no")), ""]
    if documents:
        out += [say("section_documents"), "", say("header_documents"), "|---|---|---:|---|"]
        out += [f"| `{_cell(d['source'])}` | " + (f"`{d['text']}`" if d["text"] else "—") + f" | {d['words']} | "
                f"{_cell('; '.join(brief.render(n, lang) for n in d['notes']))} |" for d in documents]
        out.append("")
    if webs:
        out += [say("section_webs"), "", say("header_webs"), "|---|---|---|---:|---|"]
        out += [f"| {w['url']} | {_cell(w['note'])} | " + (f"`{w['folder']}/README.md`" if w["folder"] else "—") + f" | {w['pages']} | "
                f"{_cell('; '.join(brief.render(n, lang) for n in w['notes']))} |" for w in webs]
        out.append("")
    if packages:
        out += [say("section_packages"), "", say("packages_intro"), "", say("header_packages"), "|---|---|---|---|"]
        out += [f"| {p['url']} | {_cell(p['note'])} | {_cell(p['version'] or '—')} | "
                + _cell(p["error"] or (f"`{p['file']}`" if p["file"] else "")) + " |" for p in packages]
        out.append("")
    if observed:
        out += [say("section_observed"), "", say("observed_intro"), "", say("header_observed"), "|---|---|---|---|"]
        out += [f"| {o['url']} | {_cell(o.get('note') or '')} | " + (f"`{o['file']}`" if o.get("file") else "—") + " | "
                + _cell(o.get("error") or "") + " |" for o in observed]
        out.append("")
    if rules:
        families: dict[str, set[str]] = {}
        for r in rules:
            families.setdefault(r["family"], set()).add(say(f"origin_{r['origin']}"))
        out += [say("section_fonts"), "", say("fonts_intro", path=FONTS_SHEET.as_posix()), "", say("header_fonts"), "|---|---|"]
        out += [f"| {_cell(f)} | {_cell(', '.join(sorted(o)))} |" for f, o in sorted(families.items())]
        out.append("")
    if missing:
        out += [say("section_missing_fonts"), "", say("missing_fonts", families=", ".join(missing)), ""]
    if icons:
        out += [say("section_icons"), "", say("icons_line", count=len(icons), path="icons/"), ""]
    if sources:
        out += [say("section_illustrations"), "", say("illustrations_intro"), "", say("header_illustrations"), "|---|---|---|---|"]
        for s in sources:
            state = s.get("error") or (say("source_author", author=s["author"], id=s["author_id"]) if s.get("author_id")
                                       else say("source_reference"))
            out.append(f"| {s['url']} | {_cell(s.get('note') or '')} | {_cell(state)} | "
                       + ", ".join(f"`{rel(p)}`" for p in sorted((base / "style").glob(f"source-{s.get('author')}-*.jpg"))[:3]) + " |")
        out.append("")
    listed = [("section_logos", logos), ("section_tokens", sorted((base / "tokens").glob("*")) if (base / "tokens").is_dir() else []),
              ("section_images", found.get("image", [])), ("section_other", found.get("other", []))]
    for key, files in listed:
        if files:
            out += [say(key), ""] + [f"- `{rel(p)}`" for p in sorted(set(files))] + [""]
    out += [f"> {n}" for n in notes]
    if len(out) <= 7:
        out += [say("index_empty"), ""]
    (base / "index.md").write_text("\n".join(out).rstrip() + "\n", encoding="utf-8", newline="\n")


GENERIC_FONTS = {"serif", "sans-serif", "monospace", "system-ui", "ui-sans-serif", "ui-monospace", "ui-serif", "cursive", "fantasy",
                 "-apple-system", "blinkmacsystemfont", "segoe ui", "arial", "helvetica", "helvetica neue", "times new roman", "georgia"}


def observe(url: str, base: Path, refresh: bool = False, log=None) -> dict:
    """The style of a website as a browser draws it, in text/observed/<site>.md (and .json), with its screenshots in style/: clues
    for the agent, never rules of the brand. Run again only with --refresh."""
    import shutil
    import subprocess
    import tempfile

    from coursekit import brief, store
    from coursekit.htmlkit.build import template_dir
    from coursekit.htmlkit.playcheck import find_browser

    slug = brief.site_slug(url)
    md, data_file = base / "text" / "observed" / f"{slug}.md", base / "text" / "observed" / f"{slug}.json"
    row = {"url": url, "file": md.relative_to(base).as_posix() if md.exists() else None}
    if md.exists() and data_file.exists() and not refresh:
        seen = json.loads(data_file.read_text(encoding="utf-8"))
        return {**row, "families": _families(seen), "google": seen.get("google") or []}
    node = shutil.which("node")
    if not node:
        return {**row, "error": i18n.t("brand", "observe_no_node")}
    workspace = store.ensure_workspace("html-checker", template_dir() / "checker" / "package.json", log or (lambda m: None))
    if workspace is None:
        return {**row, "error": i18n.t("brand", "observe_no_workspace")}
    shutil.copy2(Path(__file__).parent / "tools" / "brand-observe.mjs", workspace / "brand-observe.mjs")
    style = base / "style"
    style.mkdir(parents=True, exist_ok=True)
    if log:
        log(i18n.t("brand", "observing", url=url))
    with tempfile.TemporaryDirectory() as tmp:
        job = Path(tmp) / "job.json"
        job.write_text(json.dumps({"url": url, "browser": find_browser(), "light": str(style / f"observed-{slug}.png"),
                                   "dark": str(style / f"observed-{slug}-dark.png")}), encoding="utf-8")
        done = subprocess.run([node, "brand-observe.mjs", str(job)], cwd=workspace, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", check=False, timeout=300)
    try:
        seen = json.loads((done.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        seen = {"ok": False, "error": (done.stderr or done.stdout or "?").strip()[-300:]}
    if not seen.get("ok"):
        return {**row, "error": i18n.t("brand", "observe_failed", url=url, error=seen.get("error") or "?")}
    md.parent.mkdir(parents=True, exist_ok=True)
    data_file.write_text(json.dumps(seen, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    md.write_text(_observed_markdown(url, seen, base), encoding="utf-8")
    return {**row, "file": md.relative_to(base).as_posix(), "families": _families(seen), "google": seen.get("google") or []}


def _families(seen: dict) -> list[str]:
    names = {f.get("family", "") for f in seen.get("fonts") or [] if f.get("status") == "loaded"}
    names |= {s.get("family", "") for s in seen.get("sources") or []}
    return sorted(n for n in names if n and n.lower() not in GENERIC_FONTS)


def _observed_markdown(url: str, seen: dict, base: Path) -> str:
    say = lambda key, **v: i18n.t("brand", key, **v)  # noqa: E731
    out = [say("observed_title", url=url), "", say("observed_warning"), ""]
    if seen.get("vars"):
        out += [say("observed_vars"), "", "```css"] + [f"{k}: {v};" for k, v in list(seen["vars"].items())[:150]] + ["```", ""]
    out += [say("observed_elements"), "", "| | color | background | font | weight | size | radius | border | shadow |",
            "|---|---|---|---|---|---|---|---|---|"]
    for name, el in (seen.get("elements") or {}).items():
        if el:
            cells = (name, el.get("color") or "", el.get("background") or "", el.get("font", "")[:60], el.get("weight"), el.get("size"),
                     el.get("radius"), el.get("border"), (el.get("shadow") or "")[:50])
            out.append("| " + " | ".join(_cell(x) for x in cells) + " |")
    total = sum(c["n"] for c in seen.get("background") or []) or 1
    out += ["", say("observed_backgrounds"), ""] + [f"- `{c['color']}` {100 * c['n'] / total:.0f} %" for c in seen.get("background") or []]
    chars = sum(c["n"] for c in seen.get("text") or []) or 1
    out += ["", say("observed_text"), ""] + [f"- `{c['color']}` {100 * c['n'] / chars:.0f} %" for c in seen.get("text") or []]
    out += ["", say("observed_fonts"), ""] + [f"- {f}" for f in _families(seen)]
    for src in seen.get("sources") or []:
        out.append(f"  - {src.get('family')} {src.get('weight') or ''}: `{_cell(src.get('src') or '')[:160]}`")
    if seen.get("logos"):
        out += ["", say("observed_logos"), ""]
        out += [f"- {lg['kind']}: " + (f"`{lg['src']}`" if lg.get("src") else "SVG") for lg in seen["logos"]]
    shots = [p.relative_to(base).as_posix() for p in sorted((base / "style").glob(f"observed-{_slug(url)}*.png"))]
    if shots:
        out += ["", say("observed_shots"), ""] + [f"- `{s}`" for s in shots]
    return "\n".join(out).rstrip() + "\n"


def _slug(url: str) -> str:
    from coursekit import brief

    return brief.site_slug(url)
