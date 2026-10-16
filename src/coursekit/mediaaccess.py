"""What a video shows, as text: its integrated audio description, its accessible transcript and its track of descriptions.

The scenes of a video are described next to its brief, in `media/scripts/<id>.scenes.yaml`:

    words: media/files/u1-s2-m1.words.json     # the timings of the narration (default: <file of the video>.words.json)
    scenes:
      - text: "Minimum length: 12"             # the text on screen (one or a list)
        shows: "The security settings, with the minimum length field"   # what is seen, in a sentence
        says: "Open the security settings and set the minimum length to twelve."

- Integrated audio description (WCAG 1.2.5): what matters on screen is also said. `not_said` lists the text on screen that
  the narration of its scene does not say (most of its meaningful words), unless the scene says what is seen in `shows`.
  `coursekit media check` reports it.
- Accessible transcript (WCAG 1.2.3, 1.2.8): scene by scene, the minute, what is seen and what is said.
- A WebVTT track of descriptions (kind="descriptions"): what is seen in each scene, while it is seen.
`coursekit media transcript CODE ID` writes the last two next to the video and makes the transcript the one of the resource
(what the assembly puts in the course).
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import yaml

from coursekit import course as coursemod
from coursekit import lang
from coursekit import media as mediamod
from coursekit.i18n import t
from coursekit.mediatools import vtt_time


class AccessError(Exception):
    pass


def scenes_file(course: dict, asset_id: str) -> Path:
    return course["_dir"] / "media" / "scripts" / f"{asset_id}.scenes.yaml"


def read_scenes(course: dict, asset_id: str) -> dict | None:
    path = scenes_file(course, asset_id)
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise AccessError(t("mediaaccess", "bad_scenes", path=path.name, error=str(exc).splitlines()[0])) from None
    if isinstance(data, list):
        data = {"scenes": data}
    if not isinstance(data, dict) or not isinstance(data.get("scenes"), list):
        raise AccessError(t("mediaaccess", "bad_scenes", path=path.name, error="scenes"))
    return data


def _normal(text: str) -> str:
    text = unicodedata.normalize("NFD", str(text)).encode("ascii", "ignore").decode() if text else ""
    return re.sub(r"[^a-z0-9 ]+", " ", text.lower())


def _texts(value) -> list[str]:
    if value is None:
        return []
    return [str(v) for v in value] if isinstance(value, list) else [str(value)]


def said(text: str, narration: str, numbers: list[str]) -> bool:
    """Whether a text on screen is said: most (60 %) of its meaningful words (four letters or more, or numbers) sound."""
    heard = set(_normal(narration).split())
    meaningful = [w for w in _normal(text).split() if len(w) >= 4 or w.isdigit()]
    if not meaningful:
        return True
    sound = [w for w in meaningful if w in heard or (w.isdigit() and int(w) < len(numbers) and _normal(numbers[int(w)]) in heard)]
    return len(sound) / len(meaningful) >= 0.6


def not_said(course: dict, asset: dict) -> list[str]:
    """The text on screen of each scene that its narration does not say (and the scene does not describe in `shows`)."""
    try:
        data = read_scenes(course, str(asset["id"]))
    except AccessError as exc:
        return [str(exc)]
    if not data:
        return []
    numbers = list(lang.tokens(coursemod.language(course)).get("number_words") or [])
    out = []
    for n, scene in enumerate(data["scenes"], 1):
        if not isinstance(scene, dict) or scene.get("shows"):
            continue
        missing = [x for x in _texts(scene.get("text")) if not said(x, str(scene.get("says") or ""), numbers)]
        if missing:
            out.append(t("mediaaccess", "not_said", n=n, text="; ".join(f"«{m}»" for m in missing[:3])))
    return out


# ── when each scene starts ───────────────────────────────────────────────────────────────────

def _words(course: dict, asset: dict, data: dict) -> list[dict]:
    name = data.get("words")
    path = course["_dir"] / str(name) if name else (course["_dir"] / str(asset.get("file") or "")).with_suffix(".words.json")
    try:
        return list(json.loads(path.read_text(encoding="utf-8")).get("words") or [])
    except (OSError, ValueError):
        return []


def starts(scenes: list[dict], words: list[dict]) -> list[float | None]:
    """When the narration of each scene starts: its first words, the first time they are said after the scene before."""
    said_words = [_normal(w["w"]).strip() for w in words]
    out, cursor = [], 0
    for scene in scenes:
        first = [w for w in _normal(str(scene.get("says") or "")).split() if w][:3]
        found = None
        if first:
            for i in range(cursor, len(said_words) - len(first) + 1):
                if said_words[i:i + len(first)] == first:
                    found, cursor = float(words[i]["start"]), i + 1
                    break
        out.append(found)
    return out


def _minute(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def transcript(course: dict, asset: dict) -> tuple[str, str]:
    """The accessible transcript (what is seen and what is said, scene by scene, with its minute) and the VTT of descriptions."""
    data = read_scenes(course, str(asset["id"]))
    if not data:
        raise AccessError(t("mediaaccess", "no_scenes", path=f"media/scripts/{asset['id']}.scenes.yaml"))
    scenes = [s for s in data["scenes"] if isinstance(s, dict)]
    words = _words(course, asset, data)
    times = starts(scenes, words)
    label = lang.tokens(coursemod.language(course))["transcript_on_screen"]
    parts, cues = [], []
    end_of_all = float(words[-1]["end"]) if words else None
    for i, scene in enumerate(scenes):
        seen = str(scene.get("shows") or "") or ". ".join(_texts(scene.get("text")))
        lines = [f"[{_minute(times[i])}]"] if times[i] is not None else []
        if seen:
            lines.append(f"{label}: {seen}")
        if scene.get("says"):
            lines.append(str(scene["says"]).strip())
        parts.append("\n".join(lines))
        if seen and times[i] is not None:
            following = next((x for x in times[i + 1:] if x is not None), end_of_all)
            cues.append((times[i], max(times[i] + 1.0, following or times[i] + 3.0), seen))
    vtt = ["WEBVTT", ""]
    for n, (a, b, text) in enumerate(cues, 1):
        vtt += [str(n), f"{vtt_time(a)} --> {vtt_time(b)}", text, ""]
    return "\n\n".join(p for p in parts if p) + "\n", "\n".join(vtt)


def write(course: dict, asset_id: str) -> dict:
    """Writes the transcript and the descriptions next to the video and makes the transcript the one of the resource."""
    ry, path, data = mediamod.load_manifest(course["_dir"])
    asset = next((a for a in data["assets"] if str(a["id"]) == asset_id), None)
    if asset is None:
        raise AccessError(t("media", "asset_not_found", asset_id=asset_id))
    if not asset.get("file"):
        raise AccessError(t("mediaaccess", "no_file", id=asset_id))
    text, vtt = transcript(course, asset)
    video = course["_dir"] / str(asset["file"])
    out_text, out_vtt = video.with_suffix(".transcript.txt"), video.with_suffix(".descriptions.vtt")
    out_text.write_text(text, encoding="utf-8", newline="\n")
    out_vtt.write_text(vtt, encoding="utf-8", newline="\n")
    asset["transcript"] = text.strip()
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        ry.dump(data, fh)
    return {"transcript": out_text, "descriptions": out_vtt, "scenes": text.count("\n\n") + 1}
