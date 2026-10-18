"""Job aids (the resource type `job_aid`): a checklist or a quick guide the learner downloads to use at work. The writer puts
its text in the body of its placeholder (the lines after the fields); coursekit lays it out with the job aid template of the
theme and the Chrome of the machine prints it to PDF (`coursekit media render`). Every job aid of a project comes out of one
template, so they all look alike: `coursekit theme sample` prints one with sample text, to adjust the template with the
theme; the template is signed with the style guide of the media."""

from __future__ import annotations

import html as htmlmod
import re
from pathlib import Path

from coursekit import config as configmod
from coursekit import course as coursemod
from coursekit import mediatools
from coursekit import theme as thememod
from coursekit.i18n import t

NAME = "job-aid.html"
DEFAULT = Path(__file__).parent / "templates" / "media" / NAME
SAMPLE = Path("branding") / "samples" / "job-aid.pdf"  # inside the theme folder of the project or of the course
CHECKBOX = re.compile(r"^\[ \]\s+")


class JobAidError(Exception):
    pass


def own_template(project, course: dict | None = None) -> Path | None:
    """The template of the course (courses/<CODE>/theme/templates/), else of the project (theme/templates/); None when
    neither has one and the default of coursekit is used."""
    folders = ([course["_dir"] / "theme" / "templates"] if course else []) + [project.theme_dir / "templates"]
    return next((folder / NAME for folder in folders if (folder / NAME).is_file()), None)


def template(project, course: dict | None = None) -> Path:
    return own_template(project, course) or DEFAULT


def page(project, course: dict | None = None) -> str:
    """The page of the job aids (`media › job_aid`), as CSS writes it: "A4 portrait"."""
    cfg = configmod.effective("media", project, course).value.get("job_aid") or {}
    size, orientation = str(cfg.get("page") or "A4"), str(cfg.get("orientation") or "portrait")
    if orientation not in ("portrait", "landscape"):
        raise JobAidError(t("jobaid", "bad_orientation", value=orientation))
    return f"{size} {orientation}"


def body_html(body: str) -> str:
    """The text of the placeholder as HTML; a list whose items all start with `[ ]` is a checklist."""
    from coursekit.assemble import html

    out = html(body)

    def checklist(m: re.Match) -> str:
        items = re.findall(r"<li>(.*?)</li>", m.group(1), re.S)
        if not items or not all(CHECKBOX.match(item.strip()) for item in items):
            return m.group(0)
        return '<ul class="checklist">' + "".join(f"<li>{CHECKBOX.sub('', item.strip())}</li>" for item in items) + "</ul>"

    return re.sub(r"<ul>(.*?)</ul>", checklist, out, flags=re.S)


def page_html(project, course: dict | None, title: str, subtitle: str, body: str, language: str) -> str:
    """The page of a job aid: its template with the theme, the fonts of the brand and the text."""
    from coursekit import brand

    try:
        tokens_css = thememod.css(thememod.load(project, course))
    except thememod.ThemeError:
        tokens_css = ""  # without tokens the template keeps its own neutral colours
    sheet = brand.fonts_stylesheet(project, course)
    try:
        fonts_css = brand.inline_fonts(sheet, project.root)[0] if sheet else ""
    except brand.BrandError as exc:
        raise JobAidError(str(exc)) from None
    values = {"lang": language, "title": htmlmod.escape(title), "subtitle": htmlmod.escape(subtitle),
              "content": body_html(body), "page": page(project, course), "tokens_css": tokens_css, "fonts_css": fonts_css}
    return re.sub(r"\{\{(\w+)\}\}", lambda m: values.get(m.group(1), m.group(0)),
                  template(project, course).read_text(encoding="utf-8"))


def render(project, course: dict | None, title: str, subtitle: str, body: str, language: str, out: Path) -> Path:
    if not body.strip():
        raise JobAidError(t("jobaid", "no_body", title=title))
    out.parent.mkdir(parents=True, exist_ok=True)
    source = out.with_suffix(".print.html")
    source.write_text(page_html(project, course, title, subtitle, body, language), encoding="utf-8", newline="\n")
    try:
        mediatools.print_pdf(source, out)
    finally:
        source.unlink(missing_ok=True)
    return out


def render_asset(course: dict, asset: dict) -> Path:
    """The PDF of a job aid of the manifest, in media/<id>.pdf."""
    unit = coursemod.package_unit(course, asset.get("unit"))
    tk = coursemod.tokens(course)
    subtitle = f"{course['title']} · {tk['unit']} {unit['n']}. {unit['title']}" if unit else course["title"]
    out = course["_dir"] / "media" / f"{str(asset['id']).lower()}.pdf"
    return render(course["_project"], course, str(asset.get("title") or asset["id"]), subtitle, str(asset.get("body") or ""),
                  coursemod.language(course), out)


def sample(project, course: dict | None = None) -> Path:
    """A job aid with sample text, in theme/branding/samples/job-aid.pdf (of the course with its own theme): to look at the
    template while the theme is adjusted."""
    from coursekit import lang

    language = coursemod.language(course) if course else str(configmod.project_data(project).get("content_language") or "es").split("-")[0]
    text = lang.tokens(language)["job_aid_sample"]
    base = course["_dir"] / "theme" if course else project.theme_dir
    return render(project, course, text["title"], text["subtitle"], text["body"], language, base / SAMPLE)
