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
            "--depicts", "concept", "--alt", "Partes de una contraseña", "--made-with", "claude · opus",
            "--download", "media/files/U1-S2-M1.pdf", "--download-asset-path", "p/a.pdf"]
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
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced", "--depicts", "concept"]) == 0
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
    for key in ("ELEVENLABS_API_KEY", "AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION", "GOOGLE_TTS_API_KEY", "GEMINI_API_KEY", "PIPER_VOICE"):
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
        if "--align" in cmd:  # stable-ts writes its result as JSON
            segments = [{"start": 0.0, "end": 0.6, "text": " Hola.", "words": [{"word": " Hola.", "start": 0.0, "end": 0.6}]},
                        {"start": 0.8, "end": 1.5, "text": " Adiós.", "words": [{"word": " Adiós.", "start": 0.8, "end": 1.5}]}]
            Path(cmd[cmd.index("-o") + 1]).write_text(json.dumps({"segments": segments}), encoding="utf-8")

        class Done:
            returncode = 0

        return Done()

    monkeypatch.setattr(mediatools.subprocess, "run", fake_run)
    script = tmp_path / "s.txt"
    script.write_text("Hola.  Adiós.", encoding="utf-8")
    assert main(["tts", "--course", "PWD", "--engine", "piper", "--in", str(script), "--out", str(tmp_path / "a.wav")]) == 0
    assert calls[0][:3] == ["/fake/piper", "-m", str(Path("/voices/v.onnx"))]
    assert (tmp_path / "a.wav").exists()
    (tmp_path / "a.mp3").write_bytes(b"ID3")
    assert main(["subtitles", "--course", "PWD", "--audio", str(tmp_path / "a.mp3"), "--text", str(script), "--out", "a.vtt"]) == 0
    assert calls[-1][:2] == ["/fake/stable-ts", str(tmp_path / "a.mp3")]
    assert calls[-1][calls[-1].index("--language") + 1] == "es"
    vtt = (course.parent.parent / "a.vtt").read_text(encoding="utf-8")
    assert vtt.startswith("WEBVTT") and "00:00:00.800 --> 00:00:01.500\nAdiós." in vtt
    words = json.loads((course.parent.parent / "a.words.json").read_text(encoding="utf-8"))["words"]
    assert words == [{"w": "Hola.", "start": 0.0, "end": 0.6}, {"w": "Adiós.", "start": 0.8, "end": 1.5}]


def _wav(samples: bytes, rate: int = 24000) -> bytes:
    import io
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(samples)
    return buf.getvalue()


def test_the_pieces_of_a_long_script_are_joined_as_samples_and_encoded_once(monkeypatch, tmp_path):
    import base64

    monkeypatch.setenv("GOOGLE_TTS_API_KEY", "g")
    monkeypatch.setattr(mediatools, "sentence_chunks", lambda text, limit: text.split("|"))
    answers = iter([_wav(b"\x01\x00" * 3), _wav(b"\x02\x00" * 2)])
    sent = []

    def fake_post(url, body, headers):
        sent.append(json.loads(body))
        return json.dumps({"audioContent": base64.b64encode(next(answers)).decode()}).encode()

    encoded = []
    monkeypatch.setattr(mediatools, "post", fake_post)
    monkeypatch.setattr(mediatools, "run", lambda cmd, **kw: encoded.append((cmd, kw.get("input"))))
    mediatools.tts_google("Uno.|Dos.", tmp_path / "a.mp3", "es-ES-Chirp3-HD-Aoede")
    assert sent[0]["audioConfig"] == {"audioEncoding": "LINEAR16", "sampleRateHertz": 24000}
    assert len(encoded) == 1  # one pass of the encoder for the whole script, without the WAV headers in between
    cmd, pcm = encoded[0]
    assert cmd[cmd.index("-f") + 1] == "s16le" and pcm == b"\x01\x00" * 3 + b"\x02\x00" * 2
    mediatools.encode_pcm(pcm, tmp_path / "a.wav")
    assert mediatools.wav_frames((tmp_path / "a.wav").read_bytes()) == (pcm, 24000)


def test_the_gemini_voice(course, monkeypatch, tmp_path):  # noqa: F811
    import base64

    from coursekit import course as coursemod
    from coursekit.project import find_project

    for key in ("ELEVENLABS_API_KEY", "AZURE_SPEECH_KEY", "GOOGLE_TTS_API_KEY", "PIPER_VOICE"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "gm")
    assert main(["voice", "set", "PWD", "gemini"]) == 0
    c = coursemod.load(find_project(), "PWD")
    assert c["media"]["voice"] == {"provider": "gemini", "voice": "Aoede", "model": "gemini-3.8-flash-tts"}
    assert voices.resolve(c) == ("gemini", "Aoede", None)
    c["media"]["gemini"] = {"style": "calm and warm"}  # course.yaml › media › gemini
    c["media"]["voice"]["model"] = "gemini-3.1-flash-tts-preview"  # the model the course started with wins
    answers = iter([{"inlineData": {"mimeType": "audio/wav", "data": base64.b64encode(_wav(b"\x01\x00")).decode()}},
                    {"inlineData": {"mimeType": "audio/L16;codec=pcm;rate=24000", "data": base64.b64encode(b"\x02\x00").decode()}}])
    sent = []

    def fake_post(url, body, headers, timeout=300):
        sent.append((url, json.loads(body), headers))
        return json.dumps({"candidates": [{"content": {"parts": [next(answers)]}}]}).encode()

    encoded = []
    monkeypatch.setattr(mediatools, "post", fake_post)
    monkeypatch.setattr(mediatools, "sentence_chunks", lambda text, limit: ["Hola.", "Adiós."])
    monkeypatch.setattr(mediatools, "run", lambda cmd, **kw: encoded.append(kw.get("input")))
    script = tmp_path / "s.txt"
    script.write_text("Hola. Adiós.", encoding="utf-8")
    assert "gemini · Aoede" in mediatools.tts(c, None, script, tmp_path / "a.mp3")
    url, body, headers = sent[0]
    assert url.endswith("/models/gemini-3.1-flash-tts-preview:generateContent") and headers["x-goog-api-key"] == "gm"
    assert body["contents"][0]["parts"][0] == {"text": "Hola.", "speechMetadata": {"style": "calm and warm"}}
    assert body["serviceTier"] == "flex"  # half the price by default
    speech = body["generationConfig"]["speechConfig"]
    assert speech == {"languageCode": "es-ES", "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Aoede"}}}
    assert encoded == [b"\x01\x00\x02\x00"]
    with pytest.raises(mediatools.ToolError, match="Gemini returned no audio .reason: SAFETY"):
        mediatools.gemini_audio({"candidates": [{"finishReason": "SAFETY"}]})


def test_the_words_of_the_character_timings():
    text = "Abre los ajustes"
    words = mediatools.words_from_characters(list(text), [i * 0.1 for i in range(len(text))], [i * 0.1 + 0.1 for i in range(len(text))])
    assert [w["w"] for w in words] == ["Abre", "los", "ajustes"] and words[1]["start"] == 0.5


def test_vtt_from_characters():
    text = "Hola. Adiós."
    starts = [i * 0.1 for i in range(len(text))]
    vtt = mediatools.vtt_from_characters(list(text), starts, [s + 0.1 for s in starts])
    assert vtt.splitlines()[:6] == ["WEBVTT", "", "1", "00:00:00.000 --> 00:00:00.500", "Hola.", ""]
    assert "Adiós." in vtt


def test_voices_of_the_characters(course, monkeypatch, capsys):  # noqa: F811
    for key in ("ELEVENLABS_API_KEY", "GOOGLE_TTS_API_KEY", "GEMINI_API_KEY", "PIPER_VOICE"):
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
    for key in ("ELEVENLABS_API_KEY", "AZURE_SPEECH_KEY", "GOOGLE_TTS_API_KEY", "GEMINI_API_KEY"):
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


def prepare_asset(course, capsys):  # noqa: F811
    import_theme(course)
    assert main(["media", "extract", "PWD"]) == 0
    capsys.readouterr()


def test_a_generated_resource_says_what_it_shows_before_it_is_produced(course, capsys):  # noqa: F811
    prepare_asset(course, capsys)
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced", "--recipe", "agent-svg"]) == 1
    assert "say what it shows before it is produced" in capsys.readouterr().err
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced", "--recipe", "agent-svg", "--depicts", "concept"]) == 0
    assert manifest(course)[0]["depicts"] == "concept"


def test_the_interface_of_a_real_application_is_never_drawn(course, capsys):  # noqa: F811
    prepare_asset(course, capsys)
    for recipe in ("agent-svg", "remotion", "magnific-api"):
        assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced", "--recipe", recipe, "--depicts", "interface"]) == 1
        err = capsys.readouterr().err
        assert "the interface of a real application is not invented" in err and recipe in err
    assert manifest(course)[0]["status"] == "pending"  # nothing was written
    # real material is fine: a capture a person provided, without saying more
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced", "--recipe", "screenshot", "--depicts", "interface"]) == 0


def test_the_plan_offers_only_real_material_for_an_interface(course, capsys):  # noqa: F811
    prepare_asset(course, capsys)
    assert main(["media", "plan", "PWD"]) == 0
    out = capsys.readouterr().out
    assert "what does it show?" in out and "screenshot" not in out  # not classified: nothing real is offered yet
    assert main(["media", "set", "PWD", "U1-S2-M1", "--depicts", "interface", "--status", "scripted", "--recipe", "screenshot"]) == 0
    capsys.readouterr()
    assert main(["media", "plan", "PWD"]) == 0
    out = capsys.readouterr().out
    assert "shows the interface of a real application" in out and "waits for a person" in out
    assert "agent-svg" not in out and "screenshot" in out
    assert main(["media", "set", "PWD", "U1-S2-M1", "--depicts", "concept"]) == 0
    capsys.readouterr()
    assert main(["media", "plan", "PWD"]) == 0
    out = capsys.readouterr().out
    assert "agent-svg" in out and "screenshot" not in out


def test_what_is_already_produced_is_not_asked_again(course, capsys):  # noqa: F811
    prepare_asset(course, capsys)
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced", "--recipe", "agent-svg", "--depicts", "concept"]) == 0
    data = yaml.safe_load((course / "media" / "manifest.yaml").read_text(encoding="utf-8"))
    data["assets"][0].pop("depicts")  # a resource produced before the rule
    (course / "media" / "manifest.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "uploaded", "--asset-path", "p/a.png"]) == 0


def test_a_resource_waiting_for_a_recording_does_not_hold_the_handoff(course, capsys):  # noqa: F811
    from coursekit import course as coursemod
    from coursekit import handoff
    from coursekit.project import find_project

    prepare_asset(course, capsys)
    assert main(["media", "set", "PWD", "U1-S2-M1", "--depicts", "interface", "--status", "scripted", "--recipe", "screen-recording"]) == 0
    loaded = coursemod.load(find_project(), "PWD")
    assert handoff._pending_media(loaded) == []  # it waits for a person, not for the media agent
    assert [a["id"] for a in handoff.awaiting_recordings(loaded)] == ["U1-S2-M1"]
    assert main(["media", "set", "PWD", "U1-S2-M1", "--recipe", "agent-svg"]) == 0  # a generated recipe: the media agent's again
    assert [a["id"] for a in handoff._pending_media(coursemod.load(find_project(), "PWD"))] == ["U1-S2-M1"]


def test_redo_clean_forgets_what_the_discarded_version_left(course, capsys):  # noqa: F811
    prepare_asset(course, capsys)
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "uploaded", "--recipe", "agent-svg", "--depicts", "concept",
                 "--file", "media/files/a.svg", "--alt", "Parts", "--transcript", "T", "--made-with", "tool",
                 "--asset-path", "p/a.svg"]) == 0
    assert main(["media", "redo", "PWD", "U1-S2-M1"]) == 0  # as before: the file and the rest stay for the agent to start from
    kept = manifest(course)[0]
    assert kept["status"] == "scripted" and kept["file"] == "media/files/a.svg" and kept["asset_path"] is None
    assert main(["media", "redo", "PWD", "U1-S2-M1", "--clean"]) == 0
    clean = manifest(course)[0]
    assert clean["status"] == "scripted"
    assert all(clean[k] is None for k in ("file", "alt", "transcript", "subtitles_path", "made_with", "asset_path"))
    assert clean["depicts"] == "concept"  # what it shows does not change


def test_the_flex_tier_tries_again_and_then_goes_on_in_the_standard_one(monkeypatch):
    calls, waits = [], []

    def busy(url, body, headers, timeout=300):
        calls.append(json.loads(body).get("serviceTier", "standard"))
        if calls[-1] == "flex":
            raise mediatools.ToolError("busy", 503)
        return json.dumps({"ok": True}).encode()

    monkeypatch.setattr(mediatools, "post", busy)
    payload = mediatools.gemini_request("Hola.", "Aoede", "es", "")
    assert mediatools.gemini_post("u", payload, "k", {"tier": "flex"}, sleep=waits.append) == {"ok": True}
    assert calls == ["flex"] * 4 + ["standard"] and waits == list(mediatools.FLEX_WAITS)
    calls.clear()
    with pytest.raises(mediatools.ToolError, match="no capacity in the flex tier"):
        mediatools.gemini_post("u", payload, "k", {"tier": "flex", "flex_fallback": False}, sleep=waits.append)
    calls.clear()
    assert mediatools.gemini_post("u", payload, "k", {"tier": "standard"}) == {"ok": True} and calls == ["standard"]

    def broken(url, body, headers, timeout=300):
        raise mediatools.ToolError("bad key", 400)

    monkeypatch.setattr(mediatools, "post", broken)
    with pytest.raises(mediatools.ToolError, match="bad key"):  # not a matter of capacity: no attempts and no fallback
        mediatools.gemini_post("u", payload, "k", {"tier": "flex"}, sleep=waits.append)


def test_a_decorative_image_comes_from_the_catalog_first_and_the_rest_is_generated(monkeypatch):
    from coursekit import i18n, media

    monkeypatch.setenv("MAGNIFIC_API_KEY", "mg")
    chain = media.options_for("image", media.config())
    ids = [o["id"] for o in chain]
    assert ids[:2] == ["creator-stock", "magnific-api"] and ids.count("creator-stock") == 2
    assert chain[0]["only"] == "decorative" and "only for decorative content" in chain[0]["available"]
    assert "only" not in chain[ids.index("creator-stock", 1)]  # lower down, for any image
    i18n.use("es")
    try:
        assert "solo para contenido decorativo" in media.options_for("image", media.config())[0]["available"]
        assert "solo para contenido de terminal" in media.options_for("video", media.config())[-1]["available"]
    finally:
        i18n.use(None)
