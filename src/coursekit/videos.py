"""`coursekit videos`: videos hosted on a site `rules › forbidden` lists, allowed when they come from an official channel.

`check` finds every such address in the content of a course and asks the site (oEmbed, no key) who publishes it: a channel
named in `rules › forbidden › allow_channels` makes it `approved`; anything else is `pending` and has to be replaced. The
writing agent looks for an equivalent video on an official channel and registers it with `propose`; a person checks it in
`reviews/external-videos.md` and settles it with `approve` or `reject`. The registry (`media/external-videos.yaml`) is what
`coursekit verify` reads, so verifying never needs the network.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

from coursekit import course as coursemod
from coursekit import i18n, identity
from coursekit.i18n import t
from coursekit.util import USER_AGENT

REGISTRY = "media/external-videos.yaml"
REPORT = "reviews/external-videos.md"
URL = re.compile(r"https?://[^\s)>\]\"'<]+", re.I)
OEMBED = {"youtube.com": "https://www.youtube.com/oembed?format=json&url={url}",
          "youtu.be": "https://www.youtube.com/oembed?format=json&url={url}",
          "vimeo.com": "https://vimeo.com/api/oembed.json?url={url}"}
USABLE = ("approved", "proposed")   # the statuses `verify` lets through (a proposed one with a warning)


class VideoError(Exception):
    pass


def host_of(url: str) -> str:
    return (urllib.parse.urlparse(url).hostname or "").lower().removeprefix("www.")


def on_host(url: str, hosts: list[str]) -> bool:
    host = host_of(url)
    return any(host == h or host.endswith(f".{h}") for h in hosts)


def key(url: str) -> str:
    """The same video whatever the form of its address (`watch?v=`, `youtu.be/`, `embed/`, `shorts/`, with or without `www`)."""
    parsed = urllib.parse.urlparse(url)
    host = host_of(url)
    if host.endswith("youtube.com") or host.endswith("youtube-nocookie.com") or host == "youtu.be":
        query = urllib.parse.parse_qs(parsed.query)
        parts = [p for p in parsed.path.split("/") if p]
        ident = (query.get("v") or [""])[0] or (parts[0] if host == "youtu.be" and parts else "") \
            or (parts[1] if len(parts) > 1 and parts[0] in ("embed", "shorts", "live", "v") else "")
        if ident:
            return f"youtube:{ident}"
    return f"{host}{parsed.path}".rstrip("/")


def forbidden_rules(course: dict) -> dict:
    return coursemod.rules(course).get("forbidden") or {}


def load(course_dir: Path) -> list[dict]:
    path = course_dir / REGISTRY
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [v for v in data.get("videos") or [] if isinstance(v, dict) and v.get("url")]


def by_key(course_dir: Path) -> dict[str, dict]:
    return {key(v["url"]): v for v in load(course_dir)}


def save(course_dir: Path, videos: list[dict]) -> None:
    path = course_dir / REGISTRY
    path.parent.mkdir(parents=True, exist_ok=True)
    header = "# Videos on sites that rules › forbidden lists. Written by `coursekit videos`; `coursekit verify` reads it.\n"
    path.write_text(header + yaml.safe_dump({"videos": videos}, allow_unicode=True, sort_keys=False, width=120),
                    encoding="utf-8", newline="\n")


def oembed(url: str) -> dict | None:
    """Who publishes a video, as its site says (`author_name`, `author_url`, `title`); None when it cannot be asked."""
    host = host_of(url)
    template = next((v for h, v in OEMBED.items() if host == h or host.endswith(f".{h}")), None)
    if template is None:
        return None
    request = urllib.request.Request(template.format(url=urllib.parse.quote(url, safe="")), headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None
    return {"name": data.get("author_name") or "", "url": data.get("author_url") or "", "title": data.get("title") or ""}


def official(channel: dict | None, allowed: list[str]) -> bool:
    """Whether the channel is one of `allow_channels` (by its name, its handle, its id or its address)."""
    if not channel:
        return False
    url = str(channel.get("url") or "").rstrip("/")
    tokens = {str(channel.get("name") or "").casefold(), url.casefold(), url.rsplit("/", 1)[-1].casefold()}
    tokens = {x.lstrip("@") for x in tokens if x}
    return any(str(entry).strip().casefold().lstrip("@") in tokens for entry in allowed if str(entry).strip())


def content_files(course: dict) -> list[Path]:
    root = course["_dir"] / "content"
    return sorted(p for p in root.glob("unit-*/*.md") if p.name in ("content.md", "assessment.md")) if root.is_dir() else []


def addresses(course: dict, hosts: list[str]) -> list[str]:
    """The addresses on a forbidden host in the content of the course, once each, in order."""
    found: dict[str, str] = {}
    for path in content_files(course):
        for url in URL.findall(path.read_text(encoding="utf-8")):
            url = url.rstrip(".,;:")
            if on_host(url, hosts):
                found.setdefault(key(url), url)
    return list(found.values())


def today() -> str:
    return dt.date.today().isoformat()


def check(course: dict) -> list[dict]:
    """Registers every video of the content on a forbidden host: `approved` when its channel is official, else `pending`."""
    rules = forbidden_rules(course)
    hosts = [str(h).strip().lower().lstrip(".") for h in rules.get("hosts") or [] if str(h).strip()]
    allowed = list(rules.get("allow_channels") or [])
    registry = {key(v["url"]): v for v in load(course["_dir"])}
    present = set()
    for url in addresses(course, hosts):
        present.add(key(url))
        entry = registry.get(key(url))
        if entry and entry.get("status") in ("approved", "proposed", "rejected"):
            continue  # settled by a rule, by the agent (waiting for a person) or by a person: not asked again
        info = oembed(url)
        channel = {"name": info["name"], "url": info["url"]} if info else None
        status = "approved" if official(channel, allowed) else "pending"
        why = "" if status == "approved" else t("videos", "pending_channel" if info else "pending_unresolved")
        registry[key(url)] = {"url": url, "title": (info or {}).get("title", ""), "channel": channel, "status": status, "why": why,
                              "checked": today(), **({"by": "rules"} if status == "approved" else {})}
    for k, entry in registry.items():
        entry["in_content"] = k in present
    videos = list(registry.values())
    save(course["_dir"], videos)
    return videos


def propose(course: dict, url: str, why: str, replaces: str | None = None) -> dict:
    """The agent registers a video from a channel it found official, with its evidence, for a person to check."""
    if not why.strip():
        raise VideoError(t("videos", "why_needed"))
    videos = load(course["_dir"])
    info = oembed(url)
    entry = {"url": url, "title": (info or {}).get("title", ""), "channel": {"name": info["name"], "url": info["url"]} if info else None,
             "status": "proposed", "why": why.strip(), "checked": today(), "in_content": True,
             **({"replaces": replaces} if replaces else {})}
    videos = [v for v in videos if key(v["url"]) != key(url)] + [entry]
    save(course["_dir"], videos)
    return entry


def decide(course: dict, url: str, status: str) -> dict:
    """A person approves or rejects a video; it is recorded with who did it."""
    who = identity.current()
    if who is None:
        raise VideoError(t("videos", "no_identity"))
    videos = load(course["_dir"])
    entry = next((v for v in videos if key(v["url"]) == key(url)), None)
    if entry is None:
        raise VideoError(t("videos", "not_registered", url=url))
    entry.update(status=status, by=f"{who.name} <{who.email}>", decided=today())
    save(course["_dir"], videos)
    return entry


def report(course: dict, lang: str) -> Path:
    """`reviews/external-videos.md`: what a person has to check."""
    def say(name: str, **values: object) -> str:
        return i18n.t_in(lang, "videos", name, **values)

    videos = load(course["_dir"])
    out = [say("report_title", code=course["code"]), "", say("report_intro"), ""]

    def table(status: str, heading: str) -> None:
        rows = [v for v in videos if v.get("status") == status]
        if not rows:
            return
        out.extend([heading, "", say("report_header"), "|---|---|---|---|"])
        for v in rows:
            channel = v.get("channel") or {}
            name = (channel.get("name") or "—") + (f" ({channel['url']})" if channel.get("url") else "")
            note = v.get("why") or ""
            if v.get("replaces"):
                note = f"{say('report_replaces', url=v['replaces'])} {note}".strip()
            out.append(f"| {v.get('title') or '—'} · {v['url']} | {name} | {'' if v.get('in_content', True) else say('report_unused')} | "
                       f"{note.replace('|', '/')} |")
        out.append("")

    table("proposed", say("report_proposed"))
    table("pending", say("report_pending"))
    table("approved", say("report_approved"))
    table("rejected", say("report_rejected"))
    if not videos:
        out += [say("report_none"), ""]
    path = course["_dir"] / REPORT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out), encoding="utf-8", newline="\n")
    return path
