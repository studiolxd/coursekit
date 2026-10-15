"""Lighter media: images scaled and recompressed, videos re-encoded, locally and without credits.

Used by `coursekit media optimize` (the file of an asset, in place, before uploading it to creator) and by the html
backend (a lighter copy goes into the package; the source file is not touched). The limits are `media.yaml › optimize`.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from coursekit.i18n import t
from coursekit.mediatools import ToolError, require_file, run

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
VIDEO_SUFFIXES = (".mp4",)  # what Remotion and VHS write; the file keeps its name, so the manifest stays valid


def settings(cfg: dict) -> tuple[dict, dict]:
    block = cfg.get("optimize") or {}
    return block.get("image") or {}, block.get("video") or {}


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_SUFFIXES


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_SUFFIXES


def _scaled(im, max_width: int):
    from PIL import Image

    if max_width and im.width > max_width:
        return im.resize((max_width, max(1, round(im.height * max_width / im.width))), Image.LANCZOS)
    return im


def image_to_webp(source: Path, target: Path, image_cfg: dict) -> None:
    """A lighter WebP copy: WebP keeps the transparency of the portraits and weighs a fraction of the PNG."""
    from PIL import Image

    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as im:
        _scaled(im, int(image_cfg.get("max_width") or 0)).save(target, "WEBP", quality=int(image_cfg.get("quality", 82)), method=6)


def shrink_image(path: Path, image_cfg: dict) -> tuple[int, int]:
    """Scales an image down to `max_width` and recompresses it in its own format; the file is replaced only if it weighs less."""
    from PIL import Image

    require_file(path)
    before = path.stat().st_size
    quality = int(image_cfg.get("quality", 82))
    with Image.open(path) as im:
        out = _scaled(im, int(image_cfg.get("max_width") or 0))
        with tempfile.TemporaryDirectory() as tmp:
            draft = Path(tmp) / path.name
            suffix = path.suffix.lower()
            if suffix in (".jpg", ".jpeg"):
                out.convert("RGB").save(draft, "JPEG", quality=quality, optimize=True, progressive=True)
            elif suffix == ".webp":
                out.save(draft, "WEBP", quality=quality, method=6)
            else:
                out.save(draft, "PNG", optimize=True)
            if draft.stat().st_size < before:
                shutil.copyfile(draft, path)
    return before, path.stat().st_size


def _encode(source: Path, target: Path, video_cfg: dict) -> None:
    height = int(video_cfg.get("max_height") or 0)
    command = ["ffmpeg", "-loglevel", "error", "-y", "-i", str(source)]
    if height:
        command += ["-vf", f"scale=-2:'min(ih,{height})'"]
    command += ["-c:v", "libx264", "-crf", str(video_cfg.get("crf", 26)), "-preset", str(video_cfg.get("preset", "medium")),
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", f"{int(video_cfg.get('audio_kbps', 128))}k",
                "-movflags", "+faststart", str(target)]
    run(command)


def video_to_mp4(source: Path, target: Path, video_cfg: dict) -> None:
    """A lighter MP4 copy for the html package (the copy is the encoded file whether or not it is smaller)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    _encode(source, target, video_cfg)


def shrink_video(path: Path, video_cfg: dict) -> tuple[int, int]:
    """Re-encodes a video as H.264/AAC capped at `max_height`; the file is replaced only if it weighs less."""
    require_file(path)
    before = path.stat().st_size
    with tempfile.TemporaryDirectory() as tmp:
        draft = Path(tmp) / "out.mp4"
        _encode(path, draft, video_cfg)
        if draft.stat().st_size < before:
            shutil.copyfile(draft, path)
    return before, path.stat().st_size


def shrink(path: Path, cfg: dict) -> str | None:
    """Optimises the file in place by its kind; None for a kind that is left as it is (SVG, GIF, audio, folders)."""
    image_cfg, video_cfg = settings(cfg)
    if is_image(path):
        before, after = shrink_image(path, image_cfg)
    elif is_video(path):
        before, after = shrink_video(path, video_cfg)
    else:
        return None
    return t("mediatools", "optimised", path=path.name, before=before, after=after)


__all__ = ["ToolError", "image_to_webp", "is_image", "is_video", "settings", "shrink", "shrink_image", "shrink_video", "video_to_mp4"]
