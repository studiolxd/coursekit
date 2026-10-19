"""`coursekit media`: extract the media placeholders of the content and plan how to produce them.

    coursekit media extract CODE     sync media/manifest.yaml with the placeholders in content.md
    coursekit media plan CODE        per pending asset, the production options available here
    coursekit media providers        which optional providers are available on this machine
    coursekit media set CODE ID …    update an asset (used by the media agent while producing)

Asset ids are U<unit>-S<section>-M<k> (k-th placeholder of the section), the same ids
`coursekit assemble` uses to swap a placeholder for its produced media.
"""

from __future__ import annotations

import os
import re
import shutil
from contextlib import contextmanager
from pathlib import Path

import yaml

from coursekit import config as configmod
from coursekit import course as coursemod
from coursekit import i18n, lang
from coursekit import story as storymod
from coursekit import theme as thememod
from coursekit.i18n import t
from coursekit.util import LockTimeout, character_asset_id, file_lock, roundtrip_yaml, save_yaml_atomic

FIELD_KEYS = ("title", "description", "how", "specs")  # in the order of the language's placeholder_fields


class MediaError(Exception):
    pass


def in_media_tools(name: str) -> bool:
    """A media tool installed as a command (coursekit setup --media installs them with uv)."""
    return shutil.which(name) is not None


def config(project=None, course: dict | None = None) -> dict:
    return configmod.effective("media", project or (course or {}).get("_project"), course).value


def requirement_met(needs, root: Path | None = None) -> bool | None:
    """True/False for env/bin requirements; None when only the agent can tell (mcp)."""
    if needs in (None, "none"):
        return True
    results = []
    for kind, value in needs.items():
        if kind == "env":
            names = [value] if isinstance(value, str) else list(value)
            results.append(all(os.environ.get(name, "").strip() for name in names))
        elif kind == "bin":
            results.append(shutil.which(value) is not None)
        elif kind == "mcp":
            results.append(None)
        elif kind == "media":
            results.append(in_media_tools(value))
        elif kind == "path":
            results.append(root is not None and (root / value).exists())
    if False in results:
        return False
    return None if None in results else True


def options_for(kind: str, cfg: dict, root: Path | None = None) -> list[dict]:
    chain = []
    for option in cfg["types"].get(kind, []):
        met = requirement_met(option.get("needs"), root)
        if met is not False:
            only = option.get("only")
            if only:
                label = t("media", f"only_{only}") if f"only_{only}" in i18n.catalog("media") else only
                available = t("media", "available_yes_only" if met else "available_mcp_only", only=label)
            else:
                available = t("media", "available_yes" if met else "available_mcp")
            chain.append({**option, "available": available})
    return chain


DEPICTS = ("interface", "concept")


def depicts_rules(cfg: dict) -> tuple[list[str], list[str]]:
    """(the types that say what they show, the recipes that may make what shows a real interface)."""
    block = cfg.get("depicts") or {}
    return list(block.get("required_for") or []), list(block.get("interface_recipes") or [])


def capture_waiting(asset: dict) -> str | None:
    """`captured` (a capture whose personal data was covered waits for a person to review it) or `rejected` (a person rejected
    it: it is covered again, or captured again); None otherwise."""
    state = (asset.get("capture") or {}).get("state")
    return state if state in ("captured", "rejected") and asset.get("status") not in ("produced", "uploaded") else None


PERSON_RECIPES = ("screen-recording", "screenshot", "asciinema")  # recorded live from the real application: a person does it


def awaiting_recording(asset: dict) -> bool:
    """A resource that shows a real interface and waits for a person to provide the capture or the recording."""
    return (asset.get("depicts") == "interface" and asset.get("status") == "scripted"
            and asset.get("recipe") in PERSON_RECIPES and not (asset.get("capture") or {}).get("state"))


def _script_lines(course: dict, asset: dict) -> list[str]:
    """What waits for a person before a resource is made: an official video that stands in for it, or its script."""
    from coursekit import mediascript, videos

    official = videos.standing_in(course, str(asset["id"]))
    if official:
        return ["  " + t("videos", f"stands_in_{official['status']}", id=asset["id"], url=official["url"], code=course["code"])]
    if mediascript.required(course):
        state = mediascript.state(course, str(asset["id"]))
        if state in ("pending", "changed"):
            return [t("mediascript", "plan_line" if state == "pending" else "plan_changed", code=course["code"], id=asset["id"])]
    return []


JOB_AID = "job_aid"  # its text is the body of its placeholder (jobaid.py)


def scan(course: dict) -> list[dict]:
    tk = coursemod.tokens(course)
    section_re = re.compile(rf"^## {re.escape(tk['section'])} (\d+)\s*[—-]")
    placeholder_re = re.compile(rf"^>\s*\*\*\[{re.escape(tk['placeholder'])}\s*[—-]\s*(.+?)\]\*\*")
    names = "|".join(re.escape(f) for f in tk["placeholder_fields"])
    field_re = re.compile(rf"^>\s*\*\*({names}):\*\*\s*(.*)$")
    keys = dict(zip(tk["placeholder_fields"], FIELD_KEYS, strict=False))
    assets = []
    for unit in course.get("units") or []:
        path = coursemod.unit_dir(course["_dir"], unit["n"]) / "content.md"
        if not path.exists():
            continue
        section, k, current = None, 0, None
        for line in path.read_text(encoding="utf-8").splitlines():
            m = section_re.match(line)
            if m:
                section, k, current = int(m.group(1)), 0, None
                continue
            m = placeholder_re.match(line)
            if m and section is not None:
                k += 1
                written = m.group(1).strip()
                current = {"id": f"U{unit['n']}-S{section}-M{k}", "unit": unit["n"], "section": section,
                           "type": lang.media_type_id(tk, written) or written}
                assets.append(current)
                continue
            if current is not None:
                f = field_re.match(line)
                if f:
                    current[keys[f.group(1)]] = f.group(2).strip()
                elif not line.startswith(">"):
                    current = None
                elif current["type"] == JOB_AID:  # the lines after the fields are the text of the job aid
                    current["body"] = (current.get("body", "") + re.sub(r"^>\s?", "", line) + "\n")
    for asset in assets:
        if "body" in asset:
            asset["body"] = asset["body"].strip("\n")
    return assets


DIALOG_OPEN = re.compile(r"^:::dialog\s*$")
DIALOG_LINE = re.compile(r"^\*\*(.+?):\*\*")


def scan_characters(course: dict) -> list[dict]:
    """A portrait asset (an image) for every character of the dialogues, so that the agent gives each one a face instead of leaving
    an initial. The id is the same wherever the character speaks; the first dialogue gives the unit and the section, and
    `dialogue_units` lists every unit whose dialogues show it (creator takes an image only from its own content: each of those
    contents needs its copy, see `missing_uploads`)."""
    tk = coursemod.tokens(course)
    section_re = re.compile(rf"^## {re.escape(tk['section'])} (\d+)\s*[—-]")
    found: dict[str, dict] = {}
    for unit in course.get("units") or []:
        path = coursemod.unit_dir(course["_dir"], unit["n"]) / "content.md"
        if not path.exists():
            continue
        section, inside = None, False
        for line in path.read_text(encoding="utf-8").splitlines():
            m = section_re.match(line)
            if m:
                section, inside = int(m.group(1)), False
            elif DIALOG_OPEN.match(line.strip()):
                inside = True
            elif line.strip() == ":::":
                inside = False
            elif inside and section is not None and (m := DIALOG_LINE.match(line.strip())):
                name = m.group(1).strip()
                if storymod.is_learner(course, name) or storymod.is_anonymous(course, name):
                    continue
                name = storymod.canonical(course, name) or name
                units = found[character_asset_id(name)]["dialogue_units"] if character_asset_id(name) in found else []
                if unit["n"] not in units:
                    units.append(unit["n"])
                found.setdefault(character_asset_id(name), {
                    "id": character_asset_id(name), "unit": unit["n"], "section": section, "type": "image", "character": name,
                    "title": t("media", "character_title", name=name), "description": t("media", "character_description", name=name),
                    "specs": t("media", "character_specs"), "dialogue_units": units, **({"avatar": storymod.avatar(course, name)}
                                                              if storymod.avatar(course, name) else {})})
    return list(found.values())


STYLES = ("flat", "pixel-art", "3d", "isometric", "illustration", "photo")
SIMULATION_KINDS = ("background", "layer", "portrait")  # the images of the simulations (their `kind` in the manifest)


def visual(course: dict) -> dict:
    """The visual style in force for a course (`media › visual`), checked."""
    value = dict(config(course=course).get("visual") or {})
    for key in ("style", "fallback"):
        if value.get(key) not in STYLES:
            raise MediaError(t("media", "bad_style", key=key, value=value.get(key), valid=", ".join(STYLES)))
    return value


def scan_simulations(course: dict) -> list[dict]:
    """An image for every background, layer and portrait (with each expression) of the simulations of the course, one per id
    in the whole course; the first simulation that uses it gives the unit and the section. A portrait carries the `look` of
    its character in the story bible."""
    from coursekit import simulation as simmod
    from coursekit import story as storymod
    from coursekit.verify import Report, parse_directives

    rules = coursemod.rules(course)["content"]
    names = tuple(rules.get("simulation_directives") or ())
    bible, _ = storymod.load(course) if (course["_dir"] / storymod.FILE).exists() else (None, [])
    looks = {str(p.get("name", "")).strip().casefold(): str(p.get("look") or "") for p in (bible or {}).get("characters") or []
             if isinstance(p, dict)}
    tk = coursemod.tokens(course)
    section_re = re.compile(rf"^## {re.escape(tk['section'])} (\d+)\s*[—-]")
    found: dict[str, dict] = {}
    for unit in course.get("units") or []:
        folder = coursemod.unit_dir(course["_dir"], unit["n"])
        for name in ("content.md", "assessment.md"):
            path = folder / name
            if not path.exists():
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
            for line_no, directive, body in parse_directives(path, lines, rules, Report()):
                if directive not in names:
                    continue
                section = next((int(m.group(1)) for line in reversed(lines[:line_no]) if (m := section_re.match(line))), 0)
                try:
                    data = yaml.safe_load("\n".join(body))
                except yaml.YAMLError:
                    continue
                if not isinstance(data, dict):
                    continue
                for ref in simmod.media_refs(data):
                    entry = {"id": ref["id"], "unit": unit["n"], "section": section, "type": "image", "kind": ref["kind"],
                             "simulation": str(data.get("id") or "")}
                    if ref["kind"] == "portrait":
                        look = looks.get(ref["character"].casefold(), "")
                        entry.update(character=ref["character"], expression=ref["expression"] or None,
                                     title=t("media", "portrait_title", name=ref["character"],
                                             expression=f" ({ref['expression']})" if ref["expression"] else ""),
                                     description=t("media", "portrait_description", name=ref["character"], look=look or "-",
                                                   expression=ref["expression"] or t("media", "expression_neutral")),
                                     specs=t("media", "portrait_specs"))
                    elif ref["kind"] == "voice":  # the narration of a scene: `coursekit media narrate` produces it
                        speaker = ref["character"] or t("media", "voice_narrator")
                        entry.update(type="audio", title=t("media", "voice_title", simulation=data.get("id"), id=ref["id"]),
                                     description=t("media", "voice_description", speaker=speaker), narration=ref["description"],
                                     character=ref["character"] or None, specs=t("media", "voice_specs"))
                    else:
                        entry.update(title=ref["description"],
                                     description=t("media", f"{ref['kind']}_description", text=ref["description"]),
                                     specs=t("media", f"{ref['kind']}_specs"))
                    found.setdefault(ref["id"], entry)
                if coursemod.backend(course) == "creator" and data.get("id"):
                    from coursekit.htmlkit.simpackage import asset_id

                    found.setdefault(asset_id(str(data["id"])), {
                        "id": asset_id(str(data["id"])), "unit": unit["n"], "section": section, "type": "simulation",
                        "kind": "package", "simulation": str(data["id"]), "title": str(data.get("title") or data["id"]),
                        "description": t("media", "package_description", id=data["id"]), "specs": t("media", "package_specs")})
    return list(found.values())


def load_manifest(course_dir):
    ry = roundtrip_yaml()
    path = course_dir / "media" / "manifest.yaml"
    data = ry.load(path.read_text(encoding="utf-8")) if path.exists() else None
    if not data:
        data = {"assets": []}
    if data.get("assets") is None:
        data["assets"] = []
    return ry, path, data


def save_manifest(ry, path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    save_yaml_atomic(ry, data, path)


@contextmanager
def editing_manifest(course_dir: Path):
    """The manifest to change, locked from the read to the write: agents working in parallel (`media set` from several at once)
    each change it on top of what the others saved, and none loses what another wrote. Saved when the block ends without an error."""
    try:
        with file_lock(course_dir / "media" / ".manifest.lock"):
            ry, path, data = load_manifest(course_dir)
            yield data
            save_manifest(ry, path, data)
    except LockTimeout:
        raise MediaError(t("media", "manifest_locked", path=(course_dir / "media" / "manifest.yaml").as_posix())) from None


def extract(course: dict) -> dict[str, int]:
    with editing_manifest(course["_dir"]) as data:
        return _extract(course, data)


def _extract(course: dict, data: dict) -> dict[str, int]:
    existing = {a["id"]: a for a in data["assets"]}
    simulations = scan_simulations(course)
    of_simulations = {a["id"] for a in simulations}
    # a character who speaks in a dialogue and appears in a simulation has one portrait: the one of the simulation, transparent
    # and larger, which also serves as the avatar of the dialogue
    characters = scan_characters(course)
    for asset in simulations:  # the dialogues that take the portrait of a simulation show it too
        speaks = next((c["dialogue_units"] for c in characters if c["id"] == asset["id"]), None)
        if speaks:
            asset["dialogue_units"] = speaks
    found = scan(course) + [a for a in characters if a["id"] not in of_simulations] + simulations
    merged = []
    for asset in found:
        old = existing.pop(asset["id"], None)
        if old is not None:
            changed = any(old.get(k) != asset.get(k) for k in ("type", "title", "description", "specs", "kind", "narration",
                                                               "body"))
            for k, v in asset.items():
                old[k] = v
            if "dialogue_units" not in asset:
                old.pop("dialogue_units", None)
            if changed and old.get("status") not in (None, "pending"):
                old["status"] = "pending"
                old["note"] = "The placeholder changed in the content: produce it again"
            merged.append(old)
        else:
            merged.append({**asset, "status": "pending", "recipe": None, "file": None, "asset_path": None,
                           "alt": None, "transcript": None, "subtitles_path": None})
    for orphan in existing.values():
        orphan["status"] = "orphaned"
        merged.append(orphan)
    data["assets"] = merged
    from coursekit import anchors as anchorsmod

    with_points = anchorsmod.points_of(course, merged)
    for asset in merged:  # the images with points: the media agent leaves room and their crosshairs are drawn on them
        if with_points.get(asset["id"]):
            asset["points"] = [p.label for p in with_points[asset["id"]]]
        else:
            asset.pop("points", None)
    for asset in merged:
        if asset.get("avatar") and asset.get("status") in (None, "pending"):
            _take_avatar(course, asset)
    by_status: dict[str, int] = {}
    for a in merged:
        by_status[a["status"]] = by_status.get(a["status"], 0) + 1
    return dict(sorted(by_status.items()))


def _take_avatar(course: dict, asset: dict) -> None:
    """The portrait of a speaker with an avatar of the brand (`speakers › avatars`): that file, copied as the produced asset."""
    origin = next((base / asset["avatar"] for base in (course["_dir"], course["_project"].root) if (base / asset["avatar"]).is_file()),
                  None)
    if origin is None:
        asset["note"] = t("media", "avatar_missing", path=asset["avatar"])
        return
    target = course["_dir"] / "media" / "files" / f"{asset['id']}{origin.suffix.lower()}"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origin, target)
    asset.update(status="produced", recipe="brand-avatar", file=f"media/files/{target.name}", made_with="brand-avatar",
                 alt=asset.get("alt") or asset.get("character"))
    asset.pop("note", None)


DOWNLOAD_HINT = re.compile(r"\b(pdf|descargable|descarga|download|downloadable|docx|xlsx|pptx)\b", re.I)


def missing_downloads(asset: dict) -> list[str]:
    """Why a produced asset still lacks the downloadable file its specs ask for."""
    if asset.get("status") in (None, "pending", "scripted", "orphaned"):
        return []
    if not DOWNLOAD_HINT.search(f"{asset.get('specs') or ''} {asset.get('how') or ''}"):
        return []
    downloads = asset.get("downloads") or []
    if not downloads:
        return [t("media", "missing_download_specs")]
    if asset.get("status") == "uploaded" and not all(d.get("asset_path") for d in downloads):
        return [t("media", "missing_download_upload")]
    return []


def missing_uploads(course: dict, asset: dict) -> list[int]:
    """The units whose dialogues show an uploaded portrait that is not uploaded to their content yet (creator takes an image
    only from the content that shows it: `asset_path` is the one of the content of the asset's unit, `uploads` the others)."""
    if asset.get("status") != "uploaded" or coursemod.backend(course) != "creator":
        return []
    uploads = asset.get("uploads") or {}
    missing = []
    for n in asset.get("dialogue_units") or []:
        if n == asset.get("unit"):
            if not asset.get("asset_path"):
                missing.append(n)
            continue
        unit = coursemod.package_unit(course, n)
        if not (unit and unit.get("content_id") and uploads.get(str(unit["content_id"]))):
            missing.append(n)
    return missing


def style_approval(course: dict) -> dict | None:
    """The last sign-off of the style sheet of the course (`coursekit approve style`), while the style has not changed since."""
    approvals = [a for a in course.get("approvals") or [] if a.get("gate") == "style"]
    if not approvals:
        return None
    try:
        current = visual(course)["style"]
    except MediaError:
        return None
    return approvals[-1] if approvals[-1].get("style") in (current, visual(course)["fallback"]) else None


def plan(course: dict) -> tuple[list[str], list[str]]:
    """(warnings, lines): the production options of every pending asset."""
    cfg = config(course=course)
    root = course["_project"].root if course.get("_project") else None
    _, _, data = load_manifest(course["_dir"])
    warnings = [f"{a['id']}: {p}" for a in data["assets"] for p in missing_downloads(a)]
    if course.get("_project"):
        warnings += [t("media", "missing_unit_upload", asset=a["id"], units=", ".join(str(n) for n in units), code=course["code"])
                     for a in data["assets"] if (units := missing_uploads(course, a))]
    uses_theme = [a for a in data["assets"] if a["type"] in (cfg.get("uses_theme") or [])]
    if uses_theme and course.get("_project"):
        found = thememod.status(course["_project"], course)
        if found.state != "derived":
            warnings.append(t("media", f"theme_{found.state}", code=course["code"]))
        elif found.tokens:
            current = thememod.fingerprint(found.tokens)
            warnings += [t("media", "theme_changed", asset=a["id"]) for a in uses_theme
                         if a.get("status") in ("produced", "uploaded") and a.get("theme") and a["theme"] != current]
    lines = []
    simulation_assets = [a for a in data["assets"] if a.get("kind") in SIMULATION_KINDS and a.get("status") != "orphaned"]
    if simulation_assets:
        style = visual(course)
        generator = any(requirement_met(o.get("needs"), root) is not False for o in cfg["types"].get("image", [])
                        if o.get("id") not in ("agent-svg", "creator-stock"))
        lines.append(t("media", "style_line", style=style["style"] if generator else style["fallback"]))
        if not generator:
            warnings.append(t("media", "no_generator", fallback=style["fallback"]))
        if not style_approval(course):
            warnings.append(t("media", "style_not_approved", code=course["code"]))
    from coursekit import mediastyle

    if mediastyle.waiting(course):
        warnings.append(t("media", "media_style_not_approved", code=course["code"]))
    guide = mediastyle.path(course)
    missing = mediastyle.missing_notes(guide) if guide else []
    if missing:
        warnings.append(t("media", "media_style_notes_missing", count=len(missing), path=guide.parent.name + "/notes.md"))
    required, real = depicts_rules(cfg)
    from coursekit import capture as capturemod

    capturable = set(capturemod.capturable(course))
    for a in (a for a in data["assets"] if a.get("status") in ("pending", "scripted")):
        chain = options_for(a["type"], cfg, root)
        real_interface = a.get("depicts") == "interface"
        chain = [o for o in chain if (o["id"] in real or o.get("shows") == "interface")] if real_interface \
            else [o for o in chain if o.get("shows") != "interface"]
        lines.append(f"{a['id']} [{a['type']}] {a.get('title', '')}")
        lines += _script_lines(course, a)
        if real_interface:
            lines.append(t("media", "interface_line"))
            waiting = capture_waiting(a)
            if waiting:
                note = (a.get("capture") or {}).get("note") or "—"
                lines.append(t("media", f"capture_{waiting}_line", code=course["code"], id=a["id"], note=note))
            elif awaiting_recording(a) and str(a["id"]) in capturable:
                lines.append(t("media", "capturable_line", path=f"media/scripts/{a['id']}.md"))
            elif awaiting_recording(a):
                lines.append(t("media", "awaiting_line", path=f"media/scripts/{a['id']}.md", folder=f"media/recordings/{a['id']}"))
        elif a["type"] in required and not a.get("depicts"):
            lines.append(t("media", "classify_line", id=a["id"]))
        if not chain:
            lines.append(t("media", "interface_no_option" if real_interface else "no_option"))
        for option in chain:
            settings = ", ".join(f"{key}: {option[key]}" for key in ("model", "resolution", "variants") if option.get(key) is not None)
            lines.append(f"  - {option['id']} ({option['available']}): {option['how']}" + (f" [{settings}]" if settings else ""))
        if a["type"] in ("video", "audio"):
            for group in ("voice", "subtitles"):
                avail = [o["id"] for o in cfg[group] if requirement_met(o.get("needs"), root) is not False]
                lines.append(t("media", f"{group}_options", options=", ".join(avail)) if avail else t("media", f"{group}_none"))
    return warnings, lines


def providers(project) -> list[str]:
    cfg = config(project)
    seen = {}
    for group in [*cfg["types"].values(), cfg["voice"], cfg["subtitles"]]:
        for option in group:
            seen.setdefault(option["id"], option)
    words = {True: t("media", "provider_available"), False: t("media", "provider_missing"), None: t("media", "provider_mcp")}
    width = max(len(w) for w in words.values()) + 1
    out = []
    for oid, option in seen.items():
        met = requirement_met(option.get("needs"), project.root if project else None)
        out.append(f"{oid:<22} {words[met]:<{width}} {option['needs']}")
    return out


def embed(course: dict, asset_id: str) -> str:
    """Wraps the SVG of an asset in `media/src/<id>/index.html`, the EMBED package that creator takes in place of an SVG image; for
    the package of a simulation (`SIM-…`), builds the simulation with its images."""
    _, _, data = load_manifest(course["_dir"])
    asset = next((a for a in data["assets"] if a["id"] == asset_id), None)
    if asset is None:
        raise MediaError(t("media", "asset_not_found", asset_id=asset_id))
    from coursekit.htmlkit import embedbridge

    if asset.get("kind") == "package":
        from coursekit import assemble as assemblemod
        from coursekit.htmlkit import simpackage

        unit = next((u for u in course.get("units") or [] if u["n"] == asset.get("unit")), None)
        plan_data, _, _ = assemblemod.build_plan(course, unit, simulations=True) if unit else ({"lessons": []}, [], [])
        brick = next((b for lesson in plan_data["lessons"] for b in assemblemod.walk(lesson["bricks"])
                      if b["type"] == "SIMULATION" and b["data"].get("id") == asset.get("simulation")), None)
        if brick is None:
            raise MediaError(t("media", "package_not_found", asset=asset_id))
        page = simpackage.build(course, brick, course["_dir"] / "media" / "src" / asset_id)
        return t("media", "embed_written", path=page.as_posix(), asset=asset_id)
    source = course["_dir"] / "media" / str(asset.get("file") or "").removeprefix("media/")
    if not str(asset.get("file") or "").lower().endswith(".svg") or not source.is_file():
        raise MediaError(t("media", "embed_needs_svg", asset=asset_id))
    svg = re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", source.read_text(encoding="utf-8"))
    title = (asset.get("title") or asset_id).replace("&", "&amp;").replace("<", "&lt;")
    page = (f'<!doctype html>\n<html lang="{coursemod.language(course)}">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{title}</title>\n<style>html,body{{margin:0;background:transparent}}svg{{display:block;width:100%;height:auto}}\n"
            "@media (prefers-reduced-motion: reduce){svg *{animation-play-state:paused !important}}</style>\n</head>\n"
            f"<body>\n{svg}\n<script>\n{embedbridge.script()}</script>\n</body>\n</html>\n")
    folder = course["_dir"] / "media" / "src" / asset_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "index.html").write_text(page, encoding="utf-8", newline="\n")
    embedbridge.write_manifest(folder, ["resize"])  # it takes the height of the drawing; nothing to finish
    return t("media", "embed_written", path=(folder / "index.html").as_posix(), asset=asset_id)


def narrate(course: dict, ids: list[str] | None = None, again: bool = False, say=print, batch: bool = False) -> int:
    """Produce the narration of the scenes (`VO-…`, simulations with `audio: true`) with the configured voices: the character
    of a conversation with its own voice (`coursekit voice set --character`), the rest with the voice of the course. Only the
    ones still pending, unless they are named or `again`. Returns how many were produced (with `batch`, how many were put in the
    queue of the Gemini batch: `coursekit tts-batch collect` produces them)."""
    import tempfile

    from coursekit import mediatools, ttsbatch

    _, _, data = load_manifest(course["_dir"])
    todo = [a for a in data["assets"] if a.get("kind") == "voice" and a.get("narration")
            and ((ids and a["id"] in ids) or (not ids and (again or a.get("status") in (None, "pending", "scripted"))))]
    done = 0
    for asset in todo:
        out = course["_dir"] / "media" / "files" / f"{asset['id']}.mp3"
        if batch:
            try:
                if ttsbatch.add(course, "narrate", str(asset["id"]), str(asset["narration"]), out, asset=str(asset["id"]),
                                character=asset.get("character") or None):
                    say(t("media", "narration_queued", asset=asset["id"]))
                    done += 1
            except ttsbatch.BatchError as exc:
                raise MediaError(str(exc)) from None
            continue
        with tempfile.TemporaryDirectory() as tmp:
            text = Path(tmp) / "scene.txt"
            text.write_text(str(asset["narration"]), encoding="utf-8")
            say(mediatools.tts(course, None, text, out, character=asset.get("character") or None))
        with editing_manifest(course["_dir"]) as fresh:  # after each one: a provider that fails halfway keeps what was made
            saved = next((a for a in fresh["assets"] if a["id"] == asset["id"]), None)
            if saved is not None:
                saved.update(status="produced", file=f"media/files/{out.name}", transcript=str(asset["narration"]),
                             recipe="coursekit media narrate", note=None)
        done += 1
    return done


def stock(course: dict, asset_id: str, find: str | None = None, take: int | None = None, color: str | None = None,
          limit: int = 12) -> list[str]:
    """`coursekit media stock`: the illustrations of the illustration sources of the brand for a resource (`find`, in English),
    or one of them taken as its SVG (`take`), recoloured to the brand and recorded with where it comes from."""
    from coursekit import brand, illustrations

    _, _, data = load_manifest(course["_dir"])
    asset = next((a for a in data["assets"] if a["id"] == asset_id), None)
    if asset is None:
        raise MediaError(t("media", "asset_not_found", asset_id=asset_id))
    if not find and not take:
        raise MediaError(t("illustrations", "stock_needs"))
    cfg = config(course=course).get("stock") or {}
    sources = illustrations.load(brand.folder(course["_project"], course))
    if not any(s.get("author_id") for s in sources):
        raise MediaError(t("illustrations", "no_sources"))
    try:
        if find:
            found = illustrations.search(sources, find, color if color is not None else cfg.get("color"), limit)
            return [t("illustrations", "candidate", id=f["id"], title=f["title"], author=f["author"],
                      licenses=", ".join(f["licenses"]) or "?", preview=f["preview"] or "—") for f in found] \
                or [t("illustrations", "none_found", term=find)]
        svg, _ = illustrations.download_svg(int(take))
        about = illustrations.detail(int(take))
    except illustrations.IllustrationError as exc:
        raise MediaError(str(exc)) from None
    if cfg.get("color") == "black" and not illustrations.is_line_art(svg):  # a colour version: the line one is another resource
        raise MediaError(t("illustrations", "not_line_art", resource=take))
    try:
        colors = thememod.load(course["_project"], course).get("color") or {}
    except thememod.ThemeError as exc:
        raise MediaError(str(exc)) from None
    ink, paper = colors.get(str(cfg.get("ink") or "text"), "#000000"), colors.get(str(cfg.get("paper") or "background"), "#FFFFFF")
    out = course["_dir"] / "media" / "files" / f"{asset_id}.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(illustrations.recolour(svg, ink, paper), encoding="utf-8", newline="\n")
    author = about.get("author")
    with editing_manifest(course["_dir"]) as fresh:
        saved = next((a for a in fresh["assets"] if a["id"] == asset_id), None)
        if saved is None:
            raise MediaError(t("media", "asset_not_found", asset_id=asset_id))
        saved.update(file=f"media/files/{out.name}", recipe="magnific-stock",
                     source={"provider": "magnific", "resource": int(take), "author": author, "url": about.get("url"),
                             "license": about.get("license"), "license_url": about.get("license_url")})
    return [t("illustrations", "taken", asset=asset_id, path=f"media/files/{out.name}", resource=take, author=author or "?", ink=ink)]


def image_tool(course: dict, asset_id: str | None, action: str, size: str | None = None, file: str | None = None) -> str:
    """`fit`: the file of an asset to an exact size; `render`: its SVG as a PNG next to it (to look at it, and for creator).
    With `file`, that file instead of the one of the manifest: one not recorded yet, or a sample of the style sheet."""
    from coursekit import mediatools

    bases = (course["_dir"], course["_dir"] / "media", course["_project"].root)
    if file:
        path = next((base / file for base in bases if (base / file).is_file()), None)
        if path is None:
            raise MediaError(t("media", "file_not_found", file=file))
    else:
        _, _, data = load_manifest(course["_dir"])
        asset = next((a for a in data["assets"] if a["id"] == asset_id), None)
        if asset is None:
            raise MediaError(t("media", "asset_not_found", asset_id=asset_id))
        if asset["type"] == JOB_AID and action == "render":  # made from its text, not from a file
            return render_job_aid(course, asset_id)
        path = next((base / str(asset.get("file") or "") for base in bases[:2]
                     if asset.get("file") and (base / str(asset["file"])).is_file()), None)
        if path is None:
            raise MediaError(t("media", "asset_without_file", asset=asset_id))
    if action == "fit":
        return mediatools.fit(path, mediatools.parse_size(size or ""))
    if path.suffix.lower() != ".svg":
        raise MediaError(t("media", "render_needs_svg", asset=asset_id or path.name))
    from coursekit import brand

    sheet = brand.fonts_stylesheet(course["_project"], course)
    try:
        fonts_css = brand.inline_fonts(sheet, course["_project"].root)[0] if sheet else None
    except brand.BrandError as exc:
        raise MediaError(str(exc)) from None
    return mediatools.render_svg(path, path.with_suffix(".png"), mediatools.parse_size(size) if size else None, fonts_css)


def anchors(course: dict, ids: list[str] | None = None, sets: list[str] | None = None) -> list[str]:
    """Draws the crosshairs of the points on their images (all of them, or the ones named) from the content, and records them
    in the manifest. `sets` ("<point>=x,y", with one image named) first writes the position of those points in the content."""
    from coursekit import anchors as anchorsmod
    from coursekit.lang import directive_key

    with editing_manifest(course["_dir"]) as data:
        live = [a for a in data["assets"] if a.get("status") != "orphaned"]
        if sets:
            if not ids or len(ids) != 1:
                raise MediaError(t("anchors", "set_needs_one_image"))
            key = directive_key(coursemod.tokens(course), "position")
            for item in sets:
                label, _, value = item.partition("=")
                parts = [v.strip() for v in value.split(",")]
                try:
                    at = (float(parts[0]), float(parts[1]))
                except (ValueError, IndexError):
                    raise MediaError(t("anchors", "bad_set", value=item)) from None
                if not all(0 <= v <= 100 for v in at):
                    raise MediaError(t("anchors", "bad_set", value=item))
                points = anchorsmod.points_of(course, live).get(ids[0], [])
                point = next((p for p in points if p.label == label.strip()), None)
                if point is None:
                    raise MediaError(t("anchors", "unknown_point", label=label.strip(), asset=ids[0],
                                       points=", ".join(p.label for p in points) or "-"))
                if point.kind != "point":
                    raise MediaError(t("anchors", "hotspot_moves_in_content", label=point.label))
                anchorsmod.set_position(point, at, key)
        out = []
        for asset_id, points in anchorsmod.points_of(course, live).items():
            if ids and asset_id not in ids:
                continue
            asset = next((a for a in live if a["id"] == asset_id), None)
            if asset is None:
                continue
            missing = [p.label for p in points if p.at is None]
            if missing:
                out.append(t("anchors", "without_position", asset=asset_id, points=", ".join(missing), code=course["code"]))
                continue
            path = next((base / str(asset.get("file") or "") for base in (course["_dir"] / "media", course["_dir"])
                         if asset.get("file") and (base / str(asset["file"])).is_file()), None)
            if path is None:
                out.append(t("anchors", "not_produced", asset=asset_id))
                continue
            marks = anchorsmod.recorded(points)
            try:
                anchorsmod.draw(path, marks)
            except anchorsmod.AnchorError as exc:
                raise MediaError(f"{asset_id}: {exc}") from None
            changed = asset.get("anchors") != marks
            asset["anchors"] = marks
            if changed and asset.get("status") == "uploaded":  # the platform has the image without these crosshairs
                asset["status"], asset["asset_path"] = "produced", None
                asset["note"] = "The crosshairs changed: upload it again"
            out.append(t("anchors", "drawn", asset=asset_id, count=len(marks), file=path.name)
                       + (" " + t("anchors", "render_again", code=course["code"], asset=asset_id)
                          if path.suffix.lower() == ".svg" and coursemod.backend(course) == "creator" else ""))
        return out


def render_job_aid(course: dict, asset_id: str) -> str:
    """The PDF of a job aid (media/<id>.pdf), from the text of its placeholder and the template of the theme."""
    from coursekit import jobaid, mediatools

    _, _, data = load_manifest(course["_dir"])
    asset = next((a for a in data["assets"] if a["id"] == asset_id), None)
    if asset is None:
        raise MediaError(t("media", "asset_not_found", asset_id=asset_id))
    try:
        out, warnings = jobaid.render_asset(course, asset)
    except (jobaid.JobAidError, mediatools.ToolError) as exc:
        raise MediaError(str(exc)) from None
    root = course["_project"].root
    return "\n".join([t("jobaid", "rendered", path=out.relative_to(root).as_posix(), code=course["code"], asset=asset_id,
                         file=out.relative_to(course["_dir"] / "media").as_posix()),
                       *(t("commands", "warning_line", text=w) for w in warnings)])


def optimize(course: dict, ids: list[str] | None = None) -> list[str]:
    """Makes the files of the produced assets lighter, in place (images scaled and recompressed, MP4 re-encoded): the ones named,
    else all. What cannot be made lighter (SVG, GIF, audio, packages) stays as it is. One line per file."""
    from coursekit import mediaopt

    cfg = config(course=course)
    _, _, data = load_manifest(course["_dir"])
    known = {a["id"] for a in data["assets"]}
    for asset_id in ids or []:
        if asset_id not in known:
            raise MediaError(t("media", "asset_not_found", asset_id=asset_id))
    lines = []
    for asset in data["assets"]:
        if (ids and asset["id"] not in ids) or asset.get("status") not in ("produced", "uploaded") or not asset.get("file"):
            continue
        path = next((base / str(asset["file"]) for base in (course["_dir"], course["_dir"] / "media")
                     if (base / str(asset["file"])).is_file()), None)
        if path is None:
            continue
        line = mediaopt.shrink(path, cfg)
        if line:
            lines.append(f"{asset['id']}: {line}")
    return lines


def adopt(course: dict, asset_id: str, source: str, alt: str | None = None) -> str:
    """Takes a file that already exists (an image of an imported package, in the brief) as the produced asset `asset_id`:
    it is copied to media/files/<id>.<ext> and the asset is marked produced, so it is not made again."""
    _, _, data = load_manifest(course["_dir"])
    if not any(a["id"] == asset_id for a in data["assets"]):
        raise MediaError(t("media", "asset_not_found", asset_id=asset_id))
    origin = Path(source)
    if not origin.is_absolute():
        origin = next((base / origin for base in (course["_dir"], course["_project"].root) if (base / origin).is_file()), origin)
    if not origin.is_file():
        raise MediaError(t("media", "adopt_missing", path=source))
    target = course["_dir"] / "media" / "files" / f"{asset_id}{origin.suffix.lower()}"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origin, target)
    # a file that already exists was not made with the tokens of the theme: the guard of the media that use it does not apply
    return set_asset(course, asset_id, status="produced", recipe="imported", file=f"media/files/{target.name}", alt=alt,
                     made_with="imported", force=True)


STALE = ("file", "alt", "transcript", "subtitles_path", "made_with")


def redo(course: dict, ids: list[str] | None = None, everything: bool = False, clean: bool = False,
         recapture: bool = False) -> list[str]:
    """Marks assets to be produced again: the ones named, else those that use the theme and were made with other tokens than the
    current ones (every one that uses the theme with `everything`). They go back to `scripted`, forgetting the fingerprint and
    the uploaded path; their script and file stay for the agent to start from. With `clean` they also forget the file, the alt
    text, the transcript, the captions and the tool that made them (the files stay on disk): for what is made again from
    nothing, as a resource that showed an interface that was invented. With `recapture` a resource that shows a real interface
    also forgets its capture and its recordings leave media/recordings/ (to .cache/capture/<CODE>/replaced/<time>/): it waits
    to be captured again (by a person, or by the media agent when a permission allows it), instead of being composed again
    from the recording it had."""
    with editing_manifest(course["_dir"]) as data:
        chosen = _redo(course, data, ids, everything, clean, recapture)
        interface = [a["id"] for a in data["assets"] if a["id"] in chosen and a.get("depicts") == "interface"]
    if recapture and interface:
        _set_aside_recordings(course, interface)
    return chosen


def _set_aside_recordings(course: dict, ids: list[str]) -> None:
    """The recordings of these resources out of media/recordings/ (a file there is real material to compose from), kept in
    the cache of the project in case a person wants them back."""
    import datetime as dt

    folder = course["_dir"] / "media" / "recordings"
    target = course["_project"].cache_dir / "capture" / course["code"] / "replaced" / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    for asset_id in ids:
        for path in sorted(folder.glob(f"{asset_id}.*")) + sorted(folder.glob(f"{asset_id}-*.*")):
            target.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), target / path.name)


def _redo(course: dict, data: dict, ids: list[str] | None, everything: bool, clean: bool, recapture: bool = False) -> list[str]:
    cfg = config(course=course)
    found = thememod.status(course["_project"], course)
    current = thememod.fingerprint(found.tokens) if found.tokens else None
    known = {a["id"] for a in data["assets"]}
    for asset_id in ids or []:
        if asset_id not in known:
            raise MediaError(t("media", "asset_not_found", asset_id=asset_id))
    chosen = []
    for asset in data["assets"]:
        if ids:
            hit = asset["id"] in ids
        else:
            themed = asset["type"] in (cfg.get("uses_theme") or []) and asset.get("status") in ("produced", "uploaded")
            hit = themed and (everything or bool(asset.get("theme") and current and asset["theme"] != current))
        if hit:
            asset["status"] = "scripted"
            asset.pop("theme", None)
            asset["asset_path"] = None
            asset.pop("uploads", None)
            if clean:
                for key in STALE:
                    asset[key] = None
                for download in asset.get("downloads") or []:
                    download["asset_path"] = None
            for download in asset.get("downloads") or []:
                download["asset_path"] = None
            if recapture and asset.get("depicts") == "interface":
                asset.pop("capture", None)  # the recording on disk is replaced by the next one
            chosen.append(asset["id"])
    return chosen


def set_asset(course: dict, asset_id: str, **values) -> str:
    """Update an asset of the manifest. `download` adds or updates an extra downloadable file."""
    with editing_manifest(course["_dir"]) as data:
        return _set_asset(course, data, asset_id, **values)


def _set_asset(course: dict, data: dict, asset_id: str, **values) -> str:
    asset = next((a for a in data["assets"] if a["id"] == asset_id), None)
    if asset is None:
        raise MediaError(t("media", "asset_not_found", asset_id=asset_id))
    cfg = config(course=course)
    statuses = cfg["statuses"]
    if values.get("status") and values["status"] not in statuses:
        raise MediaError(t("media", "bad_status", statuses=statuses))
    if values.get("status") in ("produced", "uploaded") and asset.get("kind") in SIMULATION_KINDS and not values.get("force"):
        if not style_approval(course):
            raise MediaError(t("media", "style_not_approved", code=course["code"]))
    visual_types = set(cfg.get("uses_theme") or []) | {"image"}
    if values.get("status") in ("produced", "uploaded") and asset["type"] in visual_types and not values.get("force"):
        from coursekit import mediastyle

        if mediastyle.waiting(course):
            raise MediaError(t("media", "media_style_not_approved", code=course["code"]))
    if values.get("status") in ("produced", "uploaded") and asset["type"] in (cfg.get("uses_theme") or []):
        found = thememod.status(course["_project"], course)
        if found.state != "derived" and not values.get("force"):
            raise MediaError(t("media", f"theme_{found.state}", code=course["code"]))
        if found.tokens:
            asset["theme"] = thememod.fingerprint(found.tokens)
    capture_state = (asset.get("capture") or {}).get("state")
    if values.get("status") in ("produced", "uploaded") and capture_state in ("captured", "rejected"):
        raise MediaError(t("media", f"capture_{capture_state}", asset=asset_id, code=course["code"]))
    first_time = asset.get("status") not in ("produced", "uploaded")
    depicts = values.get("depicts") or asset.get("depicts")
    if depicts and depicts not in DEPICTS:
        raise MediaError(t("media", "bad_depicts", value=depicts, valid=", ".join(DEPICTS)))
    required, real = depicts_rules(cfg)
    recipe = values.get("recipe") or asset.get("recipe")
    in_simulation = asset.get("kind") in SIMULATION_KINDS  # backgrounds, layers, portraits: the application there is fictional
    if values.get("status") in ("produced", "uploaded") and first_time and asset["type"] in required and recipe not in real \
            and not in_simulation:
        if not depicts:  # a generated resource says what it shows; a real one (a capture, a recording) needs not
            raise MediaError(t("media", "depicts_missing", asset=asset_id))
        if depicts == "interface":
            raise MediaError(t("media", "interface_generated", asset=asset_id, recipe=recipe or "-", allowed=", ".join(real)))
    if values.get("depicts"):
        asset["depicts"] = values["depicts"]
    unit_n = values.get("unit")
    if unit_n is not None and values.get("asset_path") is None:
        raise MediaError(t("media", "unit_needs_asset_path"))
    if unit_n is not None and unit_n != asset.get("unit"):
        # the copy uploaded to the content of another unit (a portrait its dialogues show): creator takes an image only from
        # the content that shows it
        unit = coursemod.package_unit(course, unit_n)
        if unit is None:
            raise MediaError(t("media", "unit_not_found", n=unit_n))
        if not unit.get("content_id"):
            raise MediaError(t("media", "unit_without_content", n=unit_n))
        asset["uploads"] = {**(asset.get("uploads") or {}), str(unit["content_id"]): values["asset_path"]}
        values = {**values, "asset_path": None}
    for key in ("status", "recipe", "asset_path", "file", "alt", "transcript", "subtitles_path", "made_with"):
        if values.get(key) is not None:
            asset[key] = values[key]
    if values.get("file") and asset["type"] == JOB_AID:  # its weight goes under the title of the download
        local = course["_dir"] / "media" / str(values["file"]).removeprefix("media/")
        if local.is_file():
            asset["size"] = local.stat().st_size
    if values.get("status") in ("produced", "uploaded"):
        asset.pop("note", None)  # "produce it again" no longer applies
    download = values.get("download")
    if download:
        downloads = asset.get("downloads") or []
        entry = next((d for d in downloads if d.get("file") == download), None)
        if entry is None:
            entry = {"file": download, "title": None, "asset_path": None, "size": None}
            downloads.append(entry)
        local = course["_dir"] / "media" / download.removeprefix("media/")
        if local.exists():
            entry["size"] = local.stat().st_size
        if values.get("download_title") is not None:
            entry["title"] = values["download_title"]
        if values.get("download_asset_path") is not None:
            entry["asset_path"] = values["download_asset_path"]
        asset["downloads"] = downloads
    elif values.get("download_title") or values.get("download_asset_path"):
        raise MediaError(t("media", "download_needs_file"))
    return f"{asset_id}: {asset.get('status')}"
