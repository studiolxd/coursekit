"""`coursekit media check` and `coursekit media sheet`: the audios and videos produced, looked at before they go to the course.

check, for each audio or video produced (or the ones named):
- loudness: the integrated loudness and the true peak, measured with ffmpeg (`loudnorm`), against `media › checks`
  (EBU R128 for the web: -16 LUFS, peak -1 dBTP). With `--fix` a file out of range is brought there in place (two passes of
  `loudnorm`; the picture of a video is copied, not encoded again);
- captions: the cues of its VTT or SRT (next to the file, with its name) faster than `max_cps` characters per second;
- what is seen and not said (when the resource describes its scenes, see `mediaaccess`).

sheet: `sheet_frames` frames of a video, spread over its length, in one image (`.cache/media/<CODE>/<id>-sheet.png`), so the
agent can look at a video without playing it.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from coursekit import config as configmod
from coursekit import media as mediamod
from coursekit.i18n import t

AUDIO = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac")
VIDEO = (".mp4", ".webm", ".mov", ".mkv")
CUE_RE = re.compile(r"(\d+:)?(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(\d+:)?(\d{2}):(\d{2})[.,](\d{3})")


class CheckError(Exception):
    pass


@dataclass
class Finding:
    asset: str
    code: str  # LOUDNESS | CAPTIONS_FAST | NOT_SAID | NOT_CHECKED
    text: str


def settings(course: dict) -> dict:
    return dict(configmod.effective("media", course["_project"], course).get("checks") or {})


def _ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if not found:
        raise CheckError(t("mediacheck", "ffmpeg_missing"))
    return found


def media_of(course: dict, ids: list[str] | None) -> list[tuple[dict, Path]]:
    """The produced assets whose file is an audio or a video, with that file."""
    _, _, data = mediamod.load_manifest(course["_dir"])
    out = []
    for asset in data["assets"]:
        if ids and asset["id"] not in ids:
            continue
        name = str(asset.get("file") or "")
        if asset.get("status") not in ("produced", "uploaded") or not name.lower().endswith(AUDIO + VIDEO):
            continue
        path = course["_dir"] / name
        if path.exists():
            out.append((asset, path))
    return out


# ── loudness ─────────────────────────────────────────────────────────────────────────────────

def loudness(path: Path, filters: str = "") -> dict:
    """What `loudnorm` measures in a file: input_i (LUFS), input_tp (dBTP), input_lra, input_thresh."""
    target = filters or "loudnorm=print_format=json"
    done = subprocess.run([_ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", target, "-vn", "-f", "null", "-"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", done.stderr, re.S)
    if not match:
        raise CheckError(t("mediacheck", "no_audio", name=path.name))
    return json.loads(match.group(0))


def loudness_finding(asset: dict, path: Path, cfg: dict) -> Finding | None:
    measured = loudness(path)
    try:
        level, peak = float(measured["input_i"]), float(measured["input_tp"])
    except (KeyError, ValueError):
        return Finding(asset["id"], "NOT_CHECKED", t("mediacheck", "silent", name=path.name))
    target, top, margin = float(cfg["loudness_lufs"]), float(cfg["true_peak_db"]), float(cfg["loudness_tolerance"])
    if abs(level - target) <= margin and peak <= top:
        return None
    return Finding(asset["id"], "LOUDNESS", t("mediacheck", "loudness", name=path.name, level=f"{level:.1f}", peak=f"{peak:.1f}",
                                              target=f"{target:g}", top=f"{top:g}"))


def fix_loudness(path: Path, cfg: dict) -> None:
    """Brings the loudness of a file to the target in place: a first pass measures, the second applies (linear)."""
    target, top = float(cfg["loudness_lufs"]), float(cfg["true_peak_db"])
    m = loudness(path, f"loudnorm=I={target}:TP={top}:LRA=11:print_format=json")
    second = (f"loudnorm=I={target}:TP={top}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
              f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m.get('target_offset', 0)}:linear=true")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / f"fixed{path.suffix}"
        video = path.suffix.lower() in VIDEO
        codec = ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k"] if video else \
            {".mp3": ["-c:a", "libmp3lame", "-q:a", "2"], ".wav": ["-c:a", "pcm_s16le"]}.get(path.suffix.lower(), [])
        done = subprocess.run([_ffmpeg(), "-y", "-loglevel", "error", "-i", str(path), "-af", second, "-ar", "48000", *codec,
                               str(out)], capture_output=True, text=True, check=False)
        if done.returncode != 0 or not out.exists():
            raise CheckError(t("mediacheck", "fix_failed", name=path.name))
        shutil.move(str(out), path)


# ── captions ─────────────────────────────────────────────────────────────────────────────────

def cues(text: str) -> list[tuple[float, float, str]]:
    """The cues of a VTT or an SRT: (start, end, text)."""
    out = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        lines = block.strip().split("\n")
        for i, line in enumerate(lines):
            m = CUE_RE.search(line)
            if m:
                g = m.groups()
                start = int((g[0] or "0:")[:-1]) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 1000
                end = int((g[4] or "0:")[:-1]) * 3600 + int(g[5]) * 60 + int(g[6]) + int(g[7]) / 1000
                body = re.sub(r"<[^>]+>", "", " ".join(lines[i + 1:])).strip()
                if body:
                    out.append((start, end, body))
                break
    return out


def captions_of(path: Path) -> Path | None:
    return next((c for c in (path.with_suffix(".vtt"), path.with_suffix(".srt")) if c.exists()), None)


def caption_findings(asset: dict, path: Path, cfg: dict) -> list[Finding]:
    captions = captions_of(path)
    if captions is None:
        return []
    limit = float(cfg["max_cps"])
    fast = [(a, b, body) for a, b, body in cues(captions.read_text(encoding="utf-8", errors="replace"))
            if len(body) / max(0.001, b - a) > limit]
    if not fast:
        return []
    a, b, body = max(fast, key=lambda c: len(c[2]) / max(0.001, c[1] - c[0]))
    return [Finding(asset["id"], "CAPTIONS_FAST", t("mediacheck", "captions_fast", name=captions.name, count=len(fast),
                                                    at=f"{int(a // 60)}:{a % 60:04.1f}", cps=f"{len(body) / max(0.001, b - a):.0f}",
                                                    limit=f"{limit:g}"))]


# ── the check ────────────────────────────────────────────────────────────────────────────────

def check(course: dict, ids: list[str] | None = None, fix: bool = False) -> tuple[list[Finding], list[str]]:
    """What is wrong in the audios and videos produced, and what was fixed."""
    from coursekit import mediaaccess

    cfg = settings(course)
    findings, fixed = [], []
    for asset, path in media_of(course, ids):
        problem = loudness_finding(asset, path, cfg)
        if problem and problem.code == "LOUDNESS" and fix:
            fix_loudness(path, cfg)
            fixed.append(t("mediacheck", "fixed", name=path.name, target=f"{float(cfg['loudness_lufs']):g}"))
            problem = loudness_finding(asset, path, cfg)
        if problem:
            findings.append(problem)
        findings += caption_findings(asset, path, cfg)
        findings += [Finding(asset["id"], "NOT_SAID", text) for text in mediaaccess.not_said(course, asset)]
    return findings, fixed


def duration(path: Path) -> float:
    probe = shutil.which("ffprobe")
    if not probe:
        raise CheckError(t("mediacheck", "ffmpeg_missing"))
    done = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                          capture_output=True, text=True, check=False)
    try:
        return float(done.stdout.strip())
    except ValueError:
        raise CheckError(t("mediacheck", "no_video", name=path.name)) from None


def sheet(course: dict, asset_id: str, frames: int | None = None) -> Path:
    """`frames` frames of a video spread over its length, in one image, with the second of each one."""
    cfg = settings(course)
    found = [(a, p) for a, p in media_of(course, [asset_id]) if p.suffix.lower() in VIDEO]
    if not found:
        raise CheckError(t("mediacheck", "no_video", name=asset_id))
    _, path = found[0]
    n = max(1, int(frames or cfg.get("sheet_frames") or 24))
    columns = min(n, 6)
    rows = -(-n // columns)
    length = duration(path)
    out = course["_project"].cache_dir / "media" / course["code"] / f"{asset_id}-sheet.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    width = int(cfg.get("sheet_width") or 480)
    label = "drawtext=text='%{pts\\:hms}':x=8:y=8:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6"
    graph = f"fps={n}/{max(0.1, length):.3f},scale={width}:-2,{label},tile={columns}x{rows}:padding=6:margin=6"
    done = subprocess.run([_ffmpeg(), "-y", "-loglevel", "error", "-i", str(path), "-vf", graph, "-frames:v", "1", str(out)],
                          capture_output=True, text=True, check=False)
    if done.returncode != 0 or not out.exists():  # drawtext needs a font: without one, the sheet without the seconds
        graph = f"fps={n}/{max(0.1, length):.3f},scale={width}:-2,tile={columns}x{rows}:padding=6:margin=6"
        done = subprocess.run([_ffmpeg(), "-y", "-loglevel", "error", "-i", str(path), "-vf", graph, "-frames:v", "1", str(out)],
                              capture_output=True, text=True, check=False)
    if done.returncode != 0 or not out.exists():
        raise CheckError(t("mediacheck", "sheet_failed", name=path.name))
    return out
