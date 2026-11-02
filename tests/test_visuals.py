"""The visual support of the sections: an introduction and a summary carry a visual resource; a content section carries one
or says why not."""

import yaml

from coursekit.cli import main
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture
from tests.test_course_flow import CONTENT


def placeholder(kind, title):
    return (f"> **[RECURSO MULTIMEDIA — {kind}]**\n> **Título:** {title}\n> **Descripción:** {title}, para el apartado.\n"
            "> **Cómo se elabora:** De las fuentes de la marca.\n> **Especificaciones:** 1600 × 900.\n")


def with_rule(course_dir):
    path = course_dir / "course.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["rules"]["content"].update(visual_sections=["intro", "summary"], visual_decision=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def verify(course_dir, content, capsys):
    (course_dir / "content" / "unit-01" / "content.md").write_text(content, encoding="utf-8")
    main(["verify", "PWD", "--no-update"])
    return capsys.readouterr().out


def test_an_introduction_and_a_summary_carry_a_visual_resource(course, capsys):  # noqa: F811
    with_rule(course)
    out = verify(course, CONTENT, capsys)
    assert out.count("an introduction or a summary always carries a visual resource") == 2
    assert "Apartado 2: it has no visual resource" not in out  # its infographic supports it
    intro, summary = "## Apartado 1 — Introducción y objetivos *(mín. 40 palabras)*\n", "## Apartado 3 — Resumen *(mín. 40 palabras)*\n"
    content = CONTENT.replace(intro, intro + "\n" + placeholder("Imagen", "Una llave en una cerradura"))
    content = content.replace(summary, summary + "\n" + placeholder("Ilustración", "Las tres claves de una contraseña"))
    assert "always carries a visual resource" not in verify(course, content, capsys)


def test_a_content_section_carries_a_visual_resource_or_says_why_not(course, capsys):  # noqa: F811
    with_rule(course)
    start = CONTENT.index("> **[RECURSO MULTIMEDIA — Infografía]**")
    end = CONTENT.index("1600 × 900.", start) + len("1600 × 900.\n")
    bare = CONTENT[:start] + CONTENT[end:]
    assert "Apartado 2: it has no visual resource and does not say why" in verify(course, bare, capsys)
    marked = bare.replace(":::single-choice", "<!-- SIN IMAGEN -->\n\n:::single-choice")
    assert "Apartado 2: <!-- SIN IMAGEN --> with no reason" in verify(course, marked, capsys)
    reasoned = bare.replace(":::single-choice", "<!-- SIN IMAGEN: el acordeón ya ordena las ideas -->\n\n:::single-choice")
    out = verify(course, reasoned, capsys)
    assert "Apartado 2: it has no visual resource" not in out and "with no reason" not in out
    iconic = bare.replace(":::single-choice", placeholder("Icono", "Un candado") + "\n:::single-choice")
    assert "Apartado 2: it has no visual resource" not in verify(course, iconic, capsys)


# ── how much is seen, and where the media go ───────────────────────────────────────────────────

def media_content(extra=""):
    """The sample unit with a carousel whose first step carries its capture, two photos in a row and one beside its text."""
    capture = placeholder("Imagen", "El engranaje")
    return CONTENT.replace(":::accordion\n#### Longitud\nMás larga es mejor.\n:::",
                           ":::carousel\n#### Abre la configuración\nPulsa el engranaje.\n\n" + capture
                           + "\n#### Cambia la longitud\nEscribe doce.\n:::\n\n" + placeholder("Imagen", "Foto uno") + "\n"
                           + placeholder("Imagen", "Foto dos") + "\n" + placeholder("Imagen", "Junto")
                           + "> **Disposición:** junto al texto\n\nEste párrafo va al lado de la imagen.\n" + extra)


def plan_of(course_dir, manifest_changes=None):
    from coursekit import assemble
    from coursekit import course as coursemod
    from coursekit.project import find_project

    assert main(["media", "extract", "PWD"]) == 0
    if manifest_changes:
        path = course_dir / "media" / "manifest.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for asset in data["assets"]:
            asset.update(manifest_changes.get(asset["id"], {}))
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    loaded = coursemod.load(find_project(), "PWD")
    plan, errors, warnings = assemble.build_plan(loaded, loaded["units"][0])
    assert not errors
    return loaded, [b for lesson in plan["lessons"] for b in lesson["bricks"]], warnings


def test_a_unit_that_only_draws_is_warned_never_failed(course, capsys):  # noqa: F811
    out = verify(course, CONTENT, capsys)
    assert "0 photograph(s) or capture(s) < 1" in out
    assert "WARNING [media] content.md: 0 photograph" in out
    assert "photograph(s) or capture(s)" not in verify(course, media_content(), capsys)


def test_the_placeholders_inside_panels_are_numbered_with_their_section(course, capsys):  # noqa: F811
    (course / "content" / "unit-01" / "content.md").write_text(media_content(), encoding="utf-8")
    loaded, bricks, _ = plan_of(course)
    from coursekit import assemble

    titles = {a["id"]: a["title"] for a in assemble.manifest_assets(loaded).values()}
    assert titles["U1-S2-M1"] == "El engranaje" and titles["U1-S2-M4"] == "Junto" and titles["U1-S2-M5"] == "Anatomía de una contraseña"
    carousel = next(b for b in bricks if b["type"] == "CAROUSEL")
    assert "El engranaje" in carousel["data"]["items"][0]["content"]  # not produced yet: a line in its text


def test_a_step_carries_its_capture_and_images_in_a_row_go_together(course, capsys):  # noqa: F811
    (course / "content" / "unit-01" / "content.md").write_text(media_content(), encoding="utf-8")
    uploaded = lambda n: {"status": "uploaded", "asset_path": f"c/U1-S2-M{n}.jpg", "alt": f"alt {n}"}  # noqa: E731
    _, bricks, warnings = plan_of(course, {
        "U1-S2-M1": {"provisional_path": "c/U1-S2-M1.png"},
        "U1-S2-M2": uploaded(2),
        "U1-S2-M3": {**uploaded(3), "source": {"provider": "magnific", "author": "Lena", "attribution": True}},
        "U1-S2-M4": uploaded(4)})
    step = next(b for b in bricks if b["type"] == "CAROUSEL")["data"]["items"][0]
    assert step["mediaType"] == "image" and step["imagePath"] == "c/U1-S2-M1.png" and "Pendiente" in step["imageAlt"]
    assert any("U1-S2-M1" in w and "provisional" in w for w in warnings)
    gallery = next(b for b in bricks if b["type"] == "IMAGE_GALLERY")["data"]["items"]
    assert [i["imagePath"] for i in gallery] == ["c/U1-S2-M2.jpg", "c/U1-S2-M3.jpg"]
    assert "Foto: Lena (Magnific)" in gallery[1]["content"] and "Foto:" not in gallery[0]["content"]
    beside = next(b for b in bricks if b["type"] == "IMAGE_TEXT")["data"]
    assert beside["properties"]["imagePath"] == "c/U1-S2-M4.jpg" and "al lado de la imagen" in beside["content"]["content"]


def test_a_placeholder_that_would_be_lost_in_a_directive_fails(course, capsys):  # noqa: F811
    lost = CONTENT.replace(":::accordion\n#### Longitud\nMás larga es mejor.\n:::",
                           ":::note\n" + placeholder("Imagen", "Perdida") + ":::\n\n:::accordion\n#### Longitud\nMás larga es mejor.\n:::")
    assert "inside :::note would be lost" in verify(course, lost, capsys)
    two = CONTENT.replace("#### Longitud\nMás larga es mejor.\n",
                          "#### Longitud\nMás larga es mejor.\n" + placeholder("Imagen", "Una") + placeholder("Imagen", "Otra"))
    assert "a panel carries one media placeholder only" in verify(course, two, capsys)


def test_the_provisional_image_of_a_pending_resource(course, tmp_path):  # noqa: F811
    from coursekit.htmlkit import build
    from coursekit.media import provisional

    asset = {"id": "U1-S2-M1", "type": "image", "title": "Ventana de la contraseña", "specs": "1280x720", "depicts": "interface",
             "status": "scripted"}
    svg = provisional.svg({"language": "es"}, asset)
    assert 'width="1280"' in svg and "Pendiente: captura de la aplicación" in svg and "Ventana de la contraseña" in svg
    assert not provisional.applies({**asset, "status": "produced"}) and not provisional.applies({**asset, "kind": "background"})
    (course / "content" / "unit-01" / "content.md").write_text(media_content(), encoding="utf-8")
    loaded, _, _ = plan_of(course)
    prepared, _ = build.prepare_assets(loaded, tmp_path / "pkg")
    assert prepared["U1-S2-M1"]["provisional_path"] == "media/U1-S2-M1.provisional.svg"
    assert (tmp_path / "pkg" / "media" / "U1-S2-M1.provisional.svg").is_file()
