"""The commands of assembly and delivery: assemble, directives, delivery and theme."""


from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from coursekit import assemble as assemblemod
from coursekit import (
    config,
    directives,
)
from coursekit import course as coursemod
from coursekit import delivery as deliverymod
from coursekit import states as statesmod
from coursekit import theme as thememod
from coursekit.commands import common
from coursekit.i18n import t
from coursekit.media import tools as mediatools


def cmd_assemble_build(course: dict, args: argparse.Namespace) -> int:
    from coursekit.htmlkit import build as htmlbuild

    if coursemod.backend(course) != "html":
        print(t("commands", "assemble_build_needs_html", code=course["code"], backend=coursemod.backend(course)), file=sys.stderr)
        return 1
    units = [u for u in coursemod.package_units(course) if args.unit is None or u["n"] == args.unit]
    if not units:
        print(t("commands", "unit_not_found", n=args.unit), file=sys.stderr)
        return 1
    failed = False
    for unit in units:
        result = htmlbuild.build(course, unit, args.version)
        for warning in result.warnings:
            print(t("commands", "warning_line", text=warning))
        print(t("htmlkit", "built", n=unit["n"], files=result.files, path=result.out_dir.relative_to(course["_project"].root).as_posix()))
        if result.package and not args.no_check and not _print_check(course, unit, args.browser):
            result.package.unlink(missing_ok=True)
            print(t("playcheck", "not_delivered"), file=sys.stderr)
            failed = True
            continue
        if result.package:
            print(t("htmlkit", "packaged", name=result.package.name, size=_size(result.package)))
        else:
            index = (result.out_dir / "index.html").relative_to(course["_project"].root).as_posix()
            print(t("htmlkit", "preview", code=course["code"], path=index))
    message = htmlbuild.mark_assembled(course)
    if message:
        print(message)
    common.mirror(course["_project"], course["code"])
    return 1 if failed else 0

def _print_check(course: dict, unit: dict, browser: str | None) -> bool:
    """`assemble check` of one built unit, printed; True when it has no errors."""
    from coursekit.htmlkit import playcheck

    result = playcheck.check(course, unit, browser)
    for warning in result.warnings:
        print(t("commands", "warning_line", text=warning))
    for error in result.errors:
        print(t("commands", "error_line", text=error))
    if result.played:
        print(t("playcheck", "summary", n=unit["n"], lessons=result.lessons, tests=result.tests, simulations=result.simulations,
                paths=result.paths, errors=len(result.errors), warnings=len(result.warnings)))
    else:
        print(t("playcheck", "files_only", n=unit["n"], errors=len(result.errors), warnings=len(result.warnings)))
    return not result.errors

def cmd_assemble_check(course: dict, args: argparse.Namespace) -> int:
    from coursekit import preview
    from coursekit.htmlkit import build as htmlbuild

    if coursemod.backend(course) != "html":
        print(t("commands", "assemble_build_needs_html", code=course["code"], backend=coursemod.backend(course)), file=sys.stderr)
        return 1
    units = [u for u in coursemod.package_units(course) if args.unit is None or u["n"] == args.unit]
    if not units:
        print(t("commands", "unit_not_found", n=args.unit), file=sys.stderr)
        return 1
    ok = True
    for unit in units:
        if not preview.stamp(course, unit["n"]):
            print(t("preview", "building", n=unit["n"]))
            htmlbuild.build(course, unit, None)
        ok = _print_check(course, unit, args.browser) and ok
    return 0 if ok else 1

def _size(path: Path) -> str:
    from coursekit import store

    return store.human(path.stat().st_size)

def cmd_assemble(args: argparse.Namespace) -> int:
    import json

    course = coursemod.load(common.project(), args.code)
    statesmod.ensure_active(course)
    if args.action == "build":
        return cmd_assemble_build(course, args)
    if args.action == "check":
        return cmd_assemble_check(course, args)
    if coursemod.backend(course) == "html":
        print(t("commands", "assemble_creator_only", code=course["code"], action=args.action), file=sys.stderr)
        return 1
    if args.unit is None:
        print(t("commands", "assemble_needs_unit", action=args.action), file=sys.stderr)
        return 2
    unit = coursemod.package_unit(course, args.unit)
    if unit is None:
        print(t("commands", "unit_not_found", n=args.unit), file=sys.stderr)
        return 1
    if args.action == "plan":
        plan, errors, warnings, counts = assemblemod.write_plan(course, unit)
        for w in warnings:
            print(t("commands", "warning_line", text=w))
        for e in errors:
            print(t("commands", "error_line", text=e))
        if plan is None:
            return 1
        print(t("commands", "assemble_plan", path=f"assembly/unit-{args.unit:02d}.plan.json", lessons=len(plan["lessons"]),
                bricks=sum(counts.values()), detail=", ".join(f"{k} {v}" for k, v in counts.items())))
        return 0
    if args.action == "diff":
        print(json.dumps(assemblemod.diff(course, unit), indent=1, ensure_ascii=False))
        return 0
    if args.action == "checked":
        print(assemblemod.record_checked(course, unit))
        common.mirror(course["_project"], course["code"])
        return 0
    if args.action == "link":
        if not (args.content_id or args.preview or args.review):
            print(t("commands", "link_needs_content_id"), file=sys.stderr)
            return 2
        print(assemblemod.link(course, unit, args.content_id, args.preview, args.review))
        common.mirror(course["_project"], course["code"])
        return 0
    if args.content:
        print(assemblemod.record_content_title(course, unit))
        common.mirror(course["_project"], course["code"])
        return 0
    if not (args.lesson and (args.lesson_id or args.keep_ids)):
        print(t("commands", "applied_needs_lesson"), file=sys.stderr)
        return 2
    ids = args.brick_ids
    if args.brick_ids_file:
        ids = Path(args.brick_ids_file).read_text(encoding="utf-8")
    replace = dict(pair.split("=", 1) for pair in re.split(r"[,\s]+", args.replace_id or "") if "=" in pair)
    print(assemblemod.record_lesson(course, unit, args.lesson, args.lesson_id, [b for b in re.split(r"[,\s]+", ids) if b],
                                    args.keep_ids, replace))
    common.mirror(course["_project"], course["code"])
    return 0

def cmd_directives(args: argparse.Namespace) -> int:
    project = common.project()
    registry = config.effective("directives", project).value
    new_lines, removed, total = directives.check(registry, Path(args.file))
    for line in [*new_lines, *removed]:
        print(line)
    if not new_lines and not removed:
        print(t("commands", "directives_ok", total=total))
        return 0
    return 1

def cmd_delivery(args: argparse.Namespace) -> int:
    course = coursemod.load(common.project(), args.code)
    if args.action == "check":
        warning = deliverymod.check_ready(course)
        print(warning or t("commands", "delivery_ready", code=course["code"]))
        return 0
    if args.action == "questions":
        if not args.version:
            print(t("commands", "delivery_needs_version", action=args.action), file=sys.stderr)
            return 2
        print(deliverymod.add_questions(course, args.version, args.url))
        common.mirror(course["_project"], course["code"])
        return 0
    if args.unit is None or not args.version:
        print(t("commands", "delivery_needs_unit_version", action=args.action), file=sys.stderr)
        return 2
    if args.action == "name":
        deliverymod.check_ready(course)
        print(deliverymod.expected_name(course, args.unit, args.version))
        return 0
    if args.action == "download":
        if not args.url:
            print(t("commands", "delivery_download_needs_url"), file=sys.stderr)
            return 2
        print(deliverymod.download(course, args.unit, args.version, args.url))
        return 0
    if not args.file:
        print(t("commands", "delivery_add_needs_file"), file=sys.stderr)
        return 2
    print(deliverymod.add(course, args.unit, args.version, args.file, args.job, args.snapshot))
    common.mirror(course["_project"], course["code"])
    return 0

def _print_contrast(tokens: dict) -> bool:
    results = thememod.check(tokens)
    for ok, line in results:
        print(t("commands", "theme_check_ok" if ok else "theme_check_fail", line=line))
    return all(ok for ok, _ in results)

def cmd_theme(args: argparse.Namespace) -> int:
    project = common.project()
    if args.action == "show" and args.file and not args.course:
        args.course = args.file  # `theme show PWD` is `theme show --course PWD`
    course = coursemod.load(project, args.course) if args.course else None
    rel = lambda path: path.relative_to(project.root).as_posix()  # noqa: E731
    if args.action == "tokens":
        print(t("commands", "theme_wrote", path=rel(thememod.write_css(project, course))))
        return 0
    if args.action == "import":
        project_backend = (config.project_data(project).get("assembly") or {}).get("backend") or "creator"
        backend = coursemod.backend(course) if course else project_backend
        if not args.file and backend != "html":
            print(t("commands", "theme_import_needs_file"), file=sys.stderr)
            return 2
        path, tokens = thememod.import_creator(project, course, Path(args.file) if args.file else None)
        origin = tokens["origin"]
        if origin["source"] == "css":
            print(t("commands", "theme_imported_css", path=rel(path), file=origin["file"]))
        else:
            print(t("commands", "theme_imported", path=rel(path), name=origin.get("name") or "-", theme_id=origin.get("theme_id") or "-"))
        for note in origin["notes"]:
            print(t("commands", "warning_line", text=note))
        if not _print_contrast(tokens):
            print(t("commands", "theme_contrast_hint_css" if origin["source"] == "css" else "theme_contrast_hint"))
        return 0
    if args.action == "sample":
        from coursekit import jobaid

        try:
            out, warnings = jobaid.sample(project, course)
        except (jobaid.JobAidError, mediatools.ToolError) as exc:
            print(t("commands", "error_line", text=exc), file=sys.stderr)
            return 1
        used = jobaid.own_template(project, course)
        print(t("jobaid", "sample", path=rel(out), template=rel(used) if used else "coursekit"))
        for warning in warnings:
            print(t("commands", "warning_line", text=warning))
        return 0
    if args.action == "roles":
        tokens = thememod.load(project, course)
        for row in thememod.roles(tokens):
            origin = t("theme", f"role_from_{row['from']}", ref=row["ref"] or "")
            print(t("theme", "role_line", role=row["role"], value=row["value"], name=f" ({row['palette']})" if row["palette"] else "",
                    origin=origin))
            print(t("theme", "role_seen", use=row["use"]))
        palette = tokens.get("palette") or {}
        if palette:
            print(t("theme", "roles_palette", palette=", ".join(f"{k} {v}" for k, v in palette.items())))
        return 0
    if args.action == "show":
        found = thememod.status(project, course)
        print(t("commands", "theme_scope_course" if found.scope == "course" else "theme_scope_project", path=rel(found.path)))
        if found.state == "missing":
            print(t("commands", "theme_missing", path=rel(found.path)))
        elif found.state == "manual":
            print(t("commands", "theme_manual"))
        elif found.origin.get("source") == "css":
            o = found.origin
            print(t("commands", "theme_origin_css", file=o.get("file") or "-", digest=o.get("sha256") or "-",
                    date=str(o.get("imported_at") or "")[:10]))
        else:
            o = found.origin
            print(t("commands", "theme_origin", name=o.get("name") or "-", theme_id=o.get("theme_id") or "-",
                    version=o.get("version") or "-", date=str(o.get("imported_at") or "")[:10]))
        return 0
    return 0 if _print_contrast(thememod.load(project, course)) else 1
