"""`coursekit video`: a video as data, a montage of scenes of the library, the project or the course."""

import json
from pathlib import Path

import pytest
import yaml

from coursekit import mediacheck, mediatools, video
from coursekit.cli import main
from coursekit.course import load as load_course
from coursekit.project import find_project
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture
from tests.test_media import manifest, prepare_asset


@pytest.fixture(autouse=True)
def no_script_gate(request, monkeypatch):
    """These tests are about what is made, not about its sign-off: the approval of the script is tested in test_media_script."""
    from coursekit import mediascript

    monkeypatch.setattr(mediascript, "required", lambda _course: False)


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
    assert "Two sides compared" in text and "— a figure is never shown without its source" in text


def test_the_catalog_speaks_the_language_of_the_person(course, monkeypatch):  # noqa: F811
    monkeypatch.setenv("COURSEKIT_LANG", "es")
    text = "\n".join(video.catalog(montage(course)))
    assert "compare [biblioteca]: Dos lados comparados" in text and "— una cifra nunca se muestra sin su fuente" in text
    assert "[library]" not in text and "Two sides" not in text


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


def test_the_shapes_weights_and_fonts_of_a_brand_go_inside_the_video(voiced, course):  # noqa: F811
    video.voice(voiced, "U1-S2-M1", lambda m: None)
    root = course.parent.parent
    resolved = video.resolve(montage(course), "U1-S2-M1")["style"]
    assert resolved["shapes"] == {} and resolved["weights"] == {} and resolved["fonts"] is None  # what each piece draws
    fonts = root / "theme" / "branding" / "fonts"
    (fonts / "acme-sans").mkdir(parents=True)
    (fonts / "acme-sans" / "acme-sans-latin.woff2").write_bytes(b"wOF2font")
    (fonts / "fonts.css").write_text("/* the ACME fonts */\n@font-face {\n  font-family: 'ACME Sans';\n  font-weight: 1 1000;\n"
                                     "  src: url('./acme-sans/acme-sans-latin.woff2') format('woff2');\n}\n", encoding="utf-8")
    write_style(root, shapes={"radius": 0, "shadow": "none", "border": 1}, weights={"normal": 300, "strong": 500},
                fonts="theme/branding/fonts/fonts.css")
    resolved = video.resolve(montage(course), "U1-S2-M1")["style"]
    assert resolved["shapes"] == {"radius": 0, "border": 1, "shadow": "none"}
    assert resolved["weights"] == {"normal": 300, "strong": 500}
    assert resolved["fonts"]["families"] == ["ACME Sans"]
    assert 'url("data:font/woff2;base64,d09GMmZvbnQ=")' in resolved["fonts"]["css"] and "ACME fonts" not in resolved["fonts"]["css"]
    (fonts / "fonts.css").write_text("@font-face { font-family: X; src: url('https://fonts.example/x.woff2'); }\n", encoding="utf-8")
    with pytest.raises(video.VideoError, match="from the internet"):
        video.resolve(montage(course), "U1-S2-M1")
    (fonts / "fonts.css").write_text("@font-face { font-family: X; src: url('../../../../outside.woff2'); }\n", encoding="utf-8")
    with pytest.raises(video.VideoError, match="which is not in the project"):
        video.resolve(montage(course), "U1-S2-M1")


def test_every_piece_of_the_library_has_an_example_in_each_language_with_its_required_props(course):  # noqa: F811
    data = montage(course)
    for kind in ("scenes", "layers"):
        for name, piece in video.pieces(data, kind).items():
            if name == "screencast":  # it needs a real recording
                assert video.example(piece, "en") is None
                continue
            for language in ("en", "es"):
                props = video.example(piece, language)
                assert props, f"{kind}/{name} has no example in {language}"
                required = [k for k, v in (piece["meta"].get("props") or {}).items() if isinstance(v, dict) and v.get("required")]
                assert all(props.get(k) not in (None, "", []) for k in required), f"{kind}/{name} ({language})"
    assert video.example(video.pieces(data)["title"], "es")["title"] == "Las contraseñas largas protegen más"


def test_the_gallery_draws_every_piece_with_the_theme_and_the_style_of_the_course(course, capsys, monkeypatch):  # noqa: F811
    prepare_asset(course, capsys)
    root = course.parent.parent
    (root / "tools" / "remotion" / "node_modules").mkdir(parents=True)
    scene_folder(course / "video" / "scenes", "timeline", "a timeline of this course")  # no example: listed, not drawn
    write_style(root, shapes={"radius": 0, "shadow": "none"})
    rendered, stills = [], []

    def remotion(workspace, args):
        rendered.append(args)
        out = Path(args[3])
        out.write_bytes(b"mp4")

    def run(cmd, **kw):
        stills.append(cmd)
        Path(cmd[-1]).write_bytes(b"png")

    monkeypatch.setattr(video, "_remotion", remotion)
    monkeypatch.setattr(video.mediatools, "run", run)
    page = video.gallery(montage(course), lambda m: None)
    props = json.loads(Path(next(a for a in rendered[0] if a.startswith("--props=")).split("=", 1)[1]).read_text(encoding="utf-8"))
    names = [s["layers"][0]["id"] if s["layers"] else s["id"] for s in props["scenes"]]
    assert names == ["compare", "diagram", "list", "outro", "quote", "split", "stat", "title", "callout", "highlight", "lower-third"]
    layer = props["scenes"][-1]
    assert layer["type"] == "title" and layer["layers"][0]["props"]["subtitle"] == "Responsable de seguridad, ACME"
    assert props["style"]["shapes"] == {"radius": 0, "shadow": "none"} and props["tokens"]["color"]["background"]
    assert "--scale=0.5" in rendered[0] and len(stills) == len(names)
    assert (page.parent / "gallery-sample.svg").exists() and (page.parent / "frames" / "title.png").exists()
    text = page.read_text(encoding="utf-8")
    assert 'src="gallery.mp4#t=0.00,3.50"' in text and "timeline" in text and "no example" in text and "lower-third" in text
    assert "scene · library" in text and "Two sides compared" in text and "Props: title, left*, right* (* required)" in text
    assert "Background: " in text and "weights: normal" in text and '<html lang="en">' in text
    monkeypatch.setenv("COURSEKIT_LANG", "es")  # the page speaks the language of the person, all of it
    text = video.gallery(montage(course), lambda m: None).read_text(encoding="utf-8")
    assert '<html lang="es">' in text and "escena · biblioteca" in text and "capa · biblioteca" in text
    assert "Dos lados comparados" in text and "(* obligatoria)" in text and "Fondo: " in text and "sin ejemplo" in text
    for english in ("scene ·", "layer ·", "library", "Two sides", "required", "Background", "&amp;#x27;"):
        assert english not in text


def test_without_a_code_the_gallery_is_the_one_of_the_project(course, capsys, monkeypatch):  # noqa: F811
    prepare_asset(course, capsys)
    root = course.parent.parent
    (root / "tools" / "remotion" / "node_modules").mkdir(parents=True)
    scene_folder(course / "video" / "scenes", "timeline", "a timeline of this course")  # of the course: not in the project's
    monkeypatch.setattr(video, "_remotion", lambda workspace, args: Path(args[3]).write_bytes(b"mp4"))
    monkeypatch.setattr(video.mediatools, "run", lambda cmd, **kw: Path(cmd[-1]).write_bytes(b"png"))
    assert main(["video", "gallery"]) == 0
    page = root / ".cache" / "media" / "project" / "gallery" / "index.html"
    assert "media/project/gallery/index.html" in capsys.readouterr().out and "timeline" not in page.read_text(encoding="utf-8")
    assert main(["video", "catalog"]) == 0 and "timeline" not in capsys.readouterr().out
    assert main(["video", "check"]) == 2 and "needs the code of the course" in capsys.readouterr().err
    guide = root / "theme" / "branding" / "media-style.md"  # the signature of the guide points to that gallery first
    guide.parent.mkdir(parents=True, exist_ok=True)
    guide.write_text("# Style\n", encoding="utf-8")
    assert main(["approve", "media-style", "--yes", "--no-commit"]) == 0
    assert ".cache/media/project/gallery/index.html" in capsys.readouterr().out
    assert main(["approve", "media-style", "PWD", "--yes", "--no-commit"]) == 0
    assert "coursekit video gallery PWD draws the gallery" in capsys.readouterr().out


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


# ── for an editor ────────────────────────────────────────────────────────────────────────────

from coursekit import videoedit  # noqa: E402


def sample_timeline(tmp_path):
    scenes = videoedit.Track("video", "scenes", [videoedit.Clip("a", tmp_path / "a.mp4", 0, 60),
                                                  videoedit.Clip("b", tmp_path / "b.mp4", 60, 90)])
    layers = videoedit.Track("video", "layers", [videoedit.Clip("b-1", tmp_path / "b-1.mov", 75, 30)])
    voices = videoedit.Track("audio", "voices", [videoedit.Clip("voice a", tmp_path / "a.mp3", 0, 50, 50),
                                                  videoedit.Clip("voice b", tmp_path / "b.mp3", 60, 80, 80)])
    return videoedit.Timeline("PWD U1", 30, 1920, 1080, 150, [scenes, layers, voices], [(0, "a"), (60, "b")])


def test_the_fcpxml_puts_layers_above_and_voices_below_each_scene(tmp_path):
    import xml.etree.ElementTree as ET

    root = ET.fromstring(videoedit.fcpxml(sample_timeline(tmp_path)).split("\n", 2)[2])
    assert root.get("version") == "1.10" and root.find("resources/format").get("frameDuration") == "1/30s"
    spine = root.find("library/event/project/sequence/spine")
    first, second = spine.findall("asset-clip")
    assert (first.get("offset"), first.get("duration"), second.get("offset")) == ("0s", "60/30s", "60/30s")
    connected = {c.get("name"): (c.get("lane"), c.get("offset"), c.get("duration")) for c in second.findall("asset-clip")}
    assert connected == {"b-1": ("1", "15/30s", "30/30s"), "voice b": ("-1", "0s", "80/30s")}
    assert [m.get("value") for m in first.findall("marker")] == ["a"]
    sources = [a.find("media-rep").get("src") for a in root.findall("resources/asset")]
    assert all(s.startswith("file://") for s in sources) and len(sources) == 5


def test_the_otio_has_a_gap_wherever_a_track_has_no_clip(tmp_path):
    data = json.loads(videoedit.otio(sample_timeline(tmp_path)))
    scenes, layers, voices = data["tracks"]["children"]
    assert [c["OTIO_SCHEMA"] for c in layers["children"]] == ["Gap.1", "Clip.2"]
    assert layers["children"][0]["source_range"]["duration"]["value"] == 75
    assert [c["OTIO_SCHEMA"] for c in voices["children"]] == ["Clip.2", "Gap.1", "Clip.2"] and voices["kind"] == "Audio"
    assert [m["name"] for m in scenes["markers"]] == ["a", "b"] and data["OTIO_SCHEMA"] == "Timeline.1"


def test_captions_for_an_editor_are_srt():
    srt = videoedit.srt("WEBVTT\n\n1\n00:00:01.500 --> 00:00:03.250\nHola & adiós.\n")
    assert srt == "1\n00:00:01,500 --> 00:00:03,250\nHola & adiós.\n\n"


def test_export_leaves_each_piece_apart_and_the_timeline(voiced, course, monkeypatch):  # noqa: F811
    import shutil as sh
    import subprocess

    if not sh.which("ffmpeg"):
        pytest.skip("ffmpeg is not installed")
    data = json.loads(json.dumps(MONTAGE))
    data["scenes"][1]["layers"] = [{"type": "callout", "props": {"text": "Doce o más"}, "at": "doce", "until": "más"}]
    voiced = montage(course, data)
    video.voice(voiced, "U1-S2-M1", lambda m: None)
    (course.parent.parent / "tools" / "remotion" / "node_modules").mkdir(parents=True)
    rendered = []

    def remotion(root, args):
        rendered.append(args)
        out = next(a for a in args if a.endswith((".mp4", ".mov")))
        frames = 360 if out.endswith("clean.mp4") else 57
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30",
                        "-frames:v", str(frames), "-pix_fmt", "yuv420p", out], check=True)

    monkeypatch.setattr(video, "_remotion", remotion)
    done = video.export(voiced, "U1-S2-M1", lambda m: None)
    folder = course / "media" / "edit" / "U1-S2-M1"
    assert done == {"folder": folder, "scenes": 3, "layers": 1, "voices": 2}
    assert sorted(p.name for p in (folder / "scenes").iterdir()) == ["01-opening.mp4", "02-length.mp4", "03-close.mp4"]
    assert (folder / "layers" / "length-1.mov").exists() and not (folder / "clean.mp4").exists()
    assert any("--prores-profile=4444" in a for a in rendered[1]) and "--frames=180-236" in rendered[1]
    props = json.loads((course.parent.parent / ".cache" / "video" / "PWD" / "U1-S2-M1.props.json").read_text(encoding="utf-8"))
    assert props["mode"] == {"layer": "length-1"}
    assert "timeline.fcpxml" in [p.name for p in folder.iterdir()]
    assert (folder / "captions.srt").read_text(encoding="utf-8").startswith("1\n")
