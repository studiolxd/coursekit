"""Voice-over (`coursekit tts`) and captions (`coursekit subtitles`).

Without --engine, the provider is the course's voice (course.yaml › media.voice) or the only one
configured. ElevenLabs also writes <out>.vtt from the character timestamps the API returns; with
Azure, Google, Gemini or Piper, align the audio with `coursekit subtitles` (stable-ts, word by word
against the known script).
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

from coursekit import course as coursemod
from coursekit.i18n import t
from coursekit.util import USER_AGENT
from coursekit.voices import LOCALES, resolve, resolve_character
from coursekit.voices import course_voice as chosen_voice


class ToolError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status  # the HTTP status of the answer, when the failure was one


def run(command: list[str], **kwargs) -> None:
    """subprocess.run that reports a missing program or a failed run as a ToolError (a message, not a traceback)."""
    try:
        subprocess.run(command, check=True, **kwargs)
    except FileNotFoundError:
        raise ToolError(t("mediatools", "program_missing", program=Path(command[0]).name)) from None
    except subprocess.CalledProcessError as exc:
        raise ToolError(t("mediatools", "program_failed", program=Path(command[0]).name, code=exc.returncode)) from None


def fetch(req: urllib.request.Request, timeout: int = 300) -> bytes:
    """The body of an API response; an HTTP or network failure is a ToolError that names the service and the status."""
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise ToolError(t("mediatools", "http_failed", host=req.host, status=exc.code, reason=exc.reason), exc.code) from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ToolError(t("mediatools", "network_failed", host=req.host, reason=getattr(exc, "reason", exc))) from None


def upload(path: Path, url: str, content_type: str, method: str = "PUT") -> str:
    """Sends a file to the upload address a platform minted for it (creator's `request_asset_upload` gives `uploadUrl`)."""
    require_file(path)
    if not url.startswith("https://"):
        raise ToolError(t("mediatools", "upload_not_https"))
    headers = {"Content-Type": content_type, "User-Agent": USER_AGENT}
    req = urllib.request.Request(url, data=path.read_bytes(), method=method.upper(), headers=headers)
    fetch(req)
    return t("mediatools", "uploaded", name=path.name, size=path.stat().st_size)


def download(url: str, out: Path, root: Path) -> str:
    """Saves what an https address serves (the export of a platform, for instance) in a file inside the project: the sessions
    without an interface have `coursekit`, not `curl`."""
    if not url.startswith("https://"):
        raise ToolError(t("mediatools", "upload_not_https"))
    target = (out if out.is_absolute() else root / out).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ToolError(t("mediatools", "download_outside", path=out.as_posix()))
    body = fetch(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    return t("mediatools", "downloaded", path=target.relative_to(root.resolve()).as_posix(), size=len(body))


def require_file(path: Path) -> None:
    if not path.is_file():
        raise ToolError(t("mediatools", "input_missing", path=path.as_posix()))


def to_mp3(wav: Path, out: Path) -> None:
    if out.suffix.lower() == ".wav":
        wav.replace(out)
        return
    run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav), "-codec:a", "libmp3lame", "-qscale:a", "3", str(out)])


def vtt_time(seconds: float) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def vtt_from_characters(chars: list[str], starts: list[float], ends: list[float], max_len: int = 84) -> str:
    """Group characters into cues at sentence ends or every ~max_len characters."""
    cues, buf, cue_start = [], "", None
    for ch, st, en in zip(chars, starts, ends, strict=False):
        if cue_start is None and ch.strip():
            cue_start = st
        buf += ch
        if cue_start is not None and ((ch in ".?!" ) or (len(buf) >= max_len and ch == " ")):
            cues.append((cue_start, en, buf.strip()))
            buf, cue_start = "", None
    if buf.strip() and cue_start is not None:
        cues.append((cue_start, ends[-1], buf.strip()))
    lines = ["WEBVTT", ""]
    for i, (a, b, text) in enumerate(cues, 1):
        lines += [str(i), f"{vtt_time(a)} --> {vtt_time(b)}", text, ""]
    return "\n".join(lines)


def words_path(path: Path) -> Path:
    """Where the timings of the words of a voice-over or its captions go: `u1.mp3`/`u1.vtt` → `u1.words.json`."""
    return path.with_suffix(".words.json")


def write_words(words: list[dict], out: Path) -> None:
    """The words said, each with when it starts and ends (seconds): what anchors a zoom or a layer to a word."""
    clean = [{"w": str(w["w"]).strip(), "start": round(float(w["start"]), 3), "end": round(float(w["end"]), 3)}
             for w in words if str(w["w"]).strip()]
    out.write_text(json.dumps({"words": clean}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")


def words_from_characters(chars: list[str], starts: list[float], ends: list[float]) -> list[dict]:
    words, current, start, end = [], "", None, None
    for ch, st, en in zip(chars, starts, ends, strict=False):
        if ch.isspace():
            if current:
                words.append({"w": current, "start": start, "end": end})
            current, start = "", None
            continue
        if start is None:
            start = st
        current, end = current + ch, en
    if current:
        words.append({"w": current, "start": start, "end": end})
    return words


def tts_piper(text: str, out: Path, voice: str | None, speaker: str | None = None, language: str = "es",
              course: dict | None = None) -> None:
    model = voice or os.environ.get("PIPER_VOICE", "")
    if not model:
        raise ToolError(t("mediatools", "piper_voice"))
    piper = shutil.which("piper")
    if not piper:
        raise ToolError(t("mediatools", "piper_missing"))
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "out.wav"
        cmd = [piper, "-m", str(Path(model).expanduser()), "-f", str(wav)]
        speaker = speaker if speaker is not None else os.environ.get("PIPER_SPEAKER", "").strip()
        if speaker:
            cmd += ["-s", speaker]
        run(cmd, input=text.encode())
        to_mp3(wav, out)


def tts_elevenlabs(text: str, out: Path, voice: str | None, speaker: str | None = None, language: str = "es",
                   course: dict | None = None) -> None:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    voice_id = voice or os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
    if not key or not voice_id:
        raise ToolError(t("mediatools", "elevenlabs_needs"))
    body = json.dumps({"text": text, "model_id": "eleven_multilingual_v2", "language_code": language}).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128",
        data=body, headers={"xi-api-key": key, "Content-Type": "application/json"}, method="POST")
    data = json.loads(fetch(req))
    out.write_bytes(base64.b64decode(data["audio_base64"]))
    al = data.get("alignment") or data.get("normalized_alignment")
    if al:
        vtt = vtt_from_characters(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"])
        out.with_suffix(".vtt").write_text(vtt, encoding="utf-8")
        write_words(words_from_characters(al["characters"], al["character_start_times_seconds"],
                                          al["character_end_times_seconds"]), words_path(out))



def sentence_chunks(text: str, limit: int) -> list[str]:
    """Split text at sentence ends into chunks of at most `limit` UTF-8 bytes."""
    chunks, current = [], ""
    for sentence in re.split(r"(?<=[.!?…])\s+", text):
        candidate = f"{current} {sentence}".strip()
        if current and len(candidate.encode()) > limit:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


GEMINI_API = "https://generativelanguage.googleapis.com/v1beta"
PCM_RATE = 24000  # Hz: what Azure, Google and Gemini are asked for (16-bit mono)


def wav_frames(data: bytes) -> tuple[bytes, int]:
    """(samples, rate) of a 16-bit mono WAV, so that pieces are joined as samples and not as compressed files."""
    with wave.open(io.BytesIO(data)) as wav:
        return wav.readframes(wav.getnframes()), wav.getframerate()


def encode_pcm(pcm: bytes, out: Path, rate: int = PCM_RATE) -> None:
    """Writes 16-bit mono samples (the pieces of a long script, already one after the other) as one MP3, encoded once: no
    silence of the encoder between the pieces and no second pass of compression. An `out` ending in .wav keeps a WAV."""
    if out.suffix.lower() == ".wav":
        with wave.open(str(out), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(pcm)
        return
    run(["ffmpeg", "-loglevel", "error", "-y", "-f", "s16le", "-ar", str(rate), "-ac", "1", "-i", "pipe:0",
         "-codec:a", "libmp3lame", "-qscale:a", "3", str(out)], input=pcm)


def post(url: str, body: bytes, headers: dict, timeout: int = 300) -> bytes:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    return fetch(req, timeout)


def tts_azure(text: str, out: Path, voice: str | None, speaker: str | None = None, language: str = "es",
              course: dict | None = None) -> None:
    from xml.sax.saxutils import escape

    key, region = os.environ["AZURE_SPEECH_KEY"].strip(), os.environ["AZURE_SPEECH_REGION"].strip()
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {"Ocp-Apim-Subscription-Key": key, "Content-Type": "application/ssml+xml",
               "X-Microsoft-OutputFormat": "raw-24khz-16bit-mono-pcm", "User-Agent": "coursekit"}
    parts = []
    for chunk in sentence_chunks(text, 4000):
        ssml = f"<speak version='1.0' xml:lang='{LOCALES.get(language, language)}'><voice name='{voice}'>{escape(chunk)}</voice></speak>"
        parts.append(post(url, ssml.encode(), headers))
    encode_pcm(b"".join(parts), out)


def tts_google(text: str, out: Path, voice: str | None, speaker: str | None = None, language: str = "es",
               course: dict | None = None) -> None:
    key = os.environ["GOOGLE_TTS_API_KEY"].strip()
    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={key}"
    parts = []
    for chunk in sentence_chunks(text, 4500):  # API limit: 5000 bytes per request
        body = json.dumps({"input": {"text": chunk}, "voice": {"languageCode": LOCALES.get(language, language), "name": voice},
                           "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": PCM_RATE}}).encode()
        data = json.loads(post(url, body, {"Content-Type": "application/json"}))
        parts.append(wav_frames(base64.b64decode(data["audioContent"]))[0])  # LINEAR16 comes with a WAV header
    encode_pcm(b"".join(parts), out)


def gemini_settings(course: dict | None) -> dict:
    """Model, style and size of the pieces of the Gemini voice: `media.yaml › gemini` (project, then course), with the model
    the course fixed when its voice was chosen (course.yaml › media.voice.model), so a course never changes model halfway."""
    from coursekit import config as configmod

    project = (course or {}).get("_project")
    settings = dict(configmod.effective("media", project, course).get("gemini") or {})
    chosen = chosen_voice(course) if course else {}
    if chosen.get("provider") == "gemini" and chosen.get("model"):
        settings["model"] = chosen["model"]
    return settings


def gemini_request(text: str, voice: str | None, language: str, style: str, tier: str | None = None) -> dict:
    """The body of one generateContent request of the Gemini voice (also each line of a batch). `tier: flex` asks for the flex
    tier: half the price, an answer in minutes instead of seconds, and refused when Google has no capacity (429, 503)."""
    part: dict = {"text": text}
    if style:
        part["speechMetadata"] = {"style": style}
    body = {"contents": [{"role": "user", "parts": [part]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"languageCode": LOCALES.get(language, language),
                                                  "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    if tier == "flex":
        body["serviceTier"] = "flex"
    return body


FLEX_WAITS = (5, 20, 60)  # seconds between the attempts when the flex tier has no capacity


def gemini_post(url: str, payload: dict, key: str, settings: dict, sleep=time.sleep) -> dict:
    """One request of the Gemini voice, in the tier of the settings. When flex has no capacity (429, 503) it tries again a few
    times and then, with `flex_fallback`, in the standard tier (the full price, but the work goes on)."""
    headers = {"Content-Type": "application/json", "x-goog-api-key": key}
    tier = str(settings.get("tier") or "standard")
    if tier != "flex":
        return json.loads(post(url, json.dumps(payload).encode(), headers))
    flex = json.dumps({**payload, "serviceTier": "flex"}).encode()
    for wait in (*FLEX_WAITS, None):
        try:
            return json.loads(post(url, flex, headers, timeout=960))  # flex answers in up to 15 minutes
        except ToolError as exc:
            if exc.status not in (429, 503):
                raise
        if wait is not None:
            sleep(wait)
    if settings.get("flex_fallback", True) is False:
        raise ToolError(t("mediatools", "gemini_flex_busy"))
    return json.loads(post(url, json.dumps(payload).encode(), headers))


def gemini_audio(response: dict) -> tuple[bytes, int]:
    """(samples, rate) of a Gemini response: a WAV (the 3.8 models) or headerless L16 (`audio/L16;rate=24000`, earlier ones)."""
    for candidate in response.get("candidates") or []:
        for part in (candidate.get("content") or {}).get("parts") or []:
            blob = part.get("inlineData") or part.get("inline_data")
            if blob and blob.get("data"):
                data = base64.b64decode(blob["data"])
                if data[:4] == b"RIFF":
                    return wav_frames(data)
                rate = re.search(r"rate=(\d+)", blob.get("mimeType") or blob.get("mime_type") or "")
                return data, int(rate.group(1)) if rate else PCM_RATE
    reason = next((c.get("finishReason") for c in response.get("candidates") or [] if c.get("finishReason")), None)
    raise ToolError(t("mediatools", "gemini_no_audio", reason=reason or "?"))


def tts_gemini(text: str, out: Path, voice: str | None, speaker: str | None = None, language: str = "es",
               course: dict | None = None) -> None:
    key = os.environ["GEMINI_API_KEY"].strip()
    settings = gemini_settings(course)
    url = f"{GEMINI_API}/models/{settings['model']}:generateContent"
    parts, rate = [], PCM_RATE
    for chunk in sentence_chunks(text, int(settings["chunk_bytes"])):
        payload = gemini_request(chunk, voice, language, str(settings.get("style") or "").strip())
        samples, rate = gemini_audio(gemini_post(url, payload, key, settings))
        parts.append(samples)
    encode_pcm(b"".join(parts), out, rate)


def subtitles(audio: Path, text_path: Path, out: Path, model_name: str = "base", language: str = "es") -> None:
    """Align the known script with the audio (stable-ts, installed by coursekit setup --media) into a VTT."""
    require_file(audio)
    require_file(text_path)
    exe = shutil.which("stable-ts")
    if not exe:
        raise ToolError(t("mediatools", "stable_ts_missing"))
    with tempfile.TemporaryDirectory() as tmp:
        result = Path(tmp) / "aligned.json"  # one output per audio: the JSON, which has both the sentences and the words
        run([exe, str(audio), "--align", str(text_path), "--language", language, "--model", model_name,
             "--regroup", "sp=./?/!_sl=84", "-o", str(result)])
        try:
            data = json.loads(result.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise ToolError(t("mediatools", "program_failed", program="stable-ts", code="?")) from None
    segments = [s for s in data.get("segments") or [] if str(s.get("text") or "").strip()]
    lines = ["WEBVTT", ""]
    for i, seg in enumerate(segments, 1):
        start = float(seg["start"])
        end = max(float(seg["end"]), start + 0.5)  # the alignment can give a stretch no time: it must still show
        if i < len(segments):
            end = min(end, max(float(segments[i]["start"]), start + 0.1))
        lines += [str(i), f"{vtt_time(start)} --> {vtt_time(end)}", str(seg["text"]).strip(), ""]
    out.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    write_words([{"w": w.get("word", ""), "start": w["start"], "end": w["end"]} for seg in segments
                 for w in seg.get("words") or []], words_path(out))


ENGINES = {"elevenlabs": tts_elevenlabs, "azure": tts_azure, "google": tts_google, "gemini": tts_gemini, "piper": tts_piper}


def tts(course: dict | None, engine: str | None, input_path: Path, out: Path, voice: str | None = None,
        speaker: str | None = None, character: str | None = None) -> str:
    require_file(input_path)
    text = re.sub(r"\s+", " ", input_path.read_text(encoding="utf-8")).strip()
    out.parent.mkdir(parents=True, exist_ok=True)
    provider, course_voice, course_speaker = resolve_character(course, character, engine) if character else resolve(course, engine)
    language = coursemod.language(course) if course else "es"
    ENGINES[provider](text, out, voice or course_voice, speaker or course_speaker, language, course)
    used_voice = voice or course_voice or t("mediatools", "default_voice")
    if provider == "elevenlabs" and out.with_suffix(".vtt").exists():
        return t("mediatools", "wrote_vtt", out=out, vtt=out.with_suffix(".vtt").name, provider=provider, voice=used_voice)
    return t("mediatools", "wrote", out=out, provider=provider, voice=used_voice)


# ── Images: size and SVG rendering (local, no credits) ─────────────────────────────────────────

BROWSERS = ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge", "microsoft-edge")
BROWSER_APPS = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")


def parse_size(text: str) -> tuple[int, int]:
    m = re.fullmatch(r"\s*(\d+)\s*[x×]\s*(\d+)\s*", text or "")
    if not m:
        raise ToolError(t("mediatools", "bad_size", size=text))
    return int(m.group(1)), int(m.group(2))


def fit(path: Path, size: tuple[int, int]) -> str:
    """Brings an image to an exact size: scaled to cover it and cropped from the centre (a transparent PNG keeps its alpha)."""
    from PIL import Image

    require_file(path)
    with Image.open(path) as im:
        before = im.size
        width, height = size
        scale = max(width / im.width, height / im.height)
        resized = im.resize((max(width, round(im.width * scale)), max(height, round(im.height * scale))), Image.LANCZOS)
        left, top = (resized.width - width) // 2, (resized.height - height) // 2
        out = resized.crop((left, top, left + width, top + height))
        out.save(path)
    return t("mediatools", "fitted", path=path.name, before=f"{before[0]}x{before[1]}", after=f"{width}x{height}")


def browser() -> str | None:
    for name in BROWSERS:
        found = shutil.which(name)
        if found:
            return found
    return next((app for app in BROWSER_APPS if Path(app).exists()), None)


def svg_size(svg: Path) -> tuple[int, int]:
    text = svg.read_text(encoding="utf-8", errors="replace")[:2000]
    box = re.search(r'viewBox="\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)', text)
    if box:
        return round(float(box.group(1))), round(float(box.group(2)))
    w, h = re.search(r'\bwidth="([\d.]+)', text), re.search(r'\bheight="([\d.]+)', text)
    return (round(float(w.group(1))), round(float(h.group(1)))) if w and h else (1600, 900)


def render_svg(svg: Path, out: Path, size: tuple[int, int] | None = None, fonts_css: str | None = None) -> str:
    """An SVG as a PNG, drawn by the Chrome, Chromium or Edge of the machine (headless): to look at it and for creator. With
    `fonts_css` (@font-face rules, their files inside as data) its text is drawn in those fonts, whatever the machine has."""
    require_file(svg)
    exe = browser()
    if not exe:
        raise ToolError(t("mediatools", "no_browser"))
    width, height = size or svg_size(svg)
    page = out.with_suffix(".render.html")
    if fonts_css:  # an <img> loads no fonts: the drawing goes inside the page, next to them
        markup = re.sub(r"^\s*(<\?xml[^>]*\?>|<!DOCTYPE[^>]*>)\s*", "", svg.read_text(encoding="utf-8"), flags=re.I)
        body = f'<div class="svg">{markup}</div>'
        extra = f"{fonts_css}\n.svg,.svg>svg{{display:block;width:{width}px;height:{height}px}}"
    else:
        body, extra = f'<img src="{svg.resolve().as_uri()}">', ""
    page.write_text(f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;background:transparent}}'
                    f'img{{display:block;width:{width}px;height:{height}px}}{extra}</style></head>'
                    f'<body>{body}</body></html>', encoding="utf-8")
    try:
        run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
             "--default-background-color=00000000", f"--window-size={width},{height}", f"--screenshot={out.resolve()}",
             "--virtual-time-budget=3000", page.resolve().as_uri()])
    finally:
        page.unlink(missing_ok=True)
    if not out.exists():
        raise ToolError(t("mediatools", "render_failed", svg=svg.name))
    return t("mediatools", "rendered", svg=svg.name, png=out.name, size=f"{width}x{height}")
