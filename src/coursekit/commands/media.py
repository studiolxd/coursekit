"""The commands of the media: media, voice, tts, subtitles, video and capture."""


from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from coursekit import capture as capturemod
from coursekit import course as coursemod
from coursekit import media as mediamod
from coursekit import states as statesmod
from coursekit import (
    ttsbatch,
    voices,
)
from coursekit import video as videomod
from coursekit.commands import common
from coursekit.i18n import t
from coursekit.media import access as mediaaccess
from coursekit.media import check as mediacheck
from coursekit.media import gallery as mediagallerymod
from coursekit.media import tools as mediatools


def cmd_capture(args: argparse.Namespace) -> int:
    project = common.project()
    try:
        if args.action == "serve":
            from coursekit.capture import session as capture_session

            capture_session.serve(project)
            return 0
        if args.action == "profiles":
            entries = capturemod.profiles(project)
            for entry in entries:
                state = (t("capture", "no_login") if not entry["login"] else
                         t("capture", "session_since", at=entry["logged_in_at"]) if entry["logged_in_at"] else t("capture", "no_session"))
                if not entry["configured"]:
                    state += " · " + t("capture", "not_configured")
                print(t("capture", "profile_line", name=entry["name"], account=entry["account"] or "—",
                        url=entry["start_url"] or "—", state=state))
            if not entries:
                print(t("capture", "no_profiles"))
            return 0
        if not args.target and args.action not in ("allow", "revoke"):  # without a course: the permission of the project
            print(t("capture", "needs_target", action=args.action), file=sys.stderr)
            return 2
        if args.action == "login":
            print(t("capture", "login_open", name=args.target))
            meta = capturemod.login(project, args.target)
            print(t("capture", "login_done", name=args.target, at=meta["logged_in_at"]))
        elif args.action == "logout":
            done = capturemod.logout(project, args.target)
            print(t("capture", "logout_done" if done else "logout_none", name=args.target))
        elif args.action == "allow":
            if not args.mode:
                print(t("capture", "needs_mode"), file=sys.stderr)
                return 2
            course = None
            if args.target:
                course = coursemod.load(project, args.target)
                statesmod.ensure_active(course)
            grant = capturemod.allow(project, course, args.ids, args.mode, args.profile, args.window, args.minutes)
            modes = "; ".join(mode + (f" ({params.get('profile') or t('capture', 'open_profile')})" if mode == "browser" else
                                      f" ({params.get('window') or t('capture', 'open_window')})" if mode == "desktop" else "")
                              for mode, params in grant["modes"].items())
            every = t("capture", "every_interface_asset" if course else "every_course")
            print(t("capture", "allowed", scope=course["code"] if course else t("capture", "scope_project"), modes=modes,
                    assets=", ".join(grant["assets"] or []) or every, until=grant["expires_at"] or t("capture", "no_expiry")))
        elif args.action == "revoke":
            done = capturemod.revoke(project, args.target.upper() if args.target else None)
            print(t("capture", "revoked" if done else "revoke_none", code=args.target or t("capture", "scope_project")))
        elif args.action == "review" and not args.ids:  # every capture of the course, on one page
            print(capturemod.review_all(coursemod.load(project, args.target)).relative_to(project.root).as_posix())
        else:
            if len(args.ids) != 1:
                print(t("capture", "needs_one_id", action=args.action), file=sys.stderr)
                return 2
            course = coursemod.load(project, args.target)
            asset_id = args.ids[0]
            if args.action == "redact":
                statesmod.ensure_active(course)
                result = capturemod.redact(project, course, asset_id, Path(args.file) if args.file else None)
                found = ", ".join(f"{kind} {n}" for kind, n in sorted(result["findings"].items())) or t("capture", "review_nothing")
                for warning in result["warnings"]:
                    print(t("commands", "warning_line", text=warning))
                print(t("capture", "redacted", id=asset_id, found=found, file=result["file"].relative_to(project.root).as_posix(),
                        review=result["review"].relative_to(project.root).as_posix()))
            elif args.action == "review":
                print(capturemod.review(course, asset_id).relative_to(project.root).as_posix())
            elif args.action == "stage":
                statesmod.ensure_active(course)
                workspace = capturemod.mount_stage(project, course, asset_id, args.prepare or [])
                print(t("capture", "stage_mounted", name=asset_id, folder=workspace.folder.as_posix(),
                        home=t("capture", "stage_home_clean") if workspace.home != Path.home() else t("capture", "stage_home_real")))
            elif args.action == "replay":
                from coursekit.capture import replay as capture_replay

                statesmod.ensure_active(course)
                try:
                    result = capture_replay.replay(project, course["code"], asset_id, part=args.part or "")
                except capture_replay.ReplayError as exc:
                    raise capturemod.CaptureError(str(exc)) from None
                for warning in result["warnings"]:
                    print(t("commands", "warning_line", text=warning))
                made = [p.relative_to(project.root).as_posix() for p in ([result["video"]] if result["video"] else [])]
                made += [p.relative_to(project.root).as_posix() for p in result["shots"][-1:]]
                found = ", ".join(f"{kind} {n}" for kind, n in result["findings"].items()) or t("capture", "review_nothing")
                print(t("capture", "replayed", id=asset_id, files=", ".join(made), found=found,
                        review=result["review"].relative_to(project.root).as_posix()))
            else:
                decision = capturemod.decide(project, course, asset_id, args.action == "approve", args.note, args.mask)
                print(t("capture", f"decided_{decision['state']}", id=asset_id, code=course["code"]))
                common.mirror(project, course["code"])
    except capturemod.CaptureError as exc:
        print(t("commands", "error_line", text=exc), file=sys.stderr)
        return 1
    return 0

def cmd_video(args: argparse.Namespace) -> int:
    project = common.project()
    if args.code is None and args.action not in ("catalog", "gallery"):
        print(t("video", "needs_code", action=args.action), file=sys.stderr)
        return 2
    course = coursemod.load(project, args.code) if args.code else videomod.project_scope(project)
    root = project.root
    if args.action not in ("catalog", "gallery") and not args.id:
        print(t("video", "needs_id", action=args.action), file=sys.stderr)
        return 2
    try:
        if args.action == "catalog":
            print("\n".join(videomod.catalog(course)))
            return 0
        if args.action == "gallery" and args.serve:  # the live gallery, in the browser, until Ctrl+C
            code = args.code
            reload = (lambda: coursemod.load(project, code)) if code else (lambda: videomod.project_scope(project))
            return videomod.serve_gallery(videomod.live_gallery(course), args.port, not args.no_open, reload=reload)
        if args.action == "gallery":
            print(t("video", "gallery_done", path=videomod.gallery(course).relative_to(root).as_posix()))
            return 0
        if args.action == "check":
            findings = videomod.check(course, args.id)
            for f in findings:
                line = t("video", "finding", where=f.where, code=f.code, text=f.text)
                print(t("commands", "error_line" if f.level == "error" else "warning_line", text=line))
            if not findings:
                print(t("video", "check_ok", id=args.id))
            return 1 if any(f.level == "error" for f in findings) else 0
        if args.action == "new":
            path = videomod.new(course, args.id)
            print(t("video", "created", path=path.relative_to(root).as_posix()))
            return 0
        statesmod.ensure_active(course)
        if args.action == "voice":
            made = videomod.voice(course, args.id, batch=args.batch)
            print(t("video", "voice_queued_done" if args.batch else "voice_done", count=made))
        elif args.action == "preview":
            print(t("video", "preview", path=videomod.preview(course, args.id).relative_to(root).as_posix()))
        elif args.action == "export":
            done = videomod.export(course, args.id)
            print(t("video", "exported", path=done["folder"].relative_to(root).as_posix(), scenes=done["scenes"], layers=done["layers"],
                    voices=done["voices"]))
        elif args.action == "render":
            done = videomod.render(course, args.id)
            print(t("video", "rendered", path=done["video"].relative_to(root).as_posix(), seconds=f"{done['seconds']:.1f}",
                    scenes=done["scenes"]))
            common.mirror(project, course["code"])
    except (videomod.VideoError, mediaaccess.AccessError, mediacheck.CheckError) as exc:
        print(t("commands", "error_line", text=exc), file=sys.stderr)
        return 1
    return 0

def cmd_media(args: argparse.Namespace) -> int:
    project = common.project()
    if args.action == "providers":
        print("\n".join(mediamod.providers(project)))
        return 0
    if not args.code:
        print(t("commands", "action_needs_course"), file=sys.stderr)
        return 2
    course = coursemod.load(project, args.code)
    if args.action == "extract":
        counts = mediamod.extract(course)
        print(t("commands", "media_manifest", total=sum(counts.values()), detail=", ".join(f"{k} {v}" for k, v in counts.items())))
        return 0
    if args.action == "plan":
        warnings, lines = mediamod.plan(course)
        for w in warnings:
            print(t("commands", "warning_line", text=w))
        print("\n".join(lines) if lines else t("commands", "media_nothing"))
        return 0
    if args.action == "check":
        try:
            findings, fixed = mediacheck.check(course, [args.id, *args.more] if args.id else None, args.fix)
        except mediacheck.CheckError as exc:
            print(t("commands", "error_line", text=exc), file=sys.stderr)
            return 1
        if getattr(args, "json", False):
            print(json.dumps({"ok": not findings, "fixed": fixed,
                              "findings": [{"asset": f.asset, "code": f.code, "text": f.text} for f in findings]},
                             ensure_ascii=False, indent=2))
            return 1 if findings else 0
        for line in fixed:
            print(line)
        for f in findings:
            print(t("commands", "warning_line", text=t("mediacheck", "line", asset=f.asset, code=f.code, text=f.text)))
        if not findings:
            print(t("mediacheck", "none"))
        return 1 if findings else 0
    if args.action in ("sheet", "transcript"):
        if not args.id:
            print(t("commands", "media_set_needs_id"), file=sys.stderr)
            return 2
        try:
            if args.action == "sheet":
                out = mediacheck.sheet(course, args.id, args.frames)
                print(t("mediacheck", "sheet", path=out.relative_to(course["_project"].root).as_posix()))
            else:
                statesmod.ensure_active(course)
                done = mediaaccess.write(course, args.id)
                root = course["_project"].root
                print(t("mediaaccess", "written", id=args.id, transcript=done["transcript"].relative_to(root).as_posix(),
                        descriptions=done["descriptions"].relative_to(root).as_posix()))
                common.mirror(course["_project"], course["code"])
        except (mediacheck.CheckError, mediaaccess.AccessError) as exc:
            print(t("commands", "error_line", text=exc), file=sys.stderr)
            return 1
        return 0
    if args.action == "gallery":
        if args.serve:  # the page in the browser, rebuilt when the course changes, until Ctrl+C
            return mediagallerymod.serve(course, lambda: coursemod.load(project, args.code), args.port, not args.no_open)
        print(t("mediagallery", "written", path=mediagallerymod.build(course).relative_to(project.root).as_posix()))
        return 0
    if args.action == "stock":
        if not args.id or not (args.find or args.take):
            print(t("illustrations", "stock_needs"), file=sys.stderr)
            return 2
        print("\n".join(mediamod.stock(course, args.id, find=args.find, take=args.take, color=args.color)))
        return 0
    if args.action == "embed":
        if not args.id:
            print(t("commands", "media_set_needs_id"), file=sys.stderr)
            return 2
        print(mediamod.embed(course, args.id))
        return 0
    if args.action == "narrate":
        statesmod.ensure_active(course)
        try:
            count = mediamod.narrate(course, [args.id, *args.more] if args.id else None, args.all, batch=args.batch)
        except (mediamod.MediaError, mediatools.ToolError) as exc:
            print(t("commands", "error_line", text=exc), file=sys.stderr)
            return 1
        print(t("commands", "media_narration_queued" if args.batch else "media_narrated", count=count))
        common.mirror(course["_project"], course["code"])
        return 0
    if args.action == "anchors":
        statesmod.ensure_active(course)
        try:
            lines = mediamod.anchors(course, [args.id, *args.more] if args.id else None, args.anchor_set)
        except mediamod.MediaError as exc:
            print(t("commands", "error_line", text=exc), file=sys.stderr)
            return 1
        print("\n".join(lines) if lines else t("anchors", "nothing"))
        common.mirror(course["_project"], course["code"])
        return 0
    if args.action in ("fit", "render"):
        if not (args.id or args.file) or (args.action == "fit" and not args.size):
            print(t("commands", "media_fit_needs"), file=sys.stderr)
            return 2
        try:
            print(mediamod.image_tool(course, args.id, args.action, args.size, args.file))
        except (mediamod.MediaError, mediatools.ToolError) as exc:
            print(t("commands", "error_line", text=exc), file=sys.stderr)
            return 1
        return 0
    if args.action == "adopt":
        statesmod.ensure_active(course)
        if not (args.id and args.file):
            print(t("commands", "media_adopt_needs"), file=sys.stderr)
            return 2
        try:
            print(mediamod.adopt(course, args.id, args.file, args.alt))
        except mediamod.MediaError as exc:
            print(t("commands", "error_line", text=exc), file=sys.stderr)
            return 1
        common.mirror(course["_project"], course["code"])
        return 0
    if args.action == "optimize":
        statesmod.ensure_active(course)
        try:
            lines = mediamod.optimize(course, [args.id, *args.more] if args.id else None)
        except (mediamod.MediaError, mediatools.ToolError) as exc:
            print(t("commands", "error_line", text=exc), file=sys.stderr)
            return 1
        print("\n".join(lines) if lines else t("commands", "media_optimize_none"))
        common.mirror(course["_project"], course["code"])
        return 0
    if args.action == "redo":
        statesmod.ensure_active(course)
        chosen = mediamod.redo(course, [args.id, *args.more] if args.id else None, args.all, args.clean, args.recapture)
        print(t("commands", "media_redo", assets=", ".join(chosen)) if chosen else t("commands", "media_redo_none"))
        common.mirror(course["_project"], course["code"])
        return 0
    if args.action == "upload":
        if not (args.file and args.url and args.content_type):
            print(t("commands", "media_upload_needs"), file=sys.stderr)
            return 2
        path = Path(args.file)
        for base in (course["_dir"], course["_project"].root):
            if not path.is_absolute() and (base / path).is_file():
                path = base / path
                break
        print(mediatools.upload(path, args.url, args.content_type, args.method))
        return 0
    if not args.id:
        print(t("commands", "media_set_needs_id"), file=sys.stderr)
        return 2
    statesmod.ensure_active(course)
    values = {k: getattr(args, k) for k in ("status", "recipe", "asset_path", "file", "alt", "transcript", "subtitles_path",
                                            "made_with", "download", "download_title", "download_asset_path", "force", "depicts",
                                            "unit", "decorative")}
    print(mediamod.set_asset(course, args.id, **values))
    common.mirror(course["_project"], course["code"])
    return 0

def cmd_download(args: argparse.Namespace) -> int:
    project = common.project()
    print(mediatools.download(args.url, Path(args.out), project.root))
    return 0

def cmd_voice(args: argparse.Namespace) -> int:
    project = common.project()
    if args.code in voices.PROVIDERS and args.provider is None:  # `voice set gemini`: the voice of the project
        args.code, args.provider = None, args.code
    course = coursemod.load(project, args.code) if args.code else None
    if args.action == "list":
        print("\n".join(voices.listing(course, project)))
        return 0
    if args.action == "unset":
        print(voices.unset_voice(course, project))
        return 0
    if not args.provider or (course is None and args.character):
        print(t("commands", "voice_set_needs"), file=sys.stderr)
        return 2
    if course is None:
        message, warning = voices.set_project_voice(project, args.provider, args.voice, args.speaker)
    else:
        message, warning = voices.set_voice(course, args.provider, args.voice, args.speaker, args.character)
    if warning:
        print(t("commands", "voice_warning", warning=warning), file=sys.stderr)
    print(message)
    return 0

def cmd_tts(args: argparse.Namespace) -> int:
    project = common.project()
    course = coursemod.load(project, args.course) if args.course else None
    if args.batch:
        if course is None or args.engine or args.voice or args.speaker:
            print(t("commands", "tts_batch_needs"), file=sys.stderr)
            return 2
        mediatools.require_file(Path(args.input))
        out = Path(args.out).resolve()
        try:
            out.relative_to(project.root.resolve())
        except ValueError:
            print(t("commands", "tts_batch_outside", path=Path(args.out).as_posix()), file=sys.stderr)
            return 2
        ident = out.relative_to(project.root.resolve()).as_posix()
        added = ttsbatch.add(course, "tts", ident, Path(args.input).read_text(encoding="utf-8"), out, character=args.character)
        print(t("commands", "tts_queued" if added else "tts_already_queued", path=ident, code=course["code"]))
        return 0
    print(mediatools.tts(course, args.engine, Path(args.input), Path(args.out), args.voice, args.speaker, args.character))
    return 0

def cmd_tts_batch(args: argparse.Namespace) -> int:
    course = coursemod.load(common.project(), args.code)
    if args.action == "list":
        print("\n".join(ttsbatch.listing(course)))
        return 0
    if args.action == "send":
        done = ttsbatch.send(course)
        print(t("ttsbatch", "sent", job=done["job"], items=done["items"], requests=done["requests"]))
        if done["left"]:
            print(t("ttsbatch", "left_for_later", count=done["left"]))
        return 0
    if args.action == "status":
        done = ttsbatch.status(course)
        if not done["state"]:
            print(t("ttsbatch", "no_job_queued", code=course["code"], count=done["queued"]))
            return 0
        stats = ", ".join(f"{k} {v}" for k, v in done["stats"].items())
        print(t("ttsbatch", "status_line", job=done["job"], state=done["state"], stats=stats or "—"))
        return 0
    done = ttsbatch.collect(course)
    if done["state"] not in ttsbatch.FINISHED:
        print(t("ttsbatch", "still_waiting", state=done["state"], count=done["waiting"]))
        return 0
    print(t("ttsbatch", "collected", done=done["done"], failed=done["failed"], state=done["state"]))
    common.mirror(course["_project"], course["code"])
    return 1 if done["failed"] else 0

def cmd_subtitles(args: argparse.Namespace) -> int:
    project = common.project()
    language = coursemod.language(coursemod.load(project, args.course)) if args.course else args.language
    mediatools.subtitles(Path(args.audio), Path(args.text), Path(args.out), args.model, language)
    print(t("commands", "subtitles_wrote", path=args.out))
    return 0
