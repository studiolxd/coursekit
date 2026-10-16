"""`coursekit video`: a video as data, a montage of scenes, rendered with the library of scenes of coursekit in Remotion.

A montage is `media/scripts/<id>.video.yaml`:

    version: 1
    format: {width: 1920, height: 1080, fps: 30}
    scenes:
      - id: opening
        type: title
        props: {kicker: "Unit 1", title: "Strong passwords", stress: "strong"}
        says: "Let us see what makes a password strong."
      - id: length
        type: split
        props: {title: "Length first", points: [{text: "At least 12 characters", say: "twelve characters"}], media: files/u1.png}
        says: "Length matters most: at least twelve characters."
      - id: close
        type: outro
        props: {title: "Long, unique, managed"}
        duration: 3                       # a scene without narration says how long it lasts

Each scene lasts what its voice lasts (`video voice` makes it and measures it), so changing a text changes the timing, not
the code. The scenes are those of the library (`tools/remotion/kit/`, written from the package), of the project
(`tools/remotion/src/scenes/<name>/`) and of the course (`courses/<CODE>/video/scenes/<name>/`): a scene of the course hides
one of the project with the same name, and one of the project hides one of the library. Each scene is a folder with
`index.tsx` and `scene.yaml` (what it is, its props, what it is built from); `video catalog` lists them all.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import yaml

from coursekit import course as coursemod
from coursekit import lang, mediaaccess, mediacheck, mediatools
from coursekit import media as mediamod
from coursekit import theme as thememod
from coursekit.i18n import t

VERSION = 1
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,39}$")
DEFAULT_FORMAT = {"width": 1920, "height": 1080, "fps": 30}
PAD = 0.5  # seconds of air after the narration of a scene
KIT = "kit"
COURSE_COPY = Path("src") / ".course"  # course scenes are rendered from a copy at the depth of the project scenes


class VideoError(Exception):
    pass


@dataclass
class Finding:
    level: str  # error | warning
    code: str
    where: str
    text: str


# ── where things are ─────────────────────────────────────────────────────────────────────────

def montage_file(course: dict, asset_id: str) -> Path:
    return course["_dir"] / "media" / "scripts" / f"{asset_id}.video.yaml"


def workspace(course: dict) -> Path:
    return course["_project"].root / "tools" / "remotion"


def voice_dir(course: dict, asset_id: str) -> Path:
    return course["_dir"] / "media" / "files" / asset_id


def kit_source() -> Path:
    return Path(str(resources.files("coursekit.videokit")))


# ── the scenes there are ─────────────────────────────────────────────────────────────────────

def _scene_folders(base: Path) -> dict[str, Path]:
    if not base.is_dir():
        return {}
    return {p.name: p for p in sorted(base.iterdir()) if p.is_dir() and NAME_RE.match(p.name) and (p / "index.tsx").exists()}


def _meta(folder: Path) -> dict:
    try:
        data = yaml.safe_load((folder / "scene.yaml").read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        data = {}
    return data if isinstance(data, dict) else {}


def scenes(course: dict) -> dict[str, dict]:
    """The scenes a montage of this course can use: name → {origin, folder, meta}, the course first, then the project."""
    found: dict[str, dict] = {}
    layers = (("library", kit_source() / "scenes"), ("project", workspace(course) / "src" / "scenes"),
              ("course", course["_dir"] / "video" / "scenes"))
    for origin, base in layers:
        for name, folder in _scene_folders(base).items():
            found[name] = {"origin": origin, "folder": folder, "meta": _meta(folder),
                           "hides": found[name]["origin"] if name in found else None}
    return found


def catalog(course: dict) -> list[str]:
    """The scenes, the atoms and the molecules, with their props and what each scene is built from."""
    lines = []
    for name, scene in sorted(scenes(course).items()):
        meta = scene["meta"]
        hides = t("video", "hides", origin=scene["hides"]) if scene["hides"] else ""
        lines.append(t("video", "catalog_scene", name=name, origin=scene["origin"], hides=hides,
                       description=meta.get("description") or "—"))
        if meta.get("built_from"):
            lines.append(t("video", "catalog_built", parts=", ".join(str(p) for p in meta["built_from"])))
        for prop, spec in (meta.get("props") or {}).items():
            spec = spec if isinstance(spec, dict) else {}
            bits = [str(spec.get("type") or "?")]
            bits += [t("video", "catalog_required")] if spec.get("required") else []
            bits += [t("video", "catalog_max", n=spec["max_chars"])] if spec.get("max_chars") else []
            bits += [t("video", "catalog_on_screen")] if spec.get("on_screen") else []
            lines.append(f"      {prop}: {', '.join(bits)}" + (f" — {spec['help']}" if spec.get("help") else ""))
    kit = kit_source()
    for kind in ("atoms", "molecules"):
        names = sorted(p.stem for p in (kit / kind).glob("*.tsx"))
        lines.append(t("video", f"catalog_{kind}", names=", ".join(names)))
    return lines


# ── reading and checking a montage ───────────────────────────────────────────────────────────

def load(course: dict, asset_id: str) -> dict:
    path = montage_file(course, asset_id)
    if not path.exists():
        raise VideoError(t("video", "no_montage", path=f"media/scripts/{asset_id}.video.yaml", code=course["code"], id=asset_id))
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise VideoError(t("video", "bad_yaml", path=path.name, error=str(exc).splitlines()[0])) from None
    if not isinstance(data, dict):
        raise VideoError(t("video", "bad_yaml", path=path.name, error="—"))
    return migrate(data)


def migrate(data: dict) -> dict:
    """The montage in the format of this version (a montage without `version` is of version 1)."""
    version = int(data.get("version") or VERSION)
    if version > VERSION:
        raise VideoError(t("video", "newer_version", version=version, supported=VERSION))
    data["version"] = VERSION
    return data


def _text(value) -> str:
    return "" if value is None else str(value)


def _texts_on_screen(props: dict, spec: dict, labels: bool = True) -> list[tuple[str, str]]:
    """(prop, text) of every prop the scene shows on screen, lists included; without `labels`, those marked `label` (a kicker,
    a tag: they need not be said)."""
    out = []
    for prop, rule in (spec or {}).items():
        rule = rule if isinstance(rule, dict) else {}
        value = props.get(prop)
        if rule.get("type") == "list" and isinstance(value, list):
            for item in value:
                for sub, sub_rule in (rule.get("items") or {}).items():
                    if isinstance(sub_rule, dict) and sub_rule.get("on_screen") and isinstance(item, dict) and item.get(sub) is not None \
                            and (labels or not sub_rule.get("label")):
                        out.append((f"{prop}.{sub}", _text(item[sub])))
        elif rule.get("on_screen") and value is not None and (labels or not rule.get("label")):
            out.append((prop, _text(value)))
    return out


def check(course: dict, asset_id: str) -> list[Finding]:
    """What is wrong in a montage, before its voice and its render: each finding says where and what."""
    data = load(course, asset_id)
    available = scenes(course)
    found: list[Finding] = []
    fmt = {**DEFAULT_FORMAT, **(data.get("format") or {})}
    if not all(isinstance(fmt[k], int) and fmt[k] > 0 for k in ("width", "height", "fps")):
        found.append(Finding("error", "FORMAT", "format", t("video", "bad_format")))
    items = data.get("scenes")
    if not isinstance(items, list) or not items:
        return [*found, Finding("error", "NO_SCENES", "scenes", t("video", "no_scenes"))]
    seen: set[str] = set()
    numbers = list(lang.tokens(coursemod.language(course)).get("number_words") or [])
    for n, scene in enumerate(items, 1):
        where = f"#{n}"
        if not isinstance(scene, dict):
            found.append(Finding("error", "SCENE", where, t("video", "bad_scene")))
            continue
        sid = _text(scene.get("id"))
        where = sid or where
        if not ID_RE.match(sid):
            found.append(Finding("error", "SCENE_ID", where, t("video", "bad_id", id=sid or "—")))
        elif sid in seen:
            found.append(Finding("error", "SCENE_ID", where, t("video", "repeated_id", id=sid)))
        seen.add(sid)
        kind = _text(scene.get("type"))
        if kind not in available:
            found.append(Finding("error", "UNKNOWN_SCENE", where, t("video", "unknown_scene", type=kind or "—",
                                                                   known=", ".join(sorted(available)))))
            continue
        spec = available[kind]["meta"].get("props") or {}
        props = scene.get("props") or {}
        if not isinstance(props, dict):
            found.append(Finding("error", "PROPS", where, t("video", "bad_props")))
            continue
        for prop, rule in spec.items():
            rule = rule if isinstance(rule, dict) else {}
            value = props.get(prop)
            if rule.get("required") and value in (None, "", []):
                found.append(Finding("error", "PROP_MISSING", where, t("video", "prop_missing", prop=prop)))
            if rule.get("type") == "media" and value and not re.match(r"^https?:", str(value)):
                if not (course["_dir"] / "media" / str(value)).exists():
                    found.append(Finding("error", "MEDIA_MISSING", where, t("video", "media_missing", prop=prop, path=f"media/{value}")))
            if rule.get("type") == "list" and isinstance(value, list) and rule.get("max_items") and len(value) > int(rule["max_items"]):
                found.append(Finding("warning", "TOO_MANY", where, t("video", "too_many", prop=prop, n=len(value), max=rule["max_items"])))
        for prop in props:
            if prop not in spec and spec:
                found.append(Finding("warning", "UNKNOWN_PROP", where, t("video", "unknown_prop", prop=prop, type=kind)))
        for prop, text in _texts_on_screen(props, spec):
            base = prop.split(".")[0]
            rule = spec.get(base) or {}
            limit = (rule.get("items") or {}).get(prop.split(".")[1], {}).get("max_chars") if "." in prop else rule.get("max_chars")
            if limit and len(text) > int(limit):
                found.append(Finding("warning", "TEXT_LONG", where, t("video", "text_long", prop=prop, n=len(text), max=limit)))
        says = _text(scene.get("says")).strip()
        if not says and not scene.get("duration"):
            found.append(Finding("error", "NO_DURATION", where, t("video", "no_duration")))
        if not scene.get("shows"):  # what is on screen is also said (a silent scene describes it with `shows`)
            for prop, text in _texts_on_screen(props, spec, labels=False):
                if not mediaaccess.said(text, says, numbers):
                    found.append(Finding("warning", "NOT_SAID", where, t("video", "not_said", prop=prop, text=text)))
    return found


# ── the voice ────────────────────────────────────────────────────────────────────────────────

def _hash(*parts: str) -> str:
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()[:16]


def _voice_record(course: dict, asset_id: str) -> dict:
    path = voice_dir(course, asset_id) / "voice.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def voice(course: dict, asset_id: str, say=print) -> int:
    """The narration of each scene, with the timings of its words; only what changed is made again. How many were made."""
    from coursekit import voices

    data = load(course, asset_id)
    folder = voice_dir(course, asset_id)
    folder.mkdir(parents=True, exist_ok=True)
    record = _voice_record(course, asset_id)
    language = coursemod.language(course)
    try:
        provider = voices.resolve(course)[0]
    except voices.VoiceError as exc:
        raise VideoError(str(exc)) from None
    made = 0
    for scene in data.get("scenes") or []:
        says = _text(scene.get("says")).strip() if isinstance(scene, dict) else ""
        if not says:
            continue
        sid = str(scene["id"])
        key = _hash(says, provider, json.dumps(voices.course_voice(course), sort_keys=True))
        audio, words = folder / f"{sid}.mp3", folder / f"{sid}.words.json"
        if record.get(sid, {}).get("key") == key and audio.exists() and words.exists():
            continue
        text = folder / f"{sid}.txt"
        text.write_text(says + "\n", encoding="utf-8")
        words.unlink(missing_ok=True)
        try:
            mediatools.tts(course, None, text, audio)
            if not words.exists():  # ElevenLabs writes its words with the audio; the other voices are aligned with stable-ts
                mediatools.subtitles(audio, text, folder / f"{sid}.vtt", language=language)
        except (mediatools.ToolError, voices.VoiceError) as exc:
            raise VideoError(t("video", "voice_failed", scene=sid, error=exc)) from None
        record[sid] = {"key": key, "seconds": mediacheck.duration(audio)}
        say(t("video", "voice_made", scene=sid, seconds=f"{record[sid]['seconds']:.1f}"))
        made += 1
    (folder / "voice.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8", newline="\n")
    return made


# ── the montage resolved: what Remotion renders ──────────────────────────────────────────────

def _words(path: Path) -> list[dict]:
    try:
        return list(json.loads(path.read_text(encoding="utf-8")).get("words") or [])
    except (OSError, ValueError):
        return []


def resolve(course: dict, asset_id: str) -> dict:
    """Frames of each scene (its voice, or its `duration`), the tokens of the theme and everything a scene needs."""
    data = load(course, asset_id)
    errors = [f for f in check(course, asset_id) if f.level == "error"]
    if errors:
        raise VideoError(t("video", "has_errors", count=len(errors), code=course["code"], id=asset_id))
    fmt = {**DEFAULT_FORMAT, **(data.get("format") or {})}
    fps = int(fmt["fps"])
    record = _voice_record(course, asset_id)
    folder = voice_dir(course, asset_id)
    try:
        tokens = thememod.load(course["_project"], course)
    except thememod.ThemeError as exc:
        raise VideoError(str(exc)) from None
    resolved, cursor = [], 0
    for scene in data["scenes"]:
        sid = str(scene["id"])
        says = _text(scene.get("says")).strip()
        props = dict(scene.get("props") or {})
        if scene.get("type") == "screencast" and props.get("recording") and "events" not in props:
            events = (course["_dir"] / "media" / str(props["recording"])).with_suffix(".events.json")
            if events.exists():
                props["events"] = json.loads(events.read_text(encoding="utf-8")).get("events") or []
        if says:
            if sid not in record or not (folder / f"{sid}.mp3").exists():
                raise VideoError(t("video", "voice_pending", scene=sid, code=course["code"], id=asset_id))
            seconds = float(record[sid]["seconds"]) + PAD
            audio, words = f"files/{asset_id}/{sid}.mp3", _words(folder / f"{sid}.words.json")
        else:
            seconds, audio, words = float(scene.get("duration") or 3), None, []
        if scene.get("duration") and says:
            seconds = max(seconds, float(scene["duration"]))
        frames = max(1, round(seconds * fps))
        resolved.append({"id": sid, "type": str(scene["type"]), "from": cursor, "frames": frames, "props": props, "audio": audio,
                         "words": words, "says": says})
        cursor += frames
    return {"fps": fps, "width": int(fmt["width"]), "height": int(fmt["height"]), "frames": cursor,
            "tokens": {k: tokens[k] for k in ("color", "font", "radius", "space") if k in tokens},
            "motion": {"enter": 18, "stagger": 6, "fade": 10, "damping": 18, **(data.get("motion") or {})},
            "scenes": resolved}


# ── the workspace of Remotion ────────────────────────────────────────────────────────────────

def sync(course: dict) -> Path:
    """The library in tools/remotion/kit/ (from the package, never edited there), the copies of the scenes of the course and
    the registry of the scenes that win. Returns the workspace."""
    root = workspace(course)
    if not (root / "node_modules").exists():
        raise VideoError(t("video", "no_workspace"))
    kit = root / KIT
    source = kit_source()
    shutil.rmtree(kit, ignore_errors=True)
    shutil.copytree(source, kit, ignore=shutil.ignore_patterns("__init__.py", "__pycache__"))
    (kit / "README.md").write_text(t("video", "kit_readme") + "\n", encoding="utf-8")
    copies = root / COURSE_COPY
    shutil.rmtree(copies, ignore_errors=True)
    lines, names = [], []
    for name, scene in sorted(scenes(course).items()):
        if scene["origin"] == "library":
            path = f"./scenes/{name}"
        elif scene["origin"] == "project":
            path = f"../src/scenes/{name}"
        else:
            target = copies / f"{course['code'].lower()}-{name}"
            shutil.copytree(scene["folder"], target)
            path = f"../{COURSE_COPY.as_posix()}/{target.name}"
        ident = "s_" + re.sub(r"[^a-z0-9]", "_", name)
        lines.append(f'import {ident} from "{path}";')
        names.append(f'"{name}": {ident}')
    (kit / "registry.generated.ts").write_text(
        "// Written by coursekit (`coursekit video …`): the scenes of the library, the project and the course that win. Do not edit.\n"
        'import type React from "react";\nimport type { SceneProps } from "./contract";\n' + "\n".join(lines) +
        "\n\n// eslint-disable-next-line @typescript-eslint/no-explicit-any\n"
        f"export const scenes: Record<string, React.FC<SceneProps<any>>> = {{ {', '.join(names)} }};\n", encoding="utf-8", newline="\n")
    return root


def _remotion(root: Path, args: list[str]) -> None:
    exe = root / "node_modules" / ".bin" / ("remotion.cmd" if os.name == "nt" else "remotion")
    if not exe.exists():
        raise VideoError(t("video", "no_workspace"))
    done = subprocess.run([str(exe), *args], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if done.returncode != 0:
        tail = [line for line in (done.stderr or done.stdout).strip().splitlines() if line.strip()][-6:]
        raise VideoError(t("video", "render_failed", reason=" | ".join(tail) or "?"))


def _props_file(course: dict, asset_id: str, resolved: dict) -> Path:
    path = course["_project"].cache_dir / "video" / course["code"] / f"{asset_id}.props.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(resolved, ensure_ascii=False), encoding="utf-8")
    return path


def preview(course: dict, asset_id: str) -> Path:
    """A frame of each scene (at 70 % of it, when what enters has entered) in one image, rendered small, before the whole video."""
    from PIL import Image

    resolved = resolve(course, asset_id)
    root = sync(course)
    props = _props_file(course, asset_id, resolved)
    media = course["_dir"] / "media"
    out = course["_project"].cache_dir / "media" / course["code"] / f"{asset_id}-preview.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        frames = []
        for scene in resolved["scenes"]:
            still = Path(tmp) / f"{scene['id']}.png"
            _remotion(root, ["still", f"{KIT}/entry.ts", "Montage", str(still), f"--props={props}", f"--public-dir={media}",
                             f"--frame={scene['from'] + int(scene['frames'] * 0.7)}", "--scale=0.25", "--log=error"])
            frames.append(Image.open(still).convert("RGB"))
        width, height = frames[0].size
        columns = min(4, len(frames))
        rows = -(-len(frames) // columns)
        sheet = Image.new("RGB", (columns * (width + 8) + 8, rows * (height + 8) + 8), (40, 40, 40))
        for i, frame in enumerate(frames):
            sheet.paste(frame, (8 + (i % columns) * (width + 8), 8 + (i // columns) * (height + 8)))
        sheet.save(out)
    return out


def _captions(resolved: dict) -> tuple[str, list[dict]]:
    """The VTT of the whole video (a cue per sentence of each scene) and its words, in seconds of the video."""
    fps, cues, every = resolved["fps"], [], []
    for scene in resolved["scenes"]:
        start = scene["from"] / fps
        words = [{"w": w["w"], "start": round(start + float(w["start"]), 3), "end": round(start + float(w["end"]), 3)}
                 for w in scene["words"]]
        every += words
        sentence: list[dict] = []
        for w in words:
            sentence.append(w)
            if re.search(r"[.!?…:;]$", w["w"]) or len(" ".join(x["w"] for x in sentence)) > 70:
                cues.append((sentence[0]["start"], sentence[-1]["end"], " ".join(x["w"] for x in sentence)))
                sentence = []
        if sentence:
            cues.append((sentence[0]["start"], sentence[-1]["end"], " ".join(x["w"] for x in sentence)))
    lines = ["WEBVTT", ""]
    for i, (a, b, text) in enumerate(cues, 1):
        # a caption stays until the next one starts (up to 1.5 s more): the voice is quicker than reading
        following = cues[i][0] if i < len(cues) else b + 1.5
        end = max(a + 0.5, min(max(b, following - 0.05), b + 1.5))
        lines += [str(i), f"{mediatools.vtt_time(a)} --> {mediatools.vtt_time(end)}", text, ""]
    return "\n".join(lines), every


def render(course: dict, asset_id: str) -> dict:
    """The video, its captions, its words, its scenes described and its accessible transcript; the asset becomes produced."""
    resolved = resolve(course, asset_id)
    root = sync(course)
    props = _props_file(course, asset_id, resolved)
    media = course["_dir"] / "media"
    out = media / "files" / f"{asset_id}.mp4"
    _remotion(root, ["render", f"{KIT}/entry.ts", "Montage", str(out), f"--props={props}", f"--public-dir={media}", "--log=error"])
    vtt, words = _captions(resolved)
    out.with_suffix(".vtt").write_text(vtt, encoding="utf-8", newline="\n")
    mediatools.write_words([{"w": w["w"], "start": w["start"], "end": w["end"]} for w in words], mediatools.words_path(out))
    available = scenes(course)
    described = []
    for scene, raw in zip(resolved["scenes"], load(course, asset_id)["scenes"], strict=True):
        spec = available.get(scene["type"], {}).get("meta", {}).get("props") or {}
        everything = _texts_on_screen(scene["props"], spec)
        told = _texts_on_screen(scene["props"], spec, labels=False)
        item = {"at": round(scene["from"] / resolved["fps"], 3), "labels": [x for _, x in everything if (_, x) not in told],
                "text": [x for _, x in told], "says": scene["says"]}
        if raw.get("shows"):
            item["shows"] = raw["shows"]
        described.append(item)
    scenes_path = mediaaccess.scenes_file(course, asset_id)
    scenes_path.write_text(yaml.safe_dump({"words": f"media/files/{asset_id}.words.json", "scenes": described},
                                          allow_unicode=True, sort_keys=False), encoding="utf-8")
    _, _, manifest = mediamod.load_manifest(course["_dir"])
    asset = next(a for a in manifest["assets"] if str(a["id"]) == asset_id)
    recording = any(s["type"] == "screencast" and s["props"].get("recording") for s in resolved["scenes"])
    # what shows a real interface can only come from a real recording: a montage with one is a screen recording composed
    recipe = "screen-recording" if asset.get("depicts") == "interface" and recording else "montage"
    local_captions = f"media/files/{out.with_suffix('.vtt').name}" if coursemod.backend(course) == "html" else None
    try:
        mediamod.set_asset(course, asset_id, status="produced", recipe=recipe, file=f"media/files/{out.name}",
                           subtitles_path=local_captions, made_with="coursekit video")
    except mediamod.MediaError as exc:
        raise VideoError(str(exc)) from None
    mediaaccess.write(course, asset_id)
    return {"video": out, "seconds": resolved["frames"] / resolved["fps"], "scenes": len(resolved["scenes"])}


def new(course: dict, asset_id: str) -> Path:
    """A first montage for a video resource: an opening with its title, a scene to fill and a close."""
    _, _, data = mediamod.load_manifest(course["_dir"])
    asset = next((a for a in data["assets"] if str(a["id"]) == asset_id), None)
    if asset is None:
        raise VideoError(t("media", "asset_not_found", asset_id=asset_id))
    path = montage_file(course, asset_id)
    if path.exists():
        raise VideoError(t("video", "exists", path=f"media/scripts/{path.name}"))
    title = str(asset.get("title") or asset_id)
    skeleton = {"version": VERSION, "format": dict(DEFAULT_FORMAT), "scenes": [
        {"id": "opening", "type": "title", "props": {"title": title}, "says": ""},
        {"id": "idea", "type": "split", "props": {"title": "", "points": []}, "says": ""},
        {"id": "close", "type": "outro", "props": {"title": ""}, "duration": 3}]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(t("video", "skeleton_header") + "\n" + yaml.safe_dump(skeleton, allow_unicode=True, sort_keys=False),
                    encoding="utf-8", newline="\n")
    return path
