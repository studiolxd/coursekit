"""`coursekit import`: courses from folders of eXeLearning packages.

A folder of packages is a course and each `.elp` is a unit. The parent folder of many courses is scanned too: every
subfolder with packages is one course. The title and the hours of a course are not in its packages, so they come from the
plan file (`import.yaml`), from a spreadsheet (folder and hours) or from a default for all of them; a course without them is
skipped and reported. The packages are copied to `brief/sources/` of the new course, in the order of their units, and the
brief converts them (`coursekit brief`).
"""

from __future__ import annotations

import csv
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from coursekit import brief as briefmod
from coursekit import config, course, new
from coursekit.i18n import t
from coursekit.project import Project
from coursekit.util import slugify

PLAN_FILE = "import.yaml"
SUFFIXES = (".elp",)

UNIT_WORD = re.compile(r"(?:m[oó]dulo|mod|unidad|unit|tema|bloque)\D{0,3}(\d{1,2})(?!\d)", re.I)
LEADING = re.compile(r"^\s*(\d{1,2})(?=[\s._-])")
MIDDLE = re.compile(r"[_\s-](\d{1,2})[_\s.-](?=\D)")
ENDING = re.compile(r"[_\s-](\d{1,2})$")
TRAILING = re.compile(r"[^\d\W_](\d{1,2})(?=[_\s-]?v?\d*\s*(?:rev)?$|[_\s-]v)", re.I)
VERSION = re.compile(r"[_\s-]*v\s*(\d+|rev)\s*$", re.I)


class ImporterError(Exception):
    pass


@dataclass
class Unit:
    path: Path
    number: int | None
    version: str | None


@dataclass
class CoursePlan:
    folder: Path
    code: str
    units: list[Unit] = field(default_factory=list)
    title: str = ""
    hours: float | None = None
    problems: list[str] = field(default_factory=list)   # decisions a person has to take
    notes: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list) # versions of the same unit: the plan settles them by listing the units


@dataclass
class Scan:
    courses: list[CoursePlan] = field(default_factory=list)
    empty: list[str] = field(default_factory=list)       # folders with no package


def unit_number(name: str) -> int | None:
    """The number of the unit in the name of its package (`..._2_vREV`, `MOD3`, `Unidad 2. …`, `3_…`, `…AUTOR4_v5`)."""
    stem = VERSION.sub("", Path(name).stem)
    for pattern in (UNIT_WORD, LEADING, MIDDLE, ENDING, TRAILING):
        found = pattern.search(stem)
        if found:
            return int(found.group(1))
    return None


def unit_version(name: str) -> str | None:
    found = VERSION.search(Path(name).stem)
    return found.group(1).upper() if found else None


def _packages(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in SUFFIXES and not p.name.startswith("."))


def _plan_of(folder: Path) -> CoursePlan:
    plan = CoursePlan(folder=folder, code=slugify(folder.name).upper())
    plan.units = [Unit(p, unit_number(p.name), unit_version(p.name)) for p in _packages(folder)]
    numbers = [u.number for u in plan.units]
    if any(n is None for n in numbers):
        plan.units.sort(key=lambda u: u.path.name.casefold())
        plan.notes.append(t("importer", "order_by_name"))
    else:
        duplicated = sorted({n for n in numbers if numbers.count(n) > 1})
        for n in duplicated:
            names = ", ".join(u.path.name for u in plan.units if u.number == n)
            plan.duplicates.append(t("importer", "duplicate_unit", number=n, names=names))
        plan.units.sort(key=lambda u: (u.number, u.path.name.casefold()))
        expected = list(range(1, len(set(numbers)) + 1))
        if sorted(set(numbers)) != expected:
            plan.notes.append(t("importer", "numbers_gap", numbers=", ".join(str(n) for n in sorted(set(numbers)))))
    return plan


def scan(root: Path) -> Scan:
    if not root.is_dir():
        raise ImporterError(t("importer", "not_a_folder", path=root.as_posix()))
    found = Scan()
    if _packages(root):
        found.courses.append(_plan_of(root))
        return found
    for folder in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        if _packages(folder):
            found.courses.append(_plan_of(folder))
        else:
            found.empty.append(folder.name)
    return found


# ── Hours and titles ───────────────────────────────────────────────────────────────────────────

def _number(text: object) -> float | None:
    try:
        value = float(str(text).strip().replace(",", "."))
    except ValueError:
        return None
    return value if value > 0 else None


def read_table(path: Path) -> dict[str, dict]:
    """A spreadsheet (.xlsx) or a CSV with the folder (or code), the hours and, optionally, the title of each course."""
    if not path.is_file():
        raise ImporterError(t("importer", "table_missing", path=path.as_posix()))
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook

        sheet = load_workbook(path, read_only=True, data_only=True).worksheets[0]
        rows = [list(r) for r in sheet.iter_rows(values_only=True)]
    else:
        text = path.read_text(encoding="utf-8-sig")
        dialect = csv.Sniffer().sniff(text[:2000], delimiters=",;\t") if text.strip() else csv.excel
        rows = list(csv.reader(text.splitlines(), dialect))
    rows = [[("" if c is None else str(c).strip()) for c in r] for r in rows if any(c not in (None, "") for c in r)]
    if not rows:
        return {}
    names = {"folder": ("carpeta", "folder", "código", "codigo", "code", "curso", "course"),
             "hours": ("horas", "hours", "duración", "duracion", "duration"),
             "title": ("título", "titulo", "title", "nombre", "name")}
    header = [c.casefold() for c in rows[0]]
    columns = {key: next((i for i, c in enumerate(header) if c in words), None) for key, words in names.items()}
    if columns["folder"] is not None and columns["hours"] is not None:
        body = rows[1:]
    else:
        columns, body = {"folder": 0, "hours": 1, "title": 2 if len(rows[0]) > 2 else None}, rows
    table = {}
    for row in body:
        if len(row) <= max(i for i in (columns["folder"], columns["hours"]) if i is not None):
            continue
        key = row[columns["folder"]].casefold()
        title = row[columns["title"]] if columns["title"] is not None and columns["title"] < len(row) else ""
        table[key] = {"hours": _number(row[columns["hours"]]), "title": title}
    return table


def read_plan(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(c.get("folder")).casefold(): c for c in data.get("courses") or [] if isinstance(c, dict) and c.get("folder")}


def write_plan(path: Path, found: Scan, existing: dict[str, dict]) -> None:
    """The plan to review: what was detected, keeping the title and hours already written by hand."""
    courses = []
    for plan in found.courses:
        old = existing.get(plan.folder.name.casefold(), {})
        courses.append({
            "folder": plan.folder.name,
            "code": old.get("code") or plan.code,
            "title": old.get("title") or "",
            "hours": old.get("hours"),
            "units": [u.path.name for u in plan.units],
            "check": plan.problems + plan.notes,
        })
    header = t("importer", "plan_header")
    body = yaml.safe_dump({"courses": courses}, allow_unicode=True, sort_keys=False, width=120)
    path.write_text("".join(f"# {line}\n" for line in header.splitlines()) + body, encoding="utf-8", newline="\n")


def resolve(found: Scan, plan: dict[str, dict], table: dict[str, dict], default_hours: float | None,
            hours: float | None = None, title: str | None = None, code: str | None = None) -> list[str]:
    """Fills the title, the code, the hours and the units of each course: the plan wins, then the table, then the default.
    Returns the rows of the table that match no course."""
    single = len(found.courses) == 1
    for item in found.courses:
        entry = plan.get(item.folder.name.casefold(), {})
        row = table.get(item.folder.name.casefold()) or table.get(item.code.casefold()) or {}
        if entry.get("code") or (code and single):
            item.code = str(entry.get("code") or code).upper()
        item.title = str(entry.get("title") or (title if single else "") or row.get("title") or "").strip()
        item.hours = _number(entry.get("hours")) or (hours if single else None) or row.get("hours") or default_hours
        if not item.title:
            item.title = item.folder.name
            item.notes.append(t("importer", "provisional_title"))
        if item.hours is None:
            item.problems.append(t("importer", "no_hours"))
        listed = entry.get("units")
        if not listed:
            item.problems += item.duplicates
            continue
        by_name = {u.path.name: u for u in item.units}
        missing = [n for n in listed if n not in by_name]
        if missing:
            item.problems.append(t("importer", "plan_unit_missing", names=", ".join(missing)))
        else:
            item.units = [by_name[n] for n in listed]
    return [name for name in table if not any(c.folder.name.casefold() == name or c.code.casefold() == name for c in found.courses)]


# ── Import ─────────────────────────────────────────────────────────────────────────────────────

def import_course(project: Project, item: CoursePlan, log=print) -> Path:
    """Creates the course, copies its packages to the brief in the order of its units and converts them."""
    folder = new.create(project, item.title, item.hours, code=item.code, origin="import")
    sources = folder / "brief" / "sources"
    for index, unit in enumerate(item.units, 1):
        shutil.copy2(unit.path, sources / f"{index:02d}-{unit.path.name}")
    loaded = course.load(project, folder.name)
    summary = briefmod.build(folder / "brief", loaded["code"], language=course.language(loaded),
                             importing=config.effective("import", project, loaded).value,
                             forbidden=config.effective("rules", project, loaded).value.get("forbidden"))
    for source, note in summary["notes"]:
        log(t("commands", "brief_note", source=source, note=note))
    return folder
