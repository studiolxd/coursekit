"""The brand of a project in its media: the colours of the brand for the roles of the tokens (`theme.roles`), the brand material
(`coursekit brand`: a Storybook read whole, a website observed, the fonts, the logos), the style guide of the media and its
signature. The network and the browser are stood in for: these tests reach no website."""

import json
from pathlib import Path

import pytest
import yaml

from coursekit import brand, brief, media, mediastyle, mediatools, storybook, theme
from coursekit.cli import main
from coursekit.course import load as load_course
from coursekit.project import find_project
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture
from tests.test_media import prepare_asset

THEME = Path(__file__).parent / "fixtures" / "creator_theme.json"


def set_theme(root, **values):
    data = yaml.safe_load((root / "project.yaml").read_text(encoding="utf-8"))
    data["theme"] = {**(data.get("theme") or {}), **values}
    (root / "project.yaml").write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


# ── the colours of the brand for the roles ───────────────────────────────────────────────────

def test_the_project_fixes_the_colours_the_platform_lacks_without_touching_the_theme(course, capsys):  # noqa: F811
    root = course.parent.parent
    set_theme(root, roles={"surface": "white", "line": "navy", "text-soft": "text"}, radius=0, shadow="none")
    assert main(["theme", "import", str(THEME)]) == 0
    tokens = json.loads((root / "theme" / "tokens.json").read_text(encoding="utf-8"))
    assert tokens["color"]["surface"] == "#FFFFFF" and tokens["color"]["line"] == "#1B365D"
    assert tokens["color"]["text-soft"] == tokens["color"]["text"]
    assert tokens["origin"]["set"] == {"surface": "white", "line": "navy", "text-soft": "text", "radius": "0", "shadow": "none"}
    assert "surface" not in tokens["origin"]["derived"] and "highlight" in tokens["origin"]["derived"]
    assert tokens["radius"] == "0px" and tokens["shadow"] == {"soft": "none"} and tokens["origin"]["defaults"] == ["space"]
    assert "--radius: 0px;" in (root / "theme" / "tokens.css").read_text(encoding="utf-8")
    capsys.readouterr()
    assert main(["theme", "roles"]) == 0
    out = capsys.readouterr().out
    assert "surface  #FFFFFF (white)  · fixed by the project (white)" in out
    assert "highlight" in out and "derived by coursekit" in out and "seen in: the background of the cards" in out
    assert "Palette of the theme (for theme › roles): black #000000, white #FFFFFF" in out
    set_theme(root, roles={"surface": "grey-lightest"})
    assert main(["theme", "import", str(THEME)]) == 1
    assert "grey-lightest is not a colour of the palette of the theme" in capsys.readouterr().err


def test_a_course_fixes_its_own_roles_over_those_of_the_project(course):  # noqa: F811
    root = course.parent.parent
    set_theme(root, roles={"surface": "white", "line": "navy"})
    data = yaml.safe_load((course / "course.yaml").read_text(encoding="utf-8"))
    data["theme"] = {"roles": {"line": "black"}, "radius": 4}
    (course / "course.yaml").write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    fixed = theme.settings(find_project(), load_course(find_project(), "PWD"))
    assert fixed == {"roles": {"surface": "white", "line": "black"}, "radius": 4}
    assert theme.settings(find_project()) == {"roles": {"surface": "white", "line": "navy"}}


# ── coursekit brand ──────────────────────────────────────────────────────────────────────────

SB = "https://brand.acme.example/"
STORYBOOK = {
    SB + "index.json": {"v": 5, "entries": {"foundations-colours--docs": {"title": "Foundations/Colours", "type": "docs"}}},
    SB + "manifests/docs.json": {"docs": {"foundations-colours--docs": {
        "id": "foundations-colours--docs", "title": "Foundations/Colours",
        "content": 'import { Meta } from "@storybook/addon-docs/blocks";\n\n<Meta title="Foundations/Colours" />\n\n# Colours\n\n'
                   "Navy is the ink; the accent is only a fill. Logo: [logo.svg](/brand/logo.svg)."}}},
    SB + "manifests/components.json": {"components": {"atoms-card": {
        "id": "atoms-card", "name": "Card", "import": "import { Card } from '@acme/brand';",
        "reactDocgen": {"props": {"tone": {"required": False, "tsType": {"name": "'plain' | 'accent'"}, "description": "Its colour"}}},
        "stories": [{"name": "Default", "description": "A plain card.", "snippet": "<Card>Hi</Card>"}],
        "docs": {"atoms-card--docs": {"title": "Atoms/Card", "content": "# Card\n\nSquare corners, no shadow."}}}}},
}
GOOGLE_CSS = ("/* cyrillic */\n@font-face { font-family: 'Acme Sans'; font-style: normal; font-weight: 1 1000; "
              "src: url(https://fonts.gstatic.com/s/acme/cyr.woff2) format('woff2'); }\n"
              "/* latin */\n@font-face { font-family: 'Acme Sans'; font-style: normal; font-weight: 1 1000; "
              "src: url(https://fonts.gstatic.com/s/acme/latin.woff2) format('woff2'); unicode-range: U+0000-00FF; }\n")


def fake_get(url, timeout=60):
    if url in STORYBOOK:
        return json.dumps(STORYBOOK[url]).encode()
    if url == SB + "brand/logo.svg":
        return b"<svg xmlns='http://www.w3.org/2000/svg'/>"
    if url == SB + "index.html":
        return b'<link href="https://fonts.googleapis.com/css2?family=Acme+Sans&amp;display=swap" rel="stylesheet">'
    if url.startswith("https://fonts.googleapis.com/"):
        return GOOGLE_CSS.encode()
    if url.startswith("https://fonts.gstatic.com/"):
        return b"wOF2" + url.encode()
    return None


@pytest.fixture
def branding(course, monkeypatch):  # noqa: F811
    monkeypatch.setattr(storybook, "get", fake_get)
    observed = []

    def observe(url, base, refresh=False, log=None):
        observed.append(url)
        out = base / "text" / "observed" / "www-acme-example.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("# Style observed\n", encoding="utf-8")
        return {"url": url, "file": "text/observed/www-acme-example.md", "families": ["Acme Sans", "Acme Serif"], "google": []}

    monkeypatch.setattr(brand, "observe", observe)
    return course.parent.parent / "theme" / "branding", observed


def test_brand_reads_a_storybook_whole_observes_a_website_and_takes_out_fonts_and_logos(branding, capsys):
    base, observed = branding
    assert main(["brand"]) == 0  # the first time: the folder and its two files
    assert (base / "sources").is_dir() and "# Websites to infer the style from" not in (base / "links.md").read_text(encoding="utf-8")
    assert "# Webs de las que inferir el estilo" in (base / "links.md").read_text(encoding="utf-8")  # the project speaks Spanish
    (base / "links.md").write_text(f"# Material de marca\n\n- {SB} — the design system\n\n# Webs de las que inferir el estilo\n\n"
                                   "- https://www.acme.example/ — the website\n", encoding="utf-8")
    (base / "notes.md").write_text("La lavanda solo como relleno.\n", encoding="utf-8")
    (base / "sources" / "guide.md").write_text("# Guide\n\nThe brand is calm and clear, with plenty of white space.\n", encoding="utf-8")
    (base / "sources" / "tokens.json").write_text('{"color": {"navy": "#1B365D"}}', encoding="utf-8")
    (base / "sources" / "acme-logo.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    (base / "sources" / "fonts").mkdir()
    (base / "sources" / "fonts" / "acme-serif-italic-700.woff2").write_bytes(b"wOF2serif")
    (base / "sources" / "fonts" / "OFL.txt").write_text("SIL Open Font License", encoding="utf-8")
    capsys.readouterr()
    assert main(["brand"]) == 0
    out = capsys.readouterr().out
    assert "fonts: Acme Sans, Acme Serif" in out and observed == ["https://www.acme.example/"]
    web = base / "text" / "web" / brief.site_slug(SB)
    page = (web / "docs" / "foundations-colours.md").read_text(encoding="utf-8")
    assert "Navy is the ink" in page and "import" not in page and "<Meta" not in page
    card = (web / "components" / "atoms-card.md").read_text(encoding="utf-8")
    assert "# Card" in card and "| `tone` |" in card and "### Default" in card and "Square corners, no shadow." in card
    assert (web / "files" / "brand" / "logo.svg").exists() and (base / "logo" / "logo.svg").exists()
    assert (base / "logo" / "acme-logo.svg").exists() and (base / "tokens" / "tokens.json").exists()
    sheet = (base / "fonts" / "fonts.css").read_text(encoding="utf-8")
    assert sheet.startswith(brand.GENERATED) and "font-family: 'Acme Serif';" in sheet and "font-style: italic;" in sheet
    assert "font-weight: 700;" in sheet and "font-family: 'Acme Sans'" in sheet and "cyr" not in sheet  # only the Latin alphabets
    assert (base / "fonts" / "acme-sans" / "acme-sans-normal-latin.woff2").exists() and (base / "fonts" / "OFL.txt").exists()
    index = (base / "index.md").read_text(encoding="utf-8")
    assert "Indicaciones en `notes.md`: sí" in index and "sources/guide.md" in index and "un Storybook" in index
    assert "text/observed/www-acme-example.md" in index and "Acme Serif" in index and "logo/acme-logo.svg" in index
    assert brand.fonts_stylesheet(find_project()) == base / "fonts" / "fonts.css"


def test_a_font_the_brand_uses_without_files_is_asked_for(branding, capsys):
    base, _ = branding
    brand.prepare(base, "en")
    (base / "links.md").write_text("# Websites to infer the style from\n\n- https://www.acme.example/\n", encoding="utf-8")
    assert main(["brand"]) == 0
    assert "the files of Acme Sans, Acme Serif are missing" in capsys.readouterr().out
    assert "## Fuentes sin ficheros" in (base / "index.md").read_text(encoding="utf-8")


def test_the_links_are_read_or_observed_by_their_heading_in_either_language(tmp_path):
    links = tmp_path / "links.md"
    links.write_text("- https://a.example/\n# Brand material\n- https://b.example/ — the book\n<!-- - https://hidden.example/ -->\n"
                     "# Websites to infer the style from\n- https://c.example/\n## Más\n- https://d.example/\n"
                     "# Webs de las que inferir el estilo\n- https://e.example/\n", encoding="utf-8")
    links.write_text(links.read_text(encoding="utf-8") + "# Fuentes de ilustraciones\n- https://www.magnific.com/author/acme-art\n",
                     encoding="utf-8")
    content, style, sources = brand.parse_links(links)
    assert [u for u, _ in content] == ["https://a.example/", "https://b.example/", "https://d.example/"]
    assert [u for u, _ in style] == ["https://c.example/", "https://e.example/"] and content[1][1] == "the book"
    assert sources == [("https://www.magnific.com/author/acme-art", "")]


def test_the_brief_also_reads_a_storybook_whole(course, monkeypatch):  # noqa: F811
    monkeypatch.setattr(storybook, "get", fake_get)
    base = course / "brief"
    (base / "links.md").write_text(f"- {SB}?path=/docs/foundations-colours--docs\n", encoding="utf-8")
    rows, failed = brief.download_links(base, {}, refresh=False)
    assert failed == 0 and rows[0]["pages"] == 2 and [k for k, _ in rows[0]["notes"]] == ["storybook"]
    assert storybook.base_of(f"{SB}iframe.html?id=x") == SB and storybook.detect("https://nothing.example/") is None


# ── the fonts of the brand in what is made ───────────────────────────────────────────────────

def test_an_svg_is_drawn_with_the_fonts_of_the_brand_inside(tmp_path, monkeypatch):
    svg = tmp_path / "a.svg"
    svg.write_text('<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20"><text>Hi</text></svg>',
                   encoding="utf-8")
    pages = []

    def run(cmd, **kw):
        from urllib.parse import urlparse
        from urllib.request import url2pathname

        pages.append(Path(url2pathname(urlparse(cmd[-1]).path)).read_text(encoding="utf-8"))  # the page, from its file:// address
        Path(next(a for a in cmd if a.startswith("--screenshot=")).split("=", 1)[1]).write_bytes(b"png")

    monkeypatch.setattr(mediatools, "browser", lambda: "chrome")
    monkeypatch.setattr(mediatools, "run", run)
    mediatools.render_svg(svg, tmp_path / "a.png", None, "@font-face { font-family: 'Acme Sans'; src: url(data:font/woff2;base64,AA); }")
    assert "@font-face" in pages[0] and '<div class="svg"><svg' in pages[0] and "<?xml" not in pages[0]
    mediatools.render_svg(svg, tmp_path / "b.png")
    assert "<img src=" in pages[1] and "@font-face" not in pages[1]


# ── the style guide of the media and its signature ──────────────────────────────────────────

def test_no_visual_resource_is_produced_until_a_person_signs_the_style_guide(course, capsys):  # noqa: F811
    prepare_asset(course, capsys)
    root = course.parent.parent
    guide = root / "theme" / "branding" / "media-style.md"
    guide.parent.mkdir(parents=True, exist_ok=True)
    guide.write_text("# Style\n\nOnly the colours of the brand.\n", encoding="utf-8")
    produce = ["media", "set", "PWD", "U1-S2-M1", "--status", "produced", "--recipe", "agent-svg", "--depicts", "concept"]
    assert main(produce) == 1
    assert "the style guide of the media is not signed" in capsys.readouterr().err
    assert main(["media", "plan", "PWD"]) == 0 and "approve media-style PWD" in capsys.readouterr().out
    assert main(["approve", "media-style", "PWD", "--yes", "--no-commit"]) == 0
    assert "style guide theme/branding/media-style.md approved by Ana" in capsys.readouterr().out
    signed = load_course(find_project(), "PWD")
    assert mediastyle.approval(signed)["path"] == "theme/branding/media-style.md"
    guide.write_text("# Style\n\nOnly the colours of the brand, and no shadows.\n", encoding="utf-8")  # it changed: signed again
    assert mediastyle.waiting(load_course(find_project(), "PWD"))
    own = course / "theme" / "branding" / "media-style.md"  # a course with a guide of its own: that is the one in force
    own.parent.mkdir(parents=True)
    own.write_text("# The style of this course\n", encoding="utf-8")
    assert mediastyle.path(load_course(find_project(), "PWD")) == own
    assert main(["approve", "media-style", "PWD", "--yes", "--no-commit"]) == 0
    assert main(produce) == 0


def test_the_signature_of_the_guide_can_be_turned_off(course, capsys):  # noqa: F811
    from tests.test_exelearning import edit_course

    root = course.parent.parent
    (root / "theme" / "branding").mkdir(parents=True, exist_ok=True)
    (root / "theme" / "branding" / "media-style.md").write_text("# Style\n", encoding="utf-8")
    assert mediastyle.waiting(load_course(find_project(), "PWD"))
    edit_course(course, lambda d: d.update(rules={"review": {"media_style": "none"}}))
    assert not mediastyle.waiting(load_course(find_project(), "PWD"))
    assert media.config(course=load_course(find_project(), "PWD"))["fonts"] == "auto"


def test_a_package_of_the_design_system_gives_its_fonts_icons_logos_and_tokens_never_its_code(course, tmp_path):  # noqa: F811
    import io
    import tarfile

    base = course.parent.parent / "theme" / "branding"
    brand.prepare(base, "en")
    files = {"package/package.json": b'{"name": "@acme/brand"}', "package/dist/index.js": b"export const x = 1;",
             "package/dist/fonts.css": b"@font-face { font-family: 'Acme Sans'; src: url('./assets/fonts/acme.woff2') format('woff2'); }",
             "package/dist/assets/fonts/acme.woff2": b"wOF2acme", "package/dist/assets/logo.svg": b"<svg/>",
             "package/dist/assets/icons/glyphs/logout.svg": b"<svg/>", "package/dist/assets/icons/glyphs/search.svg": b"<svg/>",
             "package/src/tokens/tokens.json": b'{"color": {}}', "package/src/tokens/components/button.css": b":root { --b: 1px; }"}
    with tarfile.open(base / "sources" / "acme-brand-1.0.0.tgz", "w:gz") as tf:
        for name, body in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(body)
            tf.addfile(info, io.BytesIO(body))
    (base / "sources" / "icons").mkdir()
    (base / "sources" / "icons" / "home.svg").write_text("<svg/>", encoding="utf-8")
    done = brand.build(find_project())
    assert sorted(p.name for p in (base / "icons").iterdir()) == ["home.svg", "logout.svg", "search.svg"]
    assert sorted(p.name for p in (base / "logo").iterdir()) == ["logo.svg"]  # logout is an icon, not a logo
    assert sorted(p.name for p in (base / "tokens").iterdir()) == ["tokens.json"]  # not the stylesheet of a component
    assert done["fonts"] == ["Acme Sans"] and (base / "fonts" / "assets" / "fonts" / "acme.woff2").exists()
    assert not list((base / "text" / "archives").rglob("*.js"))
    assert "3 iconos de la marca en `icons/`" in (base / "index.md").read_text(encoding="utf-8")  # the language of the courses


def test_the_borders_and_weights_of_the_brand_reach_the_simulations_and_the_videos(course, capsys, monkeypatch):  # noqa: F811
    from coursekit import video
    from tests.test_video import montage

    root = course.parent.parent
    set_theme(root, border=1, weights={"normal": 300, "strong": 500})
    assert main(["theme", "import", str(THEME)]) == 0
    css = (root / "theme" / "tokens.css").read_text(encoding="utf-8")
    assert "--border-width: 1px;" in css and "--font-weight: 300;" in css and "--font-weight-strong: 500;" in css
    assert ".btn:hover { color: var(--color-accent-strong" in css and "border-left: 4px solid var(--color-accent-strong" in css
    assert video._weights(montage(course), {}) == {"normal": 300.0, "strong": 500.0}
    assert video._weights(montage(course), {"weights": {"strong": 600}}) == {"normal": 300.0, "strong": 600.0}


# ── the illustration sources and coursekit media stock ──────────────────────────────────────

LINE = '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path d="M0 0h5"/>' \
       '<rect style="fill:#FFFFFF;" width="2" height="2"/><circle fill="#010102" r="1"/></svg>'
COLOUR = '<svg xmlns="http://www.w3.org/2000/svg"><path fill="#E38DDD" d="M0 0"/><path fill="#311944" d="M1 1"/></svg>'


def fake_magnific(path, params=None):
    params = params or {}
    item = lambda rid, title: {"id": rid, "title": title, "author": {"id": 99, "slug": "acme-art"},  # noqa: E731
                               "licenses": [{"type": "freemium"}], "image": {"source": {"url": f"https://img.example/{rid}.jpg"}},
                               "meta": {"available_formats": {"svg": {}, "eps": {}}}}
    if path == "resources" and params.get("term") == "acme art":
        return {"data": [item(1, "Something"), {**item(2, "Other"), "author": {"id": 7, "slug": "someone"}}]}
    if path == "resources" and params.get("filters[author]") == 99:
        return {"data": [item(11, "Password security concept"), item(12, "Lock concept")]}
    if path.startswith("resources/") and path.endswith("/download/svg"):
        return {"data": [{"filename": "x.svg", "url": f"https://dl.example/{path.split('/')[1]}.svg"}]}
    if path.startswith("resources/"):
        return {"data": {"url": "https://www.magnific.com/free-vector/x_11.htm", "premium": False, "author": {"slug": "acme-art"},
                         "license": "https://www.magnific.com/profile/license/pdf/11"}}
    return {"data": []}


def test_an_author_of_magnific_becomes_an_illustration_source_and_its_illustrations_come_recoloured(course, capsys, monkeypatch):  # noqa: F811
    from coursekit import illustrations

    monkeypatch.setenv("MAGNIFIC_API_KEY", "mk")
    monkeypatch.setattr(illustrations, "get", fake_magnific)
    monkeypatch.setattr(illustrations, "fetch", lambda url: (COLOUR if "12" in url else LINE).encode() if url.endswith(".svg")
                        else b"jpg")
    root = course.parent.parent
    assert main(["theme", "import", str(THEME)]) == 0
    base = root / "theme" / "branding"
    brand.prepare(base, "es")
    (base / "links.md").write_text("# Fuentes de ilustraciones\n\n- https://www.magnific.com/author/acme-art — line art\n"
                                   "- https://illustrations.example/ — a reference\n", encoding="utf-8")
    brand.build(find_project())
    sources = illustrations.load(base)
    assert sources[0]["author_id"] == 99 and sources[1]["provider"] is None
    assert sorted(p.name for p in (base / "style").glob("source-*")) == ["source-acme-art-11.jpg", "source-acme-art-12.jpg"]
    assert "autor acme-art de Magnific (id 99)" in (base / "index.md").read_text(encoding="utf-8")
    prepare_asset(course, capsys)
    assert main(["media", "stock", "PWD", "U1-S2-M1", "--find", "password"]) == 0
    out = capsys.readouterr().out
    assert "11  Password security concept (acme-art; licence: freemium)" in out and "https://img.example/12.jpg" in out
    assert main(["media", "stock", "PWD", "U1-S2-M1", "--take", "12"]) == 1  # a colour version
    assert "is a colour version, not a line one" in capsys.readouterr().err
    assert main(["media", "stock", "PWD", "U1-S2-M1", "--take", "11"]) == 0
    svg = (course / "media" / "files" / "U1-S2-M1.svg").read_text(encoding="utf-8")
    ink = json.loads((root / "theme" / "tokens.json").read_text(encoding="utf-8"))["color"]["text"]
    assert f'<svg fill="{ink}"' in svg and "#010102" not in svg and f'fill="{ink}"' in svg and "fill:#FFFFFF" in svg
    asset = next(a for a in yaml.safe_load((course / "media" / "manifest.yaml").read_text(encoding="utf-8"))["assets"]
                 if a["id"] == "U1-S2-M1")
    assert asset["recipe"] == "magnific-stock" and asset["source"]["resource"] == 11 and asset["source"]["license"] == "freemium"
    assert asset.get("status") != "produced"  # the agent checks it, makes its PNG and marks it


def test_media_stock_says_what_it_needs(course, capsys, monkeypatch):  # noqa: F811
    prepare_asset(course, capsys)
    assert main(["media", "stock", "PWD", "U1-S2-M1"]) == 2
    monkeypatch.setenv("MAGNIFIC_API_KEY", "mk")
    assert main(["media", "stock", "PWD", "U1-S2-M1", "--find", "lock"]) == 1
    assert "there are no illustration sources" in capsys.readouterr().err
