import json

import pytest
import yaml

from coursekit import mediatools, voices
from coursekit.cli import main
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture


def manifest(course_dir):
    return yaml.safe_load((course_dir / "media" / "manifest.yaml").read_text(encoding="utf-8"))["assets"]


def test_extract_plan_and_set(course, capsys):  # noqa: F811
    assert main(["media", "extract", "PWD"]) == 0
    assert "manifest: 1 assets (pending 1)" in capsys.readouterr().out
    asset = manifest(course)[0]
    assert asset["id"] == "U1-S2-M1"
    assert asset["type"] == "Infografía" and asset["title"] == "Anatomía de una contraseña"
    assert asset["how"] == "SVG con los tokens del proyecto."
    assert main(["media", "plan", "PWD"]) == 0
    out = capsys.readouterr().out
    assert "U1-S2-M1 [Infografía]" in out and "agent-svg (yes)" in out

    (course / "media" / "files").mkdir(exist_ok=True)
    (course / "media" / "files" / "U1-S2-M1.pdf").write_bytes(b"%PDF" + b"0" * 2000)
    args = ["media", "set", "PWD", "U1-S2-M1", "--status", "uploaded", "--recipe", "agent-svg", "--asset-path", "p/a.svg",
            "--alt", "Partes de una contraseña", "--made-with", "claude · opus", "--download", "media/files/U1-S2-M1.pdf",
            "--download-asset-path", "p/a.pdf"]
    assert main(args) == 0
    asset = manifest(course)[0]
    assert asset["status"] == "uploaded" and asset["made_with"] == "claude · opus"
    assert asset["downloads"][0]["size"] == 2004

    # the assembly swaps the placeholder for the image and adds the attachment after it
    assert main(["assemble", "plan", "PWD", "--unit", "1"]) == 0
    plan = json.loads((course / "assembly" / "unit-01.plan.json").read_text(encoding="utf-8"))
    bricks = plan["lessons"][1]["bricks"]
    i = next(k for k, b in enumerate(bricks) if b["type"] == "IMAGE")
    assert bricks[i]["data"]["properties"] == {"imagePath": "p/a.svg", "imageAlt": "Partes de una contraseña"}
    attachment = bricks[i + 1]
    assert attachment["type"] == "ATTACHMENT"
    assert attachment["data"]["properties"]["fileName"] == "anatomia-de-una-contrasena.pdf"
    assert "Descargar: Anatomía de una contraseña" in attachment["data"]["content"]["title"]


def test_changed_placeholder_goes_back_to_pending(course, capsys):  # noqa: F811
    assert main(["media", "extract", "PWD"]) == 0
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced"]) == 0
    content = course / "content" / "unit-01" / "content.md"
    content.write_text(content.read_text(encoding="utf-8").replace("Anatomía de una contraseña", "Partes de una contraseña"),
                       encoding="utf-8")
    assert main(["media", "extract", "PWD"]) == 0
    asset = manifest(course)[0]
    assert asset["status"] == "pending" and "produce it again" in asset["note"]


def test_bad_status_and_unknown_asset(course, capsys):  # noqa: F811
    assert main(["media", "extract", "PWD"]) == 0
    capsys.readouterr()
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "nope"]) == 1
    assert "status must be one of" in capsys.readouterr().err
    assert main(["media", "set", "PWD", "X", "--status", "produced"]) == 1


def test_voice_choice(course, monkeypatch, capsys):  # noqa: F811
    for key in ("ELEVENLABS_API_KEY", "AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION", "GOOGLE_TTS_API_KEY", "PIPER_VOICE"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("AZURE_SPEECH_KEY", "k")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "westeurope")
    monkeypatch.setenv("GOOGLE_TTS_API_KEY", "g")
    from coursekit import course as coursemod
    from coursekit.project import find_project

    c = coursemod.load(find_project(), "PWD")
    with pytest.raises(voices.VoiceError, match="several voice providers"):
        voices.resolve(c)
    assert main(["voice", "set", "PWD", "azure"]) == 0
    c = coursemod.load(find_project(), "PWD")
    assert voices.resolve(c) == ("azure", "es-ES-ElviraNeural", None)
    assert main(["voice", "list", "PWD"]) == 0
    assert "PWD uses: azure · es-ES-ElviraNeural" in capsys.readouterr().out


def test_tts_and_subtitles_with_fake_tools(course, monkeypatch, tmp_path):  # noqa: F811
    calls = []
    monkeypatch.setenv("PIPER_VOICE", "/voices/v.onnx")
    monkeypatch.setattr(mediatools.shutil, "which", lambda t: f"/fake/{t}")
    monkeypatch.setattr(voices.shutil, "which", lambda t: f"/fake/{t}")

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if "-f" in cmd:  # piper writes the wav
            open(cmd[cmd.index("-f") + 1], "wb").write(b"RIFF")

        class Done:
            returncode = 0

        return Done()

    monkeypatch.setattr(mediatools.subprocess, "run", fake_run)
    script = tmp_path / "s.txt"
    script.write_text("Hola.  Adiós.", encoding="utf-8")
    assert main(["tts", "--course", "PWD", "--engine", "piper", "--in", str(script), "--out", str(tmp_path / "a.wav")]) == 0
    from pathlib import Path

    assert calls[0][:3] == ["/fake/piper", "-m", str(Path("/voices/v.onnx"))]
    assert (tmp_path / "a.wav").exists()
    assert main(["subtitles", "--course", "PWD", "--audio", "a.mp3", "--text", str(script), "--out", "a.vtt"]) == 0
    assert calls[-1][:2] == ["/fake/stable-ts", "a.mp3"]
    assert calls[-1][calls[-1].index("--language") + 1] == "es"


def test_vtt_from_characters():
    text = "Hola. Adiós."
    starts = [i * 0.1 for i in range(len(text))]
    vtt = mediatools.vtt_from_characters(list(text), starts, [s + 0.1 for s in starts])
    assert vtt.splitlines()[:6] == ["WEBVTT", "", "1", "00:00:00.000 --> 00:00:00.500", "Hola.", ""]
    assert "Adiós." in vtt
