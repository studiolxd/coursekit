"""The illustration sources of the brand (the third part of theme/branding/links.md: the page of an author on Magnific whose
illustrations the brand likes) and `coursekit media stock`: find among them the illustration a resource needs, take it as SVG
and recolour it to the brand. The Magnific API (MAGNIFIC_API_KEY) searches by author and format; its previews cost no
download, and a download of a plan with stock downloads costs no credits (within its daily limit)."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from coursekit.i18n import t

API = "https://api.magnific.com/v1"
SOURCES = "illustration-sources.json"
AUTHOR_URL = re.compile(r"^https?://(?:www\.)?(?:magnific|freepik)\.[a-z.]+/(?:[a-z]{2}/)?author/([A-Za-z0-9_.-]+)", re.I)


class IllustrationError(Exception):
    pass


def key() -> str:
    found = os.environ.get("MAGNIFIC_API_KEY", "").strip()
    if not found:
        raise IllustrationError(t("illustrations", "no_key"))
    return found


def get(path: str, params: dict | None = None) -> dict:
    """A call to the Magnific API (the tests stand in for it)."""
    url = f"{API}/{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"x-magnific-api-key": key(), "Accept-Language": "en-US"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"data": [], "meta": {"total": 0}}
        detail = exc.read().decode("utf-8", "replace")[:200]
        raise IllustrationError(t("illustrations", "api_failed", status=exc.code, detail=detail)) from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise IllustrationError(t("illustrations", "network_failed", reason=getattr(exc, "reason", exc))) from None


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 coursekit"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise IllustrationError(t("illustrations", "network_failed", reason=getattr(exc, "reason", exc))) from None


def author_of(url: str) -> str | None:
    """The slug of the author of a page of Magnific (…/author/vectorjuice), or None when it is not one."""
    found = AUTHOR_URL.match(url.strip())
    return found.group(1) if found else None


def resolve(slug: str) -> int | None:
    """The id of an author from its slug: the API searches no author by name, but a search of the slug finds its work."""
    for page in (1, 2):
        for item in get("resources", {"term": slug.replace("-", " "), "limit": 50, "page": page}).get("data") or []:
            author = item.get("author") or {}
            if str(author.get("slug") or "").lower() == slug.lower():
                return int(author["id"])
    return None


def load(folder: Path) -> list[dict]:
    path = folder / SOURCES
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []


def search(sources: list[dict], term: str, color: str | None = None, limit: int = 12) -> list[dict]:
    """The illustrations of the sources that match a term (in English, the language of the catalog) and come as SVG."""
    found = []
    for source in sources:
        if not source.get("author_id"):
            continue
        params = {"term": term, "filters[author]": source["author_id"], "filters[vector][type]": "svg", "limit": limit}
        if color:
            params["filters[color]"] = color
        for item in get("resources", params).get("data") or []:
            formats = (item.get("meta") or {}).get("available_formats") or {}
            if "svg" not in formats:
                continue
            found.append({"id": int(item["id"]), "title": str(item.get("title") or ""), "author": (item.get("author") or {}).get("slug"),
                          "licenses": sorted({lic.get("type") for lic in item.get("licenses") or [] if lic.get("type")}),
                          "preview": ((item.get("image") or {}).get("source") or {}).get("url"), "url": item.get("url")})
    return found[:limit]


def detail(resource: int) -> dict:
    """Where a resource is (its page), who drew it and its licences."""
    data = get(f"resources/{resource}").get("data") or {}
    return {"url": data.get("url"), "author": (data.get("author") or {}).get("slug"),
            "license": "premium" if data.get("premium") else "freemium", "license_url": data.get("license")}


def download_svg(resource: int) -> tuple[str, str]:
    """(the SVG of a resource, its file name)."""
    data = get(f"resources/{resource}/download/svg").get("data")
    data = data[0] if isinstance(data, list) and data else data
    if not isinstance(data, dict) or not data.get("url"):
        raise IllustrationError(t("illustrations", "no_svg", resource=resource))
    return fetch(data["url"]).decode("utf-8", "replace"), str(data.get("filename") or f"{resource}.svg")


HEX = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    h = "".join(c * 2 for c in h) if len(h) == 3 else h
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _light(hex_color: str) -> bool:
    r, g, b = _rgb(hex_color)
    return (0.299 * r + 0.587 * g + 0.114 * b) > 128


def is_line_art(svg: str) -> bool:
    """Whether an illustration is drawn in black (or greys) and white only, as the line versions are: the colour versions of
    the same illustration have hues, and recolouring them would turn their fills into blots."""
    return all(max(_rgb(c)) - min(_rgb(c)) <= 24 for c in set(HEX.findall(svg)))


def recolour(svg: str, ink: str, paper: str = "#FFFFFF") -> str:
    """A line illustration in the colours of the brand: every dark colour becomes the ink and every light one the paper, and
    what declares no colour (which SVG draws black) inherits the ink."""
    svg = HEX.sub(lambda m: paper if _light(m.group(0)) else ink, svg)
    return re.sub(r"<svg\b", f'<svg fill="{ink}"', svg, count=1)
