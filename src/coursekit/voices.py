"""Voice-over providers: which are available here, and which one each course uses.

Every course uses ONE voice for all its narration (course.yaml › media.voice), so a course never
mixes voices. When several providers are available and the course has none chosen yet, the
person picks one with `coursekit voice set`.
"""

from __future__ import annotations

import os
import shutil

from coursekit import course as coursemod
from coursekit.i18n import t
from coursekit.util import edit_yaml, save_yaml

PROVIDERS = {
    "elevenlabs": {
        "label": "ElevenLabs", "env": ["ELEVENLABS_API_KEY"], "voice_env": "ELEVENLABS_VOICE_ID",
        "default_voice": {}, "note_key": "note_elevenlabs",
    },
    "azure": {
        "label": "Azure AI Speech", "env": ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"], "voice_env": "AZURE_SPEECH_VOICE",
        "default_voice": {"es": "es-ES-ElviraNeural", "en": "en-GB-SoniaNeural"}, "note_key": "note_azure",
    },
    "google": {
        "label": "Google Cloud TTS", "env": ["GOOGLE_TTS_API_KEY"], "voice_env": "GOOGLE_TTS_VOICE",
        "default_voice": {"es": "es-ES-Chirp3-HD-Aoede", "en": "en-GB-Chirp3-HD-Aoede"}, "note_key": "note_google",
    },
    "piper": {
        "label": "Piper (local)", "env": ["PIPER_VOICE"], "voice_env": "PIPER_VOICE", "speaker_env": "PIPER_SPEAKER",
        "default_voice": {}, "command": "piper", "note_key": "note_piper",
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
            raise VoiceError(t("voices", "unknown_provider", provider=provider, providers=", ".join(PROVIDERS)))
        if not is_available(provider):
            needs = " + ".join(PROVIDERS[provider]["env"])
            raise VoiceError(t("voices", "not_configured", label=PROVIDERS[provider]["label"], needs=needs))
    else:
        found = available()
        if not found:
            raise VoiceError(t("voices", "none_configured"))
        if len(found) > 1:
            code = course["code"] if course else "<CODE>"
            raise VoiceError(t("voices", "several_available", found=", ".join(found), code=code))
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
    status = {True: t("voices", "status_available"), False: t("voices", "status_missing")}
    width = max(len(w) for w in status.values())
    lines = [f"{status[p in found]:<{width}}  {p:<11} {s['label']:<18} {t('voices', s['note_key'])}" for p, s in PROVIDERS.items()]
    if course:
        chosen = course_voice(course)
        if chosen:
            shown = {"code": course["code"], "provider": chosen.get("provider"),
                     "voice": chosen.get("voice") or t("voices", "default_voice_listing")}
            if chosen.get("speaker") is not None:
                lines.append(t("voices", "course_uses_speaker", speaker=chosen["speaker"], **shown))
            else:
                lines.append(t("voices", "course_uses", **shown))
        elif len(found) > 1:
            lines.append(t("voices", "course_several", code=course["code"]))
        elif found:
            lines.append(t("voices", "course_default", code=course["code"], provider=found[0]))
        else:
            lines.append(t("voices", "course_nothing", code=course["code"]))
    return lines


def set_voice(course: dict, provider: str, voice: str | None, speaker: str | None) -> tuple[str, str | None]:
    """Fix the course voice. Returns (message, warning)."""
    if provider not in PROVIDERS:
        raise VoiceError(t("voices", "unknown_provider_short", provider=provider, providers=", ".join(PROVIDERS)))
    warning = None if is_available(provider) else t("voices", "not_configured_warning", provider=provider)
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
    shown = {"code": data["code"], "provider": provider, "voice": entry["voice"] or t("voices", "default_voice_set")}
    if speaker is not None:
        return t("voices", "voice_set_speaker", speaker=speaker, **shown), warning
    return t("voices", "voice_set", **shown), warning
