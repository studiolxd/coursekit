"""How much of a course is seen: per unit, the sections that carry a visual resource already produced, the visual resources
still to produce by type (those that go in as provisional images), and the mix of types against the visual plan of the design.
`coursekit media report CODE` prints it, `coursekit media plan` and the handoff sum it up, so that a course that is poor to the
eye shows before it is assembled."""

from __future__ import annotations

from coursekit import assemble
from coursekit import course as coursemod
from coursekit.i18n import t
from coursekit.media import provisional

DONE = ("produced", "uploaded")


def units(course: dict) -> list[dict]:
    """Per unit: sections (introduction, content, summary) and how many carry a visual produced; visuals by type and status."""
    rules = coursemod.rules(course)["content"]
    kinds = set(rules.get("visual_types") or [])
    assets = [a for a in assemble.manifest_assets(course).values()
              if a.get("type") in kinds and not a.get("kind") and a.get("status") != "orphaned"]
    from coursekit import visualplan

    plan, _ = visualplan.load(course)
    out = []
    for unit in course.get("units") or []:
        sections = [s for s in unit.get("sections") or [] if s.get("kind") in ("intro", "content", "summary")]
        mine = [a for a in assets if a.get("unit") == unit["n"]]
        seen = {a.get("section") for a in mine if a.get("status") in DONE}
        by_type: dict[str, dict[str, int]] = {}
        for a in mine:
            entry = by_type.setdefault(str(a["type"]), {"done": 0, "pending": 0})
            entry["done" if a.get("status") in DONE else "pending"] += 1
        planned: dict[str, int] = {}
        for (n, _section), items in plan.items():
            if n == unit["n"]:
                for item in items:
                    planned[item["type"]] = planned.get(item["type"], 0) + 1
        out.append({"n": unit["n"], "title": unit.get("title", ""), "sections": len(sections),
                    "seen": sum(1 for s in sections if s["n"] in seen), "by_type": by_type, "planned": planned,
                    "provisional": [a["id"] for a in mine if provisional.applies(a)]})
    return out


def summary(course: dict) -> list[str]:
    """One line per unit: sections seen, visuals produced and pending (the provisional images)."""
    lines = []
    for u in units(course):
        done = sum(v["done"] for v in u["by_type"].values())
        pending = sum(v["pending"] for v in u["by_type"].values())
        lines.append(t("media", "coverage_line", n=u["n"], seen=u["seen"], sections=u["sections"], done=done, pending=pending))
    return lines


def report(course: dict) -> list[str]:
    """`coursekit media report`: per unit, the sections seen and, per type, what is produced, pending and planned."""
    tokens = coursemod.tokens(course)
    lines = []
    for u in units(course):
        lines.append(t("media", "report_unit", n=u["n"], title=u["title"], seen=u["seen"], sections=u["sections"]))
        types = sorted(set(u["by_type"]) | set(u["planned"]))
        for kind in types:
            counts = u["by_type"].get(kind, {"done": 0, "pending": 0})
            lines.append(t("media", "report_type", type=tokens["media_types"].get(kind, kind), done=counts["done"],
                           pending=counts["pending"], planned=u["planned"].get(kind, 0)))
        if not types:
            lines.append(t("media", "report_no_visuals"))
        if u["provisional"]:
            lines.append(t("media", "report_provisional", ids=", ".join(u["provisional"])))
    return lines
