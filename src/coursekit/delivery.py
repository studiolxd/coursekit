"""`coursekit delivery`: record a delivered SCORM package in course.yaml › deliveries.

The assembly agent exports each unit (creator: create_export), downloads the zip to
courses/<CODE>/delivery/ and records it here. When the tests go apart (`delivery › assessment › placement: separate`) their
package is one more unit; with a question-bank format (`format: aiken | gift | moodle-xml`) `coursekit delivery questions`
writes and records the bank. When every package (and the bank, if any) of the same version is recorded, the course moves to
`delivered`.
"""

from __future__ import annotations

import datetime as dt
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from coursekit import clientreview, config, identity
from coursekit import course as coursemod
from coursekit.i18n import t
from coursekit.states import ensure_active, history_entry
from coursekit.util import USER_AGENT, edit_yaml, save_yaml, sha256_file


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


def download(course: dict, unit: int, version: str, url: str) -> str:
    """Saves the package of an export job (its `downloadUrl`) in the delivery folder with the name `expected_name` gives, and checks
    it. Returns the path, ready for `add`."""
    check_ready(course)
    if not url.startswith("https://"):
        raise DeliveryError(t("delivery", "download_not_https"))
    folder = course["_dir"] / "delivery"
    folder.mkdir(exist_ok=True)
    path = folder / expected_name(course, unit, version)
    partial = path.with_name(path.name + ".part")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=300) as response, partial.open("wb") as out:
            while chunk := response.read(1 << 20):
                out.write(chunk)
    except urllib.error.HTTPError as exc:
        partial.unlink(missing_ok=True)
        raise DeliveryError(t("delivery", "download_failed", status=exc.code, reason=exc.reason)) from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        partial.unlink(missing_ok=True)
        raise DeliveryError(t("delivery", "download_failed", status="-", reason=getattr(exc, "reason", exc))) from None
    problem = check_package(partial)
    if problem:
        partial.unlink(missing_ok=True)
        raise DeliveryError(f"{path.name}: {problem}")
    partial.replace(path)
    return path.as_posix()


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
    if coursemod.package_unit(course, unit) is None:
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
    return _close(course, ry, data, version, path.name, warning)


def _pending(course: dict, deliveries: list[dict], version: str) -> list[str]:
    """What the version still lacks: the packages (by unit number) and the question bank when the tests are exported as one."""
    done = [d for d in deliveries if d.get("version") == version]
    units = {d.get("unit") for d in done if d.get("kind", "package") == "package"}
    pending = [str(u["n"]) for u in coursemod.package_units(course) if u["n"] not in units]
    if coursemod.assessment_delivery(course)[1] != "platform" and not any(d.get("kind") == "questions" for d in done):
        pending.append(t("delivery", "pending_questions"))
    return pending


def _close(course: dict, ry, data: dict, version: str, name: str, warning: str | None) -> str:
    """Saves the record and, when nothing of the version is missing, moves the course to `delivered`."""
    pending = _pending(course, data["deliveries"], version)
    if not pending and data["status"] in ("assembly", "client_review"):
        data["status"] = "delivered"
        who = data["deliveries"][-1].get("by") or "unknown"
        data.setdefault("history", []).append(history_entry("delivered", f"Version {version} delivered", who))
    save_yaml(ry, data, course["_dir"] / "course.yaml")
    note = f"\n{warning}" if warning else ""
    if pending:
        return t("delivery", "recorded_pending", name=name, version=version, pending=", ".join(pending)) + note
    return t("delivery", "recorded_done", name=name) + note


def add_questions(course: dict, version: str) -> str:
    """Writes the question bank of the course (`delivery › assessment › format`) in delivery/ and records it."""
    from coursekit import questionbank

    warning = check_ready(course)
    fmt = coursemod.assessment_delivery(course)[1]
    files = questionbank.export(course, version, fmt)
    course_path = course["_dir"] / "course.yaml"
    ry, data = edit_yaml(course_path)
    if data.get("deliveries") is None:
        data["deliveries"] = []
    who = identity.current() or identity.suggested()
    data["deliveries"].append({
        "version": version,
        "kind": "questions",
        "format": fmt,
        "date": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "by": str(who) if who else "unknown",
        "files": [{"file": p.name, "sha256": sha256_file(p)} for p in files],
    })
    names = ", ".join(p.name for p in files)
    return t("questionbank", "written", format=fmt, files=names) + "\n" + _close(course, ry, data, version, names, warning)
