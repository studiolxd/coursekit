"""The fix report of a unit for the handoff: `courses/<CODE>/reviews/unit-NN-fix.md`.

When a unit fails (`coursekit verify` has errors, or the AI review says "not ready"), the writer gets a deterministic list
of what to fix and nothing else: the errors of verify with the place they point at, and the blocking findings of the
review that were not applied, with their section and criterion. Each round stores the fingerprint of its findings (the
same findings, even when their line numbers moved, give the same fingerprint); when a round ends with the findings of the
round before, the handoff stops instead of spending more rounds on the same thing.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from coursekit import verify
from coursekit.i18n import t

FINGERPRINT_RE = re.compile(r"<!--\s*fingerprint:\s*([0-9a-f]+)\s*-->")


@dataclass(frozen=True)
class Finding:
    source: str  # "verify" or "review"
    text: str


def report_path(course: dict, n: int) -> Path:
    return course["_dir"] / "reviews" / f"unit-{n:02d}-fix.md"


def verify_findings(course: dict, n: int) -> list[Finding]:
    unit = next(u for u in course.get("units") or [] if u["n"] == n)
    return [Finding("verify", error) for error in verify.verify_unit(course, unit).errors]


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def review_findings(course: dict, n: int) -> list[Finding]:
    """The blocking findings of the AI review of the unit that were not applied: rows of its findings table whose severity
    is `blocking` and whose action does not start with `applied` (both written untranslated, as the review skill says)."""
    path = course["_dir"] / "reviews" / f"unit-{n:02d}-ai-review.md"
    if not path.exists():
        return []
    found = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = _cells(line)
        if len(cells) < 6:
            continue
        severity = cells[3].strip("`* ").lower()
        action = cells[5].strip("`* ").lower()
        if severity == "blocking" and not action.startswith("applied"):
            found.append(Finding("review", f"{cells[1]} · {cells[2]}: {cells[4]}"))
    return found


def fingerprint(findings: list[Finding]) -> str:
    """The same findings give the same fingerprint, whatever their order and their line numbers."""
    normal = sorted({f"{f.source}:{re.sub(r'[0-9]+', '#', f.text)}" for f in findings})
    return hashlib.sha256("\n".join(normal).encode("utf-8")).hexdigest()[:16]


def previous_fingerprint(course: dict, n: int) -> str | None:
    path = report_path(course, n)
    if not path.exists():
        return None
    found = FINGERPRINT_RE.findall(path.read_text(encoding="utf-8"))
    return found[-1] if found else None


def write_package_check(course: dict, problems: dict[int, list[str]]) -> Path:
    """`reviews/package-check.md`: what `coursekit assemble check` found in the packages, per unit."""
    path = course["_dir"] / "reviews" / "package-check.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {t('fixes', 'package_title', code=course['code'])}", "", t("fixes", "package_intro", code=course["code"]), ""]
    for n, items in sorted(problems.items()):
        lines += [f"## {t('fixes', 'package_unit', n=n)}", ""] + [f"{i}. {text}" for i, text in enumerate(items, 1)] + [""]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def write(course: dict, n: int, findings: list[Finding], round_no: int) -> Path:
    """Write the fix report of the unit (it replaces the one before)."""
    path = report_path(course, n)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {t('fixes', 'title', code=course['code'], n=n, round=round_no)}",
             f"<!-- fingerprint: {fingerprint(findings)} -->", "", t("fixes", "intro", code=course["code"], n=n), ""]
    for source in ("verify", "review"):
        items = [f for f in findings if f.source == source]
        if not items:
            continue
        lines += [f"## {t('fixes', f'section_{source}')}", ""]
        lines += [f"{i}. {f.text}" for i, f in enumerate(items, 1)]
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path
