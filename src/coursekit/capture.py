"""`coursekit capture`: real captures of an application that coursekit makes itself, with the permission of a person.

For the resources that show a real interface, an agent drives the application and coursekit captures it, instead of waiting
for a person to drop the file in media/recordings/<id>. What only a person may do lives here:

- **profiles**: a web application is opened in a browser of the machine with a profile of its own, kept outside the
  project in the per-machine store (`capture/<project>/profiles/<name>/`). The person logs in once
  (`coursekit capture login NAME`, single sign-on and second factor included) and the session stays in the profile:
  coursekit never sees or stores the password. `capture.yaml › profiles` says where each one starts and the only domains
  it may open.
- **grants**: nothing is captured without a permission that expires (`coursekit capture allow`), for one course, its
  resources (all those that show an interface, or the ones named), one mode (browser or desktop) and a profile or a window.
  It is signed with the identity of the `.env`. `coursekit capture revoke` takes it back.

The generated agent configurations deny `login`, `logout`, `allow` and `revoke` to the agents.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

from coursekit import config, identity, store
from coursekit import media as mediamod
from coursekit.i18n import t
from coursekit.project import Project
from coursekit.util import slugify

MODES = ("browser", "desktop")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")

Launcher = Callable[[Path, str], None]


class CaptureError(Exception):
    pass


def settings(project: Project) -> dict:
    return config.effective("capture", project).value


def _now() -> dt.datetime:
    return dt.datetime.now().astimezone()


def _stamp(moment: dt.datetime) -> str:
    return moment.isoformat(timespec="seconds")


# ── where it lives ───────────────────────────────────────────────────────────────────────────

def project_key(project: Project) -> str:
    """The folder of a project in the store: its name and a hash of its path, so two projects never share a profile."""
    root = project.root.resolve()
    return f"{slugify(root.name, 32) or 'project'}-{hashlib.sha256(str(root).encode('utf-8')).hexdigest()[:10]}"


def base_dir(project: Project) -> Path:
    return store.home() / "capture" / project_key(project)


def _private_dir(path: Path) -> Path:
    """A folder only its owner can read (profiles hold live sessions: whoever has one enters with that account)."""
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":  # on Windows the store is already in the user's own LOCALAPPDATA
        top = store.home() / "capture"
        for folder in (path, *path.parents):
            if folder != top and top not in folder.parents:
                break
            os.chmod(folder, 0o700)
    return path


def profile_dir(project: Project, name: str) -> Path:
    return base_dir(project) / "profiles" / name


def _profile_meta(project: Project, name: str) -> Path:
    return base_dir(project) / "profiles" / f"{name}.json"


def _grant_file(project: Project, code: str) -> Path:
    return base_dir(project) / "grants" / f"{code}.json"


def _write_json(path: Path, data: dict) -> None:
    _private_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ── profiles ─────────────────────────────────────────────────────────────────────────────────

def _require_enabled(cfg: dict) -> None:
    if not cfg.get("enabled"):
        raise CaptureError(t("capture", "not_enabled"))


def check_name(name: str) -> str:
    if not NAME_RE.match(name or ""):
        raise CaptureError(t("capture", "bad_name", name=name))
    return name


def domain_allowed(host: str, domains: list[str]) -> bool:
    """Whether a host is one of the domains or a subdomain of one."""
    host = (host or "").lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in (str(d).lower().strip().rstrip(".") for d in domains) if d)


def profile_config(cfg: dict, name: str) -> dict:
    """The configuration of a profile, checked: where it starts and the domains it may open."""
    check_name(name)
    profile = (cfg.get("profiles") or {}).get(name)
    if not isinstance(profile, dict):
        known = ", ".join(sorted(cfg.get("profiles") or {})) or "—"
        raise CaptureError(t("capture", "unknown_profile", name=name, known=known))
    url = str(profile.get("start_url") or "").strip()
    parts = urlsplit(url)
    if parts.scheme not in ("https", "http") or not parts.hostname:
        raise CaptureError(t("capture", "bad_start_url", name=name, url=url or "—"))
    domains = [str(d) for d in (profile.get("allow_domains") or []) if str(d).strip()]
    if not domains:
        raise CaptureError(t("capture", "no_domains", name=name))
    if not domain_allowed(parts.hostname, domains):
        raise CaptureError(t("capture", "start_outside", name=name, host=parts.hostname))
    return {"start_url": url, "allow_domains": domains, "account": str(profile.get("account") or "")}


def _launch_login(folder: Path, url: str) -> None:
    """Opens a visible browser of the machine with the profile and waits until the person closes it."""
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise CaptureError(t("capture", "playwright_missing")) from None
    from coursekit.htmlkit.playcheck import find_browser

    executable = find_browser()
    if not executable:
        raise CaptureError(t("capture", "no_browser"))
    try:
        with sync_playwright() as pw:
            context = pw.chromium.launch_persistent_context(str(folder), executable_path=executable, headless=False,
                                                            no_viewport=True)
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url)
            context.wait_for_event("close", timeout=0)
    except PlaywrightError as exc:
        raise CaptureError(t("capture", "browser_failed", reason=str(exc).splitlines()[0])) from None


def login(project: Project, name: str, launch: Launcher | None = None) -> dict:
    """A person logs in to the application of a profile; the session stays in the profile, outside the project."""
    cfg = settings(project)
    _require_enabled(cfg)
    profile = profile_config(cfg, name)
    folder = _private_dir(profile_dir(project, name))
    (launch or _launch_login)(folder, profile["start_url"])
    who = identity.current()
    meta = {"profile": name, "start_url": profile["start_url"], "account": profile["account"],
            "logged_in_at": _stamp(_now()), "by": str(who) if who else identity.display_name()}
    _write_json(_profile_meta(project, name), meta)
    return meta


def logout(project: Project, name: str) -> bool:
    """Deletes a profile and its session. False when there was none."""
    check_name(name)
    folder, meta = profile_dir(project, name), _profile_meta(project, name)
    existed = folder.exists() or meta.exists()
    shutil.rmtree(folder, ignore_errors=True)
    meta.unlink(missing_ok=True)
    return existed


def profiles(project: Project) -> list[dict]:
    """The profiles configured and those with a session in the store (a session whose profile left the configuration is listed
    too, so it can be deleted)."""
    configured = settings(project).get("profiles") or {}
    stored = {p.stem for p in (base_dir(project) / "profiles").glob("*.json")}
    out = []
    for name in sorted(set(configured) | stored):
        meta = _read_json(_profile_meta(project, name)) or {}
        entry = configured.get(name) if isinstance(configured.get(name), dict) else {}
        out.append({"name": name, "configured": name in configured, "start_url": entry.get("start_url") or meta.get("start_url", ""),
                    "account": entry.get("account") or meta.get("account", ""),
                    "logged_in_at": meta.get("logged_in_at") if profile_dir(project, name).exists() else None})
    return out


def logged_in(project: Project, name: str) -> bool:
    return profile_dir(project, name).is_dir() and _profile_meta(project, name).exists()


# ── grants ───────────────────────────────────────────────────────────────────────────────────

def _interface_assets(course: dict) -> dict[str, dict]:
    _, _, data = mediamod.load_manifest(course["_dir"])
    return {str(a["id"]): a for a in data["assets"] if a.get("depicts") == "interface"}


def allow(project: Project, course: dict, ids: list[str], mode: str, profile: str | None = None, window: str | None = None,
          minutes: float | None = None) -> dict:
    """A person gives the permission to capture, until it expires. It replaces the one the course had."""
    cfg = settings(project)
    _require_enabled(cfg)
    who = identity.current()
    if who is None:
        raise CaptureError(t("capture", "no_identity"))
    allowed_modes = [m for m in (cfg.get("modes") or []) if m in MODES]
    if mode not in allowed_modes:
        raise CaptureError(t("capture", "mode_not_allowed", mode=mode, modes=", ".join(allowed_modes) or "—"))
    if mode == "browser":
        if not profile:
            raise CaptureError(t("capture", "browser_needs_profile"))
        profile_config(cfg, profile)
        if not logged_in(project, profile):
            raise CaptureError(t("capture", "not_logged_in", name=profile))
        window = None
    else:
        if not (window or "").strip():
            raise CaptureError(t("capture", "desktop_needs_window"))
        profile = None
    interface = _interface_assets(course)
    unknown = [i for i in ids if i not in interface]
    if unknown:
        raise CaptureError(t("capture", "not_interface", ids=", ".join(unknown), code=course["code"]))
    if not ids and not interface:
        raise CaptureError(t("capture", "no_interface_assets", code=course["code"]))
    minutes = float(minutes if minutes is not None else cfg.get("grant_minutes") or 0)
    if minutes <= 0:
        raise CaptureError(t("capture", "bad_minutes"))
    start = _now()
    grant = {"code": course["code"], "assets": list(ids) or None, "mode": mode, "profile": profile,
             "window": window.strip() if window else None, "by": str(who), "granted_at": _stamp(start),
             "expires_at": _stamp(start + dt.timedelta(minutes=minutes))}
    _write_json(_grant_file(project, course["code"]), grant)
    return grant


def revoke(project: Project, code: str) -> bool:
    path = _grant_file(project, code)
    existed = path.exists()
    path.unlink(missing_ok=True)
    return existed


def active_grant(project: Project, code: str, asset_id: str | None = None, now: dt.datetime | None = None) -> dict | None:
    """The permission in force for the course (and the resource, if given); None when there is none or it expired."""
    grant = _read_json(_grant_file(project, code))
    if not grant:
        return None
    try:
        expires = dt.datetime.fromisoformat(grant["expires_at"])
    except (KeyError, TypeError, ValueError):
        return None
    if (now or _now()) >= expires:
        return None
    if asset_id is not None and grant.get("assets") and asset_id not in grant["assets"]:
        return None
    return grant
