"""`coursekit capture replay`: the steps of the `capture` block of the brief, repeated at the pace of a person, recorded.

A capture session (the agent) writes down what it did; the replay does it again without a model, in the same clean browser
(the personal data replaced on screen, see `capture_session`), with a visible pointer that travels to each target, the
pauses of `capture.yaml › replay` and the text typed letter by letter. The stretches between `record: start` and
`record: stop` are recorded with the screencast of the browser and become media/recordings/<id>.mp4 (with ffmpeg; with
`redact › pixel_check` the video is also covered on the pixels); a `shot` step saves media/recordings/<id>.png. The result
waits for a person, as any capture (`coursekit capture review` and `approve`).

A step names its target by role and name, by label or by text (`{click: {role: button, name: Save}}`, `{click: {label:
Minimum length}}`) and, when it was recorded by a session, also by position: the name is tried first, so a new version
of the application that moved a button is still repeated; the position is the fallback.

    steps:
      - click: {label: "Security"}
      - fill: {label: "Minimum length", value: "12"}
      - record: start
      - click: {role: button, name: "Save"}
      - wait: 1500
      - record: stop
      - shot: true
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from coursekit import capture as capturemod
from coursekit import capture_session as sessionmod
from coursekit import redact as redactmod
from coursekit.i18n import t
from coursekit.mcpserver import ToolError

KINDS = ("click", "fill", "point", "move", "drag", "scroll", "type", "key", "wait", "navigate", "shot", "record")


class Timeline:
    """When and where each click and each point happens in the video (seconds from its start; position as fractions of the
    screen): what a zoom of the video follows, so its coordinates are never guessed."""

    def __init__(self, viewport: tuple[int, int]):
        self.viewport = viewport
        self.events: list[dict] = []
        self.offset = 0.0  # seconds of the stretches already recorded
        self.started: float | None = None
        self._part: list[dict] = []

    def start(self) -> None:
        self.started, self._part = time.time(), []

    def stop(self, duration: float, first_frame: float | None = None) -> None:
        """Closes a stretch of `duration` seconds; `first_frame`, when known, is when its first frame appeared."""
        shift = (first_frame - self.started) if first_frame and self.started else 0.0
        for event in self._part:
            event["t"] = round(max(0.0, min(duration, event["t"] - shift)) + self.offset, 3)
        self.events += self._part
        self.offset += duration
        self.started, self._part = None, []

    def note(self, kind: str, x: float, y: float, label: str = "") -> None:
        if self.started is None:
            return  # not recording
        w, h = self.viewport
        event = {"t": time.time() - self.started, "kind": kind, "fx": round(x / w, 4), "fy": round(y / h, 4)}
        if label:
            event["label"] = label
        self._part.append(event)

    def write(self, path: Path, video: Path) -> None:
        data = {"video": video.name, "width": self.viewport[0], "height": self.viewport[1], "duration": round(self.offset, 3),
                "events": self.events}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")


def events_path(video: Path) -> Path:
    """`U1-S2-M1.mp4` → `U1-S2-M1.events.json`."""
    return video.with_suffix(".events.json")


def duration_of(video: Path) -> float | None:
    probe = shutil.which("ffprobe")
    if not probe:
        return None
    done = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                          capture_output=True, text=True, check=False)
    try:
        return float(done.stdout.strip())
    except ValueError:
        return None


class ReplayError(Exception):
    pass


def _target(step: dict) -> dict:
    return {k: step[k] for k in ("role", "name", "label") if step.get(k)} | dict(step.get("target") or {})


def _point(session, step: dict, n: int) -> tuple[float, float]:
    """Where a step acts, in css pixels: the element it names, else the position it was recorded at."""
    found = session.backend.locate(_target(step)) if _target(step) else None
    if found:
        return found
    if "x" in step and "y" in step:
        return float(step["x"]), float(step["y"])
    raise ReplayError(t("capture", "replay_not_found", n=n, target=_target(step) or step))


def encode(frames: list[tuple[float, bytes]], target: Path, fps: int) -> None:
    """The frames of a screencast (each with the time it appeared; the last one, empty, is when it stopped) as an MP4."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ReplayError(t("redact", "ffmpeg_missing"))
    shown = [(at, data) for at, data in frames if data]
    if not shown:
        raise ReplayError(t("capture", "replay_no_frames"))
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        lines = []
        for i, (at, data) in enumerate(shown):
            name = f"f{i:05d}.jpg"
            (folder / name).write_bytes(data)
            following = shown[i + 1][0] if i + 1 < len(shown) else frames[-1][0]
            lines += [f"file '{name}'", f"duration {max(1 / fps, following - at):.4f}"]
        lines.append(f"file 'f{len(shown) - 1:05d}.jpg'")  # the concat demuxer needs the last one twice
        (folder / "list.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        total = max(1 / fps, frames[-1][0] - shown[0][0])  # the repeated last image would add its own length: cut it
        done = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(folder / "list.txt"),
                               "-t", f"{total:.3f}",
                               "-vf", f"fps={fps},scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-crf", "20",
                               "-pix_fmt", "yuv420p", str(target)], capture_output=True, text=True, check=False)
        if done.returncode != 0:
            raise ReplayError(t("redact", "encode_failed", reason=redactmod._last_line(done.stderr)))


def _join(parts: list[Path], target: Path) -> None:
    if len(parts) == 1:
        shutil.move(str(parts[0]), target)
        return
    ffmpeg = shutil.which("ffmpeg")
    listing = target.with_suffix(".parts.txt")
    listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    try:
        done = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy",
                               str(target)], capture_output=True, text=True, check=False)
    finally:
        listing.unlink(missing_ok=True)
        for part in parts:
            part.unlink(missing_ok=True)
    if done.returncode != 0:
        raise ReplayError(t("redact", "encode_failed", reason=redactmod._last_line(done.stderr)))


def _label(spec: dict) -> str:
    target = _target(spec)
    return str(spec.get("note") or target.get("name") or target.get("label") or "")


def run_steps(session, steps: list, pace: dict, record, timeline: Timeline | None = None) -> list[Path]:
    """Does every step at the pace of a person. `record(on)` starts or stops a stretch of video; returns the shots saved."""
    pause, move_ms, delay = int(pace.get("pause_ms") or 0), int(pace.get("move_ms") or 0), int(pace.get("type_delay_ms") or 0)
    backend, shots = session.backend, []
    timeline = timeline or Timeline(backend.viewport)
    for n, raw in enumerate(steps, 1):
        if not isinstance(raw, dict) or len(raw) != 1 or next(iter(raw)) not in KINDS:
            raise ReplayError(t("capture", "replay_bad_step", n=n, step=raw, kinds=", ".join(KINDS)))
        session.check()
        kind, step = next(iter(raw.items()))
        if kind in ("click", "fill"):
            spec = step if isinstance(step, dict) else {"label": str(step)}
            x, y = _point(session, spec, n)
            backend.glide(x, y, move_ms)
            timeline.note("click", x, y, _label(spec))
            backend.click(x, y, spec.get("button", "left"), int(spec.get("count", 1)))
            if kind == "fill":
                if backend.focused_is_secret():
                    raise ToolError(t("capture", "secret_field"))
                backend.key("ControlOrMeta+A")
                backend.type_slowly(str(spec.get("value", "")), delay)
        elif kind == "point":  # a place of the screen, marked without touching it, for a zoom of the video
            spec = step if isinstance(step, dict) else {"label": str(step)}
            timeline.note("point", *_point(session, spec, n), _label(spec))
        elif kind == "move":
            backend.glide(*_point(session, step, n), move_ms)
        elif kind == "drag":
            (x1, y1), (x2, y2) = step["from"], step["to"]
            backend.glide(x1, y1, move_ms)
            backend.drag(x1, y1, x2, y2)
        elif kind == "scroll":
            backend.glide(float(step["x"]), float(step["y"]), move_ms)
            backend.scroll(float(step["x"]), float(step["y"]), float(step.get("dx", 0)), float(step.get("dy", 0)))
        elif kind == "type":
            if backend.focused_is_secret():
                raise ToolError(t("capture", "secret_field"))
            backend.type_slowly(str(step), delay)
        elif kind == "key":
            backend.key(sessionmod.normalize_key(str(step)))
        elif kind == "wait":
            backend.wait(max(0, min(int(step), 30000)))
        elif kind == "navigate":
            session.navigate(str(step))
            session.steps.pop()  # a replay writes down nothing
        elif kind == "shot":
            shots.append(session.save_shot())
            session.steps.pop()
        elif kind == "record":
            record(str(step) == "start")
        if kind not in ("wait", "record", "point"):
            backend.wait(pause)
    return shots


def replay(project, code: str, asset_id: str, backend_factory=None) -> dict:
    """Repeats the steps of the brief of a resource, records its video and leaves the result waiting for a person."""
    cfg = capturemod.settings(project)
    pace = dict(cfg.get("replay") or {})
    try:
        session = sessionmod.start(project, code, asset_id, backend_factory, cursor=bool(pace.get("cursor", True)))
    except ToolError as exc:
        raise ReplayError(str(exc)) from None
    course = session.course
    steps = sessionmod.read_block(course, asset_id).get("steps") or []
    shutil.rmtree(capturemod.review_dir(course, asset_id), ignore_errors=True)
    recordings = course["_dir"] / "media" / "recordings"
    parts: list[Path] = []
    recording = {"on": False}
    timeline = Timeline(session.backend.viewport)
    fps = int(pace.get("fps") or 30)

    def record(on: bool) -> None:
        if on and not recording["on"]:
            session.backend.start_recording()
            timeline.start()
        elif not on and recording["on"]:
            part = recordings / f"{asset_id}.part{len(parts)}.mp4"
            stopped = time.time()
            recorded = session.backend.stop_recording()
            first = None
            if isinstance(recorded, Path):  # the desktop records a video by itself
                part.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(recorded), part)
            else:
                first = next((at for at, data in recorded if data), None)
                encode(recorded, part, fps)
            timeline.stop(duration_of(part) or max(0.0, stopped - (timeline.started or stopped)), first)
            parts.append(part)
        recording["on"] = on

    try:
        if not steps:
            raise ReplayError(t("capture", "replay_no_steps", path=sessionmod.brief_file(course, asset_id).name))
        try:
            shots = run_steps(session, steps, pace, record, timeline)
            if recording["on"]:
                record(False)  # a record: start with no stop records until the end
        except ToolError as exc:
            raise ReplayError(str(exc)) from None
        video = None
        if parts:
            video = recordings / f"{asset_id}.mp4"
            _join(parts, video)
            parts.clear()
            timeline.write(events_path(video), video)
            if session.redactor is not None:
                covered = video.with_suffix(".covered.mp4")
                try:
                    redactmod.redact_video(video, covered, session.redactor, float(cfg["redact"].get("video_fps") or 4),
                                           capturemod.review_dir(course, asset_id))
                    covered.replace(video)
                except redactmod.RedactError as exc:
                    covered.unlink(missing_ok=True)
                    if session.grant.get("mode") == "desktop":  # nothing cleaned it before: it is not kept uncovered
                        video.unlink(missing_ok=True)
                        raise ReplayError(str(exc)) from None
                    session.warnings.append(str(exc))
            else:
                _sample_frames(video, capturemod.review_dir(course, asset_id))
    finally:
        for part in parts:
            part.unlink(missing_ok=True)
        session.close()
    findings = {kind: len(values) for kind, values in sorted(session.seen.items())}
    if session.redactor is not None:
        for kind, n in session.redactor.report.findings.items():
            findings[f"{kind} (pixels)"] = n
    if not video and not shots:
        raise ReplayError(t("capture", "replay_nothing", path=sessionmod.brief_file(course, asset_id).name))
    engine = "pixels" if session.grant.get("mode") == "desktop" else "page"
    report = {"engine": engine + (f" + {session.redactor.report.engine}" if session.redactor else ""), "findings": findings,
              "warnings": session.warnings, "frames": len(list(capturemod.review_dir(course, asset_id).glob("t*.png"))),
              "samples": []}
    review = capturemod.write_review(course, asset_id, report)
    _, _, _, asset = capturemod.find_asset(course, asset_id)
    previous = dict(asset.get("capture") or {})
    main = video or (shots[-1] if shots else None)
    asset["capture"] = {"state": "captured", "source": "replay", "engine": report["engine"], "at": sessionmod._now(),
                        "findings": findings, "warnings": session.warnings,
                        "file": main.relative_to(course["_dir"]).as_posix() if main else None, "masks": previous.get("masks")}
    capturemod.save_capture(course, asset_id, asset["capture"])
    return {"video": video, "shots": shots, "findings": findings, "warnings": session.warnings, "review": review,
            "events": events_path(video) if video else None}


def _sample_frames(video: Path, folder: Path) -> None:
    """A frame per second of the video for the review sheet (when the video was not read on the pixels)."""
    ffmpeg = shutil.which("ffmpeg")
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("t*.png"):
        old.unlink()
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(video), "-vf", "fps=1", str(folder / "t%04d.png")],
                   capture_output=True, check=False)
