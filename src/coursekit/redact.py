"""Personal data hidden on the pixels of a capture or a recording (`coursekit capture redact`).

The text on the image is read (OCR: Apple Vision on macOS, or rapidocr, both installed with the `capture` extra, or the
`tesseract` program of the machine),
the stretches with personal data are found with `pii.find` (on the pixels every text with the shape counts, because the
reading can be wrong), and each one is covered (`capture.yaml › redact › pixels`: pixelate, blur or solid) with some margin.
Faces are found with the face detector OpenCV ships. A video is read `video_fps` times a second; what one reading finds stays
covered until the reading after it (both are covered in between), so that a scroll between two readings never shows it.

What it returns is a report without the real values: the kinds and how many, the boxes, and what could not be checked.
"""

from __future__ import annotations

import csv
import io
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from coursekit import pii
from coursekit.i18n import t

TESSERACT_LANGUAGES = {"es": "spa+eng", "en": "eng"}
STYLES = ("pixelate", "blur", "solid")


class RedactError(Exception):
    pass


def _last_line(text: str | None) -> str:
    lines = (text or "").strip().splitlines()
    return lines[-1] if lines else "?"


@dataclass(frozen=True)
class Box:
    x: int
    y: int
    w: int
    h: int
    kind: str

    def grown(self, margin: int, width: int, height: int) -> Box:
        x, y = max(0, self.x - margin), max(0, self.y - margin)
        return Box(x, y, min(width, self.x + self.w + margin) - x, min(height, self.y + self.h + margin) - y, self.kind)


@dataclass
class Line:
    """A line of text read on the image, with the box of each word and where the word is in the text."""

    text: str
    words: list[tuple[int, int, tuple[int, int, int, int]]]  # (start, end, (x, y, w, h))


@dataclass
class Report:
    engine: str
    findings: Counter = field(default_factory=Counter)
    warnings: list[str] = field(default_factory=list)
    samples: list[dict] = field(default_factory=list)  # {"t": seconds, "boxes": [[x, y, w, h, kind], ...]}
    frames: int = 0

    def as_dict(self) -> dict:
        return {"engine": self.engine, "findings": dict(self.findings), "warnings": self.warnings, "frames": self.frames,
                "samples": self.samples}


Reader = Callable[[Image.Image], list[Line]]


# ── reading the text ─────────────────────────────────────────────────────────────────────────

def _line_from_words(words: list[tuple[str, tuple[int, int, int, int]]]) -> Line:
    text, spans = "", []
    for word, box in words:
        if text:
            text += " "
        spans.append((len(text), len(text) + len(word), box))
        text += word
    return Line(text, spans)


def _rapidocr() -> Reader:
    try:
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        raise RedactError(t("redact", "ocr_missing")) from None
    engine = RapidOCR()

    def read(image: Image.Image) -> list[Line]:
        result, _ = engine(np.array(image.convert("RGB")))
        lines = []
        for points, text, _score in result or []:
            xs, ys = [p[0] for p in points], [p[1] for p in points]
            x, y, w, h = int(min(xs)), int(min(ys)), int(max(xs) - min(xs)), int(max(ys) - min(ys))
            # one box per line: each word gets the part of the width that its characters take
            words, cursor, step = [], 0, w / max(1, len(text))
            for word in str(text).split(" "):
                if word:
                    words.append((word, (x + round(cursor * step), y, max(1, round(len(word) * step)), h)))
                cursor += len(word) + 1
            lines.append(_line_from_words(words))
        return lines

    return read


def _tesseract(language: str) -> Reader:
    program = shutil.which("tesseract")
    if not program:
        raise RedactError(t("redact", "ocr_missing"))

    def run(path: Path, languages: str) -> subprocess.CompletedProcess:
        return subprocess.run([program, str(path), "stdout", "-l", languages, "tsv"], capture_output=True, text=True,
                              encoding="utf-8", check=False)

    def read(image: Image.Image) -> list[Line]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "frame.png"
            image.convert("RGB").save(path)
            done = run(path, TESSERACT_LANGUAGES.get(language, "eng"))
            if done.returncode != 0:
                done = run(path, "eng")  # the language data of the course may not be installed
            if done.returncode != 0:
                raise RedactError(t("redact", "ocr_failed", reason=_last_line(done.stderr)))
        grouped: dict[tuple, list] = {}
        for row in csv.DictReader(io.StringIO(done.stdout), delimiter="\t", quoting=csv.QUOTE_NONE):
            text = (row.get("text") or "").strip()
            if row.get("level") == "5" and text:
                key = (row["page_num"], row["block_num"], row["par_num"], row["line_num"])
                box = (int(row["left"]), int(row["top"]), int(row["width"]), int(row["height"]))
                grouped.setdefault(key, []).append((text, box))
        return [_line_from_words(words) for words in grouped.values()]

    return read


VISION_LANGUAGES = {"es": ["es-ES", "en-US"], "en": ["en-US", "es-ES"]}


def _vision(language: str) -> Reader:
    """Apple Vision (macOS): accurate with the accents of Spanish, quick, on the machine, and with the exact box of each word."""
    try:
        import Vision
        from Foundation import NSData
    except ImportError:
        raise RedactError(t("redact", "ocr_missing")) from None

    def read(image: Image.Image) -> list[Line]:
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, "PNG")
        raw = buffer.getvalue()
        handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(NSData.dataWithBytes_length_(raw, len(raw)), None)
        request = Vision.VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        request.setRecognitionLanguages_(VISION_LANGUAGES.get(language, ["en-US"]))
        request.setUsesLanguageCorrection_(False)  # names and codes must be read as they are, not corrected
        ok, _ = handler.performRequests_error_([request], None)
        if not ok:
            raise RedactError(t("redact", "ocr_failed", reason="Vision"))
        width, height = image.size
        lines = []
        for observation in request.results() or []:
            candidate = observation.topCandidates_(1)[0]
            text = str(candidate.string())
            words, cursor = [], 0
            for word in text.split(" "):
                if word:
                    box, _ = candidate.boundingBoxForRange_error_((cursor, len(word)), None)
                    if box is not None:
                        b = box.boundingBox()  # normalised, from the bottom left
                        x, w = b.origin.x * width, b.size.width * width
                        y, h = (1 - b.origin.y - b.size.height) * height, b.size.height * height
                        words.append((word, (round(x), round(y), max(1, round(w)), max(1, round(h)))))
                cursor += len(word) + 1
            if words:
                lines.append(_line_from_words(words))
        return lines

    return read


def reader(choice: str, language: str) -> tuple[str, Reader]:
    """The OCR to use: `vision` (Apple Vision, macOS), `rapidocr`, `tesseract`, or `auto` (Vision on macOS when it is
    installed, else rapidocr, else tesseract)."""
    if choice == "vision" or (choice == "auto" and sys.platform == "darwin"):
        try:
            return "vision", _vision(language)
        except RedactError:
            if choice == "vision":
                raise
    if choice in ("auto", "rapidocr"):
        try:
            return "rapidocr", _rapidocr()
        except RedactError:
            if choice == "rapidocr":
                raise
    return "tesseract", _tesseract(language)


# ── finding what to cover ────────────────────────────────────────────────────────────────────

def text_boxes(lines: list[Line], rules: dict, who: pii.People, terms: list[str]) -> list[Box]:
    boxes = []
    for line in lines:
        for finding in pii.find(line.text, rules, who, terms, strict=False):
            parts = [box for start, end, box in line.words if start < finding.end and end > finding.start]
            if parts:
                x0, y0 = min(b[0] for b in parts), min(b[1] for b in parts)
                x1, y1 = max(b[0] + b[2] for b in parts), max(b[1] + b[3] for b in parts)
                boxes.append(Box(x0, y0, x1 - x0, y1 - y0, finding.kind))
    return boxes


def _face_detector():
    try:
        import cv2
    except ImportError:
        return None
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    return None if cascade.empty() else (cv2, cascade)


def face_boxes(image: Image.Image, detector) -> list[Box]:
    import numpy as np

    cv2, cascade = detector
    gray = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    found = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(16, 16))
    return [Box(int(x), int(y), int(w), int(h), "face") for x, y, w, h in found]


# ── covering ─────────────────────────────────────────────────────────────────────────────────

def cover(image: Image.Image, boxes: list[Box], style: str, margin: int) -> Image.Image:
    out = image.convert("RGB").copy()
    for box in (b.grown(margin, out.width, out.height) for b in boxes):
        if box.w <= 0 or box.h <= 0:
            continue
        area = (box.x, box.y, box.x + box.w, box.y + box.h)
        part = out.crop(area)
        if style == "solid":
            covered = Image.new("RGB", part.size, (40, 40, 40))
        elif style == "blur":
            covered = part.filter(ImageFilter.GaussianBlur(max(6, box.h // 2)))
        else:
            block = max(8, box.h // 3)
            small = part.resize((max(1, part.width // block), max(1, part.height // block)), Image.Resampling.BILINEAR)
            covered = small.resize(part.size, Image.Resampling.NEAREST)
        out.paste(covered, area[:2])
    return out


def outline(image: Image.Image, boxes: list[Box], margin: int) -> Image.Image:
    """The covered image with a frame around each covered box, for the person who reviews it."""
    out = image.convert("RGB").copy()
    draw = ImageDraw.Draw(out)
    for box in (b.grown(margin, out.width, out.height) for b in boxes):
        draw.rectangle((box.x, box.y, box.x + box.w, box.y + box.h), outline=(230, 30, 120), width=3)
    return out


class Redactor:
    """Finds and covers the personal data of the frames of one capture."""

    def __init__(self, rules: dict, who: pii.People, terms: list[str], read: Reader, engine: str):
        self.rules, self.who, self.terms, self.read = rules, who, list(terms), read
        style = str(rules.get("pixels") or "pixelate")
        self.style = style if style in STYLES else "pixelate"
        self.margin = int(rules.get("padding") or 0)
        self.report = Report(engine)
        self.faces = _face_detector() if rules.get("faces") else None
        if rules.get("faces") and self.faces is None:
            self.report.warnings.append(t("redact", "faces_unchecked"))

    def boxes(self, image: Image.Image) -> list[Box]:
        found = text_boxes(self.read(image), self.rules, self.who, self.terms)
        if self.faces is not None:
            found += face_boxes(image, self.faces)
        return found

    def note(self, seconds: float, boxes: list[Box]) -> None:
        self.report.findings.update(b.kind for b in boxes)
        self.report.samples.append({"t": round(seconds, 2), "boxes": [[b.x, b.y, b.w, b.h, b.kind] for b in boxes]})


def redact_image(source: Path, target: Path, redactor: Redactor, review: Path | None = None) -> Report:
    with Image.open(source) as image:
        image.load()
        boxes = redactor.boxes(image)
        redactor.note(0, boxes)
        redactor.report.frames = 1
        covered = cover(image, boxes, redactor.style, redactor.margin)
    target.parent.mkdir(parents=True, exist_ok=True)
    covered.save(target)
    if review is not None:
        review.parent.mkdir(parents=True, exist_ok=True)
        outline(covered, boxes, redactor.margin).save(review)
    return redactor.report


def redact_video(source: Path, target: Path, redactor: Redactor, fps: float, review_dir: Path | None = None) -> Report:
    """Reads the video `fps` times a second, covers what each reading finds until the next one, and encodes it with the audio."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        raise RedactError(t("redact", "video_needs_extra")) from None
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RedactError(t("redact", "ffmpeg_missing"))
    probe = cv2.VideoCapture(str(source))
    if not probe.isOpened():
        raise RedactError(t("redact", "video_unreadable", name=source.name))
    rate = probe.get(cv2.CAP_PROP_FPS) or 25.0
    probe.release()
    every = max(1, round(rate / max(0.1, fps)))

    def frames():
        video = cv2.VideoCapture(str(source))
        try:
            while True:
                ok, frame = video.read()
                if not ok:
                    return
                yield Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        finally:
            video.release()

    # first pass: the readings
    readings: dict[int, list[Box]] = {}
    count = 0
    for index, image in enumerate(frames()):
        count = index + 1
        if index % every == 0:
            readings[index] = redactor.boxes(image)
            redactor.note(index / rate, readings[index])
            if review_dir is not None:
                review_dir.mkdir(parents=True, exist_ok=True)
                outline(cover(image, readings[index], redactor.style, redactor.margin), readings[index], redactor.margin) \
                    .save(review_dir / f"t{index / rate:07.2f}.png")
    redactor.report.frames = count
    if not count:
        raise RedactError(t("redact", "video_unreadable", name=source.name))
    # second pass: every frame covered with the reading before it and the one after it
    keys = sorted(readings)
    with tempfile.TemporaryDirectory() as tmp:
        silent = Path(tmp) / "covered.avi"
        writer = None
        for index, image in enumerate(frames()):
            before = max(k for k in keys if k <= index)
            after = next((k for k in keys if k > index), before)
            covered = cover(image, readings[before] + readings[after], redactor.style, redactor.margin)
            frame = cv2.cvtColor(np.array(covered), cv2.COLOR_RGB2BGR)
            if writer is None:
                writer = cv2.VideoWriter(str(silent), cv2.VideoWriter_fourcc(*"MJPG"), rate, (frame.shape[1], frame.shape[0]))
            writer.write(frame)
        if writer is not None:
            writer.release()
        target.parent.mkdir(parents=True, exist_ok=True)
        done = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(source), "-map", "0:v", "-map",
                               "1:a?", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", str(target)],
                              capture_output=True, text=True, check=False)
        if done.returncode != 0:
            raise RedactError(t("redact", "encode_failed", reason=_last_line(done.stderr)))
    return redactor.report
