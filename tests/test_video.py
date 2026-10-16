"""`coursekit video`: a video as data, a montage of scenes of the library, the project or the course."""

import json

import pytest
import yaml

from coursekit import mediacheck, mediatools, video
from coursekit.cli import main
from coursekit.course import load as load_course
from coursekit.project import find_project
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture
from tests.test_media import manifest, prepare_asset

MONTAGE = {"version": 1, "scenes": [
    {"id": "opening", "type": "title", "props": {"kicker": "Unidad 1", "title": "Contraseñas largas"},
     "says": "Hoy vemos por qué las contraseñas largas protegen más."},
    {"id": "length", "type": "split", "props": {"title": "La longitud manda", "points": [{"text": "Doce caracteres o más", "say": "doce"}]},
     "says": "La longitud manda: doce caracteres o más."},
    {"id": "close", "type": "outro", "props": {"title": "Larga y única"}, "duration": 3,
     "shows": "El cierre, sobre el color de acento: «Larga y única»"}]}


def montage(course_dir, data=MONTAGE):
    path = course_dir / "media" / "scripts" / "U1-S2-M1.video.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return load_course(find_project(), "PWD")


def scene_folder(base, name, description="mine"):
    folder = base / name
    folder.mkdir(parents=True)
    (folder / "index.tsx").write_text("export default function S() { return null; }\n", encoding="utf-8")
    meta = {"description": description, "props": {"title": {"type": "text", "on_screen": True}}}
    (folder / "scene.yaml").write_text(yaml.safe_dump(meta), encoding="utf-8")


def test_the_catalog_shows_the_library_and_how_it_is_built(course):  # noqa: F811
    lines = video.catalog(montage(course))
    text = "\n".join(lines)
    for name in ("title", "split", "stat", "outro", "screencast", "compare", "list", "quote", "diagram", "lower-third", "callout"):
        assert f"{name} [library]" in text
    assert "built from: Background, TitleBlock" in text and "title: text, required, max 60, on screen" in text
    assert "atoms: Arrow, Background, Badge, Card, Counter" in text and "molecules: BulletList, CompareColumn, StatBlock" in text
    assert text.index("Scenes:") < text.index("Layers (over a scene")


def test_a_scene_of_the_course_hides_one_of_the_project_which_hides_one_of_the_library(course):  # noqa: F811
    root = course.parent.parent
    scene_folder(root / "tools" / "remotion" / "src" / "scenes", "title", "the title of the project")
    scene_folder(root / "tools" / "remotion" / "src" / "scenes", "timeline", "a timeline of the project")
    scene_folder(course / "video" / "scenes", "timeline", "a timeline of this course")
    found = video.scenes(montage(course))
    assert found["title"]["origin"] == "project" and found["title"]["hides"] == "library"
    assert found["timeline"]["origin"] == "course" and found["timeline"]["meta"]["description"] == "a timeline of this course"
    assert found["split"]["origin"] == "library"


def test_the_registry_imports_the_scenes_that_win(course):  # noqa: F811
    root = course.parent.parent
    (root / "tools" / "remotion" / "node_modules").mkdir(parents=True)
    scene_folder(root / "tools" / "remotion" / "src" / "scenes", "title")
    scene_folder(course / "video" / "scenes", "timeline")
    workspace = video.sync(montage(course))
    registry = (workspace / "kit" / "registry.generated.ts").read_text(encoding="utf-8")
    assert 'import s_title from "../src/scenes/title";' in registry and 'import s_split from "./scenes/split";' in registry
    assert 'import s_timeline from "../src/.course/pwd-scenes-timeline";' in registry
    assert (workspace / "src" / ".course" / "pwd-scenes-timeline" / "index.tsx").exists()
    assert 'import l_lower_third from "./layers/lower-third";' in registry and '"lower-third": l_lower_third' in registry
    assert (workspace / "kit" / "Montage.tsx").exists() and not (workspace / "kit" / "__init__.py").exists()


def test_check_says_what_is_wrong_and_where(course, capsys):  # noqa: F811
    prepare_asset(course, capsys)
    bad = {"scenes": [
        {"id": "a", "type": "title", "props": {"title": "Un título demasiado largo para caber en la pantalla de un vídeo de formación"},
         "says": "Algo distinto."},
        {"id": "a", "type": "nope", "props": {}, "says": "x"},
        {"id": "c", "type": "split", "props": {"media": "files/none.png"}},
        {"id": "Bad Id", "type": "outro", "props": {"title": "Fin"}, "duration": 2}]}
    found = {(f.where, f.code) for f in video.check(montage(course, bad), "U1-S2-M1")}
    assert {("a", "TEXT_LONG"), ("a", "NOT_SAID"), ("a", "SCENE_ID"), ("a", "UNKNOWN_SCENE"), ("c", "PROP_MISSING"),
            ("c", "MEDIA_MISSING"), ("c", "NO_DURATION"), ("Bad Id", "SCENE_ID")} <= found
    montage(course)
    assert main(["video", "check", "PWD", "U1-S2-M1"]) == 0
    assert "the montage is fine" in capsys.readouterr().out


@pytest.fixture
def voiced(course, capsys, monkeypatch):  # noqa: F811
    """A course with its theme, a montage and a fake voice: each scene says its words at half a second each."""
    prepare_asset(course, capsys)
    data = montage(course)
    monkeypatch.setattr("coursekit.voices.resolve", lambda course, engine=None: ("piper", None, None))

    def tts(course, engine, text_path, out, *a, **k):
        out.write_bytes(b"ID3")

    def subtitles(audio, text_path, out, model_name="base", language="es"):
        words = text_path.read_text(encoding="utf-8").split()
        mediatools.write_words([{"w": w, "start": i * 0.5, "end": i * 0.5 + 0.4} for i, w in enumerate(words)], mediatools.words_path(out))

    monkeypatch.setattr(video.mediatools, "tts", tts)
    monkeypatch.setattr(video.mediatools, "subtitles", subtitles)
    monkeypatch.setattr(video.mediacheck, "duration", lambda path: 4.0)
    return data


def test_each_scene_lasts_what_its_voice_lasts_and_only_what_changed_is_voiced_again(voiced, course, capsys):  # noqa: F811
    with pytest.raises(video.VideoError, match="the scene opening has no voice yet"):
        video.resolve(voiced, "U1-S2-M1")
    assert video.voice(voiced, "U1-S2-M1", lambda m: None) == 2
    assert video.voice(voiced, "U1-S2-M1", lambda m: None) == 0  # nothing changed
    resolved = video.resolve(voiced, "U1-S2-M1")
    timing = [(s["id"], s["from"], s["frames"]) for s in resolved["scenes"]]
    assert timing == [("opening", 0, 135), ("length", 135, 135), ("close", 270, 90)]
    assert resolved["frames"] == 360 and resolved["scenes"][1]["audio"] == "files/U1-S2-M1/length.mp3"
    assert resolved["scenes"][1]["words"][0] == {"w": "La", "start": 0.0, "end": 0.4}
    assert resolved["tokens"]["color"]["background"] and resolved["motion"]["enter"] == 18
    changed = json.loads(json.dumps(MONTAGE))
    changed["scenes"][1]["says"] = "La longitud es lo que más cuenta: doce caracteres o más."
    assert video.voice(montage(course, changed), "U1-S2-M1", lambda m: None) == 1  # only that scene


def test_render_leaves_the_video_with_its_captions_words_and_accessible_transcript(voiced, course, monkeypatch):  # noqa: F811
    video.voice(voiced, "U1-S2-M1", lambda m: None)
    (course.parent.parent / "tools" / "remotion" / "node_modules").mkdir(parents=True)
    calls = []

    def remotion(root, args):
        calls.append(args)
        out = next(a for a in args if a.endswith(".mp4"))
        __import__("pathlib").Path(out).write_bytes(b"mp4")

    monkeypatch.setattr(video, "_remotion", remotion)
    monkeypatch.setattr(video.mediacheck, "loudness_finding", lambda *a: None)
    with pytest.raises(video.VideoError, match="say what it shows before it is produced"):
        video.render(voiced, "U1-S2-M1")  # a generated video says first that it shows no real interface
    assert main(["media", "set", "PWD", "U1-S2-M1", "--depicts", "concept"]) == 0
    done = video.render(voiced, "U1-S2-M1")
    assert calls[0][:3] == ["render", "kit/entry.ts", "Montage"] and any(a.startswith("--public-dir=") for a in calls[0])
    files = course / "media" / "files"
    assert done["video"] == files / "U1-S2-M1.mp4" and done["scenes"] == 3
    vtt = (files / "U1-S2-M1.vtt").read_text(encoding="utf-8")
    assert "Hoy vemos por qué las contraseñas largas protegen más." in vtt and "00:00:04.500 -->" in vtt  # the second scene, at 4.5 s
    words = json.loads((files / "U1-S2-M1.words.json").read_text(encoding="utf-8"))["words"]
    assert words[0]["w"] == "Hoy" and any(w["w"] == "La" and w["start"] == 4.5 for w in words)
    asset = manifest(course)[0]
    assert asset["status"] == "produced" and asset["recipe"] == "montage" and asset["file"] == "media/files/U1-S2-M1.mp4"
    assert asset["transcript"].startswith("[0:00]\nEn pantalla: Unidad 1. Contraseñas largas")
    scenes = yaml.safe_load((course / "media" / "scripts" / "U1-S2-M1.scenes.yaml").read_text(encoding="utf-8"))
    assert scenes["scenes"][1]["text"] == ["La longitud manda", "Doce caracteres o más"] and scenes["scenes"][1]["at"] == 4.5
    assert scenes["scenes"][0]["labels"] == ["Unidad 1"] and scenes["scenes"][0]["text"] == ["Contraseñas largas"]
    assert "[0:09]\nEn pantalla: El cierre, sobre el color de acento" in asset["transcript"]  # a silent scene has its minute too


def test_a_new_montage_starts_from_the_resource(course, capsys):  # noqa: F811
    prepare_asset(course, capsys)
    assert main(["video", "new", "PWD", "U1-S2-M1"]) == 0
    data = yaml.safe_load((course / "media" / "scripts" / "U1-S2-M1.video.yaml").read_text(encoding="utf-8"))
    assert [s["type"] for s in data["scenes"]] == ["title", "split", "outro"] and data["scenes"][0]["props"]["title"]
    assert main(["video", "new", "PWD", "U1-S2-M1"]) == 1
    assert "there is already a montage" in capsys.readouterr().err


def test_the_montage_is_the_first_option_for_a_video():
    from coursekit import config

    recipes = [r["id"] for r in config.package_defaults("media")["types"]["video"]]
    assert recipes[:2] == ["montage", "remotion"]
    assert mediacheck  # used by the voice


def test_nested_props_are_checked_and_said(course, capsys):  # noqa: F811
    prepare_asset(course, capsys)
    data = {"scenes": [{"id": "sides", "type": "compare", "props": {
        "left": {"title": "Una contraseña corta", "items": ["Se adivina en minutos con un programa de diccionario"]},
        "right": {"title": "Una frase larga", "items": ["Tarda siglos"]}},
        "says": "Una contraseña corta frente a una frase larga, que tarda siglos."}]}
    found = {(f.code, f.text.split(" ")[0]) for f in video.check(montage(course, data), "U1-S2-M1")}
    assert ("TEXT_LONG", "left.items[0]") in found and ("NOT_SAID", "left.items[0]") in found
    assert not any(where.startswith("right") for code, where in found)


def test_a_layer_enters_with_its_word_and_leaves_with_another(voiced, course, capsys):  # noqa: F811
    data = json.loads(json.dumps(MONTAGE))
    data["scenes"][1]["layers"] = [
        {"type": "callout", "props": {"text": "Doce o más"}, "at": "doce", "until": "más"},
        {"type": "lower-third", "props": {"title": "Ana López", "subtitle": "Seguridad"}, "at": "nunca"},
        {"type": "nope", "props": {}}]
    checked = montage(course, data)
    found = {(f.where, f.code) for f in video.check(checked, "U1-S2-M1")}
    assert ("length/2", "ANCHOR_NOT_SAID") in found and ("length/3", "UNKNOWN_LAYER") in found
    assert not any(where == "length/1" for where, _ in found)
    data["scenes"][1]["layers"] = data["scenes"][1]["layers"][:2]
    video.voice(montage(course, data), "U1-S2-M1", lambda m: None)
    layers = video.resolve(montage(course, data), "U1-S2-M1")["scenes"][1]["layers"]
    # "La longitud manda: doce caracteres o más." at half a second a word: "doce" at 1.5 s, "más." ends at 3.4 s
    assert layers == [{"id": "length-1", "type": "callout", "from": 45, "frames": 57, "props": {"text": "Doce o más"}}]


def test_when_a_phrase_is_said():
    words = [{"w": w, "start": i, "end": i + 0.5} for i, w in enumerate(["La", "longitud", "mínima:", "doce", "caracteres."])]
    assert video.when_said(words, "Longitud mínima") == {"start": 1, "end": 2.5}
    assert video.when_said(words, "doce caracteres", after=3) == {"start": 3, "end": 4.5}
    assert video.when_said(words, "doce", after=3.5) is None and video.says_phrase("La longitud, mínima: doce", "longitud mínima")


# ── the style of the project and pieces of its own ───────────────────────────────────────────

def write_style(root, **values):
    (root / "config" / "video.yaml").write_text(yaml.safe_dump(values), encoding="utf-8")


def test_the_style_of_the_project_and_of_a_course_shape_the_video(voiced, course):  # noqa: F811
    from tests.test_exelearning import edit_course

    video.voice(voiced, "U1-S2-M1", lambda m: None)
    root = course.parent.parent
    (root / "theme" / "branding").mkdir(parents=True, exist_ok=True)
    (root / "theme" / "branding" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    write_style(root, motion={"character": "calm", "stagger": 8}, background="band", format={"fps": 25},
                logo={"file": "theme/branding/logo.png", "corner": "top-left", "scenes": ["title"]})
    resolved = video.resolve(montage(course), "U1-S2-M1")
    assert resolved["motion"] == {"enter": 26, "stagger": 8, "fade": 14, "damping": 28} and resolved["fps"] == 25
    assert resolved["style"]["background"] == "band" and resolved["style"]["logo"]["src"].startswith("data:image/png;base64,")
    assert resolved["style"]["logo"]["corner"] == "top-left" and resolved["style"]["logo"]["scenes"] == ["title"]
    edit_course(course, lambda d: d.update(video={"motion": {"character": "lively"}}))  # one course, livelier
    assert video.resolve(montage(course), "U1-S2-M1")["motion"]["enter"] == 11
    write_style(root, logo={"file": "theme/branding/none.png"})
    with pytest.raises(video.VideoError, match="does not exist"):
        video.resolve(montage(course), "U1-S2-M1")


def test_an_atom_of_the_project_or_of_a_course_takes_the_place_of_the_library(course):  # noqa: F811
    root = course.parent.parent
    (root / "tools" / "remotion" / "node_modules").mkdir(parents=True)
    atoms = root / "tools" / "remotion" / "src" / "atoms"
    atoms.mkdir(parents=True)
    (atoms / "Heading.tsx").write_text("export const Heading = () => null; // of the project\n", encoding="utf-8")
    (course / "video" / "molecules").mkdir(parents=True)
    (course / "video" / "molecules" / "TitleBlock.tsx").write_text("export const TitleBlock = () => null; // of the course\n",
                                                                   encoding="utf-8")
    data = montage(course)
    workspace = video.sync(data)
    assert "of the project" in (workspace / "kit" / "atoms" / "Heading.tsx").read_text(encoding="utf-8")
    assert "of the course" in (workspace / "kit" / "molecules" / "TitleBlock.tsx").read_text(encoding="utf-8")
    text = "\n".join(video.catalog(data))
    assert "Heading [project]" in text and "TitleBlock [course]" in text
    (atoms / "Sparkle.tsx").write_text("export const Sparkle = () => null;\n", encoding="utf-8")
    with pytest.raises(video.VideoError, match="has no piece Sparkle in atoms"):
        video.sync(data)
    (atoms / "Sparkle.tsx").unlink()
    (atoms / "Heading.tsx").write_text("export default function H() { return null; }\n", encoding="utf-8")
    with pytest.raises(video.VideoError, match="must export Heading"):
        video.sync(data)
