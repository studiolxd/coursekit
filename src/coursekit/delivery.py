"""`coursekit delivery`: record a delivered SCORM package in course.yaml › deliveries.

The assembly agent exports each unit (creator: create_export), downloads the zip to
courses/<CODE>/delivery/ and records it here. When every unit has a package of the same version,
the course moves to `delivered`.
"""

from __future__ import annotations

import datetime as dt
import zipfile
from pathlib import Path

from coursekit import clientreview, config, identity
from coursekit.i18n import t
from coursekit.states import ensure_active, history_entry
from coursekit.util import edit_yaml, save_yaml, sha256_file


class DeliveryError(Exception):
    pass


def settings(course: dict) -> dict:
    return config.effective("delivery", course.get("_project"), course).value


DELIVERABLE = ("assembly", "client_review", "delivered")


def check_ready(course: dict) -> str | None:
    """Refuses (DeliveryError) while the course is on hold or the client's review required by the project is missing.
    Returns a warning when the course is in a status where delivery does not normally start."""
    ensure_active(course)
    problem = clientreview.gate(course)
    if problem:
        raise DeliveryError(problem)
    if course["status"] not in DELIVERABLE:
        return t("delivery", "status_warning", code=course["code"], status=course["status"])
    return None


def expected_name(course: dict, unit: int, version: str) -> str:
    cfg = settings(course)
    standard = cfg["export"]["standard"].replace("_", "")
    return cfg["file_name"].format(code=course["code"], unit=unit, version=version, standard=standard)


def check_package(path: Path) -> str | None:
    """A SCORM zip must be a valid zip with imsmanifest.xml at its root."""
    try:
        with zipfile.ZipFile(path) as zf:
            if "imsmanifest.xml" not in zf.namelist():
                return t("delivery", "no_manifest")
    except (zipfile.BadZipFile, FileNotFoundError):
        return t("delivery", "not_a_zip")
    return None


def add(course: dict, unit: int, version: str, file: str, job: str | None = None, snapshot: str | None = None) -> str:
    course_dir: Path = course["_dir"]
    warning = check_ready(course)
    path = Path(file).resolve()
    problem = check_package(path)
    if problem:
        raise DeliveryError(f"{path.name}: {problem}")
    delivery_dir = (course_dir / "delivery").resolve()
    if path.parent != delivery_dir:
        raise DeliveryError(t("delivery", "wrong_folder", folder=delivery_dir))
    course_path = course_dir / "course.yaml"
    ry, data = edit_yaml(course_path)
    units = [u["n"] for u in data.get("units") or []]
    if unit not in units:
        raise DeliveryError(t("delivery", "unit_not_found", unit=unit))
    if data.get("deliveries") is None:
        data["deliveries"] = []
    who = identity.current() or identity.suggested()
    entry = {
        "version": version,
        "unit": unit,
        "date": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "by": str(who) if who else "unknown",
        "standard": settings(course)["export"]["standard"],
        "file": path.name,
        "sha256": sha256_file(path),
        "export_job": job,
        "snapshot": snapshot,
    }
    data["deliveries"].append(entry)
    delivered = {d["unit"] for d in data["deliveries"] if d.get("version") == version}
    if set(units) <= delivered and data["status"] in ("assembly", "client_review"):
        data["status"] = "delivered"
        data.setdefault("history", []).append(history_entry("delivered", f"Version {version} delivered", entry["by"]))
    save_yaml(ry, data, course_path)
    pending = sorted(set(units) - delivered)
    note = f"\n{warning}" if warning else ""
    if pending:
        return t("delivery", "recorded_pending", name=path.name, version=version, pending=pending) + note
    return t("delivery", "recorded_done", name=path.name) + note
