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
ROLES = ("kicker", "title", "heading", "subheading", "body", "quote")
TEXT_KEYS = ("family", "size", "weight", "style", "transform", "tracking", "leading", "color")
SHAPE_KEYS = ("rule", "rule_color", "radius", "border", "fill")
CSS_VALUE = re.compile(r"^[\w .,#%-]+$")  # what a value of the style may hold: no braces, quotes or semicolons


class JobAidError(Exception):
    pass


def own_template(project, course: dict | None = None) -> Path | None:
    """The template of the course (courses/<CODE>/theme/templates/), else of the project (theme/templates/); None when
    neither has one and the default of coursekit is used."""
    folders = ([course["_dir"] / "theme" / "templates"] if course else []) + [project.theme_dir / "templates"]
    return next((folder / NAME for folder in folders if (folder / NAME).is_file()), None)


def template(project, course: dict | None = None) -> Path:
    return own_template(project, course) or DEFAULT


def style_css(project, course: dict | None, families: list[str]) -> tuple[str, list[str]]:
    """The style of the job aids (`media › job_aid › text` and `shapes`) as CSS variables for the template (`--ja-<role>-<key>`,
    `--ja-<shape>`), and the warnings: a family that is not one of the fonts of the brand is left out."""
    cfg = configmod.effective("media", project, course).value.get("job_aid") or {}
    known = {f.lower() for f in families}
    lines, warnings = [], []

    def value(key: str, raw: object) -> str | None:
        if raw is None or raw == "" or not CSS_VALUE.match(str(raw)):
            return None
        if key in ("color", "rule_color", "fill"):
            return f"var(--color-{raw})"
        if key in ("size", "rule", "radius", "border"):
            return f"{raw}pt"
        if key == "tracking":
            return f"{raw}em"
        return str(raw)

    for role in ROLES:
        values = (cfg.get("text") or {}).get(role) or {}
        for key in TEXT_KEYS:
            raw = values.get(key) if isinstance(values, dict) else None
            if key == "family" and raw:
                if str(raw).lower() not in known:
                    warnings.append(t("jobaid", "font_not_brand", family=raw, role=role, families=", ".join(families) or "-"))
                    continue
                lines.append(f'  --ja-{role}-family: "{raw}";')
                continue
            css = value(key, raw)
            if css is not None:
                lines.append(f"  --ja-{role}-{key}: {css};")
    shapes = cfg.get("shapes") or {}
    for key in SHAPE_KEYS:
        css = value(key, shapes.get(key)) if isinstance(shapes, dict) else None
        if css is not None:
            lines.append(f"  --ja-{key.replace('_', '-')}: {css};")
    margins = cfg.get("margins")
    if margins and CSS_VALUE.match(str(margins)):
        lines.append(f"  --ja-margins: {margins};")
    return (":root {\n" + "\n".join(lines) + "\n}") if lines else "", warnings


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


def page_html(project, course: dict | None, title: str, subtitle: str, body: str, language: str) -> tuple[str, list[str]]:
    """The page of a job aid: its template with the theme, the fonts and the style of the job aids, and the text; and the
    warnings of the style."""
    from coursekit import brand

    try:
        tokens_css = thememod.css(thememod.load(project, course))
    except thememod.ThemeError:
        tokens_css = ""  # without tokens the template keeps its own neutral colours
    sheet = brand.fonts_stylesheet(project, course)
    try:
        fonts_css, families = brand.inline_fonts(sheet, project.root) if sheet else ("", [])
    except brand.BrandError as exc:
        raise JobAidError(str(exc)) from None
    own_css, warnings = style_css(project, course, families)
    margins = str((configmod.effective("media", project, course).value.get("job_aid") or {}).get("margins") or "16mm 16mm 18mm")
    values = {"lang": language, "title": htmlmod.escape(title), "subtitle": htmlmod.escape(subtitle),
              "content": body_html(body), "page": page(project, course), "tokens_css": tokens_css, "fonts_css": fonts_css,
              "style_css": own_css, "margins": margins if CSS_VALUE.match(margins) else "16mm 16mm 18mm"}
    html = re.sub(r"\{\{(\w+)\}\}", lambda m: values.get(m.group(1), m.group(0)),
                  template(project, course).read_text(encoding="utf-8"))
    return html, warnings


def render(project, course: dict | None, title: str, subtitle: str, body: str, language: str,
           out: Path) -> tuple[Path, list[str]]:
    """The PDF of a job aid, and the warnings of its style."""
    if not body.strip():
        raise JobAidError(t("jobaid", "no_body", title=title))
    out.parent.mkdir(parents=True, exist_ok=True)
    source = out.with_suffix(".print.html")
    html, warnings = page_html(project, course, title, subtitle, body, language)
    source.write_text(html, encoding="utf-8", newline="\n")
    try:
        mediatools.print_pdf(source, out)
    finally:
        source.unlink(missing_ok=True)
    return out, warnings


def render_asset(course: dict, asset: dict) -> tuple[Path, list[str]]:
    """The PDF of a job aid of the manifest, in media/<id>.pdf."""
    unit = coursemod.package_unit(course, asset.get("unit"))
    tk = coursemod.tokens(course)
    subtitle = f"{course['title']} · {tk['unit']} {unit['n']}. {unit['title']}" if unit else course["title"]
    out = course["_dir"] / "media" / f"{str(asset['id']).lower()}.pdf"
    return render(course["_project"], course, str(asset.get("title") or asset["id"]), subtitle, str(asset.get("body") or ""),
                  coursemod.language(course), out)


def sample(project, course: dict | None = None) -> tuple[Path, list[str]]:
    """A job aid with sample text, in theme/branding/samples/job-aid.pdf (of the course with its own theme): to look at the
    template while the theme is adjusted."""
    from coursekit import lang

    language = coursemod.language(course) if course else str(configmod.project_data(project).get("content_language") or "es").split("-")[0]
    text = lang.tokens(language)["job_aid_sample"]
    base = course["_dir"] / "theme" if course else project.theme_dir
    return render(project, course, text["title"], text["subtitle"], text["body"], language, base / SAMPLE)
