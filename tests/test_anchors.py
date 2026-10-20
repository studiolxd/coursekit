"""The crosshairs of the images with points: drawn from the content on SVG and raster images, recorded in the manifest, moved
with --set, and checked by verify."""

import yaml

from coursekit import anchors
from coursekit.cli import main
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture

GRAPHIC = """
:::labelled-graphic
imagen: Anatomía de una contraseña
#### Longitud
posición: 20,30
La parte que más protege.
#### Frase
Cuatro palabras al azar.
:::
"""
SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900"><rect width="1600" height="900" fill="#eee"/></svg>\n'


def manifest(course_dir) -> dict:
    return yaml.safe_load((course_dir / "media" / "manifest.yaml").read_text(encoding="utf-8"))


def infographic(course_dir) -> dict:
    return next(a for a in manifest(course_dir)["assets"] if a["type"] == "infographic")


def setup_graphic(course_dir, file="anatomia.svg"):
    content = course_dir / "content" / "unit-01" / "content.md"
    text = content.read_text(encoding="utf-8")
    anchor = "> **[RECURSO MULTIMEDIA — Infografía]**"
    content.write_text(text.replace(anchor, GRAPHIC.strip() + "\n\n" + anchor, 1), encoding="utf-8")
    assert main(["media", "extract", "PWD"]) == 0
    asset = infographic(course_dir)
    assert asset["points"] == ["Longitud", "Frase"]  # the media agent knows the image is for points
    if file.endswith(".svg"):
        (course_dir / "media" / file).write_text(SVG, encoding="utf-8")
    else:
        from PIL import Image

        Image.new("RGB", (400, 200), "white").save(course_dir / "media" / file)
    assert main(["media", "set", "PWD", asset["id"], "--status", "produced", "--file", file, "--depicts", "concept",
                 "--force"]) == 0
    return asset["id"], content


def test_crosshairs_are_drawn_from_the_content_and_kept_in_step(course, capsys):  # noqa: F811
    asset_id, content = setup_graphic(course)
    capsys.readouterr()
    assert main(["media", "anchors", "PWD"]) == 0
    assert "points without a position (Frase)" in capsys.readouterr().out
    assert main(["media", "anchors", "PWD", asset_id, "--set", "Frase=70,60"]) == 0
    assert "posición: 70,60" in content.read_text(encoding="utf-8")
    svg = (course / "media" / "anatomia.svg").read_text(encoding="utf-8")
    assert svg.count("data-ck-anchor=") == 2 and 'translate(320.00 270.00)' in svg and 'translate(1120.00 540.00)' in svg
    assert infographic(course)["anchors"] == [{"label": "Longitud", "at": [20.0, 30.0]}, {"label": "Frase", "at": [70.0, 60.0]}]
    capsys.readouterr()
    main(["verify", "PWD", "--unit", "1"])
    assert "crosshairs of the image" not in capsys.readouterr().out
    content.write_text(content.read_text(encoding="utf-8").replace("posición: 20,30", "posición: 25,30"), encoding="utf-8")
    main(["verify", "PWD", "--unit", "1"])
    assert "the crosshairs of the image are not the ones of the content" in capsys.readouterr().out
    assert main(["media", "anchors", "PWD", asset_id]) == 0  # drawn again: the old crosses go
    svg = (course / "media" / "anatomia.svg").read_text(encoding="utf-8")
    assert svg.count("data-ck-anchor=") == 2 and 'translate(400.00 270.00)' in svg
    assert main(["media", "anchors", "PWD", asset_id, "--set", "Nada=1,1"]) == 1
    assert main(["media", "anchors", "PWD", asset_id, "--set", "Frase=170,1"]) == 1


def test_a_raster_image_is_drawn_over_its_clean_copy(course, capsys):  # noqa: F811
    from PIL import Image

    asset_id, _ = setup_graphic(course, "anatomia.png")
    assert main(["media", "anchors", "PWD", asset_id, "--set", "Frase=50,50"]) == 0
    clean = course / "media" / "anatomia.clean.png"
    with Image.open(course / "media" / "anatomia.png") as drawn, Image.open(clean) as original:
        assert drawn.getpixel((200, 100))[:3] != (255, 255, 255) and original.getpixel((200, 100)) == (255, 255, 255)
    assert main(["media", "anchors", "PWD", asset_id, "--set", "Frase=10,10"]) == 0
    with Image.open(course / "media" / "anatomia.png") as drawn:
        assert drawn.getpixel((200, 100))[:3] == (255, 255, 255)  # the old cross is gone


def test_the_hotspots_of_a_simulation_mark_the_centre_of_their_area(course):  # noqa: F811
    content = course / "content" / "unit-01" / "content.md"
    content.write_text(content.read_text(encoding="utf-8") + """
:::scenario
id: nota
title: La nota
start: s1
scenes:
  s1:
    text: Mira la mesa.
    background: Una mesa con una nota pegada en la pantalla
    hotspots:
      - {label: La nota, area: [60, 20, 10, 10], goto: fin}
      - {label: El teclado, area: [30, 70], goto: fin}
  fin:
    text: Fin.
    ending: good
:::
""", encoding="utf-8")
    from coursekit import course as coursemod
    from coursekit.project import find_project

    loaded = coursemod.load(find_project(), "PWD")
    points = anchors.hotspot_points(loaded, loaded["units"][0])
    (spots,) = points.values()
    assert [(p.label, p.at, p.kind) for p in spots] == [("La nota", (65.0, 25.0), "hotspot"), ("El teclado", (30.0, 70.0), "hotspot")]


def test_the_image_of_a_labelled_graphic_does_not_also_go_alone():
    from coursekit.assemble import fold_labelled_images

    image = {"type": "IMAGE", "data": {}, "meta": {"placeholder": "infographic", "title": "Anatomía"}}
    other = {"type": "IMAGE", "data": {}, "meta": {"placeholder": "image", "title": "Otra"}}
    pending = {"type": "NOTE", "data": {}, "meta": {"placeholder": "infographic", "title": "Anatomía"}}
    graphic = {"type": "LABELLED_GRAPHIC", "data": {}, "meta": {"directive": "labelled-graphic", "image": "Anatomía"}}
    assert fold_labelled_images([image, graphic, other]) == [graphic, other]
    assert fold_labelled_images([pending, graphic]) == [pending, graphic]  # not produced: its note stays
    branch = {"type": "CONDITIONAL", "data": {"branches": [{"condition": "x", "bricks": [image, graphic]}], "else": [image]},
              "meta": {}}
    folded = fold_labelled_images([branch])[0]["data"]
    assert folded["branches"][0]["bricks"] == [graphic] and folded["else"] == []
    assert fold_labelled_images([image, other]) == [image, other]


def test_verify_warns_when_a_graphic_names_the_placeholder_of_another_section(course, capsys):  # noqa: F811
    asset_id, content = setup_graphic(course)
    capsys.readouterr()
    main(["verify", "PWD", "--unit", "1"])
    assert "declared in another section" not in capsys.readouterr().out
    text = content.read_text(encoding="utf-8").replace(GRAPHIC.strip() + "\n\n", "", 1)
    head = next(line for line in text.splitlines() if line.startswith("## Apartado 3"))
    content.write_text(text.replace(head, head + "\n\n" + GRAPHIC.strip(), 1), encoding="utf-8")
    main(["verify", "PWD", "--unit", "1"])
    assert f"the graphic with points uses {asset_id}, declared in another section" in capsys.readouterr().out
