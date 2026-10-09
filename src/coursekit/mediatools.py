"""Voice-over (`coursekit tts`) and captions (`coursekit subtitles`).

Without --engine, the provider is the course's voice (course.yaml › media.voice) or the only one
configured. ElevenLabs also writes <out>.vtt from the character timestamps the API returns; with
Azure, Google or Piper, align the audio with `coursekit subtitles` (stable-ts, word by word
against the known script).
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from coursekit import course as coursemod
from coursekit.i18n import t
from coursekit.voices import LOCALES, resolve


class ToolError(Exception):
    pass


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
        raise ToolError(t("mediatools", "http_failed", host=req.host, status=exc.code, reason=exc.reason)) from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ToolError(t("mediatools", "network_failed", host=req.host, reason=getattr(exc, "reason", exc))) from None


def upload(path: Path, url: str, content_type: str, method: str = "PUT") -> str:
    """Sends a file to the upload address a platform minted for it (creator's `request_asset_upload` gives `uploadUrl`)."""
    require_file(path)
    if not url.startswith("https://"):
        raise ToolError(t("mediatools", "upload_not_https"))
    req = urllib.request.Request(url, data=path.read_bytes(), method=method.upper(), headers={"Content-Type": content_type})
    fetch(req)
    return t("mediatools", "uploaded", name=path.name, size=path.stat().st_size)


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


def tts_piper(text: str, out: Path, voice: str | None, speaker: str | None = None, language: str = "es") -> None:
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


def tts_elevenlabs(text: str, out: Path, voice: str | None, speaker: str | None = None, language: str = "es") -> None:
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


def concat_mp3(parts: list[bytes], out: Path) -> None:
    if len(parts) == 1:
        out.write_bytes(parts[0])
        return
    with tempfile.TemporaryDirectory() as tmp:
        names = []
        for i, data in enumerate(parts):
            name = Path(tmp) / f"part{i:03d}.mp3"
            name.write_bytes(data)
            names.append(name)
        listing = Path(tmp) / "list.txt"
        # Forward slashes: the concat list treats backslashes (Windows paths) as escapes.
        listing.write_text("".join(f"file '{n.as_posix()}'\n" for n in names), encoding="utf-8")
        run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
             "-codec:a", "libmp3lame", "-qscale:a", "3", str(out)])


def post(url: str, body: bytes, headers: dict) -> bytes:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    return fetch(req)


def tts_azure(text: str, out: Path, voice: str | None, speaker: str | None = None, language: str = "es") -> None:
    from xml.sax.saxutils import escape

    key, region = os.environ["AZURE_SPEECH_KEY"].strip(), os.environ["AZURE_SPEECH_REGION"].strip()
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {"Ocp-Apim-Subscription-Key": key, "Content-Type": "application/ssml+xml",
               "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3", "User-Agent": "coursekit"}
    parts = []
    for chunk in sentence_chunks(text, 4000):
        ssml = f"<speak version='1.0' xml:lang='{LOCALES.get(language, language)}'><voice name='{voice}'>{escape(chunk)}</voice></speak>"
        parts.append(post(url, ssml.encode(), headers))
    concat_mp3(parts, out)


def tts_google(text: str, out: Path, voice: str | None, speaker: str | None = None, language: str = "es") -> None:
    key = os.environ["GOOGLE_TTS_API_KEY"].strip()
    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={key}"
    parts = []
    for chunk in sentence_chunks(text, 4500):  # API limit: 5000 bytes per request
        body = json.dumps({"input": {"text": chunk}, "voice": {"languageCode": LOCALES.get(language, language), "name": voice},
                           "audioConfig": {"audioEncoding": "MP3"}}).encode()
        data = json.loads(post(url, body, {"Content-Type": "application/json"}))
        parts.append(base64.b64decode(data["audioContent"]))
    concat_mp3(parts, out)


def subtitles(audio: Path, text_path: Path, out: Path, model_name: str = "base", language: str = "es") -> None:
    """Align the known script with the audio (stable-ts, installed by coursekit setup --media) into a VTT."""
    require_file(audio)
    require_file(text_path)
    exe = shutil.which("stable-ts")
    if not exe:
        raise ToolError(t("mediatools", "stable_ts_missing"))
    run([exe, str(audio), "--align", str(text_path), "--language", language, "--model", model_name,
         "--regroup", "sp=./?/!_sl=84", "--word_level", "false", "-o", str(out)])


ENGINES = {"elevenlabs": tts_elevenlabs, "azure": tts_azure, "google": tts_google, "piper": tts_piper}


def tts(course: dict | None, engine: str | None, input_path: Path, out: Path, voice: str | None = None,
        speaker: str | None = None) -> str:
    require_file(input_path)
    text = re.sub(r"\s+", " ", input_path.read_text(encoding="utf-8")).strip()
    out.parent.mkdir(parents=True, exist_ok=True)
    provider, course_voice, course_speaker = resolve(course, engine)
    language = coursemod.language(course) if course else "es"
    ENGINES[provider](text, out, voice or course_voice, speaker or course_speaker, language)
    used_voice = voice or course_voice or t("mediatools", "default_voice")
    if provider == "elevenlabs" and out.with_suffix(".vtt").exists():
        return t("mediatools", "wrote_vtt", out=out, vtt=out.with_suffix(".vtt").name, provider=provider, voice=used_voice)
    return t("mediatools", "wrote", out=out, provider=provider, voice=used_voice)
