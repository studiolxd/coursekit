"""The timeline of a montage for an editor (DaVinci Resolve, Final Cut, Premiere), to retouch a video by hand.

A neutral structure (tracks of clips, in whole frames) and its two translations:
- FCPXML 1.10, what DaVinci imports most reliably (File › Import › Timeline): the scenes in the main storyline, the layers
  connected above them and the voices below, with a marker on each scene;
- OpenTimelineIO (JSON), the open standard, which most editors and tools read.
The paths of the media arrive absolute: the files of an export are meant for this machine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import quoteattr


@dataclass
class Clip:
    name: str
    file: Path
    start: int  # frame of the timeline
    frames: int
    source_frames: int | None = None  # length of the medium, when known


@dataclass
class Track:
    kind: str  # video | audio
    name: str
    clips: list[Clip] = field(default_factory=list)


@dataclass
class Timeline:
    name: str
    fps: int
    width: int
    height: int
    frames: int
    tracks: list[Track]  # the first video track is the main one
    markers: list[tuple[int, str]] = field(default_factory=list)


def _time(frames: int, fps: int) -> str:
    return "0s" if frames == 0 else f"{frames}/{fps}s"


def fcpxml(tl: Timeline) -> str:
    """FCPXML 1.10: the clips of the main video track in the storyline; the others connected to the scene they fall in."""
    main = next(t for t in tl.tracks if t.kind == "video")
    others = [t for t in tl.tracks if t is not main]
    assets: dict[str, str] = {}
    lines = []

    def asset(clip: Clip, kind: str) -> str:
        key = f"{kind}:{clip.file}"
        if key not in assets:
            ident = f"a{len(assets) + 1}"
            assets[key] = ident
            media = 'hasVideo="1" format="r1"' if kind == "video" else 'hasAudio="1" audioSources="1" audioChannels="2" audioRate="48000"'
            length = _time(clip.source_frames or clip.frames, tl.fps)
            lines.append(f'    <asset id="{ident}" name={quoteattr(clip.name)} start="0s" duration="{length}" {media}>\n'
                         f'      <media-rep kind="original-media" src={quoteattr(clip.file.resolve().as_uri())}/>\n    </asset>')
        return assets[key]

    spine = []
    for clip in main.clips:
        ident = asset(clip, "video")
        inner = []
        for lane_base, tracks in ((1, [t for t in others if t.kind == "video"]), (-1, [t for t in others if t.kind == "audio"])):
            for n, track in enumerate(tracks):
                lane = lane_base * (n + 1)
                for c in track.clips:
                    if clip.start <= c.start < clip.start + clip.frames:
                        ref = asset(c, track.kind)
                        inner.append(f'        <asset-clip ref="{ref}" lane="{lane}" name={quoteattr(c.name)} '
                                     f'offset="{_time(c.start - clip.start, tl.fps)}" duration="{_time(c.frames, tl.fps)}" start="0s"/>')
        for at, name in tl.markers:
            if clip.start <= at < clip.start + clip.frames:
                inner.append(f'        <marker start="{_time(at - clip.start, tl.fps)}" duration="{_time(1, tl.fps)}" '
                             f'value={quoteattr(name)}/>')
        body = "\n".join(inner)
        opening = (f'      <asset-clip ref="{ident}" name={quoteattr(clip.name)} offset="{_time(clip.start, tl.fps)}" '
                   f'duration="{_time(clip.frames, tl.fps)}" start="0s" format="r1">')
        spine.append(opening + (f"\n{body}\n      " if body else "") + "</asset-clip>")
    resources = (f'    <format id="r1" name="FFVideoFormat{tl.height}p{tl.fps}" frameDuration="1/{tl.fps}s" width="{tl.width}" '
                 f'height="{tl.height}"/>\n' + "\n".join(lines))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n<fcpxml version="1.10">\n  <resources>\n' + resources +
            f'\n  </resources>\n  <library>\n    <event name={quoteattr(tl.name)}>\n      <project name={quoteattr(tl.name)}>\n'
            f'        <sequence format="r1" duration="{_time(tl.frames, tl.fps)}" tcStart="0s" tcFormat="NDF" audioLayout="stereo" '
            f'audioRate="48k">\n          <spine>\n' + "\n".join("    " + s for s in spine) +
            "\n          </spine>\n        </sequence>\n      </project>\n    </event>\n  </library>\n</fcpxml>\n")


def _rational(frames: int, fps: int) -> dict:
    return {"OTIO_SCHEMA": "RationalTime.1", "rate": float(fps), "value": float(frames)}


def _range(start: int, frames: int, fps: int) -> dict:
    return {"OTIO_SCHEMA": "TimeRange.1", "start_time": _rational(start, fps), "duration": _rational(frames, fps)}


def otio(tl: Timeline) -> str:
    """OpenTimelineIO (JSON): one track per track, with a gap wherever there is no clip, and the markers on the main track."""
    tracks = []
    for n, track in enumerate(tl.tracks):
        children, cursor = [], 0
        for clip in sorted(track.clips, key=lambda c: c.start):
            if clip.start > cursor:
                children.append({"OTIO_SCHEMA": "Gap.1", "name": "", "source_range": _range(0, clip.start - cursor, tl.fps),
                                 "effects": [], "markers": [], "metadata": {}})
            reference = {"OTIO_SCHEMA": "ExternalReference.1", "target_url": clip.file.resolve().as_uri(), "metadata": {},
                         "available_range": _range(0, clip.source_frames or clip.frames, tl.fps)}
            children.append({"OTIO_SCHEMA": "Clip.2", "name": clip.name, "source_range": _range(0, clip.frames, tl.fps),
                             "media_references": {"DEFAULT_MEDIA": reference}, "active_media_reference_key": "DEFAULT_MEDIA",
                             "effects": [], "markers": [], "metadata": {}})
            cursor = clip.start + clip.frames
        markers = [{"OTIO_SCHEMA": "Marker.2", "name": name, "color": "RED", "marked_range": _range(at, 1, tl.fps), "comment": "",
                    "metadata": {}} for at, name in tl.markers] if n == 0 else []
        tracks.append({"OTIO_SCHEMA": "Track.1", "name": track.name, "kind": "Video" if track.kind == "video" else "Audio",
                       "children": children, "source_range": None, "effects": [], "markers": markers, "metadata": {}})
    data = {"OTIO_SCHEMA": "Timeline.1", "name": tl.name, "global_start_time": _rational(0, tl.fps), "metadata": {},
            "tracks": {"OTIO_SCHEMA": "Stack.1", "name": "tracks", "children": tracks, "source_range": None, "effects": [],
                       "markers": [], "metadata": {}}}
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def srt(vtt: str) -> str:
    """The captions of a VTT as an SRT (what every editor reads)."""
    from coursekit.mediacheck import cues

    def stamp(seconds: float) -> str:
        ms = round(seconds * 1000)
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"

    return "".join(f"{i}\n{stamp(a)} --> {stamp(b)}\n{text}\n\n" for i, (a, b, text) in enumerate(cues(vtt), 1))
