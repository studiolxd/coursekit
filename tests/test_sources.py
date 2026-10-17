"""Searching the reference material for what a section needs: passages, BM25 and `coursekit brief --find / --section`."""

from coursekit import sources
from coursekit.cli import main
from tests.test_course_flow import project  # noqa: F401 - fixture

GUIDE = """# Guía de seguridad

## Contraseñas

Una contraseña robusta es larga: una frase de cuatro palabras al azar vale más que ocho caracteres con símbolos.

No reutilices la misma contraseña en varias cuentas.

## Verificación en dos pasos

La aplicación autenticadora es más segura que el código por SMS, que se puede interceptar.

## Copias de seguridad

Haz copias de seguridad cada semana en un disco externo.
"""


def test_passages_follow_the_headings_and_the_size(tmp_path):
    file = tmp_path / "guide.md"
    file.write_text(GUIDE, encoding="utf-8")
    found = sources.passages([file], 200, sources.stopwords("es"))
    assert [(p.heading, p.start) for p in found] == [("Contraseñas", 3), ("Verificación en dos pasos", 9), ("Copias de seguridad", 13)]
    small = sources.passages([file], 5, set())
    assert len(small) > len(found)


def test_bm25_finds_the_passage_and_ignores_accents_plurals_and_stopwords(tmp_path):
    file = tmp_path / "guide.md"
    file.write_text(GUIDE, encoding="utf-8")
    words = sources.stopwords("es")
    found = sources.passages([file], 200, words)
    best = sources.rank(found, "las contrasenas que se reutilizan", words, 2)
    assert best[0][1].heading == "Contraseñas"
    assert sources.rank(found, "verificacion autenticadora", words, 1)[0][1].heading == "Verificación en dos pasos"
    assert sources.rank(found, "de la y que", words, 3) == []  # only stopwords


def test_brief_find_and_section_print_the_passages_with_where_they_are(project, capsys):  # noqa: F811
    import shutil

    from tests.test_course_flow import FIXTURES, write_course_rules

    (project / ".env").write_text("COURSEKIT_USER_NAME=Ana\nCOURSEKIT_USER_EMAIL=ana@example.com\n", encoding="utf-8")
    assert main(["new", "Contraseñas seguras", "1", "--code", "PWD"]) == 0
    course_dir = project / "courses" / "PWD"
    write_course_rules(course_dir)
    shutil.copy(FIXTURES / "matrix.json", course_dir / "design" / "matrix.json")
    assert main(["approve", "design", "PWD", "--yes", "--no-commit"]) == 0
    capsys.readouterr()
    assert main(["brief", "PWD", "--find", "contraseña robusta"]) == 1
    assert "has no converted material" in capsys.readouterr().err
    text = course_dir / "brief" / "text" / "files"
    text.mkdir(parents=True)
    (text / "guide.md").write_text(GUIDE, encoding="utf-8")
    assert main(["brief", "PWD", "--find", "SMS interceptado", "--top", "1"]) == 0
    out = capsys.readouterr().out
    assert "# 1 passage(s) of the material for «SMS interceptado» (of 3)" in out
    assert "## 1 · courses/PWD/brief/text/files/guide.md:9-12 · Verificación en dos pasos" in out and "por SMS" in out
    assert main(["brief", "PWD", "--section", "1.2"]) == 0
    out = capsys.readouterr().out
    assert "«1.2 Cómo es una contraseña robusta»" in out and "## 1 · courses/PWD/brief/text/files/guide.md:3-8 · Contraseñas" in out
    assert main(["brief", "PWD", "--section", "9.9"]) == 1
    assert main(["brief", "--find", "x"]) == 2


def test_a_site_with_pages_that_failed_keeps_its_note_and_says_so(tmp_path, monkeypatch):
    import subprocess

    from coursekit import brief

    (tmp_path / "links.md").write_text("- https://docs.acme.example/ — the ACME guide\n", encoding="utf-8")

    def web2md(cmd, **kwargs):  # some pages of the site could not be downloaded: it ends with an error
        out = tmp_path / "text" / "web" / brief.site_slug("https://docs.acme.example/")
        out.mkdir(parents=True)
        (out / "index.md").write_text("# ACME\n\nUna guía.\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 1, "", "")

    monkeypatch.setattr(brief.shutil, "which", lambda name: "node")
    monkeypatch.setattr(brief.subprocess, "run", web2md)
    rows, failed = brief.download_links(tmp_path, {}, refresh=False)
    assert failed == 0 and rows[0]["note"] == "the ACME guide" and rows[0]["pages"] == 1
    assert [key for key, _ in rows[0]["notes"]] == ["pages_failed"]


def test_a_blocked_page_is_opened_in_the_browser_of_the_machine(tmp_path, monkeypatch):
    """A site that answers empty or with a check against robots is not a downloaded page: brief tries again in the browser of
    the machine, and says so when there is none."""
    import subprocess

    from coursekit import brief

    url = "https://law.acme.example/doc?id=1"
    (tmp_path / "links.md").write_text(f"- {url} — the law\n", encoding="utf-8")
    calls = []

    def web2md(cmd, **kwargs):
        calls.append(cmd)
        out = tmp_path / "text" / "web" / brief.site_slug(url)
        out.mkdir(parents=True, exist_ok=True)
        if "--browser" not in cmd:
            return subprocess.CompletedProcess(cmd, 1, "0 páginas descargadas.\n", f"BLOCKED\t{url}\n")
        (out / "index.md").write_text("# Ley\n\nArtículo 1. Texto de la ley.\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "1 páginas descargadas.\n", f"RENDERED\t{url}\n")

    monkeypatch.setattr(brief.shutil, "which", lambda name: "node")
    monkeypatch.setattr(brief.subprocess, "run", web2md)
    monkeypatch.setattr(brief, "browser_args", lambda log=None: ["--browser", "/fake/chrome", "--playwright", "/store/ws"])
    rows, failed = brief.download_links(tmp_path, {}, refresh=False)
    assert len(calls) == 2 and calls[1][-4:] == ["--browser", "/fake/chrome", "--playwright", "/store/ws"]
    assert failed == 0 and rows[0]["pages"] == 1 and [key for key, _ in rows[0]["notes"]] == ["pages_rendered"]

    calls.clear()
    monkeypatch.setattr(brief, "browser_args", lambda log=None: [])  # no Chrome or Edge here
    rows, failed = brief.download_links(tmp_path, {}, refresh=True)
    assert len(calls) == 1 and rows[0]["pages"] == 0
    keys = [key for key, _ in rows[0]["notes"]]
    assert keys == ["pages_blocked"]  # not "pages failed", nor "no text": what to do about it
    assert url in rows[0]["notes"][0][1]["pages"]
