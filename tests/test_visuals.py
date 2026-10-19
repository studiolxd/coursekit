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
