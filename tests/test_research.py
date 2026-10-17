"""`coursekit research`: official sources through a web search API, never the network in the tests."""

import io
import json
import urllib.error
import urllib.parse

import pytest

from coursekit import research
from coursekit.cli import main
from coursekit.project import find_project

KEY = "secret-key-123"


@pytest.fixture
def course(tmp_path, monkeypatch):
    monkeypatch.delenv("COURSEKIT_PROJECT", raising=False)
    for name in ("RESEARCH_PROVIDER", *research.KEYS.values()):
        monkeypatch.delenv(name, raising=False)
    root = tmp_path / "demo"
    assert main(["init", str(root), "--yes", "--no-git"]) == 0
    monkeypatch.chdir(root)
    assert main(["new", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    return root / "courses" / "PWD"


def use(monkeypatch, name):
    monkeypatch.setenv("RESEARCH_PROVIDER", name)
    monkeypatch.setenv(research.KEYS[name], KEY)


class Response(io.BytesIO):
    def __init__(self, body, status=200, content_type="application/json"):
        super().__init__(body if isinstance(body, bytes) else json.dumps(body).encode())
        self.status, self.headers = status, {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def api(monkeypatch):
    """Every call the module makes: provider calls answer `api.answer`, pages answer from `api.pages` (else 404)."""

    class Api:
        answer: dict = {}
        pages: dict = {}
        sent: list = []

    def urlopen(req, timeout=None):
        url = req.full_url
        if any(h in url for h in ("api.exa.ai", "api.perplexity.ai", "api.search.brave.com", "api.tavily.com")):
            Api.sent.append(req)
            if isinstance(Api.answer, Exception):
                raise Api.answer
            if isinstance(Api.answer, list):
                item = Api.answer.pop(0)
                if isinstance(item, Exception):
                    raise item
                return Response(item)
            return Response(Api.answer)
        if url in Api.pages:
            return Response(Api.pages[url].encode(), content_type="text/html; charset=utf-8")
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b""))

    monkeypatch.setattr(research.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(research.time, "sleep", lambda s: None)
    Api.sent = []
    return Api


def page(lang, *alternates, title="x"):
    links = "".join(f'<link rel="alternate" hreflang="{h}" href="{u}">' for h, u in alternates)
    return f'<!doctype html><html lang="{lang}"><head><title>{title}</title>{links}</head><body>texto</body></html>'


def http_error(code):
    return urllib.error.HTTPError("https://api", code, "x", {}, io.BytesIO(b'{"error": "nope"}'))


EXA = {"results": [
    {"url": "https://blog.example.com/passwords", "title": "A blog", "highlights": ["Una opinión."]},
    {"url": "https://www.incibe.es/guia-contrasenas", "title": "Guía oficial", "publishedDate": "2025-03-01T00:00:00Z",
     "highlights": ["Introducción.", "Una contraseña segura tiene al menos doce caracteres."]},
]}


# ---------- the provider ----------


def test_without_provider_the_agent_uses_its_own_search(course, api, capsys, monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", KEY)  # a key alone does nothing
    assert main(["research", "PWD", "contraseñas seguras"]) == research.NO_PROVIDER
    assert "RESEARCH_PROVIDER" in capsys.readouterr().err
    assert not api.sent and not (course / research.LOG).exists()


def test_a_provider_without_its_key_or_an_unknown_one(course, api, capsys, monkeypatch):
    monkeypatch.setenv("RESEARCH_PROVIDER", "brave")
    assert main(["research", "PWD", "x"]) == research.NO_PROVIDER
    assert "BRAVE_API_KEY" in capsys.readouterr().err
    monkeypatch.setenv("RESEARCH_PROVIDER", "google")
    assert main(["research", "PWD", "x"]) == 1
    assert "google" in capsys.readouterr().err


def test_exa_request_and_answer(course, api, capsys, monkeypatch):
    use(monkeypatch, "exa")
    api.answer = EXA
    assert main(["research", "PWD", "longitud mínima de una contraseña segura", "--fact"]) == 0
    req = api.sent[0]
    body = json.loads(req.data)
    assert req.full_url == "https://api.exa.ai/search" and req.get_header("X-api-key") == KEY
    assert body == {"query": "longitud mínima de una contraseña segura", "type": "auto", "contents": {"highlights": True},
                    "userLocation": "ES"}
    out = capsys.readouterr().out
    assert "https://www.incibe.es/guia-contrasenas" in out and "2025-03-01" in out
    assert "doce caracteres" in out  # the passage that holds the fact, not the first one
    assert KEY not in out


def test_perplexity_brave_and_tavily_requests(course, api, monkeypatch):
    use(monkeypatch, "perplexity")
    api.answer = {"results": [{"url": "https://www.aepd.es/a", "title": "AEPD", "snippet": "72 horas", "date": "2024-01-02"}]}
    found = research.search(_load(course), "plazo brecha")
    body = json.loads(api.sent[-1].data)
    assert body["country"] == "ES" and body["search_language_filter"] == ["es"] and body["max_results"] == 10
    assert api.sent[-1].get_header("Authorization") == f"Bearer {KEY}"
    assert found.results[0].snippet == "72 horas" and found.provider == "perplexity"

    use(monkeypatch, "brave")
    api.answer = {"web": {"results": [{"url": "https://www.boe.es/x", "title": "BOE", "description": "Ley",
                                       "extra_snippets": ["Treinta días naturales de vacaciones anuales."]}]}}
    found = research.search(_load(course), "vacaciones anuales")
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(api.sent[-1].full_url).query))
    assert query["country"] == "ES" and query["search_lang"] == "es" and query["extra_snippets"] == "true"
    assert api.sent[-1].get_header("X-subscription-token") == KEY
    assert "Treinta días" in found.results[0].snippet

    use(monkeypatch, "tavily")
    api.answer = {"results": [{"url": "https://www.incibe.es/y", "title": "INCIBE", "content": "Consejos"}]}
    research.search(_load(course), "contraseñas")
    body = json.loads(api.sent[-1].data)
    assert body == {"query": "contraseñas", "search_depth": "basic", "max_results": 10, "country": "spain"}


def _load(course_dir):
    from coursekit import course as coursemod

    return coursemod.load(find_project(), course_dir.name)


# ---------- order, language, log and limit ----------


def test_preferred_domains_go_first(course, api, monkeypatch):
    use(monkeypatch, "exa")
    api.answer = EXA
    (course.parent.parent / "config" / "research.yaml").write_text("prefer_domains: [incibe.es]\n", encoding="utf-8")
    found = research.search(_load(course), "contraseñas")
    assert [r.url for r in found.results][0] == "https://www.incibe.es/guia-contrasenas" and len(found.results) == 2


def test_a_candidate_in_another_language_is_looked_for_in_the_course_language(course, api, monkeypatch):
    use(monkeypatch, "exa")
    declared = "https://docs.example.org/en/guide"
    rewritten = "https://support.example.com/en-us/teams/meeting"
    alone = "https://standards.example.org/spec"
    api.answer = {"results": [{"url": u, "title": "t"} for u in (declared, rewritten, alone, "https://docs.example.org/es/guide")]}
    api.pages = {
        declared: page("en", ("es", "/es/guide"), ("fr", "/fr/guide")),
        "https://docs.example.org/es/guide": page("es"),
        rewritten: page("en-US"),
        "https://support.example.com/es-es/teams/meeting": page("es-ES", title="Programar una reunión"),
        alone: page("en"),
    }
    found = research.search(_load(course), "x")
    assert len(found.results) == 3
    by_original = {r.original or r.url: r for r in found.results}
    assert by_original[rewritten].title == "Programar una reunión"  # the title of the translation
    assert by_original[declared].url == "https://docs.example.org/es/guide"  # hreflang, relative address resolved
    assert by_original[rewritten].url == "https://support.example.com/es-es/teams/meeting"  # the locale of the address
    assert by_original[alone].url == alone and by_original[alone].language == "en"  # no translation: stays, marked
    text = research.render(found, "es")
    assert "docs.example.org/en/guide" in text and '"en"' in text


def test_a_site_that_blocks_a_direct_download_is_marked(course, api, monkeypatch):
    use(monkeypatch, "exa")
    blocked, empty = "https://law.example.eu/doc?id=1", "https://other.example.org/page"
    api.answer = {"results": [{"url": u, "title": "t"} for u in (blocked, empty)]}
    api.pages = {empty: "<html><head></head><body><script>challenge-platform</script>Just a moment...</body></html>"}

    real = research.urllib.request.urlopen

    def urlopen(req, timeout=None):
        if req.full_url == blocked:
            return Response(b"", status=202, content_type="text/html")
        return real(req, timeout)

    monkeypatch.setattr(research.urllib.request, "urlopen", urlopen)
    found = research.search(_load(course), "x")
    assert [r.blocked for r in found.results] == [True, True]
    assert "Chrome or Edge" in research.render(found, "es")


def test_rewrites_keep_the_way_each_site_writes_its_locale():
    assert research.rewrites("https://support.microsoft.com/en-us/excel/x", "es", "ES", []) == [
        "https://support.microsoft.com/es-es/excel/x", "https://support.microsoft.com/es/excel/x"]
    assert research.rewrites("https://developer.mozilla.org/en-US/docs/a", "es", None, [])[0] == \
        "https://developer.mozilla.org/es-ES/docs/a"
    assert research.rewrites("https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:1", "es", "ES", []) == [
        "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:1"]
    assert research.rewrites("https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng", "es", "ES", []) == [
        "https://eur-lex.europa.eu/eli/reg/2016/679/oj/spa"]
    assert research.rewrites("https://support.google.com/drive/answer/1?hl=en", "es", "ES", []) == [
        "https://support.google.com/drive/answer/1?hl=es"]
    rule = {"host": "docs.python.org", "from": "/3/", "to": "/{lang}/3/"}
    assert research.rewrites("https://docs.python.org/3/library/venv.html", "es", "ES", [rule]) == [
        "https://docs.python.org/es/3/library/venv.html"]
    assert research.rewrites("https://www.boe.es/buscar/act.php?id=1", "es", "ES", []) == []


def test_every_search_is_logged_and_the_limit_stops_a_loop(course, api, capsys, monkeypatch):
    use(monkeypatch, "exa")
    api.answer = EXA
    (course.parent.parent / "config" / "research.yaml").write_text("max_per_course: 2\nwarn_at: 0.5\nlocalize: false\n",
                                                                     encoding="utf-8")
    assert main(["research", "PWD", "primera"]) == 0
    assert "1 of 2" in capsys.readouterr().err  # the warning at half the limit
    assert main(["research", "PWD", "segunda", "--fact"]) == 0
    log = (course / research.LOG).read_text(encoding="utf-8")
    assert log.count("\n## ") == 2 and "> segunda" in log and "· exa · fact" in log and KEY not in log
    assert main(["research", "PWD", "tercera"]) == 1
    assert "max_per_course" in capsys.readouterr().err and len(api.sent) == 2


def test_status_estimates_what_is_left(course, api, capsys, monkeypatch):
    unit = course / "content" / "unit-01" / "content.md"
    unit.parent.mkdir(parents=True, exist_ok=True)
    unit.write_text("Texto.\n<!-- VERIFICAR: versión -->\n<!--VERIFICAR: precio -->\n", encoding="utf-8")
    assert main(["research", "PWD", "--status"]) == 0
    out = capsys.readouterr().out
    assert "no provider" in out and "0 of 150" in out and "VERIFICAR marks left in the content: 2 (some 2–4" in out
    use(monkeypatch, "tavily")
    assert main(["research", "PWD", "--status"]) == 0
    assert "provider: tavily" in capsys.readouterr().out


def test_json_output(course, api, capsys, monkeypatch):
    use(monkeypatch, "exa")
    api.answer = EXA
    assert main(["research", "PWD", "contraseñas", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["provider"] == "exa" and data["searches"] == 1 and data["results"][1]["url"].startswith("https://www.incibe.es")


# ---------- errors of the provider ----------


def test_it_retries_busy_answers_and_explains_a_rejected_key(course, api, capsys, monkeypatch):
    use(monkeypatch, "exa")
    api.answer = [http_error(429), http_error(503), EXA]
    assert main(["research", "PWD", "x"]) == 0 and len(api.sent) == 3
    capsys.readouterr()
    api.answer = http_error(401)
    assert main(["research", "PWD", "x"]) == 1
    err = capsys.readouterr().err
    assert "EXA_API_KEY" in err and KEY not in err
    api.answer = http_error(402)
    assert main(["research", "PWD", "x"]) == 1
    assert "credit" in capsys.readouterr().err


def test_it_needs_something_to_search(course, capsys):
    assert main(["research", "PWD"]) == 2
