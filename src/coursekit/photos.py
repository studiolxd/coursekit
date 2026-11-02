"""Licensed photographs for the resources of a course (`coursekit media stock CODE ID --photos`), in every project, also without
creator: Pexels (`PEXELS_API_KEY`; its licence asks for no attribution) and the photographs of the Magnific catalogue (the
`MAGNIFIC_API_KEY` the project may already have; a premium resource asks for no attribution, a free one does). The providers
and their order are `media › photos`; a result that asks for no attribution always goes first. A taken photograph is
downloaded to `media/files/<id>.jpg` and the manifest records where it comes from and whether it must be credited: the
assembly puts the credit in its caption only then."""

from __future__ import annotations

import json
import os
import urllib.parse
from dataclasses import asdict, dataclass
from typing import Any, cast

from coursekit import http
from coursekit.i18n import t

PEXELS = "https://api.pexels.com/v1"
MAGNIFIC = "https://api.magnific.com/v1"
KEYS = {"pexels": "PEXELS_API_KEY", "magnific": "MAGNIFIC_API_KEY"}
NAMES = {"pexels": "Pexels", "magnific": "Magnific"}


class PhotoError(Exception):
    pass


@dataclass
class Photo:
    provider: str
    id: str
    title: str
    author: str
    author_url: str
    url: str           # its page
    preview: str       # a small image to look at
    download: str      # what is downloaded (empty: asked for when taken)
    license: str
    attribution: bool  # the licence asks for a credit next to it
    width: int = 0
    height: int = 0

    @property
    def ref(self) -> str:
        return f"{self.provider}:{self.id}"


def available(providers: list[str]) -> list[str]:
    """The providers of the list whose key is set."""
    return [p for p in providers if p in KEYS and os.environ.get(KEYS[p], "").strip()]


def _get(url: str, headers: dict) -> dict:
    try:
        return cast("dict", json.loads(http.request(url, headers=headers, timeout=60).body))
    except http.HttpError as exc:
        raise PhotoError(t("photos", "api_failed", provider=url.split("/")[2], status=exc.status, detail=exc.detail(200))) from None
    except http.NetworkError as exc:
        raise PhotoError(t("photos", "network_failed", reason=exc.reason)) from None


def search_pexels(term: str, language: str, limit: int, orientation: str | None) -> list[Photo]:
    params: dict[str, Any] = {"query": term, "per_page": limit, "locale": "es-ES" if language == "es" else "en-US"}
    if orientation:
        params["orientation"] = orientation
    data = _get(f"{PEXELS}/search?{urllib.parse.urlencode(params)}", {"Authorization": os.environ[KEYS["pexels"]].strip()})
    found = []
    for item in data.get("photos") or []:
        src = item.get("src") or {}
        found.append(Photo("pexels", str(item["id"]), str(item.get("alt") or ""), str(item.get("photographer") or ""),
                           str(item.get("photographer_url") or ""), str(item.get("url") or ""), str(src.get("medium") or ""),
                           str(src.get("large2x") or src.get("original") or ""), "Pexels License", False,
                           int(item.get("width") or 0), int(item.get("height") or 0)))
    return found


def _magnific_headers() -> dict:
    return {"x-magnific-api-key": os.environ[KEYS["magnific"]].strip(), "Accept-Language": "en-US"}


def search_magnific(term: str, language: str, limit: int, orientation: str | None) -> list[Photo]:
    params: dict[str, Any] = {"term": term, "limit": limit, "filters[content_type][photo]": 1}
    if orientation:
        params[f"filters[orientation][{orientation}]"] = 1
    data = _get(f"{MAGNIFIC}/resources?{urllib.parse.urlencode(params)}", _magnific_headers())
    found = []
    for item in data.get("data") or []:
        licenses = {str(lic.get("type")) for lic in item.get("licenses") or [] if lic.get("type")}
        premium = "premium" in licenses and "freemium" not in licenses
        author = item.get("author") or {}
        found.append(Photo("magnific", str(item["id"]), str(item.get("title") or ""), str(author.get("name") or author.get("slug") or ""),
                           str(author.get("url") or ""), str(item.get("url") or ""),
                           str(((item.get("image") or {}).get("source") or {}).get("url") or ""), "",
                           "premium" if premium else "freemium", not premium))
    return found


SEARCH = {"pexels": search_pexels, "magnific": search_magnific}


def search(providers: list[str], term: str, language: str, limit: int = 12, orientation: str | None = None,
           attribution: str = "avoid") -> list[Photo]:
    """The photographs of every provider with a key; with `attribution: avoid` (the default), those that ask for no credit
    first."""
    usable = available(providers)
    if not usable:
        raise PhotoError(t("photos", "no_provider", keys=", ".join(KEYS[p] for p in providers if p in KEYS)))
    found: list[Photo] = []
    for name in usable:
        found += SEARCH[name](term, language, limit, orientation)
    if attribution == "avoid":
        found.sort(key=lambda p: p.attribution)  # stable: each provider keeps its order of relevance
    return found


def download_url(photo_ref: str) -> tuple[str, dict]:
    """(what to download, what the manifest records) for `provider:id`."""
    provider, _, ident = photo_ref.partition(":")
    if provider not in SEARCH or not ident:
        raise PhotoError(t("photos", "bad_ref", ref=photo_ref))
    if not available([provider]):
        raise PhotoError(t("photos", "no_provider", keys=KEYS[provider]))
    if provider == "pexels":
        item = _get(f"{PEXELS}/photos/{urllib.parse.quote(ident)}", {"Authorization": os.environ[KEYS["pexels"]].strip()})
        src = item.get("src") or {}
        return str(src.get("large2x") or src.get("original") or ""), asdict(Photo(
            "pexels", ident, str(item.get("alt") or ""), str(item.get("photographer") or ""), str(item.get("photographer_url") or ""),
            str(item.get("url") or ""), "", "", "Pexels License", False))
    detail = _get(f"{MAGNIFIC}/resources/{urllib.parse.quote(ident)}", _magnific_headers()).get("data") or {}
    files = _get(f"{MAGNIFIC}/resources/{urllib.parse.quote(ident)}/download", _magnific_headers()).get("data")
    files = files[0] if isinstance(files, list) and files else files
    if not isinstance(files, dict) or not files.get("url"):
        raise PhotoError(t("photos", "no_file", ref=photo_ref))
    premium = bool(detail.get("premium"))
    author = detail.get("author") or {}
    return str(files["url"]), asdict(Photo("magnific", ident, str(detail.get("title") or ""),
                                           str(author.get("name") or author.get("slug") or ""), str(author.get("url") or ""),
                                           str(detail.get("url") or ""), "", "", "premium" if premium else "freemium", not premium))


def fetch(url: str) -> bytes:
    try:
        return http.request(url, agent="Mozilla/5.0 coursekit", timeout=120).body
    except http.HttpError as exc:
        raise PhotoError(t("photos", "network_failed", reason=f"{exc.status} {exc.reason}")) from None
    except http.NetworkError as exc:
        raise PhotoError(t("photos", "network_failed", reason=exc.reason)) from None


def credit(source: dict, words: dict) -> str:
    """The credit of a photograph whose licence asks for it, in the language of the course; empty otherwise."""
    if not source.get("attribution"):
        return ""
    provider = NAMES.get(str(source.get("provider")), str(source.get("provider") or ""))
    return str(words.get("photo_credit", "{author} ({provider})")).format(author=source.get("author") or provider, provider=provider)
