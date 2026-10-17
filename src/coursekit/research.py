"""`coursekit research`: official sources for a course through a web search API (Exa, Perplexity, Brave or Tavily).

The provider is personal, like its key: RESEARCH_PROVIDER in the `.env` and the key of that provider. Without both nothing is
searched and the command says so with its own exit code (`NO_PROVIDER`), so the agent uses its own web search instead.

It only proposes sources (address, title, date, the passage that justifies each one); it never writes content. Only the
search endpoints are called, never the ones that write an answer. The candidates on `prefer_domains` go first, and a candidate
that is not in the language of the course is looked for in that language: the translation the page declares (hreflang), the
language changed in its address, or a rule of `localize_rules`, taken only when the page says it is in that language.
Every search is written in `brief/research-log.md` of the course, which is also what the limit per course counts.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path

from coursekit import config
from coursekit import course as coursemod
from coursekit.i18n import t
from coursekit.util import USER_AGENT

KEYS = {"exa": "EXA_API_KEY", "perplexity": "PERPLEXITY_API_KEY", "brave": "BRAVE_API_KEY", "tavily": "TAVILY_API_KEY"}
NO_PROVIDER = 3  # exit code: no provider configured, the agent uses its own web search
LOG = "brief/research-log.md"
VERIFY_MARK = re.compile(r"<!--\s*VERIFICAR\b")
RETRY_WAIT = (2, 8)  # seconds before the second and third attempt, on 429 and 5xx
PAGE_TIMEOUT = 10
HEAD_BYTES = 400_000
# Tavily wants the country by its English name; the rest of the providers take the ISO code.
COUNTRY_NAMES = {"ES": "spain", "MX": "mexico", "AR": "argentina", "CO": "colombia", "CL": "chile", "PE": "peru",
                 "US": "united states", "GB": "united kingdom", "IE": "ireland", "CA": "canada", "AU": "australia",
                 "FR": "france", "DE": "germany", "IT": "italy", "PT": "portugal", "BR": "brazil"}
LANGUAGES = {"en", "es", "fr", "de", "it", "pt", "nl", "ca", "eu", "gl", "pl", "sv", "da", "fi", "no", "nb", "cs", "ro",
             "hu", "el", "tr", "ru", "uk", "ja", "zh", "ko", "ar", "he"}
THREE_LETTERS = {"es": "spa", "en": "eng", "fr": "fra", "de": "deu", "it": "ita", "pt": "por", "nl": "nld", "ca": "cat"}
LOCALE_SEGMENT = re.compile(r"^([a-z]{2})(?:[-_]([a-z]{2}))?$", re.I)
LOCALE_PARAMS = ("hl", "lang", "locale", "language")
WORD = re.compile(r"[^\W_]+", re.U)


class ResearchError(Exception):
    pass


class NoProvider(ResearchError):
    pass


@dataclass
class Result:
    url: str
    title: str = ""
    snippet: str = ""
    date: str = ""
    language: str = ""   # the language the page says it is in, when it was looked at
    original: str = ""   # the address the provider gave, when the one in `url` is its translation


# ---------- provider ----------


def provider() -> tuple[str, str]:
    """(provider id, key) from the environment, or NoProvider saying what is missing."""
    name = os.environ.get("RESEARCH_PROVIDER", "").strip().lower()
    if not name:
        raise NoProvider(t("research", "no_provider"))
    if name not in KEYS:
        raise ResearchError(t("research", "unknown_provider", name=name, names=", ".join(KEYS)))
    key = os.environ.get(KEYS[name], "").strip()
    if not key:
        raise NoProvider(t("research", "no_key", name=name, key=KEYS[name]))
    return name, key


def settings(course: dict) -> dict:
    return config.effective("research", course.get("_project"), course).value


def country(cfg: dict, language: str) -> str | None:
    value = str(cfg.get("country") or "").strip()
    if value.lower() == "auto":
        return "ES" if language == "es" else None
    return value.upper() or None


def _call(req: urllib.request.Request, name: str) -> dict:
    """The JSON a provider answers, retrying on 429 and 5xx. The key never reaches a message."""
    for attempt in range(len(RETRY_WAIT) + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if (exc.code == 429 or exc.code >= 500) and attempt < len(RETRY_WAIT):
                time.sleep(RETRY_WAIT[attempt])
                continue
            if exc.code in (401, 403):
                raise ResearchError(t("research", "key_rejected", name=name, key=KEYS[name], status=exc.code)) from None
            if exc.code == 402:
                raise ResearchError(t("research", "no_credit", name=name)) from None
            detail = exc.read().decode("utf-8", "replace")[:300].replace("\n", " ")
            raise ResearchError(t("research", "api_failed", name=name, status=exc.code, detail=detail)) from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise ResearchError(t("research", "network_failed", name=name, reason=getattr(exc, "reason", exc))) from None
    raise ResearchError(t("research", "api_failed", name=name, status=429, detail=""))


def _post(url: str, body: dict, headers: dict) -> urllib.request.Request:
    return urllib.request.Request(url, json.dumps(body).encode("utf-8"), method="POST",
                                  headers={"Content-Type": "application/json", "User-Agent": USER_AGENT, **headers})


def _best_passage(passages: list[str], query: str) -> str:
    """The passage that shares most words with the query (the one that holds a fact), else the first."""
    words = {w.lower() for w in WORD.findall(query) if len(w) > 3}
    passages = [p for p in passages if p]
    if not passages:
        return ""
    return max(passages, key=lambda p: (len(words & {w.lower() for w in WORD.findall(p)}), -passages.index(p)))


def search_exa(key: str, query: str, n: int, where: str | None, language: str, opts: dict) -> list[Result]:
    body: dict = {"query": query, "type": opts.get("type") or "auto", "contents": {"highlights": True}}
    if n != 10:
        body["numResults"] = n
    if where:
        body["userLocation"] = where
    data = _call(_post("https://api.exa.ai/search", body, {"x-api-key": key}), "exa")
    return [Result(r.get("url", ""), r.get("title") or "", _best_passage(r.get("highlights") or [], query),
                   str(r.get("publishedDate") or "")[:10]) for r in data.get("results") or []]


def search_perplexity(key: str, query: str, n: int, where: str | None, language: str, opts: dict) -> list[Result]:
    body: dict = {"query": query, "max_results": min(n, 20), "search_type": opts.get("search_type") or "web",
                  "search_language_filter": [language]}
    if where:
        body["country"] = where
    data = _call(_post("https://api.perplexity.ai/search", body, {"Authorization": f"Bearer {key}"}), "perplexity")
    return [Result(r.get("url", ""), r.get("title") or "", r.get("snippet") or "", str(r.get("date") or "")[:10])
            for r in data.get("results") or []]


def search_brave(key: str, query: str, n: int, where: str | None, language: str, opts: dict) -> list[Result]:
    params = {"q": query, "count": min(n, 20), "search_lang": language}
    if where:
        params["country"] = where
    if opts.get("extra_snippets", True):
        params["extra_snippets"] = "true"
    req = urllib.request.Request(f"https://api.search.brave.com/res/v1/web/search?{urllib.parse.urlencode(params)}",
                                 headers={"X-Subscription-Token": key, "Accept": "application/json", "User-Agent": USER_AGENT})
    data = _call(req, "brave")
    return [Result(r.get("url", ""), r.get("title") or "",
                   _best_passage([r.get("description") or "", *(r.get("extra_snippets") or [])], query),
                   str(r.get("page_age") or "")[:10]) for r in (data.get("web") or {}).get("results") or []]


def search_tavily(key: str, query: str, n: int, where: str | None, language: str, opts: dict) -> list[Result]:
    body: dict = {"query": query, "search_depth": opts.get("search_depth") or "basic", "max_results": min(n, 20)}
    if where and where in COUNTRY_NAMES:
        body["country"] = COUNTRY_NAMES[where]
    data = _call(_post("https://api.tavily.com/search", body, {"Authorization": f"Bearer {key}"}), "tavily")
    return [Result(r.get("url", ""), r.get("title") or "", r.get("content") or "", str(r.get("published_date") or "")[:10])
            for r in data.get("results") or []]


SEARCH = {"exa": search_exa, "perplexity": search_perplexity, "brave": search_brave, "tavily": search_tavily}


# ---------- order and language ----------


def host(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").lower().removeprefix("www.")


def on(url: str, domains: list[str]) -> bool:
    name = host(url)
    return any(name == d or name.endswith("." + d) for d in (str(x).lower().removeprefix("www.") for x in domains))


def prefer(results: list[Result], domains: list[str]) -> list[Result]:
    """The candidates on the preferred domains first, each group in the order of the provider."""
    return sorted(results, key=lambda r: 0 if on(r.url, domains) else 1) if domains else results


class _Head(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang, self.alternates, self.title, self._in_title = "", {}, "", False

    def handle_starttag(self, tag, attrs):
        a = {k: v or "" for k, v in attrs}
        if tag == "html" and a.get("lang"):
            self.lang = a["lang"]
        elif tag == "link" and a.get("rel", "").lower() == "alternate" and a.get("hreflang") and a.get("href"):
            self.alternates[a["hreflang"].lower()] = a["href"]
        self._in_title = tag == "title"

    def handle_endtag(self, tag):
        self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


@dataclass
class Head:
    lang: str
    alternates: dict[str, str]
    title: str


def page_head(url: str) -> Head | None:
    """The language the page declares, its translations by hreflang and its title; None when it is not an HTML page that
    answers."""
    req = urllib.request.Request(url, headers={"User-Agent": f"Mozilla/5.0 (compatible; {USER_AGENT})"})
    try:
        with urllib.request.urlopen(req, timeout=PAGE_TIMEOUT) as resp:
            if resp.status != 200 or "html" not in (resp.headers.get("Content-Type") or ""):
                return None
            text = resp.read(HEAD_BYTES).decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    end = text.lower().find("</head>")
    parser = _Head()
    parser.feed(text if end < 0 else text[: end + 7])
    alternates = {k: urllib.parse.urljoin(url, v) for k, v in parser.alternates.items()}
    return Head(parser.lang, alternates, " ".join(parser.title.split()))


def _base(language: str) -> str:
    return language.lower().replace("_", "-").split("-")[0]


def _like(new: str, old: str) -> str:
    """`new` in the case of `old` (EN → ES, en → es)."""
    return new.upper() if old.isupper() else new.lower()


def rewrites(url: str, language: str, where: str | None, rules: list[dict]) -> list[str]:
    """Addresses of the same page in `language`: a locale segment of the path, a locale parameter, the project's rules."""
    parts = urllib.parse.urlsplit(url)
    out: list[str] = []
    segments = parts.path.split("/")
    for i, segment in enumerate(segments):
        found = LOCALE_SEGMENT.match(segment)
        options = []
        if found and found.group(1).lower() in LANGUAGES and found.group(1).lower() != language:
            own = _like(language, found.group(1))
            if found.group(2):  # en-us → es-es (es_ES, es-ES as the original writes it), then the bare language
                options.append(f"{own}{segment[2]}{_like(where or language, found.group(2))}")
            options.append(own)
        elif segment.lower() in THREE_LETTERS.values() and language in THREE_LETTERS \
                and segment.lower() != THREE_LETTERS[language]:
            options.append(_like(THREE_LETTERS[language], segment))  # eng → spa
        if options:
            out += [urllib.parse.urlunsplit(parts._replace(path="/".join([*segments[:i], o, *segments[i + 1:]])))
                    for o in options]
            break
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    if any(k.lower() in LOCALE_PARAMS for k, _ in query):
        changed = [(k, (language if "-" not in v and "_" not in v else f"{language}-{where or language}")
                    if k.lower() in LOCALE_PARAMS else v) for k, v in query]
        out.append(urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(changed))))
    for rule in rules or []:
        if on(url, [rule.get("host", "")]) and rule.get("from") and rule["from"] in url:
            out.append(url.replace(rule["from"], str(rule.get("to", "")).format(lang=language), 1))
    return [u for u in dict.fromkeys(out) if u != url]


def localize(result: Result, language: str, where: str | None, rules: list[dict]) -> Result:
    """The candidate in the language of the course when its translation can be found and checked; else as it is, with the
    language its page declares (if any)."""
    head = page_head(result.url)
    if not head:
        return result
    result.language = _base(head.lang) if head.lang else ""
    if not result.language or result.language == language:
        return result
    keys = [f"{language}-{where.lower()}"] if where else []
    keys += [language] + sorted(k for k in head.alternates if _base(k) == language)
    candidates = [head.alternates[k] for k in keys if k in head.alternates]
    candidates += rewrites(result.url, language, where, rules)
    for candidate in dict.fromkeys(candidates):
        found = page_head(candidate)
        if found and _base(found.lang) == language:
            result.original, result.url, result.language = result.url, candidate, language
            result.title = found.title or result.title
            break
    return result


# ---------- log, limit and estimate ----------


def log_path(course: dict) -> Path:
    return course["_dir"] / LOG


def searches(course: dict) -> int:
    path = log_path(course)
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("## "))


def pending_checks(course: dict) -> int:
    """The `<!-- VERIFICAR -->` marks left in the content of the course."""
    content = course["_dir"] / "content"
    if not content.exists():
        return 0
    return sum(len(VERIFY_MARK.findall(p.read_text(encoding="utf-8"))) for p in sorted(content.rglob("*.md")))


def _write_log(course: dict, name: str, query: str, fact: bool, results: list[Result]) -> None:
    path = log_path(course)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8") if path.exists() else t("research", "log_header") + "\n"
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"## {stamp} · {name}{' · fact' if fact else ''}", "", f"> {query}", ""]
    for i, r in enumerate(results, 1):
        extra = f" (← {r.original})" if r.original else (f" [{r.language}]" if r.language else "")
        lines.append(f"{i}. {r.url}{extra}")
    if not results:
        lines.append(t("research", "log_nothing"))
    path.write_text(text.rstrip("\n") + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8")


@dataclass
class Found:
    provider: str
    query: str
    results: list[Result]
    total: int
    done: int
    limit: int
    warning: str = ""

    def as_json(self) -> str:
        return json.dumps({"provider": self.provider, "query": self.query, "total": self.total, "searches": self.done,
                           "limit": self.limit, "warning": self.warning, "results": [asdict(r) for r in self.results]},
                          ensure_ascii=False, indent=1)


def search(course: dict, query: str, fact: bool = False) -> Found:
    """Search once with the provider of the `.env`, write it in the log, and return the candidates to show."""
    name, key = provider()
    cfg = settings(course)
    limit, done = int(cfg.get("max_per_course") or 0), searches(course)
    if limit and done >= limit:
        raise ResearchError(t("research", "limit_reached", code=course["code"], limit=limit))
    language = coursemod.language(course)
    where = country(cfg, language)
    found = SEARCH[name](key, query, int(cfg.get("results") or 10), where, language, (cfg.get("providers") or {}).get(name) or {})
    found = [r for r in found if r.url.startswith(("http://", "https://"))]
    shown = prefer(found, cfg.get("prefer_domains") or [])[: int(cfg.get("show") or 5)]
    if cfg.get("localize", True) and shown:
        rules = cfg.get("localize_rules") or []
        with ThreadPoolExecutor(max_workers=len(shown)) as pool:
            shown = list(pool.map(lambda r: localize(r, language, where, rules), shown))
        seen: set[str] = set()  # a translation can be a candidate the provider already gave
        shown = [r for r in shown if not (r.url in seen or seen.add(r.url))]
    _write_log(course, name, query, fact, shown)
    done += 1
    warning = ""
    if limit and done >= float(cfg.get("warn_at") or 1) * limit:
        warning = t("research", "limit_near", done=done, limit=limit, code=course["code"])
    return Found(name, query, shown, len(found), done, limit, warning)


def status(course: dict) -> list[str]:
    """What `--status` prints: the provider, the searches of the course and what is left to verify."""
    cfg = settings(course)
    try:
        name, _ = provider()
        line = t("research", "status_provider", name=name)
    except NoProvider as exc:
        line = t("research", "status_native", reason=exc)
    pending = pending_checks(course)
    limit = int(cfg.get("max_per_course") or 0)
    out = [line, t("research", "status_searches", done=searches(course), limit=limit or "-", path=LOG)]
    out.append(t("research", "status_pending", count=pending, low=pending, high=2 * pending) if pending
               else t("research", "status_no_pending"))
    return out


def render(found: Found, language: str) -> str:
    """The candidates as the agent reads them."""
    out = [t("research", "title", provider=found.provider, shown=len(found.results), total=found.total, query=found.query)]
    for i, r in enumerate(found.results, 1):
        meta = " · ".join(x for x in (host(r.url), r.date, r.language) if x)
        out += ["", f"{i}. {r.title or r.url}", f"   {r.url}", f"   {meta}"]
        if r.original:
            out.append("   " + t("research", "translated_from", url=r.original))
        elif r.language and r.language != language:
            out.append("   " + t("research", "other_language", language=r.language))
        if r.snippet:
            snippet = " ".join(r.snippet.split())
            out.append(f"   > {snippet[:400]}{'…' if len(snippet) > 400 else ''}")
    if not found.results:
        out += ["", t("research", "nothing")]
    out += ["", t("research", "footer", log=LOG)]
    return "\n".join(out)
