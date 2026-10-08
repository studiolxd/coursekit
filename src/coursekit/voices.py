"""Voice-over providers: which are available here, and which one each course uses.

Every course uses ONE voice for all its narration (course.yaml › media.voice), so a course never
mixes voices. When several providers are available and the course has none chosen yet, the
person picks one with `coursekit voice set`.
"""

from __future__ import annotations

import os
import shutil

from coursekit import course as coursemod
from coursekit.util import edit_yaml, save_yaml

PROVIDERS = {
    "elevenlabs": {
        "label": "ElevenLabs", "env": ["ELEVENLABS_API_KEY"], "voice_env": "ELEVENLABS_VOICE_ID",
        "default_voice": {}, "note": "best quality; exact captions from its timestamps",
    },
    "azure": {
        "label": "Azure AI Speech", "env": ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"], "voice_env": "AZURE_SPEECH_VOICE",
        "default_voice": {"es": "es-ES-ElviraNeural", "en": "en-GB-SoniaNeural"}, "note": "neural voices; free tier",
    },
    "google": {
        "label": "Google Cloud TTS", "env": ["GOOGLE_TTS_API_KEY"], "voice_env": "GOOGLE_TTS_VOICE",
        "default_voice": {"es": "es-ES-Chirp3-HD-Aoede", "en": "en-GB-Chirp3-HD-Aoede"}, "note": "Chirp 3 HD voices; free tier",
    },
    "piper": {
        "label": "Piper (local)", "env": ["PIPER_VOICE"], "voice_env": "PIPER_VOICE", "speaker_env": "PIPER_SPEAKER",
        "default_voice": {}, "command": "piper", "note": "local draft voice (coursekit setup --media)",
    },
}
LOCALES = {"es": "es-ES", "en": "en-GB"}


class VoiceError(Exception):
    pass


def is_available(provider: str) -> bool:
    spec = PROVIDERS[provider]
    if not all(os.environ.get(v, "").strip() for v in spec["env"]):
        return False
    return shutil.which(spec["command"]) is not None if spec.get("command") else True


def available() -> list[str]:
    return [p for p in PROVIDERS if is_available(p)]


def course_voice(course: dict) -> dict:
    return (course.get("media") or {}).get("voice") or {}


def default_voice(provider: str, language: str) -> str | None:
    return PROVIDERS[provider]["default_voice"].get(language)


def resolve(course: dict | None, engine: str | None = None) -> tuple[str, str | None, str | None]:
    """(provider, voice, speaker) to use, or VoiceError saying what the person has to do."""
    chosen = course_voice(course) if course else {}
    language = coursemod.language(course) if course else "es"
    provider = engine or chosen.get("provider")
    if provider:
        if provider not in PROVIDERS:
            raise VoiceError(f"unknown voice provider '{provider}' ({', '.join(PROVIDERS)})")
        if not is_available(provider):
            needs = " + ".join(PROVIDERS[provider]["env"])
            raise VoiceError(f"this course uses {PROVIDERS[provider]['label']} but it is not configured here ({needs} in .env)")
    else:
        found = available()
        if not found:
            raise VoiceError("no voice provider configured (ElevenLabs, Azure or Google keys, or Piper, in .env)")
        if len(found) > 1:
            code = course["code"] if course else "<CODE>"
            raise VoiceError(f"several voice providers are available ({', '.join(found)}): choose one for the course "
                             f"with `coursekit voice set {code} <provider> [--voice …]`")
        provider = found[0]
    spec = PROVIDERS[provider]
    same = chosen.get("provider") == provider
    voice = (chosen.get("voice") if same else None) or os.environ.get(spec["voice_env"], "").strip() or default_voice(provider, language)
    speaker = chosen.get("speaker") if same else None
    if speaker is None and spec.get("speaker_env"):
        speaker = os.environ.get(spec["speaker_env"], "").strip() or None
    return provider, voice, None if speaker is None else str(speaker)


def listing(course: dict | None) -> list[str]:
    found = available()
    lines = [f"{'available' if p in found else 'missing  '}  {p:<11} {s['label']:<18} {s['note']}" for p, s in PROVIDERS.items()]
    if course:
        chosen = course_voice(course)
        if chosen:
            lines.append(f"\n{course['code']} uses: {chosen.get('provider')} · {chosen.get('voice') or '(default voice)'}"
                         + (f" · speaker {chosen['speaker']}" if chosen.get("speaker") is not None else ""))
        elif len(found) > 1:
            lines.append(f"\n{course['code']}: no voice chosen and several providers available "
                         f"→ coursekit voice set {course['code']} <provider>")
        else:
            lines.append(f"\n{course['code']}: no voice chosen; {found[0] if found else 'nothing'} would be used")
    return lines


def set_voice(course: dict, provider: str, voice: str | None, speaker: str | None) -> tuple[str, str | None]:
    """Fix the course voice. Returns (message, warning)."""
    if provider not in PROVIDERS:
        raise VoiceError(f"unknown provider '{provider}' ({', '.join(PROVIDERS)})")
    warning = None if is_available(provider) else f"{provider} is not configured on this machine; others on the team may have it"
    path = course["_dir"] / "course.yaml"
    ry, data = edit_yaml(path)
    if data.get("media") is None:
        data["media"] = {}
    spec = PROVIDERS[provider]
    entry = {"provider": provider,
             "voice": voice or os.environ.get(spec["voice_env"], "").strip() or default_voice(provider, coursemod.language(course))}
    if speaker is not None:
        entry["speaker"] = int(speaker)
    data["media"]["voice"] = entry
    save_yaml(ry, data, path)
    message = f"{data['code']}: voice {provider} · {entry['voice'] or '(default)'}"
    if speaker is not None:
        message += f" · speaker {speaker}"
    return message, warning
