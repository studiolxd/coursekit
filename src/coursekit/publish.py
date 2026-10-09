"""`coursekit publish`: mirror the courses to the project's shared folder and write the catalog.

The mirror is a read-only copy of git, synced by the provider's desktop client (SharePoint,
OneDrive, Google Drive, Nextcloud) or any folder: anything edited there is overwritten on the next
publication. MIRROR_DIR (.env) is the local path of that folder; project.yaml › mirror gives the
provider and the web address used for the links in the catalog. Layout:

    <catalog>.xlsx
    courses/<CODE>/course.yaml
    courses/<CODE>/design/...        instructional design Excel
    courses/<CODE>/content/...       content.md / assessment.md per unit
    courses/<CODE>/reviews/...       review reports
    courses/<CODE>/delivery/...      SCORM packages (never deleted from the mirror)

Files are copied only when their content changed. Files published before that no longer exist
in git are removed (tracked in courses/<CODE>/.published.json); delivery/ is append-only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlencode, urlsplit, urlunsplit

from coursekit import catalog, config
from coursekit.i18n import t
from coursekit.project import Project


class PublishError(Exception):
    pass


MIRRORED = ("course.yaml", "design", "content", "reviews")
DELIVERY = "delivery"
STATE_FILE = ".published.json"
SKIP_NAMES = {".DS_Store", ".gitkeep"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def source_files(course_dir: Path, names) -> list[Path]:
    files = []
    for name in names:
        src = course_dir / name
        if src.is_file():
            files.append(src)
        elif src.is_dir():
            files += [p for p in sorted(src.rglob("*")) if p.is_file() and p.name not in SKIP_NAMES and not p.name.startswith(".~")]
    return files


def copy_if_changed(src: Path, dst: Path) -> bool:
    if dst.exists() and dst.stat().st_size == src.stat().st_size and digest(dst) == digest(src):
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(f".~{dst.name}")
    shutil.copy2(src, tmp)
    tmp.replace(dst)
    return True


def publish_course(course_dir: Path, target_root: Path) -> tuple[int, int, int]:
    """Return (copied, removed, unchanged) file counts."""
    target = target_root / "courses" / course_dir.name
    state_path = target / STATE_FILE
    previous = set(json.loads(state_path.read_text(encoding="utf-8"))) if state_path.exists() else set()

    copied = unchanged = removed = 0
    published = set()
    for src in source_files(course_dir, MIRRORED):
        rel = src.relative_to(course_dir).as_posix()
        published.add(rel)
        if copy_if_changed(src, target / rel):
            copied += 1
        else:
            unchanged += 1

    # SCORM packages are kept forever in the mirror, even if removed locally.
    for src in source_files(course_dir, (DELIVERY,)):
        dst = target / src.relative_to(course_dir)
        if dst.exists():
            unchanged += 1
            continue
        copy_if_changed(src, dst)
        copied += 1

    for rel in sorted(previous - published):
        stale = target / rel
        if stale.is_file():
            stale.unlink()
            removed += 1
            # Drop empty folders left behind, but never above the course folder.
            parent = stale.parent
            while parent != target and parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent

    target.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(sorted(published), indent=1), encoding="utf-8")
    return copied, removed, unchanged


def folder_path(base_url: str) -> str | None:
    """Decoded server path of a SharePoint / OneDrive folder from its browser URL, or None.

    Accepts the three usual forms:
      - library view:  .../Forms/AllItems.aspx?id=<folder path>&...   (address bar)
      - copy link:     /:f:/r/<folder path>?d=...                     (query ignored)
      - plain path:    /sites/<site>/<library>/<folder>
    Sharing links (/:f:/s/<token>) carry no path.
    """
    parts = urlsplit(base_url)
    if parts.path.lower().endswith(".aspx"):
        folder = parse_qs(parts.query).get("id", [None])[0]
        return folder.rstrip("/") if folder else None
    if re.match(r"^/:[a-z]:/s/", parts.path):
        return None
    return unquote(re.sub(r"^/:[a-z]:/r(?=/)", "", parts.path)).rstrip("/")


def sharepoint_link(base_url: str):
    """Return code -> URL of the course folder, in the same form the user pasted."""
    parts = urlsplit(base_url)
    root = folder_path(base_url)
    if parts.path.lower().endswith(".aspx"):
        return lambda code: urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode({"id": f"{root}/courses/{code}"}, quote_via=quote), "")
        )
    return lambda code: urlunsplit((parts.scheme, parts.netloc, quote(f"{root}/courses/{code}", safe="/()"), "", ""))


def folder_link(provider: str, base_url: str) -> Callable[[str], str] | None:
    """code -> web address of the course folder in the mirror, when the provider allows it."""
    base_url = base_url.strip().rstrip("/")
    if not base_url:
        return None
    if provider in ("sharepoint", "onedrive"):
        return sharepoint_link(base_url) if folder_path(base_url) is not None else None
    if provider == "nextcloud":
        parts = urlsplit(base_url)
        root = parse_qs(parts.query).get("dir", [""])[0].rstrip("/")
        return lambda code: urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode({"dir": f"{root}/courses/{code}"}), ""))
    if provider == "folder" and "{code}" in base_url:
        return lambda code: base_url.replace("{code}", code)
    return lambda code: base_url  # Google Drive and others: the IDs are not in the path; link the root folder


def mirror_settings(project: Project) -> tuple[str, str, Path | None]:
    mirror = config.project_data(project).get("mirror") or {}
    provider = str(mirror.get("provider") or "none")
    folder = os.environ.get("MIRROR_DIR", "").strip()
    return provider, str(mirror.get("url") or ""), (Path(folder).expanduser() if folder else None)


def check(project: Project) -> list[str]:
    provider, url, root = mirror_settings(project)
    if provider == "none":
        return [t("publish", "check_none")]
    if root is None:
        return [t("publish", "check_no_dir")]
    if not root.is_dir():
        return [t("publish", "check_dir_missing", root=root)]
    lines = [t("publish", "check_ok", provider=provider, root=root)]
    link = folder_link(provider, url)
    if not url:
        lines.append(t("publish", "check_no_url"))
    elif link is None:
        lines.append(t("publish", "check_sharing_link"))
    else:
        lines.append(t("publish", "check_links", link=link("ABC101")))
    return lines


def publish(project: Project, code: str | None = None, only_if_configured: bool = False) -> list[str]:
    provider, url, root = mirror_settings(project)
    if provider == "none":  # a choice, not a mistake: the agents' commands call publish in every project
        return [] if only_if_configured else [t("publish", "skipped_none")]
    if root is None:
        if only_if_configured:
            return []
        raise PublishError(t("publish", "no_mirror"))
    if not root.is_dir():
        raise PublishError(t("publish", "dir_missing", root=root))
    courses = [d for d in project.iter_courses() if code is None or d.name in (code, code.upper())]
    if code and not courses:
        raise PublishError(t("publish", "course_not_found", code=code))
    lines = []
    for course_dir in courses:
        copied, removed, unchanged = publish_course(course_dir, root)
        if copied or removed:
            lines.append(t("publish", "published", name=course_dir.name, copied=copied, removed=removed, unchanged=unchanged))
    output = root / catalog.file_name(project)
    try:
        n_courses, n_units = catalog.build(project, output, folder_link(provider, url))
    except PermissionError as exc:
        raise PublishError(t("publish", "cannot_replace", output=output)) from exc
    lines.append(t("publish", "wrote_catalog", output=output, courses=n_courses, units=n_units))
    return lines
