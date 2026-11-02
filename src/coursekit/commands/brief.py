"""The commands of the reference material: brief, research, official videos and the brand material."""


from __future__ import annotations

import argparse
import sys

from coursekit import brief as briefmod
from coursekit import (
    config,
    new,
)
from coursekit import course as coursemod
from coursekit import research as researchmod
from coursekit import states as statesmod
from coursekit import videos as videosmod
from coursekit.commands import common
from coursekit.i18n import t
from coursekit.project import Project


def cmd_brief_find(project: Project, args: argparse.Namespace) -> int:
    """The passages of the material (of the course and of the project) a query or a section of the design needs."""
    from coursekit import sources

    if not args.code:
        print(t("commands", "brief_find_needs_code"), file=sys.stderr)
        return 2
    course = coursemod.load(project, args.code)
    cfg = coursemod.rules(course).get("brief") or {}
    if args.section:
        found = sources.section_query(course, args.section)
        if found is None:
            print(t("commands", "brief_section_not_found", section=args.section, code=course["code"]), file=sys.stderr)
            return 1
        query, label = found
    else:
        query, label = args.find, args.find
    words = sources.stopwords(coursemod.language(course))
    files = sources.text_files(course["_dir"] / "brief", project.brief_dir)
    if not files:
        print(t("commands", "brief_find_no_text", code=course["code"]), file=sys.stderr)
        return 1
    passages = sources.passages(files, int(cfg.get("passage_words") or 200), words)
    best = sources.rank(passages, query, words, int(args.top or cfg.get("passages") or 8))
    print(t("commands", "brief_find_title", query=label, count=len(best), total=len(passages)))
    for i, (_score, passage) in enumerate(best, 1):
        where = f"{passage.file.relative_to(project.root).as_posix()}:{passage.start}-{passage.end}"
        heading = f" · {passage.heading}" if passage.heading else ""
        print(f"\n## {i} · {where}{heading}\n\n{passage.text}")
    if not best:
        print(t("commands", "brief_find_nothing"))
    return 0

def cmd_brief(args: argparse.Namespace) -> int:
    project = common.project()
    if args.find or args.section:
        return cmd_brief_find(project, args)
    log = lambda m: print(m, flush=True)  # noqa: E731
    general = project.brief_dir
    project_language = str(config.project_data(project).get("content_language") or "es")
    importing = config.effective("import", project).value
    if args.code:
        course = coursemod.load(project, args.code)
        new.ensure_brief(course["_dir"])
        new.ensure_decisions(course["_dir"])  # the courses made before it had one
        if (general / "links.md").exists() or (general / "sources").exists():
            briefmod.build(general, project.root.name, args.refresh, log=log, language=project_language, importing=importing)
        rel = "../../../brief/index.md" if (general / "index.md").exists() else None
        summary = briefmod.build(course["_dir"] / "brief", course["code"], args.refresh, general=rel, log=log,
                                 language=coursemod.language(course), importing=config.effective("import", project, course).value,
                                 forbidden=config.effective("rules", project, course).value.get("forbidden"))
        target = f"{course['code']}/brief/index.md"
    else:
        summary = briefmod.build(general, project.root.name, args.refresh, log=log, language=project_language, importing=importing)
        target = "brief/index.md"
    print(t("commands", "brief_summary", documents=summary["documents"], webs=summary["webs"], media=summary["media"], target=target))
    for source, note in summary["notes"]:
        print(t("commands", "brief_note", source=source, note=note))
    return 1 if summary["failed"] else 0

def cmd_research(args: argparse.Namespace) -> int:
    """Official sources through the search API of the `.env`; without one, the agent uses its own web search."""
    project = common.project()
    course = coursemod.load(project, args.code)
    if args.status:
        for line in researchmod.status(course):
            print(line)
        return 0
    if not args.query:
        print(t("commands", "research_needs_query"), file=sys.stderr)
        return 2
    statesmod.ensure_active(course)
    try:
        found = researchmod.search(course, args.query, fact=args.fact)
    except researchmod.NoProvider as exc:
        print(exc, file=sys.stderr)
        return researchmod.NO_PROVIDER
    print(found.as_json() if args.json else researchmod.render(found, coursemod.language(course)))
    if found.warning:
        print(found.warning, file=sys.stderr)
    return 0

def cmd_videos(args: argparse.Namespace) -> int:
    project = common.project()
    course = coursemod.load(project, args.code)
    statesmod.ensure_active(course)
    if args.action == "find":
        if not args.url:
            print(t("videos", "need_query"), file=sys.stderr)
            return 2
        try:
            found = videosmod.find(course, args.url)
        except videosmod.VideoError as exc:
            print(t("commands", "error_line", text=exc), file=sys.stderr)
            return 1
        for v in found:
            print(t("videos", "found_line", **{k: v.get(k) or "?" for k in ("url", "title", "channel", "duration", "date", "language")}))
        if not found:
            print(t("videos", "found_none", query=args.url))
        return 0
    try:
        if args.action == "check":
            videosmod.check(course)
        else:
            if not args.url:
                print(t("videos", "need_url", action=args.action), file=sys.stderr)
                return 2
            if args.action == "propose":
                videosmod.propose(course, args.url, args.why or "", args.replaces, args.asset)
            else:
                entry = videosmod.decide(course, args.url, "approved" if args.action == "approve" else "rejected")
                print(t("videos", "decided", url=entry["url"], status=entry["status"]))
    except videosmod.VideoError as exc:
        print(t("commands", "error_line", text=exc), file=sys.stderr)
        return 1
    path = videosmod.report(course, coursemod.language(course))
    registered = videosmod.load(course["_dir"])
    counts = {s: sum(1 for v in registered if v.get("status") == s) for s in ("approved", "proposed", "pending", "rejected")}
    print(t("videos", "summary", path=path.relative_to(project.root).as_posix(), **counts))
    common.mirror(project, course["code"])
    return 1 if counts["pending"] or counts["rejected"] else 0

def cmd_brand(args: argparse.Namespace) -> int:
    from coursekit import brand

    project = common.project()
    course = coursemod.load(project, args.code) if args.code else None
    done = brand.build(project, course, args.refresh, log=print)
    rel = done["folder"].relative_to(project.root).as_posix()
    print(t("brand", "done", path=rel, documents=done["documents"], webs=done["webs"], observed=done["observed"],
            fonts=", ".join(done["fonts"]) or "—", logos=done["logos"], icons=done["icons"], index=f"{rel}/index.md"))
    if done["missing_fonts"]:
        print(t("brand", "done_missing_fonts", families=", ".join(done["missing_fonts"])))
    return 1 if done["failed"] else 0
