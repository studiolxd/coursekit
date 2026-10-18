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
import sys
import tempfile
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import yaml

from coursekit import config as configmod
from coursekit import course as coursemod
from coursekit import i18n, lang, mediaaccess, mediacheck, mediatools
from coursekit import media as mediamod
from coursekit import theme as thememod
from coursekit.i18n import t

VERSION = 1
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,39}$")
DEFAULT_FORMAT = {"width": 1920, "height": 1080, "fps": 30}
MOTION = {"calm": {"enter": 26, "stagger": 10, "fade": 14, "damping": 28},
          "balanced": {"enter": 18, "stagger": 6, "fade": 10, "damping": 18},
          "lively": {"enter": 11, "stagger": 4, "fade": 6, "damping": 11},
          "none": {"enter": 0, "stagger": 0, "fade": 10, "damping": 18}}  # no movement inside a scene; the fade between scenes stays
ENTRANCES = ("auto", "fade", "rise", "slide", "scale", "none")
STRESSES = ("underline", "highlight", "colour")
TRANSITIONS = ("cut", "fade", "dip", "push", "wipe")  # how one scene gives way to the next (config/video.yaml › transition)
DIRECTIONS = ("left", "right", "up", "down")  # how a scene marks its stressed word (config/video.yaml › stress)
OVERRIDABLE = ("atoms", "molecules")
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


PROJECT_SCOPE = "project"  # the folder in .cache/media/ of the gallery of the project (the codes of the courses are in capitals)


def project_scope(project) -> dict:
    """The project as a course with nothing of its own, for the gallery and the catalog of the project: its theme, its style
    (config/video.yaml), its scenes and those of the library, before any course exists or changes them."""
    data = configmod.project_data(project)
    return {"code": PROJECT_SCOPE, "_label": str(data.get("name") or project.root.name), "_project": project,
            "_dir": project.root / ".coursekit" / "project-scope", "language": data.get("content_language") or "es"}


def workspace(course: dict) -> Path:
    return course["_project"].root / "tools" / "remotion"


def voice_dir(course: dict, asset_id: str) -> Path:
    return course["_dir"] / "media" / "files" / asset_id


def kit_source() -> Path:
    return Path(str(resources.files("coursekit.videokit")))


# ── the scenes there are ─────────────────────────────────────────────────────────────────────

META = {"scenes": "scene.yaml", "layers": "layer.yaml"}


def _folders(base: Path) -> dict[str, Path]:
    if not base.is_dir():
        return {}
    return {p.name: p for p in sorted(base.iterdir()) if p.is_dir() and NAME_RE.match(p.name) and (p / "index.tsx").exists()}


def _meta(folder: Path, kind: str = "scenes") -> dict:
    try:
        data = yaml.safe_load((folder / META[kind]).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        data = {}
    return data if isinstance(data, dict) else {}


def localized(value: object, language: str | None = None) -> str:
    """A text of the metadata of a piece (its `description`, the `help` of a prop): one string, or one per language (`en:`,
    `es:`); the language of the person, else English."""
    if isinstance(value, dict):
        value = value.get(language or i18n.language()) or value.get("en") or next(iter(value.values()), "")
    return str(value or "")


def origin_label(origin: str) -> str:
    return t("video", f"origin_{origin}")


def pieces(course: dict, kind: str = "scenes") -> dict[str, dict]:
    """The scenes (or the layers) a montage of this course can use: name → {origin, folder, meta, hides}; the course wins
    over the project, and the project over the library."""
    found: dict[str, dict] = {}
    layers = (("library", kit_source() / kind), ("project", workspace(course) / "src" / kind),
              ("course", course["_dir"] / "video" / kind))
    for origin, base in layers:
        for name, folder in _folders(base).items():
            found[name] = {"origin": origin, "folder": folder, "meta": _meta(folder, kind),
                           "hides": found[name]["origin"] if name in found else None}
    return found


def scenes(course: dict) -> dict[str, dict]:
    return pieces(course, "scenes")


def overrides(course: dict) -> list[tuple[str, str, str, Path]]:
    """The atoms and molecules the project (`tools/remotion/src/atoms|molecules/<Name>.tsx`) or the course
    (`video/atoms|molecules/<Name>.tsx`) puts in place of the library's: (kind, name, origin, file); the course wins."""
    winners: dict[tuple[str, str], tuple[str, Path]] = {}
    library = kit_source()
    for origin, base in (("project", workspace(course) / "src"), ("course", course["_dir"] / "video")):
        for kind in OVERRIDABLE:
            for path in sorted((base / kind).glob("*.tsx")) if (base / kind).is_dir() else []:
                shown = path.relative_to(course["_project"].root).as_posix()
                if not (library / kind / path.name).exists():
                    raise VideoError(t("video", "override_unknown", kind=kind, name=path.stem, path=shown))
                if f"export const {path.stem}" not in path.read_text(encoding="utf-8"):
                    raise VideoError(t("video", "override_export", name=path.stem, path=shown))
                winners[(kind, path.stem)] = (origin, path)
    return [(kind, name, origin, path) for (kind, name), (origin, path) in sorted(winners.items())]


def catalog(course: dict) -> list[str]:
    """The scenes, the atoms and the molecules, with their props and what each scene is built from."""
    lines = []
    for kind in ("scenes", "layers"):
        lines.append(t("video", f"catalog_{kind}"))
        found = pieces(course, kind)
        off = sorted(name for name, piece in found.items() if piece_rules(course, name, piece["meta"].get("props") or {})["off"])
        lines += _catalog_lines({n: p for n, p in found.items() if n not in off}, course)
        if off:
            lines.append(t("video", "catalog_off", names=", ".join(off)))
    kit = kit_source()
    replaced = {(kind, name): origin for kind, name, origin, _ in overrides(course)}
    for kind in OVERRIDABLE:
        names = [p.stem + (f" [{origin_label(replaced[(kind, p.stem)])}]" if (kind, p.stem) in replaced else "")
                 for p in sorted((kit / kind).glob("*.tsx"))]
        lines.append(t("video", f"catalog_{kind}", names=", ".join(names)))
    return lines


def _catalog_lines(found: dict[str, dict], course: dict | None = None) -> list[str]:
    lines = []
    for name, scene in sorted(found.items()):
        meta = scene["meta"]
        props = meta.get("props") or {}
        if course is not None:  # what the project and the course allow of it
            props = allowed_spec(props, piece_rules(course, name, props))
        hides = t("video", "hides", origin=origin_label(scene["hides"])) if scene["hides"] else ""
        lines.append(t("video", "catalog_scene", name=name, origin=origin_label(scene["origin"]), hides=hides,
                       description=localized(meta.get("description")) or "—"))
        if meta.get("built_from"):
            lines.append(t("video", "catalog_built", parts=", ".join(str(p) for p in meta["built_from"])))
        for prop, spec in props.items():
            spec = spec if isinstance(spec, dict) else {}
            bits = [str(spec.get("type") or "?")]
            bits += [t("video", "catalog_values", values=" | ".join(str(v) for v in spec["values"]))] if spec.get("values") else []
            bits += [t("video", "catalog_default", value=spec["default"])] if "default" in spec else []
            bits += [t("video", "catalog_required")] if spec.get("required") else []
            bits += [t("video", "catalog_max", n=spec["max_chars"])] if spec.get("max_chars") else []
            bits += [t("video", "catalog_on_screen")] if spec.get("on_screen") else []
            lines.append(f"      {prop}: {', '.join(bits)}" + (f" — {localized(spec['help'])}" if spec.get("help") else ""))
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


def _walk(value, rule: dict, path: str, out: list) -> None:
    rule = rule if isinstance(rule, dict) else {}
    kind = rule.get("type")
    if kind == "object" and isinstance(value, dict):
        for name, sub in (rule.get("fields") or {}).items():
            if value.get(name) is not None:
                _walk(value[name], sub, f"{path}.{name}", out)
    elif kind == "list" and isinstance(value, list):
        for i, item in enumerate(value):
            if rule.get("items") and isinstance(item, dict):
                for name, sub in rule["items"].items():
                    if item.get(name) is not None:
                        _walk(item[name], sub, f"{path}[{i}].{name}", out)
            elif rule.get("on_screen") and not isinstance(item, (dict, list)):
                out.append((f"{path}[{i}]", _text(item), rule.get("items_max_chars"), bool(rule.get("label"))))
    elif rule.get("on_screen") and not isinstance(value, (dict, list)):
        out.append((path, _text(value), rule.get("max_chars"), bool(rule.get("label"))))


def on_screen(props: dict, spec: dict) -> list[tuple[str, str, int | None, bool]]:
    """(where, text, maximum characters, is a label) of everything a scene shows on screen, nested props included."""
    out: list = []
    for prop, rule in (spec or {}).items():
        if props.get(prop) is not None:
            _walk(props[prop], rule, prop, out)
    return out


def _texts_on_screen(props: dict, spec: dict, labels: bool = True) -> list[tuple[str, str]]:
    """(where, text) of what a scene shows on screen; without `labels`, not those marked `label` (they need not be said)."""
    return [(where, text) for where, text, _, label in on_screen(props, spec) if labels or not label]


def check(course: dict, asset_id: str) -> list[Finding]:
    """What is wrong in a montage, before its voice and its render: each finding says where and what."""
    data = load(course, asset_id)
    available = scenes(course)
    found: list[Finding] = []
    fmt = {**DEFAULT_FORMAT, **(style(course).get("format") or {}), **(data.get("format") or {})}
    if not all(isinstance(fmt[k], int) and fmt[k] > 0 for k in ("width", "height", "fps")):
        found.append(Finding("error", "FORMAT", "format", t("video", "bad_format")))
    items = data.get("scenes")
    if not isinstance(items, list) or not items:
        return [*found, Finding("error", "NO_SCENES", "scenes", t("video", "no_scenes"))]
    seen: set[str] = set()
    found += rule_problems(course) + text_problems(course)
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
        found += rule_findings(course, "scenes", kind, spec, props, where)
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
        for prop, text, limit, _ in on_screen(props, spec):
            if limit and len(text) > int(limit):
                found.append(Finding("warning", "TEXT_LONG", where, t("video", "text_long", prop=prop, n=len(text), max=limit)))
        says = _text(scene.get("says")).strip()
        found += _check_layers(course, scene, where, says, numbers)
        if n > 1:
            found += _check_transition(course, scene, items[n - 2], where, fmt)
        if not says and not scene.get("duration"):
            found.append(Finding("error", "NO_DURATION", where, t("video", "no_duration")))
        if not scene.get("shows"):  # what is on screen is also said (a silent scene describes it with `shows`)
            for prop, text in _texts_on_screen(props, spec, labels=False):
                if not mediaaccess.said(text, says, numbers):
                    found.append(Finding("warning", "NOT_SAID", where, t("video", "not_said", prop=prop, text=text)))
    return found


def _check_layers(course: dict, scene: dict, where: str, says: str, numbers: list[str]) -> list[Finding]:
    found, available = [], pieces(course, "layers")
    for n, layer in enumerate(scene.get("layers") or [], 1):
        here = f"{where}/{layer.get('id') or n}" if isinstance(layer, dict) else f"{where}/{n}"
        if not isinstance(layer, dict) or _text(layer.get("type")) not in available:
            kind = _text(layer.get("type")) if isinstance(layer, dict) else "—"
            found.append(Finding("error", "UNKNOWN_LAYER", here, t("video", "unknown_layer", type=kind or "—",
                                                                   known=", ".join(sorted(available)))))
            continue
        spec = available[layer["type"]]["meta"].get("props") or {}
        props = layer.get("props") or {}
        found += rule_findings(course, "layers", str(layer["type"]), spec, props if isinstance(props, dict) else {}, here)
        for prop, rule in spec.items():
            if isinstance(rule, dict) and rule.get("required") and props.get(prop) in (None, "", []):
                found.append(Finding("error", "PROP_MISSING", here, t("video", "prop_missing", prop=prop)))
        for key in ("at", "until"):
            if layer.get(key) and not says_phrase(says, str(layer[key])):
                found.append(Finding("warning", "ANCHOR_NOT_SAID", here, t("video", "anchor_not_said", key=key, phrase=layer[key])))
        for prop, text, limit, label in on_screen(props, spec):
            if limit and len(text) > int(limit):
                found.append(Finding("warning", "TEXT_LONG", here, t("video", "text_long", prop=prop, n=len(text), max=limit)))
            if not label and not scene.get("shows") and not mediaaccess.said(text, says, numbers):
                found.append(Finding("warning", "NOT_SAID", here, t("video", "not_said", prop=prop, text=text)))
    return found


def style(course: dict) -> dict:
    """The style of the videos of this course (config/video.yaml, and its `video:` section of course.yaml)."""
    return dict(configmod.effective("video", course["_project"], course).value)


# ── what the project and the course allow of each piece ───────────────────────────────────────

def piece_rules(course: dict, name: str, spec: dict) -> dict:
    """What the project (config/video.yaml › scenes) and the course (course.yaml › video › scenes) allow of a scene or a layer:
    {"off", "allow": {prop: [values]}, "defaults": {prop: value}}. `"*"` is for every piece that has the prop; the piece's own
    rule wins over it; `<name>: false` leaves the piece out."""
    block = style(course).get("scenes") or {}
    out: dict = {"off": False, "allow": {}, "defaults": {}}
    for key in ("*", name):
        rule = block.get(key) if isinstance(block, dict) else None
        if rule is False and key == name:
            out["off"] = True
        if not isinstance(rule, dict):
            continue
        for prop, values in (rule.get("allow") or {}).items():
            if prop in spec:
                out["allow"][prop] = list(values) if isinstance(values, list) else [values]  # as written: a boolean stays one
        for prop, value in (rule.get("defaults") or {}).items():
            if prop in spec:
                out["defaults"][prop] = value
    return out


def _key(value: object) -> str:
    """A value of a prop as the rules compare it: `false` in the YAML and `false` in a script are the same value."""
    return str(value).lower() if isinstance(value, bool) else str(value)


def allowed_spec(spec: dict, rules: dict) -> dict:
    """The props of a piece as the project allows them: each choice with only its allowed values, and the default it takes."""
    out = {}
    for prop, rule in spec.items():
        rule = dict(rule) if isinstance(rule, dict) else {}
        allow = rules["allow"].get(prop)
        if allow is not None and rule.get("type") == "choice":
            rule["values"] = [v for v in rule.get("values") or [] if _key(v) in map(_key, allow)]
        if prop in rules["defaults"]:
            rule["default"] = rules["defaults"][prop]
        out[prop] = rule
    return out


def with_defaults(props: dict, rules: dict) -> dict:
    """The props of a piece with what the project fixes when the script says nothing: its default, or the one value allowed."""
    out = dict(props)
    for prop, allow in rules["allow"].items():
        if out.get(prop) in (None, "") and prop not in rules["defaults"] and len(allow) == 1:
            out[prop] = allow[0]
    for prop, value in rules["defaults"].items():
        if out.get(prop) in (None, ""):
            out[prop] = value
    return out


def rule_findings(course: dict, kind: str, name: str, spec: dict, props: dict, where: str) -> list[Finding]:
    """A piece the project leaves out, or a value it does not allow: an error that stops the render, a warning in the handoff
    (which renders and lists it in its log)."""
    level = "warning" if os.environ.get("COURSEKIT_HANDOFF") == "1" else "error"
    rules = piece_rules(course, name, spec)
    found = []
    if rules["off"]:
        found.append(Finding(level, "PIECE_OFF", where, t("video", "piece_off", kind=t("video", f"gallery_{kind}"), name=name)))
    for prop, allow in rules["allow"].items():
        value = with_defaults(props, rules).get(prop)
        if value not in (None, "") and _key(value) not in map(_key, allow):
            found.append(Finding(level, "NOT_ALLOWED", where, t("video", "not_allowed", prop=prop, value=_key(value),
                                                                allowed=", ".join(map(_key, allow)))))
    return found


def rule_report(course: dict) -> list[tuple[str, Finding]]:
    """(video, finding) of every montage of the course that uses a piece the project leaves out or a value it does not allow."""
    out = []
    for path in sorted((course["_dir"] / "media" / "scripts").glob("*.video.yaml")):
        asset_id = path.name.removesuffix(".video.yaml")
        try:
            out += [(asset_id, f) for f in check(course, asset_id) if f.code in ("PIECE_OFF", "NOT_ALLOWED")]
        except VideoError:
            continue
    return out


def rule_problems(course: dict) -> list[Finding]:
    """A rule of config/video.yaml › scenes that leaves a prop without any value its piece has."""
    found = []
    for kind in ("scenes", "layers"):
        for name, piece in pieces(course, kind).items():
            spec = piece["meta"].get("props") or {}
            rules = piece_rules(course, name, spec)
            for prop, rule in allowed_spec(spec, rules).items():
                if prop in rules["allow"] and rule.get("type") == "choice" and not rule.get("values"):
                    found.append(Finding("warning", "RULE_EMPTY", f"config/video.yaml › scenes › {name}",
                                         t("video", "rule_empty", prop=prop, name=name)))
    return found


def motion(course: dict, data: dict) -> dict:
    """The motion: the preset of `motion.character`, what the style sets one by one, and what the montage sets."""
    cfg = dict(style(course).get("motion") or {})
    preset = MOTION.get(str(cfg.get("character") or "balanced"), MOTION["balanced"])
    own = {k: int(v) for k, v in cfg.items() if k in MOTION["balanced"] and v is not None}
    entrance = str(cfg.get("entrance") or "auto")
    return {**preset, **own, **{k: int(v) for k, v in (data.get("motion") or {}).items() if k in MOTION["balanced"]},
            "entrance": entrance if entrance in ENTRANCES else "auto"}


def transition_setting(course: dict) -> dict:
    """The transitions of the project (config/video.yaml › transition): the type, the frames (None: those of motion.fade), the
    direction and the types a script may ask for (empty: all)."""
    cfg = style(course).get("transition")
    cfg = cfg if isinstance(cfg, dict) else {}
    frames = cfg.get("frames")
    return {"type": str(cfg.get("type") or "auto"), "frames": int(frames) if isinstance(frames, (int, float)) else None,
            "direction": str(cfg.get("direction") or "left"), "allow": [str(v) for v in (cfg.get("allow") or [])]}


def _asked_transition(scene: dict) -> dict:
    """What a scene of the script asks for its entrance: `transition: fade` or `transition: {type: push, direction: up}`."""
    raw = scene.get("transition")
    return {"type": raw} if isinstance(raw, str) else dict(raw) if isinstance(raw, dict) else {}


def _ground(course: dict, kind: str, props: dict) -> tuple[str, str]:
    """What a scene is drawn on, to tell whether two scenes share their background."""
    background = str(props.get("background") or ("accent" if kind == "outro" else style(course).get("background") or "shape"))
    return background, str(props.get("photo") or "") if background == "photo" else ""


def _check_transition(course: dict, scene: dict, before: object, where: str, fmt: dict) -> list[Finding]:
    """The entrance a scene asks for: a type that exists and the project allows, and one that does not eat the voice of the scene
    before (longer than the margin after its narration, the two voices would overlap)."""
    asked = _asked_transition(scene)
    kind = str(asked.get("type") or "")
    level = "warning" if os.environ.get("COURSEKIT_HANDOFF") == "1" else "error"
    setting = transition_setting(course)
    found = []
    if kind and kind not in (*TRANSITIONS, "auto"):
        found.append(Finding("error", "TRANSITION", where, t("video", "transition_unknown", type=kind, known=", ".join(TRANSITIONS))))
    elif kind and setting["allow"] and kind not in setting["allow"]:
        found.append(Finding(level, "NOT_ALLOWED", where, t("video", "not_allowed", prop="transition", value=kind,
                                                            allowed=", ".join(setting["allow"]))))
    look = style(course)
    pad = float(look.get("pad_seconds") if look.get("pad_seconds") is not None else 0.5)
    frames = setting["frames"] if setting["frames"] is not None else motion(course, {})["fade"]
    said_before = isinstance(before, dict) and _text(before.get("says")).strip()
    if said_before and kind != "cut" and frames > pad * int(fmt["fps"]):
        found.append(Finding("warning", "TRANSITION_LONG", where, t("video", "transition_long", frames=frames,
                                                                   pad=round(pad * int(fmt["fps"])))))
    return found


def transition_for(course: dict, before: dict, scene: dict, fade: int) -> dict:
    """How `scene` (resolved: its type and props) enters after `before`: the type (auto picks by the two scenes), its frames and
    its direction."""
    setting = transition_setting(course)
    asked = _asked_transition(scene)
    kind = str(asked.get("type") or setting["type"])
    if kind == "auto":
        same = _ground(course, before["type"], before["props"]) == _ground(course, scene["type"], scene["props"])
        kind = "wipe" if scene["type"] == "chapter" else "fade" if scene["type"] == "outro" or same else "dip"
    kind = kind if kind in TRANSITIONS else "dip"
    direction = str(asked.get("direction") or setting["direction"])
    frames = 0 if kind == "cut" else setting["frames"] if setting["frames"] is not None else fade
    return {"type": kind, "frames": max(0, int(frames)), "direction": direction if direction in DIRECTIONS else "left"}


def _progress(look: dict) -> dict:
    """The bars that show an advance (config/video.yaml › progress)."""
    cfg = look.get("progress") if isinstance(look.get("progress"), dict) else {}
    height = cfg.get("height")
    return {"track": str(cfg.get("track") or "border"), "fill": str(cfg.get("fill") or "accent-ink"), "outline": cfg.get("outline") is True,
            "height": float(height) if isinstance(height, (int, float)) and not isinstance(height, bool) and height > 0 else 10}


def _chart(look: dict) -> dict:
    """The look of the charts (config/video.yaml › chart), with what is missing or wrong left to the defaults of the package."""
    cfg = look.get("chart") if isinstance(look.get("chart"), dict) else {}
    series = [str(c) for c in (cfg.get("series") or []) if c] or ["accent"]
    number = lambda v, fallback: float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else fallback  # noqa: E731
    return {"series": series, "single": str(cfg["single"]) if cfg.get("single") else series[0],
            "bar": number(cfg.get("bar"), 56), "end": number(cfg.get("end"), None),
            "rest": "muted" if cfg.get("rest") == "muted" else "dim", "rest_color": str(cfg.get("rest_color") or "border")}


def _look(course: dict) -> dict:
    """What the montage receives of the style: the background, the logo, the shapes, the weights and the fonts."""
    look = style(course)
    found_fonts = fonts(course)
    text, base = text_roles(course, (found_fonts or {}).get("families") or [])
    stress = str(look.get("stress") or "underline")
    veil = look.get("photo_veil") if isinstance(look.get("photo_veil"), dict) else {}
    opacity = veil.get("opacity")
    return {"background": str(look.get("background") or "shape"), "logo": _logo(course),
            "stress": stress if stress in STRESSES else "underline", "chart": _chart(look), "progress": _progress(look),
            "veil": {"color": str(veil.get("color") or "background"),
                     "opacity": min(1.0, max(0.0, float(opacity))) if isinstance(opacity, (int, float)) else 0.82},
            "shapes": _numbers(look.get("shapes"), ("radius", "border"), ("shadow",)),
            "weights": _weights(course, look), "fonts": found_fonts, "text": text, "textBase": base}


TEXT_KEYS = ("family", "size", "weight", "style", "transform", "tracking", "leading", "color", "numeric", "measure")


def text_roles(course: dict, families: list[str]) -> tuple[dict, dict]:
    """(the typography of each role of the text, as the video takes it; the reference size of each role, the package's). A family
    that is not one of the fonts of the brand is left out (`text_problems` warns of it)."""
    package = configmod.package_defaults("video").get("text") or {}
    roles = style(course).get("text") or {}
    known = {f.lower() for f in families}
    out = {}
    for role, values in roles.items():
        values = {k: v for k, v in (values or {}).items() if k in TEXT_KEYS and v is not None} if isinstance(values, dict) else {}
        if values.get("family") and str(values["family"]).lower() not in known:
            values.pop("family")
        out[role] = values
    base = {role: float(v["size"]) for role, v in package.items() if isinstance(v, dict) and v.get("size")}
    return out, base


def text_problems(course: dict) -> list[Finding]:
    """A role of config/video.yaml › text that asks for a family the fonts of the brand do not have."""
    families = {f.lower() for f in (fonts(course) or {}).get("families") or []}
    found = []
    for role, values in (style(course).get("text") or {}).items():
        family = (values or {}).get("family") if isinstance(values, dict) else None
        if family and str(family).lower() not in families:
            found.append(Finding("warning", "FONT_NOT_BRAND", f"config/video.yaml › text › {role}",
                                 t("video", "font_not_brand", family=family, role=role, families=", ".join(sorted(families)) or "—")))
    return found


def _weights(course: dict, look: dict) -> dict:
    """The weights of the text: the style's, else those the theme fixes (project.yaml › theme › weights)."""
    own = _numbers(look.get("weights"), ("normal", "strong"))
    try:
        font = thememod.load(course["_project"], course).get("font") or {}
    except thememod.ThemeError:
        font = {}
    theme = {k: float(font[t]) for k, t in (("normal", "weight"), ("strong", "weight-strong")) if str(font.get(t) or "").isdigit()}
    return {**theme, **own}


def _numbers(block, numbers: tuple[str, ...], words: tuple[str, ...] = ()) -> dict:
    """The keys of a block of the style that are set: numbers as numbers, words as text."""
    block = block if isinstance(block, dict) else {}
    out = {k: float(block[k]) for k in numbers if block.get(k) is not None}
    return {**out, **{k: str(block[k]) for k in words if block.get(k) is not None}}


def fonts(course: dict) -> dict | None:
    """The fonts of the style (`fonts`: a stylesheet with @font-face rules; without it, the fonts of the brand), with each file
    inside as data, and the families it declares; None without one."""
    from coursekit import brand

    root = course["_project"].root
    name = style(course).get("fonts")
    sheet = root / str(name) if name else brand.fonts_stylesheet(course["_project"], course)
    if sheet is None:
        return None
    try:
        css, families = brand.inline_fonts(sheet, root)
    except brand.BrandError as exc:
        raise VideoError(str(exc)) from None
    return {"css": css, "families": families}


def _logo(course: dict) -> dict | None:
    import base64
    import mimetypes

    cfg = style(course).get("logo") or {}
    if not cfg.get("file"):
        return None
    path = course["_project"].root / str(cfg["file"])
    if not path.is_file():
        raise VideoError(t("video", "no_logo", path=str(cfg["file"])))
    kind = mimetypes.guess_type(path.name)[0] or "image/png"
    return {"src": f"data:{kind};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}",
            "corner": str(cfg.get("corner") or "bottom-right"), "scenes": [str(x) for x in cfg.get("scenes") or []],
            "size": int(cfg.get("size") or 64)}


def _ready(course: dict, asset_id: str) -> None:
    from coursekit import mediascript

    try:
        mediascript.ready(course, asset_id)
    except mediascript.ScriptError as exc:
        raise VideoError(str(exc)) from None


# ── the voice ────────────────────────────────────────────────────────────────────────────────

def _normal_words(text: str) -> list[str]:
    import unicodedata

    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn").lower()
    return [w for w in re.sub(r"[^a-z0-9ñ]+", " ", text).split() if w]


def when_said(words: list[dict], phrase: str, after: float = -1) -> dict | None:
    """The first word (with its start and end) of the first time a phrase is said from `after` on; the last one in `end`."""
    wanted = _normal_words(phrase)
    said = [(_normal_words(str(w["w"])) or [""])[0] for w in words]
    for i in range(0, len(said) - len(wanted) + 1):
        if wanted and float(words[i]["start"]) >= after and said[i:i + len(wanted)] == wanted:
            return {"start": float(words[i]["start"]), "end": float(words[i + len(wanted) - 1]["end"])}
    return None


def says_phrase(says: str, phrase: str) -> bool:
    """Whether a phrase is in a narration (the same words in a row), before the voice exists."""
    wanted, said = _normal_words(phrase), _normal_words(says)
    return bool(wanted) and any(said[i:i + len(wanted)] == wanted for i in range(len(said) - len(wanted) + 1))


def _hash(*parts: str) -> str:
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()[:16]


def _voice_record(course: dict, asset_id: str) -> dict:
    path = voice_dir(course, asset_id) / "voice.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def voice(course: dict, asset_id: str, say=print, batch: bool = False) -> int:
    """The narration of each scene, with the timings of its words; only what changed is made again. How many were made (with
    `batch`, how many were put in the queue of the Gemini batch: `coursekit tts-batch collect` finishes them)."""
    from coursekit import ttsbatch, voices

    data = load(course, asset_id)
    _ready(course, asset_id)
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
        if batch:
            try:
                queued = ttsbatch.add(course, "video", f"{asset_id}#{sid}", says, audio, asset=asset_id, scene=sid,
                                      extra={"voice_key": key})
            except (ttsbatch.BatchError, voices.VoiceError) as exc:
                raise VideoError(str(exc)) from None
            if queued:
                say(t("video", "voice_queued", scene=sid))
                made += 1
            continue
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


def voice_collected(course: dict, asset_id: str, sid: str, key: str, audio: Path, says: str, say=print) -> None:
    """A scene whose narration came in the Gemini batch: the timings of its words and its length, as `voice` leaves them."""
    folder = voice_dir(course, asset_id)
    text = folder / f"{sid}.txt"
    text.write_text(says + "\n", encoding="utf-8")
    (folder / f"{sid}.words.json").unlink(missing_ok=True)
    try:
        mediatools.subtitles(audio, text, folder / f"{sid}.vtt", language=coursemod.language(course))
    except mediatools.ToolError as exc:
        raise VideoError(t("video", "voice_failed", scene=sid, error=exc)) from None
    record = _voice_record(course, asset_id)
    record[sid] = {"key": key, "seconds": mediacheck.duration(audio)}
    (folder / "voice.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8", newline="\n")
    say(t("video", "voice_made", scene=sid, seconds=f"{record[sid]['seconds']:.1f}"))


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
    look = style(course)
    fmt = {**DEFAULT_FORMAT, **(look.get("format") or {}), **(data.get("format") or {})}
    fps = int(fmt["fps"])
    pad = float(look.get("pad_seconds") if look.get("pad_seconds") is not None else 0.5)
    record = _voice_record(course, asset_id)
    folder = voice_dir(course, asset_id)
    try:
        tokens = thememod.load(course["_project"], course)
    except thememod.ThemeError as exc:
        raise VideoError(str(exc)) from None
    moving = motion(course, data)
    resolved, cursor = [], 0
    for scene in data["scenes"]:
        sid = str(scene["id"])
        says = _text(scene.get("says")).strip()
        spec = (pieces(course, "scenes").get(str(scene["type"])) or {"meta": {}})["meta"].get("props") or {}
        props = with_defaults(dict(scene.get("props") or {}), piece_rules(course, str(scene["type"]), spec))
        if scene.get("type") == "screencast" and props.get("recording") and "events" not in props:
            events = (course["_dir"] / "media" / str(props["recording"])).with_suffix(".events.json")
            if events.exists():
                props["events"] = json.loads(events.read_text(encoding="utf-8")).get("events") or []
        if says:
            if sid not in record or not (folder / f"{sid}.mp3").exists():
                raise VideoError(t("video", "voice_pending", scene=sid, code=course["code"], id=asset_id))
            seconds = float(record[sid]["seconds"]) + pad + float(scene.get("hold") or 0)  # `hold`: it stays a while after it is said
            audio, words = f"files/{asset_id}/{sid}.mp3", _words(folder / f"{sid}.words.json")
        else:
            seconds, audio, words = float(scene.get("duration") or 3), None, []
        if scene.get("duration") and says:
            seconds = max(seconds, float(scene["duration"]))
        frames = max(1, round(seconds * fps))
        entry = {"id": sid, "type": str(scene["type"]), "from": cursor, "frames": frames, "props": props, "audio": audio,
                 "words": words, "says": says, "layers": _resolve_layers(scene, words, frames, fps, course), "transition": None}
        if resolved:  # it enters over the end of the one before: they overlap for the frames of the transition
            entry["transition"] = transition_for(course, resolved[-1], {**scene, "props": props}, moving["fade"])
            entry["transition"]["frames"] = min(entry["transition"]["frames"], resolved[-1]["frames"] - 1, frames - 1)
            entry["from"] = cursor - entry["transition"]["frames"]
        resolved.append(entry)
        cursor = entry["from"] + frames
    return {"fps": fps, "width": int(fmt["width"]), "height": int(fmt["height"]), "frames": cursor,
            "tokens": {k: tokens[k] for k in ("color", "font", "radius", "space", "shadow") if k in tokens},
            "motion": motion(course, data), "style": _look(course),
            "scenes": resolved}


def _layer_props(course: dict | None, layer: dict) -> dict:
    props = dict(layer.get("props") or {})
    if course is None:
        return props
    spec = (pieces(course, "layers").get(str(layer["type"])) or {"meta": {}})["meta"].get("props") or {}
    return with_defaults(props, piece_rules(course, str(layer["type"]), spec))


def _resolve_layers(scene: dict, words: list[dict], frames: int, fps: int, course: dict | None = None) -> list[dict]:
    """Each layer from the word it is anchored to (`at`) until `until` is said, or `hold` seconds (default 3), inside its scene.
    A layer whose word is not said is left out (`video check` warns of it)."""
    out = []
    for n, layer in enumerate(scene.get("layers") or [], 1):
        start = 0.0
        if layer.get("at"):
            hit = when_said(words, str(layer["at"]))
            if hit is None:
                continue
            start = hit["start"]
        end = start + float(layer.get("hold") or 3)
        if layer.get("until"):
            hit = when_said(words, str(layer["until"]), start)
            end = hit["end"] if hit else end
        first = min(frames - 1, round(start * fps))
        out.append({"id": str(layer.get("id") or f"{scene['id']}-{n}"), "type": str(layer["type"]), "from": first,
                    "frames": max(1, min(frames - first, round((end - start) * fps))), "props": _layer_props(course, layer)})
    return out


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
    for kind, name, _, path in overrides(course):  # a piece of the project (or of the course) in place of the library's
        shutil.copy2(path, kit / kind / f"{name}.tsx")
    copies = root / COURSE_COPY
    shutil.rmtree(copies, ignore_errors=True)
    lines, tables = [], {}
    for kind, prefix in (("scenes", "s_"), ("layers", "l_")):
        names = []
        for name, piece in sorted(pieces(course, kind).items()):
            if piece["origin"] == "library":
                path = f"./{kind}/{name}"
            elif piece["origin"] == "project":
                path = f"../src/{kind}/{name}"
            else:
                target = copies / f"{course['code'].lower()}-{kind}-{name}"
                shutil.copytree(piece["folder"], target)
                path = f"../{COURSE_COPY.as_posix()}/{target.name}"
            ident = prefix + re.sub(r"[^a-z0-9]", "_", name)
            lines.append(f'import {ident} from "{path}";')
            names.append(f'"{name}": {ident}')
        tables[kind] = ", ".join(names)
    (kit / "registry.generated.ts").write_text(
        "// Written by coursekit (`coursekit video …`): the scenes and layers of the library, the project and the course that win.\n"
        'import type React from "react";\nimport type { LayerProps, SceneProps } from "./contract";\n' + "\n".join(lines) +
        "\n\n// eslint-disable-next-line @typescript-eslint/no-explicit-any\n"
        f"export const scenes: Record<string, React.FC<SceneProps<any>>> = {{ {tables['scenes']} }};\n"
        "// eslint-disable-next-line @typescript-eslint/no-explicit-any\n"
        f"export const layers: Record<string, React.FC<LayerProps<any>>> = {{ {tables['layers']} }};\n", encoding="utf-8", newline="\n")
    return root


def require_current(project) -> None:
    """The Remotion workspace at the versions of coursekit, before rendering: otherwise stop and say to run `coursekit setup
    --media`. In the handoff (nobody to run it) it goes on with what is installed and warns."""
    from coursekit import setup

    outdated = setup.remotion_outdated(project)
    if not outdated:
        return
    message = t("video", "workspace_outdated", packages="; ".join(outdated))
    if os.environ.get("COURSEKIT_HANDOFF") == "1":
        print(t("commands", "warning_line", text=message), file=sys.stderr)
        return
    raise VideoError(message)


def _remotion(root: Path, args: list[str]) -> None:
    exe = root / "node_modules" / ".bin" / ("remotion.cmd" if os.name == "nt" else "remotion")
    if not exe.exists():
        raise VideoError(t("video", "no_workspace"))
    from coursekit.project import Project

    require_current(Project(root.parent.parent))
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


GALLERY_SECONDS = 3.5  # each piece in the gallery: enough to enter and settle
GALLERY_BASE = "title"  # the scene a layer is drawn over


def example(piece: dict, language: str) -> dict | None:
    """The props a piece is drawn with in the gallery (`example:` of its scene.yaml or layer.yaml, in the language of the
    course, else English)."""
    block = piece["meta"].get("example")
    if not isinstance(block, dict) or not block:
        return None
    chosen = block.get(language) or block.get("en") or next(iter(block.values()))
    return dict(chosen) if isinstance(chosen, dict) else None


SAMPLE_PHOTO = Path(__file__).parent / "videokit" / "gallery" / "sample-photo.jpg"  # a photo in the public domain (CC0)


def _sample_image(tokens: dict) -> str:
    """An image for the examples that show a medium, drawn with the colours of the theme."""
    color = tokens.get("color") or {}
    surface, accent, line = (color.get(k) or fallback for k, fallback in (("surface", "#f2f2f2"), ("accent", "#0b5fff"),
                                                                          ("border", "#d0d0d0")))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="800" viewBox="0 0 1280 800">'
            f'<rect width="1280" height="800" fill="{surface}"/><rect x="80" y="80" width="1120" height="64" fill="{line}"/>'
            f'<rect x="80" y="200" width="520" height="520" fill="{accent}"/><rect x="660" y="200" width="540" height="40" fill="{line}"/>'
            f'<rect x="660" y="280" width="420" height="40" fill="{line}"/><rect x="660" y="360" width="480" height="40" fill="{line}"/>'
            "</svg>")


GALLERY_NEXT = "statement"  # the scene the transitions of the gallery lead into, after the cover
GALLERY_FIRST = "title"  # the cover goes first in the gallery: the first scene of most videos


def _gallery_transitions(course: dict) -> dict:
    """The transitions the galleries show: each type the project allows, with its name in the language of the person, and the
    frames and the direction of the project."""
    setting = transition_setting(course)
    kinds = [k for k in TRANSITIONS if not setting["allow"] or k in setting["allow"]]
    frames = setting["frames"] if setting["frames"] is not None else motion(course, {})["fade"]
    return {"types": [{"name": k, "label": t("video", f"transition_{k}")} for k in kinds], "frames": frames,
            "direction": setting["direction"] if setting["direction"] in DIRECTIONS else "left", "directions": list(DIRECTIONS)}


def _as_allowed(course: dict, name: str, piece: dict, language: str) -> dict:
    """A piece as the project allows it, for the galleries: its props with only the allowed values, its example kept to them (a
    value it does not allow becomes the first one it does), its variants that keep to them, and whether it is left out."""
    spec = piece["meta"].get("props") or {}
    rules = piece_rules(course, name, spec)
    def kept(values: dict) -> dict:  # a value the project does not allow becomes the first one it does
        values = with_defaults(values, rules)
        for prop, allow in rules["allow"].items():
            if values.get(prop) not in (None, "") and _key(values[prop]) not in map(_key, allow) and allow:
                values[prop] = allow[0]
        return values

    props = example(piece, language)
    props = kept(props) if props is not None else None
    variants, seen = [], [props]
    for variant in piece["meta"].get("variants") or []:
        if props is None or not isinstance(variant, dict) or not variant.get("name") or not isinstance(variant.get("props"), dict):
            continue
        drawn = kept({**props, **variant["props"]})
        if drawn not in seen:  # a variant that, kept to the rules, is another one again is not drawn twice
            seen.append(drawn)
            variants.append({"name": variant["name"], "label": localized(variant.get("label")) or str(variant["name"]),
                             "props": {k: v for k, v in drawn.items() if props.get(k) != v}})
    return {"spec": allowed_spec(spec, rules), "example": props, "variants": variants, "off": rules["off"]}


def _gallery_entries(course: dict, language: str) -> list[dict]:
    """What the gallery draws, in order: the cover first, then the scenes and the layers by name; each piece with the props of its
    example, and after it each of its variants (`variants:` of its metadata, their props over those of the example); only what the
    project and the course allow (config/video.yaml › scenes)."""
    out = []
    for kind in ("scenes", "layers"):
        found = sorted(pieces(course, kind).items(), key=lambda item: (item[0] != GALLERY_FIRST, item[0]))
        for name, piece in found:
            allowed = _as_allowed(course, name, piece, language)
            if allowed["off"]:
                continue
            props = allowed["example"]
            out.append({"kind": kind, "name": name, "key": name, "piece": piece, "props": props, "variant": None, "changes": {},
                        "spec": allowed["spec"]})
            for variant in allowed["variants"]:
                out.append({"kind": kind, "name": name, "key": f"{name}-{variant['name']}", "piece": piece,
                            "props": {**props, **variant["props"]}, "variant": variant["label"], "changes": variant["props"],
                            "spec": allowed["spec"]})
    return out


LIVE_ENTRY = "kit/gallery/live.tsx"  # the app of the galleries, inside the workspace once the kit is synced


def live_gallery(course: dict, say=print, code: bool = True, fresh: bool = True) -> Path:
    """The live gallery: a page that plays every scene and layer with the player of Remotion, with a control for each prop, in
    .cache/media/<CODE>/gallery-live/. Served by `serve_gallery`, which builds it again when something changes: `code: False`
    writes only the data (a change of the configuration or the theme), `fresh: False` writes over the files the page is
    reading instead of emptying the folder first."""
    require_current(course["_project"])
    out = course["_project"].cache_dir / "media" / course["code"] / "gallery-live"
    if fresh:
        shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    return _gallery_app(course, out, {}, code, say)


def _gallery_app(course: dict, out: Path, extra: dict, code: bool, say) -> Path:
    """The interface of the galleries in a folder: the data of the pieces in the theme and the style of the course (data.js),
    the app bundled with the design system of Studio LXD (app.js, app.css and its fonts) and its two pages: index.html, the
    interface, and stage.html, where a piece is drawn with no CSS of Studio LXD. `extra` goes into the data (the clips of the
    rendered gallery)."""
    try:
        tokens = thememod.load(course["_project"], course)
    except thememod.ThemeError as exc:
        raise VideoError(str(exc)) from None
    language = coursemod.language(course)
    fmt = {**DEFAULT_FORMAT, **(style(course).get("format") or {})}
    root = sync(course) if code else workspace(course)
    if not (root / "node_modules" / "esbuild").is_dir() or not (root / "node_modules" / "@remotion" / "player").is_dir():
        raise VideoError(t("video", "no_live_tools"))
    _write(out / "gallery-sample.svg", _sample_image(tokens))
    shutil.copy2(SAMPLE_PHOTO, out / "gallery-sample-photo.jpg")
    found = []
    for kind in ("scenes", "layers"):
        for name, piece in sorted(pieces(course, kind).items(), key=lambda item: (item[0] != GALLERY_FIRST, item[0])):
            meta = piece["meta"]
            allowed = _as_allowed(course, name, piece, language)
            if allowed["off"]:
                continue
            props = {k: {**v, "help": localized(v.get("help"))} for k, v in allowed["spec"].items()}
            variants = [{"name": str(v["name"]), "label": v["label"], "props": v["props"]} for v in allowed["variants"]]
            found.append({"kind": kind, "name": name, "label": localized(meta.get("label")) or name,
                          "origin": origin_label(piece["origin"]),
                          "description": localized(meta.get("description")), "props": props, "example": allowed["example"],
                          "variants": variants})
    labels = {key: t("video", f"live_{key}") for key in LIVE_LABELS}
    data = {"title": t("video", "gallery_title", code=course.get("_label") or course["code"]), "seconds": GALLERY_SECONDS,
            "base": example(pieces(course, "scenes").get(GALLERY_BASE) or {"meta": {}}, language) or {"title": ""},
            "samples": ["gallery-sample-photo.jpg", "gallery-sample.svg", *_course_images(course, out)], "labels": labels,
            "pieces": found, "swatches": [[k, str(v)] for k, v in (tokens.get("color") or {}).items() if str(v).startswith("#")],
            "next": example(pieces(course, "scenes").get(GALLERY_NEXT) or {"meta": {}}, language) or {"text": ""},
            "transitions": _gallery_transitions(course),
            "montage": {"fps": int(fmt["fps"]), "width": int(fmt["width"]), "height": int(fmt["height"]),
                        "tokens": {k: tokens[k] for k in ("color", "font", "radius", "space", "shadow") if k in tokens},
                        "motion": motion(course, {}), "style": _look(course)}, **extra}
    _write(out / "data.js", "window.__GALLERY__ = " + json.dumps(data, ensure_ascii=False) + ";\n")
    if code or not (out / "app.js").exists():
        say(t("video", "live_bundling"))
        build = out / ".build"  # the bundle is written apart and moved in whole: the page never reads half of it
        shutil.rmtree(build, ignore_errors=True)
        options = {"entryPoints": {"app": LIVE_ENTRY}, "bundle": True, "format": "iife", "minify": True, "jsx": "automatic",
                   "define": {"process.env.NODE_ENV": '"production"'}, "outdir": str(build), "assetNames": "assets/[name]-[hash]",
                   "loader": {ext: "file" for ext in (".woff2", ".woff", ".ttf", ".otf", ".svg", ".png", ".jpg", ".webp")},
                   "logLevel": "error"}
        done = subprocess.run(["node", "-e", "require('esbuild').buildSync(JSON.parse(process.argv[1]))", json.dumps(options)],
                              cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        if done.returncode != 0:
            tail = [line for line in (done.stderr or done.stdout).strip().splitlines() if line.strip()][-6:]
            raise VideoError(t("video", "render_failed", reason=" | ".join(tail) or "?"))
        if (build / "assets").is_dir():
            shutil.copytree(build / "assets", out / "assets", dirs_exist_ok=True)
        for name in ("app.css", "app.js"):
            if (build / name).exists():
                os.replace(build / name, out / name)
        shutil.rmtree(build, ignore_errors=True)
    title = html_escape(data["title"])
    head = (f'<!doctype html><html lang="{i18n.language()}"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width, initial-scale=1"><link rel="icon" href="data:,"><title>{title}</title>')
    scripts = '<div id="root"></div><script src="data.js"></script><script src="app.js"></script></body></html>\n'
    # the interface, in the design system of Studio LXD (app.css); the piece, in a frame with no CSS of it
    _write(out / "index.html", head + '<link rel="stylesheet" href="app.css"></head><body>' + scripts)
    _write(out / "stage.html", head + '</head><body style="margin:0;overflow:hidden">' + scripts)
    return out / "index.html"


LIVE_LABELS = ("default", "none", "variant", "example", "no_example", "code", "scenes", "layers", "scenes_group", "layers_group",
               "col_prop", "col_type", "col_control", "col_help", "broken", "typography", "sample_display", "sample_heading",
               "sample_subheading", "sample_kicker", "sample_body", "sample_quote", "sample_statement", "sample_label",
               "sample_caption", "skip", "menu", "menu_close", "navigation", "typography_intro", "style_group", "colours",
               "colours_intro", "shapes", "shapes_intro", "id_hint", "background", "radius", "border", "shadow", "weight_normal",
               "weight_strong", "col_value", "rendered_hint", "less", "more", "empty",
               "transitions", "transitions_intro", "transition", "direction", "reset")


def _write(path: Path, text: str) -> None:
    """A file the page may be reading, replaced whole: never half written."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def _course_images(course: dict, out: Path, limit: int = 40) -> list[str]:
    """The images of a course (media/files/), copied next to the live gallery, to try a piece with them."""
    files = course["_dir"] / "media" / "files"
    found = []
    for path in sorted(files.glob("*")) if files.is_dir() else []:
        if path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") and path.stat().st_size < 8_000_000 and len(found) < limit:
            (out / "files").mkdir(exist_ok=True)
            shutil.copy2(path, out / "files" / path.name)
            found.append(f"files/{path.name}")
    return found


def watched(course: dict) -> dict[str, list[Path]]:
    """What the live gallery is made from: `data`, what changes only its data (the configuration, the theme, the fonts, the
    images of the course), and `code`, what needs the app bundled again (the scenes of the library, the project and the course)."""
    project = course["_project"]
    data = [project.file, project.config_dir / "video.yaml", project.config_dir / "media.yaml", project.theme_dir / "tokens.json",
            thememod.tokens_path(project, course), project.theme_dir / "branding" / "fonts"]
    if course["code"] != PROJECT_SCOPE:
        data += [course["_dir"] / "course.yaml", course["_dir"] / "theme" / "branding" / "fonts", course["_dir"] / "media" / "files"]
    return {"data": data, "code": [kit_source(), workspace(course) / "src", course["_dir"] / "video"]}


SKIP = {"node_modules", "__pycache__", ".course"}  # never a source: dependencies, caches, the copies of the course scenes


def stamp(paths: list[Path]) -> tuple:
    """When each of these files (or the files inside these folders) last changed: compared second by second by the server."""
    out = []
    for path in paths:
        if path.is_file():
            files = [path]
        else:
            files = [p for p in path.rglob("*") if p.is_file() and not SKIP & set(p.parts)] if path.is_dir() else []
        out += [(f.as_posix(), f.stat().st_mtime_ns, f.stat().st_size) for f in files]
    return tuple(sorted(out))


def serve_gallery(page: Path, port: int = 8766, open_browser: bool = True, say=print, reload=None) -> int:
    """Serve the live gallery on 127.0.0.1 (the port asked for, else a free one) until Ctrl+C. With `reload` (what gives the
    course again, read anew), it watches what the gallery is made from and builds it again when it changes: the page asks for
    version.json every second and reloads itself, keeping the piece and the values it had."""
    import functools
    import threading
    import time
    import webbrowser
    from http.server import SimpleHTTPRequestHandler

    from coursekit.preview import Server

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *args) -> None:
            pass

        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

    folder = page.parent
    state = {"version": 1, "error": None}
    _write(folder / "version.json", json.dumps(state))
    stop = threading.Event()

    def watch() -> None:
        course = reload()
        before = {kind: stamp(paths) for kind, paths in watched(course).items()}
        while not stop.wait(1):
            try:
                course = reload()
                now = {kind: stamp(paths) for kind, paths in watched(course).items()}
            except Exception:  # a file half written: next second
                continue
            if now == before:
                continue
            code = now["code"] != before["code"]
            before = now
            try:
                live_gallery(course, lambda m: None, code=code, fresh=False)
                state["error"] = None
                say(t("video", "live_updated", time=time.strftime("%H:%M:%S")))
            except Exception as exc:  # a scene being written: the page shows it, and the next save fixes it
                state["error"] = str(exc)
                say(t("commands", "error_line", text=exc))
            before = {kind: stamp(paths) for kind, paths in watched(course).items()}  # what the build itself touched
            state["version"] += 1
            _write(folder / "version.json", json.dumps(state))

    handler = functools.partial(Quiet, directory=str(folder))
    try:
        server = Server(("127.0.0.1", port), handler)
    except OSError:
        server = Server(("127.0.0.1", 0), handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    say(t("video", "live_serving", url=url))
    say(t("video", "live_watching") if reload else t("preview", "stop_hint"))
    if reload:
        threading.Thread(target=watch, daemon=True).start()
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()
    return 0


def html_escape(text: str) -> str:
    import html

    return html.escape(text)


def gallery(course: dict, say=print) -> Path:
    """Every scene and layer the course can use, drawn with its example (and each of its variants) in the theme and the style of
    the course and rendered: one short video with all of them (`gallery.mp4`), a clip and a frame of each, and the interface of
    the galleries to look at them (`index.html`, the same as the live gallery's, with the clips in place of the player), in
    .cache/media/<CODE>/gallery/. What has no example is listed without a picture."""
    require_current(course["_project"])
    try:
        tokens = thememod.load(course["_project"], course)
    except thememod.ThemeError as exc:
        raise VideoError(str(exc)) from None
    language = coursemod.language(course)
    look = style(course)
    fmt = {**DEFAULT_FORMAT, **(look.get("format") or {})}
    fps = int(fmt["fps"])
    frames = round(GALLERY_SECONDS * fps)
    entries = _gallery_entries(course, language)
    base = example(pieces(course, "scenes").get(GALLERY_BASE) or {"meta": {}}, language) or {"title": ""}
    drawn, cursor = [], 0
    for entry in entries:
        props = entry["props"]
        if props is None:
            continue
        if entry["kind"] == "scenes":
            scene = {"id": entry["key"], "type": entry["name"], "props": props, "layers": []}
        else:
            scene = {"id": f"layer-{entry['key']}", "type": GALLERY_BASE, "props": base,
                     "layers": [{"id": entry["key"], "type": entry["name"], "from": 0, "frames": frames, "props": props}]}
        drawn.append({**scene, "from": cursor, "frames": frames, "audio": None, "words": [], "says": ""})
        cursor += frames
    if not drawn:
        raise VideoError(t("video", "gallery_empty", code=course.get("_label") or course["code"]))
    ahead = example(pieces(course, "scenes").get(GALLERY_NEXT) or {"meta": {}}, language) or {"text": ""}
    shown = _gallery_transitions(course)
    pairs = {}  # transition-<type>: (its first frame, its last), the cover giving way to the next scene
    for kind in (k["name"] for k in shown["types"]):
        overlap = 0 if kind == "cut" else min(shown["frames"], frames - 1)
        first = {"id": f"transition-{kind}-from", "type": GALLERY_BASE, "props": base, "layers": [], "from": cursor, "frames": frames,
                 "audio": None, "words": [], "says": ""}
        second = {"id": f"transition-{kind}", "type": GALLERY_NEXT, "props": ahead, "layers": [], "from": cursor + frames - overlap,
                  "frames": frames, "audio": None, "words": [], "says": "",
                  "transition": {"type": kind, "frames": overlap, "direction": shown["direction"]}}
        drawn += [first, second]
        pairs[f"transition-{kind}"] = (first["from"], second["from"] + frames, second["from"] + overlap // 2)
        cursor = second["from"] + frames
    resolved = {"fps": fps, "width": int(fmt["width"]), "height": int(fmt["height"]), "frames": cursor,
                "tokens": {k: tokens[k] for k in ("color", "font", "radius", "space", "shadow") if k in tokens},
                "motion": motion(course, {}), "style": _look(course), "scenes": drawn}
    out = course["_project"].cache_dir / "media" / course["code"] / "gallery"
    shutil.rmtree(out, ignore_errors=True)
    (out / "frames").mkdir(parents=True)
    (out / "clips").mkdir()
    (out / "gallery-sample.svg").write_text(_sample_image(tokens), encoding="utf-8")
    shutil.copy2(SAMPLE_PHOTO, out / "gallery-sample-photo.jpg")
    root = sync(course)
    props_file = _props_file(course, "gallery", resolved)
    say(t("video", "gallery_rendering", count=len(drawn)))
    video_file = out / "gallery.mp4"
    _remotion(root, ["render", f"{KIT}/entry.ts", "Montage", str(video_file), f"--props={props_file}", f"--public-dir={out}", "--muted",
                     "--scale=0.5", "--log=error"])
    starts = {}
    for name, (begin, end, middle) in pairs.items():  # the clip of a transition: both scenes, its poster in the middle of it
        starts[name] = (begin / fps, end / fps)
        mediatools.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{middle / fps:.3f}", "-i", str(video_file), "-frames:v", "1",
                        str(out / "frames" / f"{name}.png")])
        mediatools.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{begin / fps:.3f}", "-t", f"{(end - begin) / fps:.3f}",
                        "-i", str(video_file), "-an", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                        str(out / "clips" / f"{name}.mp4")])
    for scene in drawn:
        if scene["id"].startswith("transition-"):
            continue
        name = scene["layers"][0]["id"] if scene["layers"] else scene["id"]
        starts[name] = (scene["from"] / fps, (scene["from"] + scene["frames"]) / fps)
        at = (scene["from"] + scene["frames"] - resolved["motion"]["fade"] - 2) / fps  # all in, before it fades out
        mediatools.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{at:.3f}", "-i", str(video_file), "-frames:v", "1",
                        str(out / "frames" / f"{name}.png")])
        # its own clip: the card plays that piece alone, not the whole gallery
        mediatools.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{scene['from'] / fps:.3f}", "-t", f"{scene['frames'] / fps:.3f}",
                        "-i", str(video_file), "-an", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                        str(out / "clips" / f"{name}.mp4")])
    clips = {key: {"clip": f"clips/{key}.mp4", "poster": f"frames/{key}.png"} for key in starts}
    return _gallery_app(course, out, {"rendered": True, "clips": clips}, True, say)


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
    _ready(course, asset_id)
    resolved = resolve(course, asset_id)
    root = sync(course)
    props = _props_file(course, asset_id, resolved)
    media = course["_dir"] / "media"
    out = media / "files" / f"{asset_id}.mp4"
    _remotion(root, ["render", f"{KIT}/entry.ts", "Montage", str(out), f"--props={props}", f"--public-dir={media}", "--log=error"])
    if any(scene["audio"] for scene in resolved["scenes"]):  # the voice at the loudness of the course (media › checks)
        cfg = mediacheck.settings(course)
        if mediacheck.loudness_finding({"id": asset_id}, out, cfg) is not None:
            mediacheck.fix_loudness(out, cfg)
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


# ── for an editor ────────────────────────────────────────────────────────────────────────────

def export_dir(course: dict, asset_id: str) -> Path:
    return course["_dir"] / "media" / "edit" / asset_id


def export(course: dict, asset_id: str, say=print) -> dict:
    """The pieces of the video, apart, and its timeline for an editor (DaVinci Resolve, Final Cut, Premiere): each scene clean
    (without its layers, without sound), each layer alone with transparency (ProRes 4444), the voice of each scene, the
    captions in SRT, and the timeline in FCPXML 1.10 and OpenTimelineIO, in media/edit/<id>/."""
    from coursekit import videoedit

    resolved = resolve(course, asset_id)
    root = sync(course)
    media = course["_dir"] / "media"
    out = export_dir(course, asset_id)
    shutil.rmtree(out, ignore_errors=True)
    for folder in ("scenes", "layers", "voices"):
        (out / folder).mkdir(parents=True, exist_ok=True)
    fps = resolved["fps"]
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise VideoError(t("redact", "ffmpeg_missing"))
    clean = out / "clean.mp4"
    say(t("video", "export_step", what="clean"))
    props = _props_file(course, asset_id, {**resolved, "mode": "clean"})
    _remotion(root, ["render", f"{KIT}/entry.ts", "Montage", str(clean), f"--props={props}", f"--public-dir={media}", "--muted",
                     "--log=error"])
    scenes_track, layers_track, voices_track = videoedit.Track("video", "scenes"), videoedit.Track("video", "layers"), \
        videoedit.Track("audio", "voices")
    markers = []
    for n, scene in enumerate(resolved["scenes"], 1):
        piece = out / "scenes" / f"{n:02d}-{scene['id']}.mp4"
        following = resolved["scenes"][n] if n < len(resolved["scenes"]) else None  # up to the next: the transitions are in the render
        first, last = scene["from"], (following["from"] if following else scene["from"] + scene["frames"]) - 1  # by the number of the frame
        length = last - first + 1
        done = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(clean), "-vf",
                               f"select='between(n\\,{first}\\,{last})',setpts=N/FRAME_RATE/TB", "-r", str(fps), "-c:v", "libx264",
                               "-crf", "16", "-pix_fmt", "yuv420p", "-an", str(piece)], capture_output=True, text=True, check=False)
        if done.returncode != 0:
            raise VideoError(t("redact", "encode_failed", reason=([*(done.stderr or "?").strip().splitlines(), "?"])[0]))
        scenes_track.clips.append(videoedit.Clip(scene["id"], piece, scene["from"], length))
        markers.append((scene["from"], scene["id"]))
        if scene["audio"]:
            voice = out / "voices" / f"{n:02d}-{scene['id']}.mp3"
            shutil.copy2(media / scene["audio"], voice)
            seconds = float(_voice_record(course, asset_id).get(scene["id"], {}).get("seconds") or scene["frames"] / fps)
            length = min(scene["frames"], round(seconds * fps))
            voices_track.clips.append(videoedit.Clip(f"voice {scene['id']}", voice, scene["from"], length, round(seconds * fps)))
        for layer in scene["layers"]:
            say(t("video", "export_step", what=layer["id"]))
            piece = out / "layers" / f"{layer['id']}.mov"
            first = scene["from"] + layer["from"]
            props = _props_file(course, asset_id, {**resolved, "mode": {"layer": layer["id"]}})
            _remotion(root, ["render", f"{KIT}/entry.ts", "Montage", str(piece), f"--props={props}", f"--public-dir={media}",
                             f"--frames={first}-{first + layer['frames'] - 1}", "--codec=prores", "--prores-profile=4444",
                             "--pixel-format=yuva444p10le", "--image-format=png", "--muted", "--log=error"])
            layers_track.clips.append(videoedit.Clip(layer["id"], piece, first, layer["frames"]))
    clean.unlink(missing_ok=True)
    vtt, _ = _captions(resolved)
    (out / "captions.srt").write_text(videoedit.srt(vtt), encoding="utf-8", newline="\n")
    timeline = videoedit.Timeline(f"{course['code']} {asset_id}", fps, resolved["width"], resolved["height"], resolved["frames"],
                                  [scenes_track, layers_track, voices_track], markers)
    (out / "timeline.fcpxml").write_text(videoedit.fcpxml(timeline), encoding="utf-8", newline="\n")
    (out / "timeline.otio").write_text(videoedit.otio(timeline), encoding="utf-8", newline="\n")
    return {"folder": out, "scenes": len(scenes_track.clips), "layers": len(layers_track.clips), "voices": len(voices_track.clips)}
