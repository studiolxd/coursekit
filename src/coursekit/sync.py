"""`coursekit sync`: derive units and sections in course.yaml from the instructional design.

Input: courses/<CODE>/design/matrix.json, the raw output of the slxd MCP tool
design_matrix_get ({matrix, competencias, objetivos, nodos, actividadesAprendizaje,
actividadesEvaluacion}). The design agent saves it every time it changes the matrix.

Output:
  - course.yaml › units: title, hours, objectives, sections (kind, title, hours, min_words,
    objectives) and activities, in design order;
  - content/unit-NN/content.md and assessment.md skeletons for units that have none (or whose
    content.md is still the untouched skeleton of a previous design).
Existing content is never overwritten; mismatching headings are reported.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

from coursekit import course as coursemod
from coursekit.i18n import t
from coursekit.lang import format_number
from coursekit.util import edit_yaml, render, save_yaml


class DesignError(Exception):
    pass


@dataclass
class SyncResult:
    units: list[dict]
    warnings: list[str] = field(default_factory=list)
    written: list[str] = field(default_factory=list)


def ordered(items):
    return sorted(items, key=lambda x: x.get("orden", 0))


def number(value: float) -> float | int:
    value = round(float(value), 2)
    return int(value) if value.is_integer() else value


def load_graph(path: Path) -> dict:
    if not path.is_file():
        raise DesignError(t("sync", "matrix_missing", path=path.as_posix()))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise DesignError(t("sync", "not_a_matrix", path=path.as_posix())) from exc
    if not isinstance(data, dict):
        raise DesignError(t("sync", "not_a_matrix", path=path.as_posix()))
    for key in ("result", "graph"):  # tolerate the MCP result wrapped in {"result": ...}
        if "nodos" not in data and isinstance(data.get(key), dict):
            data = data[key]
    if "nodos" not in data:
        raise DesignError(t("sync", "not_a_matrix", path=path.as_posix()))
    return data


def build_units(graph: dict, course: dict, cfg: dict, tokens: dict) -> tuple[list[dict], list[str]]:
    problems: list[str] = []
    intro_re = re.compile(tokens["intro_pattern"], re.I)
    summary_re = re.compile(tokens["summary_pattern"], re.I)
    unit_word = tokens["unit"]
    children: dict[str | None, list[dict]] = {}
    for node in graph["nodos"]:
        children.setdefault(node.get("parentId"), []).append(node)
    objectives = {o["id"]: o for o in graph.get("objetivos", [])}

    unit_nodes: list[dict] = []  # design order; with modules, module order first
    for top in ordered(children.get(None, [])):
        if top["tipo"] == "unidad":
            unit_nodes.append(top)
        elif top["tipo"] == "modulo":
            unit_nodes += [n for n in ordered(children.get(top["id"], [])) if n["tipo"] == "unidad"]

    intro = bool(course["design"].get("intro_section", True))
    summary = bool(course["design"].get("summary_section", True))
    units = []
    for un, unit in enumerate(unit_nodes, 1):
        section_nodes = [n for n in ordered(children.get(unit["id"], [])) if n["tipo"] == "apartado"]
        labels: dict[str, str] = {}

        def label(obj_id: str, un: int = un, labels: dict = labels) -> str:
            if obj_id not in labels:
                labels[obj_id] = f"U{un}.{len(labels) + 1}"
            return labels[obj_id]

        sections = []
        for sn, node in enumerate(section_nodes, 1):
            subs = ordered(children.get(node["id"], []))
            hours = node.get("horas")
            if hours is None and subs:
                sub_hours = [s.get("horas") for s in subs]
                hours = sum(sub_hours) if all(h is not None for h in sub_hours) else None
            obj_ids = list(node.get("objetivoIds") or [])
            for sub in subs:
                obj_ids += [o for o in sub.get("objetivoIds") or [] if o not in obj_ids]

            if intro and sn == 1:
                kind = "intro"
                if not intro_re.match(node["titulo"]):
                    problems.append(t("sync", "intro_mismatch", unit=unit_word, n=un, title=node["titulo"]))
            elif summary and sn == len(section_nodes):
                kind = "summary"
                if not summary_re.match(node["titulo"]):
                    problems.append(t("sync", "summary_mismatch", unit=unit_word, n=un, title=node["titulo"]))
            elif obj_ids:
                kind = "content"
            else:
                kind = "activities"

            if hours is None:
                problems.append(t("sync", "section_without_hours", unit=unit_word, n=un, title=node["titulo"]))
                hours = 0
            sections.append({
                "n": sn,
                "kind": kind,
                "title": node["titulo"],
                "hours": number(hours),
                "min_words": coursemod.min_words(hours, cfg),
                "objectives": [label(o) for o in obj_ids],
                "subsections": [s["titulo"] for s in subs],
                "slxd_id": node["id"],
            })

        def unit_activities(key: str, unit_id: str = unit["id"]) -> list[dict]:
            return [a for a in ordered(graph.get(key, [])) if a.get("nodeId") == unit_id]

        for act in unit_activities("actividadesAprendizaje") + unit_activities("actividadesEvaluacion"):
            for o in act.get("objetivoIds") or []:
                label(o)

        unit_hours = unit.get("horas")
        section_hours = sum(s["hours"] for s in sections)
        if unit_hours is None:
            unit_hours = section_hours
        elif abs(unit_hours - section_hours) > 0.01:
            problems.append(t("sync", "unit_hours_mismatch", unit=unit_word, n=un, declared=unit_hours, sections=section_hours))

        units.append({
            "n": un,
            "title": unit["titulo"],
            "hours": number(unit_hours),
            "objectives": [
                {
                    "id": lbl,
                    "bloom": objectives[oid].get("nivelBloom") if oid in objectives else None,
                    "text": objectives[oid].get("texto") if oid in objectives else None,
                    "slxd_id": oid,
                }
                for oid, lbl in labels.items()
            ],
            "sections": sections,
            "activities": {
                "learning": [
                    {"title": a["titulo"], "type": a.get("tipo"), "description": a.get("descripcion"),
                     "objectives": [labels[o] for o in a.get("objetivoIds") or [] if o in labels]}
                    for a in unit_activities("actividadesAprendizaje")
                ],
                "assessment": [
                    {"title": a["titulo"], "instrument": a.get("instrumento"), "criterion": a.get("criterio"),
                     "description": a.get("descripcion"),
                     "objectives": [labels[o] for o in a.get("objetivoIds") or [] if o in labels]}
                    for a in unit_activities("actividadesEvaluacion")
                ],
            },
            "content_id": None,
            "status": "pending",
            "slxd_id": unit["id"],
        })

    total = sum(u["hours"] for u in units)
    if abs(total - float(course["design"]["hours"])) > 0.01:
        problems.append(t("sync", "total_hours_mismatch", total=number(total), hours=course["design"]["hours"]))
    return units, problems


def _unit_template(language: str, name: str) -> str:
    return resources.files(f"coursekit.templates.course.{language}").joinpath(name).read_text(encoding="utf-8")


def skeleton(unit: dict, cfg: dict, tokens: dict, language: str) -> str:
    fmt = lambda n: format_number(n, language)  # noqa: E731
    objectives = "\n".join(f"> - **{o['id']}** — {o['text']}" for o in unit["objectives"]) or "> - (—)"
    blocks = []
    for s in unit["sections"]:
        hint = f"<!-- kind: {s['kind']}"
        if s["objectives"]:
            hint += f" · objectives: {', '.join(s['objectives'])}"
        if s["subsections"]:
            hint += f" · subsections: {' | '.join(s['subsections'])}"
        minimum = tokens["min_words"].format(words=fmt(s["min_words"]))
        blocks.append(f"## {tokens['section']} {s['n']} — {s['title']} *({minimum})*\n\n{hint} -->\n")
    total = sum(s["min_words"] for s in unit["sections"])
    return render(
        _unit_template(language, "content.md"),
        n=unit["n"],
        title=unit["title"],
        hours=unit["hours"],
        pages=total // cfg["words_per_page"],
        words=fmt(total),
        objectives=objectives,
        sections="\n".join(blocks),
    )


def heading_re(tokens: dict) -> re.Pattern:
    return re.compile(rf"^## {re.escape(tokens['section'])} (\d+)\s*[—-]\s*(.+?)\s*(\*\(.*\)\*)?\s*$", re.M)


def sync(course: dict, check_only: bool = False) -> SyncResult:
    course_dir: Path = course["_dir"]
    language = coursemod.language(course)
    tokens = coursemod.tokens(course)
    cfg = coursemod.rules(course)
    graph = load_graph(course_dir / "design" / "matrix.json")
    units, problems = build_units(graph, course, cfg, tokens)
    result = SyncResult(units=units, warnings=list(problems))
    if check_only:
        return result

    path = course_dir / "course.yaml"
    ry, data = edit_yaml(path)
    previous = {u.get("slxd_id"): u for u in data.get("units") or []}
    for unit in units:  # keep the progress fields coursekit already set
        old = previous.get(unit["slxd_id"])
        if old:
            unit["content_id"] = old.get("content_id")
            unit["status"] = old.get("status", "pending")
            for key in ("written_with", "reviewed_with", "reviewed_parts", "review", "links"):
                if old.get(key):
                    unit[key] = old[key]
    data["units"] = units
    save_yaml(ry, data, path)

    headings = heading_re(tokens)
    for unit in units:
        folder = coursemod.unit_dir(course_dir, unit["n"])
        content = folder / "content.md"
        old = previous.get(unit["slxd_id"])
        if content.exists() and old and content.read_text(encoding="utf-8") == skeleton(old, cfg, tokens, language):
            content.unlink()  # still the untouched skeleton of the previous design: regenerate it
        if content.exists():
            found = [(int(n), title.strip()) for n, title, _ in headings.findall(content.read_text(encoding="utf-8"))]
            expected = [(s["n"], s["title"]) for s in unit["sections"]]
            if found != expected:
                result.warnings.append(t("sync", "headings_differ", unit=tokens["unit"], n=unit["n"]))
            continue
        folder.mkdir(parents=True, exist_ok=True)
        content.write_text(skeleton(unit, cfg, tokens, language), encoding="utf-8", newline="\n")
        template = _unit_template(language, "assessment.md")
        assessment = folder / "assessment.md"
        if not assessment.exists() or assessment.read_text(encoding="utf-8") == render(template, n=(old or unit)["n"]):
            assessment.write_text(render(template, n=unit["n"]), encoding="utf-8", newline="\n")  # never overwrite what was written
        result.written.append(str(content.relative_to(course_dir)))
    return result
