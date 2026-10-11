"""One simulation as a self-contained package (`index.html` and its images) for the backends that take it as an embed: creator
puts it in an EMBED brick. The player of the simulations (`player/expr.js`, `skins.js`, `simulation.js`) goes inline, without a
bundler: each module is wrapped in a function that returns what it exports. Without SCORM inside the embed, its state lives
in the page while it is open.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from coursekit import course as coursemod
from coursekit import simulation as simmod
from coursekit.htmlkit import render
from coursekit.htmlkit.build import project_css, template_dir

MODULES = ("expr", "skins", "simulation")  # in the order they import each other
IMPORT_RE = re.compile(r'^import \{([^}]+)\} from "\./(\w+)\.js";\s*$', re.M)
EXPORT_RE = re.compile(r"^export (?:function|const) (\w+)", re.M)


def inline_player() -> str:
    """The modules of the player of the simulations as one plain script."""
    parts = []
    for name in MODULES:
        code = (template_dir() / "player" / f"{name}.js").read_text(encoding="utf-8")
        exported = EXPORT_RE.findall(code)
        code = IMPORT_RE.sub(lambda m: f"const {{{m.group(1)}}} = __{m.group(2)};", code)
        code = re.sub(r"^export (function|const) ", r"\1 ", code, flags=re.M)
        parts.append(f"const __{name} = (() => {{\n{code}\nreturn {{ {', '.join(exported)} }};\n}})();")
    return "\n".join(parts)


def asset_id(sim_id: str) -> str:
    """Id of the package of a simulation in the media manifest."""
    return f"SIM-{sim_id.upper()}"


def _local_media(course: dict) -> dict[str, Path]:
    """The produced images of the manifest, by id, as files of the course."""
    from coursekit import media as mediamod

    _, _, data = mediamod.load_manifest(course["_dir"])
    found = {}
    for asset in data["assets"]:
        file = str(asset.get("file") or "")
        if not file:
            continue
        for base in (course["_dir"], course["_dir"] / "media"):
            candidate = base / file
            if candidate.is_file():
                found[asset["id"]] = candidate
                break
    return found


def build(course: dict, brick: dict, out_dir: Path) -> Path:
    """Write the package of the simulation of a SIMULATION brick of the plan in `out_dir` (`index.html` and `media/`)."""
    data = json.loads(json.dumps(brick["data"]))
    files = _local_media(course)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "media").mkdir(parents=True)

    def image(asset: str, alt: str) -> dict | None:
        source = files.get(asset)
        if source is None:
            return None
        shutil.copy2(source, out_dir / "media" / source.name)
        return {"path": f"media/{source.name}", "alt": alt}

    def portrait(name: str, expression: object = None) -> dict | None:
        return image(simmod.portrait_id(name, expression), name) or image(simmod.portrait_id(name), name)

    character = str(data.get("character") or "")
    if character:
        data["_portrait"] = portrait(character)
    for scene in (data.get("scenes") or {}).values():
        if scene.get("background"):
            scene["_background"] = image(simmod.background_id(str(scene["background"])), str(scene["background"]))
        for layer in scene.get("layers") or []:
            layer["_image"] = image(simmod.layer_id(str(layer.get("image") or "")), str(layer.get("image") or ""))
        for person in scene.get("characters") or []:
            person["_portrait"] = portrait(str(person.get("name") or ""), person.get("expression"))
        if character:
            scene["_portrait"] = portrait(character, scene.get("expression"))
    ui = coursemod.tokens(course)["player"]
    markup = render.simulation({"type": "SIMULATION", "data": data, "meta": {}}, render.Ctx(ui, "sim"))
    css = project_css(course["_project"], course)
    boot = ("const state = { sims: {} };\n"
            "const tracker = { state, simulation(id, run) { if (run === undefined) return state.sims[id] || null; "
            "state.sims[id] = run; return run; }, interaction() {} };\n"
            f"__simulation.initSimulations(document, {json.dumps(ui, ensure_ascii=False)}, tracker);\n")
    title = re.sub(r"<[^>]+>", "", str(data.get("title") or ""))
    script = inline_player().replace("</script", "<\\/script")
    page = (f'<!doctype html>\n<html lang="{coursemod.language(course)}">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{render.a(title)}</title>\n<style>\n{css}\n.ck-embed-sim .ck-main {{ padding: 0; max-width: none; }}\n"
            ".ck-embed-sim .ck-sim { margin: 0; }\n</style>\n</head>\n"
            f'<body class="ck-js ck-embed-sim">\n<main class="ck-main">{markup}</main>\n'
            f"<script>\n{script}\n{boot}</script>\n</body>\n</html>\n")
    (out_dir / "index.html").write_text(page, encoding="utf-8", newline="\n")
    return out_dir / "index.html"
