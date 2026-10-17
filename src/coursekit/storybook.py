"""A Storybook published on the web, read whole: every page of documentation and every component (its props, its stories and
its page) as Markdown, from the index and the manifests a Storybook publishes (`index.json`, `manifests/docs.json`,
`manifests/components.json`), and the files its pages link to (logos, icons). Used by `coursekit brief` and `coursekit brand`
for a link that turns out to be a Storybook."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
ASSETS = (".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".woff2", ".woff", ".ttf", ".otf", ".json", ".css", ".pdf")


def get(url: str, timeout: int = 60) -> bytes | None:
    """The body of a URL, or None when it cannot be read (the tests stand in for it)."""
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None


def base_of(url: str) -> str:
    """The root of a Storybook from any of its addresses (…/index.html?path=/docs/…, …/iframe.html, …/)."""
    parts = urllib.parse.urlsplit(url)
    path = re.sub(r"/(index|iframe)\.html$", "/", parts.path) or "/"
    if not path.endswith("/"):
        path = path.rsplit("/", 1)[0] + "/" if "." in path.rsplit("/", 1)[-1] else path + "/"
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def _json(url: str):
    body = get(url)
    if body is None:
        return None
    try:
        return json.loads(body)
    except ValueError:
        return None


def detect(url: str) -> str | None:
    """The root of the Storybook at this address, or None when it is not one (its `index.json` lists its entries)."""
    base = base_of(url)
    found = _json(base + "index.json")
    return base if isinstance(found, dict) and isinstance(found.get("entries"), dict) else None


def slug(text: str) -> str:
    plain = text.lower().translate(str.maketrans("áéíóúüñàèìòùç", "aeiouunaeiouc"))
    return re.sub(r"[^a-z0-9]+", "-", plain).strip("-") or "page"


def clean_mdx(text: str) -> str:
    """The text of an MDX page without what only the build reads: imports, exports and the <Meta> tag."""
    text = re.sub(r"(?ms)^import\s.*?;\s*$\n?", "", text)
    text = re.sub(r"(?m)^export\s+(const|default)\s.*$\n?", "", text)
    text = re.sub(r"(?m)^<Meta\b[^>]*/>\s*$\n?", "", text)
    return text.strip() + "\n"


def _component(entry: dict) -> str:
    out = [f"# {entry.get('name') or entry.get('id')}", ""]
    if entry.get("import"):
        out += ["```ts", str(entry["import"]).strip(), "```", ""]
    doc = entry.get("reactDocgen") or {}
    if doc.get("description"):
        out += [str(doc["description"]).strip(), ""]
    props = doc.get("props") or {}
    if props:
        out += ["## Props", "", "| Prop | Type | Required | Description |", "|---|---|---|---|"]
        for name, prop in props.items():
            spec = prop.get("tsType") or prop.get("type") or {}
            kind = spec.get("raw") or spec.get("name") or ""
            text = str(prop.get("description") or "").replace("\n", " ").replace("|", "\\|")
            out.append(f"| `{name}` | `{str(kind).replace('|', '¦')[:80]}` | {'yes' if prop.get('required') else ''} | {text} |")
        out.append("")
    stories = entry.get("stories") or []
    if stories:
        out += ["## Stories", ""]
        for story in stories:
            out += [f"### {story.get('name')}", ""]
            if story.get("description"):
                out += [str(story["description"]).strip(), ""]
            if story.get("snippet"):
                out += ["```tsx", str(story["snippet"]).strip(), "```", ""]
    for page in (entry.get("docs") or {}).values():
        if isinstance(page, dict) and page.get("content"):
            out += ["## Documentation", "", clean_mdx(str(page["content"]))]
    return "\n".join(out).rstrip() + "\n"


def _assets(text: str, base: str) -> set[str]:
    """The files of the same site that a page links to (a logo, an icon, a font)."""
    host = urllib.parse.urlsplit(base).netloc
    found = set()
    for ref in re.findall(r"""(?:\]\(|href=["']|src=["'])([^)"'\s]+)""", text):
        url = urllib.parse.urljoin(base, ref.split("#")[0])
        parts = urllib.parse.urlsplit(url)
        if parts.netloc == host and parts.path.lower().endswith(ASSETS):
            found.add(urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")))
    return found


def font_links(base: str) -> list[str]:
    """The Google Fonts stylesheets the Storybook loads (its fonts, with an open licence)."""
    page = "".join((get(base + name) or b"").decode("utf-8", "replace") for name in ("iframe.html", "index.html")).replace("&amp;", "&")
    return sorted(set(re.findall(r"""https://fonts\.googleapis\.com/css2?\?[^"'\s>]+""", page)))


def download(base: str, folder: Path) -> dict:
    """Every page and component of the Storybook in `folder` (docs/, components/, files/ and a README with the index).
    Returns what it wrote."""
    index = _json(base + "index.json") or {}
    docs = (_json(base + "manifests/docs.json") or {}).get("docs") or {}
    components = (_json(base + "manifests/components.json") or {}).get("components") or {}
    folder.mkdir(parents=True, exist_ok=True)
    readme = [f"# Storybook — {base}", ""]
    links: set[str] = set()
    written = {"docs": 0, "components": 0, "files": [], "manifests": bool(docs or components)}
    if docs:
        readme += ["## Documentation", ""]
        for page in sorted(docs.values(), key=lambda p: str(p.get("title") or "")):
            title = str(page.get("title") or page.get("id"))
            target = folder / "docs" / f"{slug(title)}.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            body = clean_mdx(str(page.get("content") or ""))
            front = f"---\ntitle: {json.dumps(title, ensure_ascii=False)}\nsource: {base}?path=/docs/{page.get('id')}\n---\n\n"
            target.write_text(front + body, encoding="utf-8")
            readme.append(f"- [{title}](docs/{target.name})")
            links |= _assets(body, base)
            written["docs"] += 1
        readme.append("")
    if components:
        readme += ["## Components", ""]
        for entry in sorted(components.values(), key=lambda c: str(c.get("id"))):
            page = next(iter((entry.get("docs") or {}).values()), None) or {}
            title = str(page.get("title") or entry.get("name") or entry.get("id"))
            target = folder / "components" / f"{slug(title)}.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            body = _component(entry)
            front = f"---\ntitle: {json.dumps(title, ensure_ascii=False)}\nsource: {base}?path=/docs/{entry.get('id')}--docs\n---\n\n"
            target.write_text(front + body, encoding="utf-8")
            readme.append(f"- [{title}](components/{target.name})")
            links |= _assets(body, base)
            written["components"] += 1
        readme.append("")
    entries = index.get("entries") or {}
    if not (docs or components) and entries:  # an older Storybook: only what its index says
        readme += ["## Entries", ""] + sorted({f"- {e.get('title')}" for e in entries.values() if isinstance(e, dict)}) + [""]
    for url in sorted(links):
        body = get(url)
        if body is None:
            continue
        target = folder / "files" / urllib.parse.urlsplit(url).path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        written["files"].append(target)
    if written["files"]:
        readme += ["## Files", ""] + [f"- `{p.relative_to(folder).as_posix()}`" for p in written["files"]] + [""]
    (folder / "README.md").write_text("\n".join(readme), encoding="utf-8")
    return written
