"""Job aids: the text of their placeholder, the PDF printed with the template of the theme, the download in both assemblies,
the template signed with the style guide of the media, and the sample of `coursekit theme sample`."""

import json

import pytest
import yaml

from coursekit import jobaid, mediastyle, mediatools
from coursekit.cli import main
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture

JOB_AID = """
> **[RECURSO MULTIMEDIA — Ayuda de trabajo]**
> **Título:** Antes de crear una contraseña
> **Descripción:** Lista de comprobación para el puesto.
> **Cómo se elabora:** PDF con la plantilla del tema.
> **Especificaciones:** A4 vertical.
>
> ## Comprueba
>
> - [ ] Abro el gestor de contraseñas.
> - [ ] Uso una frase de cuatro palabras.
"""


@pytest.fixture
def printed(monkeypatch):
    """Chrome stands in: the page it would print is kept, and a PDF is written."""
    pages = []

    def fake(page, out):
        pages.append(page.read_text(encoding="utf-8"))
        out.write_bytes(b"%PDF-1.7 fake")
        return "printed"

    monkeypatch.setattr(mediatools, "print_pdf", fake)
    return pages


def add_job_aid(course_dir, text=JOB_AID):
    content = course_dir / "content" / "unit-01" / "content.md"
    body = content.read_text(encoding="utf-8")
    anchor = "> **[RECURSO MULTIMEDIA — Infografía]**"
    content.write_text(body.replace(anchor, text.strip() + "\n\n" + anchor, 1), encoding="utf-8")


def asset(course_dir, kind="job_aid"):
    manifest = yaml.safe_load((course_dir / "media" / "manifest.yaml").read_text(encoding="utf-8"))
    return next(a for a in manifest["assets"] if a["type"] == kind)


def test_the_text_of_a_job_aid_is_the_body_of_its_placeholder(course, capsys):  # noqa: F811
    add_job_aid(course)
    assert main(["media", "extract", "PWD"]) == 0
    found = asset(course)
    assert found["title"] == "Antes de crear una contraseña"
    assert found["body"] == "## Comprueba\n\n- [ ] Abro el gestor de contraseñas.\n- [ ] Uso una frase de cuatro palabras."
    assert "body" not in asset(course, "infographic")
    capsys.readouterr()
    main(["verify", "PWD", "--unit", "1"])
    assert "job aid has no text" not in capsys.readouterr().out
    add_job_aid(course, "\n".join(JOB_AID.strip().splitlines()[:5]))  # a second one, with no text
    main(["verify", "PWD", "--unit", "1"])
    assert "the job aid has no text" in capsys.readouterr().out


def test_a_job_aid_is_printed_with_the_template_and_downloaded(course, printed, capsys):  # noqa: F811
    add_job_aid(course)
    assert main(["media", "extract", "PWD"]) == 0
    capsys.readouterr()
    assert main(["media", "render", "PWD", asset(course)["id"]]) == 0
    out = capsys.readouterr().out
    pdf = course / "media" / f"{asset(course)['id'].lower()}.pdf"
    assert pdf.is_file() and "--status produced --recipe agent-html-pdf" in out
    page = printed[-1]
    assert '<ul class="checklist"><li>Abro el gestor de contraseñas.</li>' in page
    assert "Contraseñas seguras" in page and "@page { size: A4 portrait; margin: 16mm 16mm 18mm; }" in page and 'lang="es"' in page
    assert "--ja-title-color: var(--color-headings);" in page and "--ja-kicker-transform: uppercase;" in page
    assert "--ja-kicker-tracking: 0.04em;" in page and "--ja-title-size: 20pt;" in page and "--ja-rule: 2pt;" in page
    job = asset(course)["id"]
    assert main(["media", "set", "PWD", job, "--status", "uploaded", "--file", pdf.name, "--asset-path", "c/aid.pdf",
                 "--force"]) == 0
    assert asset(course)["size"] == len(b"%PDF-1.7 fake")
    assert main(["assemble", "plan", "PWD", "--unit", "1"]) == 0
    plan = json.loads((course / "assembly" / "unit-01.plan.json").read_text(encoding="utf-8"))
    brick = next(b for lesson in plan["lessons"] for b in lesson["bricks"] if b["meta"].get("placeholder") == "job_aid")
    assert brick["type"] == "ATTACHMENT"
    assert brick["data"]["properties"]["filePath"] == "c/aid.pdf"
    assert brick["data"]["properties"]["fileName"] == "antes-de-crear-una-contrasena.pdf"


def test_the_page_and_the_template_of_the_project_and_of_the_course(course, printed):  # noqa: F811
    project = course.parent.parent
    (project / "config" / "media.yaml").write_text("job_aid: {page: letter, orientation: landscape}\n", encoding="utf-8")
    own = project / "theme" / "templates" / "job-aid.html"
    own.parent.mkdir(parents=True, exist_ok=True)
    own.write_text("<html lang='{{lang}}'><style>@page { size: {{page}} }</style><h1>{{title}}</h1>{{content}}</html>",
                   encoding="utf-8")
    assert main(["theme", "sample"]) == 0
    assert (project / "theme" / "branding" / "samples" / "job-aid.pdf").is_file()
    assert "size: letter landscape" in printed[-1] and "<h1>Antes de crear una contraseña</h1>" in printed[-1]
    (project / "config" / "media.yaml").write_text("job_aid: {orientation: sideways}\n", encoding="utf-8")
    assert main(["theme", "sample"]) == 1


def test_the_template_is_signed_with_the_style_guide(course):  # noqa: F811
    project = course.parent.parent
    guide = project / "theme" / "branding" / "media-style.md"
    guide.parent.mkdir(parents=True, exist_ok=True)
    guide.write_text("# Media style\n", encoding="utf-8")
    alone = mediastyle.fingerprint(guide)
    template = project / "theme" / "templates" / jobaid.NAME
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_text("<html>{{content}}</html>", encoding="utf-8")
    with_template = mediastyle.fingerprint(guide)
    template.write_text("<html><h1>{{title}}</h1>{{content}}</html>", encoding="utf-8")
    assert len({alone, with_template, mediastyle.fingerprint(guide)}) == 3  # a new template asks for a new signature


def test_the_style_of_the_job_aids_is_their_own_and_takes_only_fonts_of_the_brand(course, printed, capsys):  # noqa: F811
    project = course.parent.parent
    fonts = project / "theme" / "branding" / "fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    (fonts / "brand.woff2").write_bytes(b"font")
    (fonts / "fonts.css").write_text('@font-face { font-family: "Acme Sans"; src: url("brand.woff2") format("woff2"); }\n',
                                     encoding="utf-8")
    (project / "config" / "media.yaml").write_text(
        "job_aid:\n  margins: 12mm\n  text:\n    title: {family: Acme Sans, size: 24, weight: 300, color: accent-ink}\n"
        "    heading: {family: Comic Sans, transform: uppercase}\n  shapes: {rule: 0, radius: 3}\n", encoding="utf-8")
    capsys.readouterr()
    assert main(["theme", "sample"]) == 0
    out = capsys.readouterr().out
    assert "«Comic Sans» is not one of the fonts of the brand (Acme Sans)" in out
    page = printed[-1]
    assert '--ja-title-family: "Acme Sans";' in page and "--ja-title-size: 24pt;" in page and "--ja-title-weight: 300;" in page
    assert "--ja-title-color: var(--color-accent-ink);" in page and "--ja-heading-family:" not in page
    assert "--ja-heading-transform: uppercase;" in page and "--ja-rule: 0pt;" in page and "--ja-radius: 3pt;" in page
    assert "margin: 12mm; }" in page
