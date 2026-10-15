import json
from pathlib import Path

import pytest
import yaml

from coursekit import mediatools, voices
from coursekit.cli import main
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture


def manifest(course_dir):
    return yaml.safe_load((course_dir / "media" / "manifest.yaml").read_text(encoding="utf-8"))["assets"]


def import_theme(course_dir, *extra):
    assert main(["theme", "import", str(Path(__file__).parent / "fixtures" / "creator_theme.json"), *extra]) == 0


def test_extract_plan_and_set(course, capsys):  # noqa: F811
    import_theme(course)
    assert main(["media", "extract", "PWD"]) == 0
    assert "manifest: 1 assets (pending 1)" in capsys.readouterr().out
    asset = manifest(course)[0]
    assert asset["id"] == "U1-S2-M1"
    assert asset["type"] == "infographic" and asset["title"] == "Anatomía de una contraseña"
    assert asset["how"] == "SVG con los tokens del proyecto."
    assert main(["media", "plan", "PWD"]) == 0
    out = capsys.readouterr().out
    assert "U1-S2-M1 [infographic]" in out and "agent-svg (yes)" in out

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
    import_theme(course)
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
    (tmp_path / "a.mp3").write_bytes(b"ID3")
    assert main(["subtitles", "--course", "PWD", "--audio", str(tmp_path / "a.mp3"), "--text", str(script), "--out", "a.vtt"]) == 0
    assert calls[-1][:2] == ["/fake/stable-ts", str(tmp_path / "a.mp3")]
    assert calls[-1][calls[-1].index("--language") + 1] == "es"


def test_vtt_from_characters():
    text = "Hola. Adiós."
    starts = [i * 0.1 for i in range(len(text))]
    vtt = mediatools.vtt_from_characters(list(text), starts, [s + 0.1 for s in starts])
    assert vtt.splitlines()[:6] == ["WEBVTT", "", "1", "00:00:00.000 --> 00:00:00.500", "Hola.", ""]
    assert "Adiós." in vtt


def test_voices_of_the_characters(course, monkeypatch, capsys):  # noqa: F811
    for key in ("ELEVENLABS_API_KEY", "GOOGLE_TTS_API_KEY", "PIPER_VOICE"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("AZURE_SPEECH_KEY", "k")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "westeurope")
    from coursekit import course as coursemod
    from coursekit.project import find_project

    assert main(["voice", "set", "PWD", "azure"]) == 0
    assert main(["voice", "set", "PWD", "azure", "--voice", "es-ES-AlvaroNeural", "--character", "Daniel"]) == 0
    c = coursemod.load(find_project(), "PWD")
    assert voices.resolve(c) == ("azure", "es-ES-ElviraNeural", None)
    assert voices.resolve_character(c, "daniel") == ("azure", "es-ES-AlvaroNeural", None)
    with pytest.raises(voices.VoiceError, match="Marta has no voice of azure"):
        voices.resolve_character(c, "Marta")
    capsys.readouterr()
    assert main(["voice", "set", "PWD", "google", "--voice", "x", "--character", "Marta"]) == 1
    assert "must be of the provider of the course (azure)" in capsys.readouterr().err
    assert main(["voice", "list", "PWD"]) == 0
    assert "Daniel: azure · es-ES-AlvaroNeural" in capsys.readouterr().out


def test_piper_drafts_alternate_the_speakers(course, monkeypatch):  # noqa: F811
    for key in ("ELEVENLABS_API_KEY", "AZURE_SPEECH_KEY", "GOOGLE_TTS_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PIPER_VOICE", "/voices/v.onnx")
    monkeypatch.setattr(voices.shutil, "which", lambda t: f"/fake/{t}")
    from coursekit import course as coursemod
    from coursekit.project import find_project

    c = coursemod.load(find_project(), "PWD")
    (c["_dir"] / "design" / "story.md").write_text(
        "---\nworld: ACME\nprotagonist: {role: x}\ncharacters: [{name: Marta}, {name: Daniel}]\n---\n", encoding="utf-8")
    assert voices.resolve_character(c, "Marta")[2] == "1"
    assert voices.resolve_character(c, "Daniel")[2] == "0"


def test_a_generator_option_shows_its_model_and_variants(course, capsys):  # noqa: F811
    from coursekit.project import find_project

    root = find_project().root
    option = "{id: magnific-mcp, needs: {mcp: images_generate}, how: Magnific, model: seedream-5-flash, resolution: 1.5k, variants: 1}"
    (root / "config" / "media.yaml").write_text(f"types:\n  infographic:\n    - {option}\n", encoding="utf-8")
    assert main(["media", "extract", "PWD"]) == 0
    capsys.readouterr()
    assert main(["media", "plan", "PWD"]) == 0
    assert "[model: seedream-5-flash, resolution: 1.5k, variants: 1]" in capsys.readouterr().out


def test_fit_and_render_work_locally(course, tmp_path, capsys):  # noqa: F811
    from PIL import Image

    from coursekit import mediatools
    from coursekit.project import find_project

    root = find_project().root
    assert main(["media", "extract", "PWD"]) == 0
    folder = root / "courses" / "PWD" / "media" / "files"
    folder.mkdir(parents=True)
    Image.new("RGBA", (2048, 1152), (10, 20, 30, 255)).save(folder / "big.png")
    manifest = yaml.safe_load((root / "courses" / "PWD" / "media" / "manifest.yaml").read_text(encoding="utf-8"))
    asset = manifest["assets"][0]["id"]
    assert main(["media", "set", "PWD", asset, "--file", "media/files/big.png"]) == 0
    capsys.readouterr()
    assert main(["media", "fit", "PWD", asset, "--size", "1920x1080"]) == 0
    assert "2048x1152 → 1920x1080" in capsys.readouterr().out
    assert Image.open(folder / "big.png").size == (1920, 1080)
    assert main(["media", "fit", "PWD", asset]) == 2
    assert main(["media", "render", "PWD", asset]) == 1  # not an SVG
    if not mediatools.browser():
        return
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100"><rect width="200" height="100" fill="#0a58ca"/></svg>'
    (folder / "d.svg").write_text(svg, encoding="utf-8")
    assert main(["media", "set", "PWD", asset, "--file", "media/files/d.svg"]) == 0
    assert main(["media", "render", "PWD", asset]) == 0
    assert Image.open(folder / "d.png").size == (200, 100)


def test_optimize_scales_and_recompresses_images(course, capsys):  # noqa: F811
    from PIL import Image

    from coursekit import mediaopt

    big = course / "media" / "files" / "big.png"
    big.parent.mkdir(parents=True, exist_ok=True)
    Image.effect_noise((3000, 1500), 80).convert("RGB").save(big)
    before = big.stat().st_size
    line = mediaopt.shrink(big, {"optimize": {"image": {"max_width": 1000, "quality": 80}}})
    with Image.open(big) as im:
        assert im.size == (1000, 500)
    assert big.stat().st_size < before and line and big.name in line
    assert mediaopt.shrink(course / "media" / "files" / "a.svg", {}) is None


def test_optimize_command_skips_unproduced(course, capsys):  # noqa: F811
    import_theme(course)
    assert main(["media", "extract", "PWD"]) == 0
    capsys.readouterr()
    assert main(["media", "optimize", "PWD"]) == 0
    assert "nothing to optimise" in capsys.readouterr().out
