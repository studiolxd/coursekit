"""`coursekit media check`, `sheet` and `transcript`: loudness, captions, contact sheet and what a video shows, as text."""

import json
import shutil
import subprocess

import pytest
import yaml

from coursekit import mediaaccess, mediacheck
from coursekit.cli import main
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture
from tests.test_media import manifest, prepare_asset

FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")
needs_ffmpeg = pytest.mark.skipif(not FFMPEG, reason="ffmpeg is not installed")


def produce(course_dir, capsys, name, make=None):
    prepare_asset(course_dir, capsys)
    files = course_dir / "media" / "files"
    files.mkdir(parents=True, exist_ok=True)
    if make:
        make(files / name)
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced", "--recipe", "agent-svg", "--depicts", "concept",
                 "--file", f"media/files/{name}"]) == 0
    capsys.readouterr()
    return files / name


def tone(volume):
    def make(path):
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
                        "-af", f"volume={volume}", str(path)], check=True)
    return make


@needs_ffmpeg
def test_a_voice_out_of_loudness_is_reported_and_fixed(course, capsys):  # noqa: F811
    produce(course, capsys, "u1.mp3", tone("-30dB"))
    assert main(["media", "check", "PWD"]) == 1
    assert "[LOUDNESS] u1.mp3: loudness" in capsys.readouterr().out
    assert main(["media", "check", "PWD", "--fix"]) == 0
    out = capsys.readouterr().out
    assert "u1.mp3: loudness brought to -16 LUFS" in out and "are fine" in out


def test_captions_too_fast_to_read_are_reported(course, capsys):  # noqa: F811
    audio = produce(course, capsys, "u1.mp3")
    audio.write_bytes(b"")
    audio.with_suffix(".vtt").write_text("WEBVTT\n\n1\n00:00:00.000 --> 00:00:01.000\nUna frase demasiado larga para un segundo.\n\n"
                                         "2\n00:00:01.000 --> 00:00:04.000\nEsta sí.\n", encoding="utf-8")
    from coursekit import course as coursemod
    from coursekit.project import find_project

    cfg = mediacheck.settings(coursemod.load(find_project(), "PWD"))
    found = mediacheck.caption_findings({"id": "U1-S2-M1"}, audio, cfg)
    assert len(found) == 1 and "1 caption(s) faster than 17" in found[0].text and "at 0:00.0, at 42" in found[0].text
    assert [c[2] for c in mediacheck.cues(audio.with_suffix(".vtt").read_text(encoding="utf-8"))] == \
        ["Una frase demasiado larga para un segundo.", "Esta sí."]


@needs_ffmpeg
def test_a_contact_sheet_shows_a_video_in_one_image(course, capsys):  # noqa: F811
    def video(path):
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=25:duration=4",
                        "-pix_fmt", "yuv420p", str(path)], check=True)

    produce(course, capsys, "u1.mp4", video)
    assert main(["media", "sheet", "PWD", "U1-S2-M1", "--frames", "8"]) == 0
    assert "contact sheet in .cache/media/PWD/U1-S2-M1-sheet.png" in capsys.readouterr().out
    from PIL import Image

    with Image.open(course.parent.parent / ".cache" / "media" / "PWD" / "U1-S2-M1-sheet.png") as sheet:
        assert sheet.width > 480 * 5  # six columns


SCENES = {"words": "media/files/u1.words.json", "scenes": [
    {"text": "Longitud mínima: 12", "says": "Abre los ajustes de seguridad y pon la longitud mínima en doce."},
    {"text": "Caducidad de 90 días", "says": "Guarda los cambios."},
    {"text": "Historial", "shows": "La lista de cambios guardados, con la fecha de cada uno", "says": "Y ya está."}]}
WORDS = [{"w": w, "start": i * 0.5, "end": i * 0.5 + 0.4} for i, w in enumerate(
    "Abre los ajustes de seguridad y pon la longitud mínima en doce. Guarda los cambios. Y ya está.".split())]


def describe(course_dir):
    scripts = course_dir / "media" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / "U1-S2-M1.scenes.yaml").write_text(yaml.safe_dump(SCENES, allow_unicode=True), encoding="utf-8")
    (course_dir / "media" / "files" / "u1.words.json").write_text(json.dumps({"words": WORDS}), encoding="utf-8")


def test_what_is_on_screen_and_not_said_is_reported(course, capsys):  # noqa: F811
    produce(course, capsys, "u1.mp4").write_bytes(b"")
    describe(course)
    asset = manifest(course)[0]
    from coursekit import course as coursemod
    from coursekit.project import find_project

    found = mediaaccess.not_said(coursemod.load(find_project(), "PWD"), asset)
    assert found == ["scene 2: the narration does not say «Caducidad de 90 días» (say it, or describe what is seen with shows)"]
    assert mediaaccess.said("Longitud mínima: 12", "pon la longitud minima en doce", ["cero"] * 12 + ["doce"])


def test_the_accessible_transcript_says_what_is_seen_and_what_is_said(course, capsys):  # noqa: F811
    video = produce(course, capsys, "u1.mp4")
    video.write_bytes(b"")
    describe(course)
    assert main(["media", "transcript", "PWD", "U1-S2-M1"]) == 0
    assert "it is now the transcript of the resource" in capsys.readouterr().out
    text = video.with_suffix(".transcript.txt").read_text(encoding="utf-8")
    assert text.startswith("[0:00]\nEn pantalla: Longitud mínima: 12\nAbre los ajustes")
    assert "[0:06]\nEn pantalla: Caducidad de 90 días\nGuarda los cambios." in text
    assert "En pantalla: La lista de cambios guardados, con la fecha de cada uno\nY ya está." in text
    vtt = video.with_suffix(".descriptions.vtt").read_text(encoding="utf-8")
    assert vtt.startswith("WEBVTT") and "00:00:06.000 --> 00:00:07.500\nCaducidad de 90 días" in vtt
    assert manifest(course)[0]["transcript"].startswith("[0:00]")
