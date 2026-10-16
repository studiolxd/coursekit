"""The batch of the Gemini voice (`coursekit tts-batch`): the narrations of a course sent together, at half the price, collected
hours later.

A course keeps its queue in `media/tts-batch.yaml` (versioned: what was sent, with which model, voice and style, and how it
went). Three things put narrations in it, with `--batch`: `coursekit tts --course CODE` (a script), `coursekit video voice`
(the scenes of a montage) and `coursekit media narrate` (the scenes of the simulations). Then:

- `send` uploads the requests (a JSONL file to the Files API: a long script is several requests) and creates one job. Creating
  a job is not idempotent (sending again would be paid twice), so it refuses while one is under way;
- `status` asks how it goes (Google aims at 24 hours; at 48 hours without finishing the job expires with no results);
- `collect` downloads the results, joins the pieces of each narration, writes its MP3 and finishes what it was for: the asset of
  a simulation becomes produced; a scene of a montage gets the timings of its words and its length, so `coursekit video render`
  goes on. What failed goes back to the queue, to be sent again.

The handoff collects by itself when the job finished, and stops (to carry on later) while it has not.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import urllib.request
from pathlib import Path

from coursekit import course as coursemod
from coursekit import mediatools
from coursekit.i18n import t

UPLOAD = "https://generativelanguage.googleapis.com/upload/v1beta/files"
DOWNLOAD = "https://generativelanguage.googleapis.com/download/v1beta"
FINISHED = ("succeeded", "failed", "cancelled", "expired")


class BatchError(Exception):
    pass


# ── the queue ────────────────────────────────────────────────────────────────────────────────

def queue_path(course: dict) -> Path:
    return course["_dir"] / "media" / "tts-batch.yaml"


def load(course: dict) -> dict:
    import yaml

    path = queue_path(course)
    data = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}
    data.setdefault("job", None)
    data.setdefault("state", None)
    data.setdefault("items", [])
    return data


def save(course: dict, data: dict) -> None:
    import yaml

    path = queue_path(course)
    if not data["items"] and not data.get("job"):
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    header = t("ttsbatch", "file_header") + "\n"
    path.write_text(header + yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8", newline="\n")


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _fingerprint(*parts: str) -> str:
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()[:16]


def add(course: dict, kind: str, ident: str, text: str, out: Path, *, asset: str | None = None, scene: str | None = None,
        character: str | None = None, extra: dict | None = None) -> bool:
    """Puts a narration in the queue (True), or leaves it when the same one is already there (False). Only the Gemini voice
    has a batch."""
    from coursekit import voices

    try:
        provider, voice, _ = voices.resolve_character(course, character) if character else voices.resolve(course)
    except voices.VoiceError as exc:
        raise BatchError(str(exc)) from None
    if provider != "gemini":
        raise BatchError(t("ttsbatch", "only_gemini", provider=provider, code=course["code"]))
    settings = mediatools.gemini_settings(course)
    language = coursemod.language(course)
    style = str(settings.get("style") or "").strip()
    text = " ".join(str(text).split())
    fingerprint = _fingerprint(text, str(voice), language, style, str(settings["model"]))
    data = load(course)
    if asset is None and kind == "tts":  # a script written to media/files/<id>.mp3 is the narration of that asset
        from coursekit import media as mediamod

        known = {str(a["id"]) for a in mediamod.load_manifest(course["_dir"])[2]["assets"]}
        asset = out.stem if out.stem in known else None
    same = next((i for i in data["items"] if i["id"] == ident), None)
    if same and same["fingerprint"] == fingerprint:
        return False
    if same and same.get("state") == "sent":
        raise BatchError(t("ttsbatch", "already_sent", id=ident))
    data["items"] = [i for i in data["items"] if i["id"] != ident]
    root = course["_project"].root
    data["items"].append({"id": ident, "kind": kind, "asset": asset, "scene": scene, "character": character, "voice": voice,
                          "language": language, "style": style, "model": str(settings["model"]), "text": text,
                          "pieces": len(mediatools.sentence_chunks(text, int(settings["chunk_bytes"]))),
                          "out": out.resolve().relative_to(root.resolve()).as_posix(), "fingerprint": fingerprint,
                          "state": "queued", "queued_at": _now(), **(extra or {})})
    save(course, data)
    return True


def waiting(course: dict) -> set[str]:
    """The assets with a narration in the queue (sent or not): neither pending for an agent nor produced yet."""
    return {i["asset"] for i in load(course)["items"] if i.get("asset")}


# ── the API ──────────────────────────────────────────────────────────────────────────────────

class Api:
    """The calls to the Gemini API the batch needs (one object, so the tests can stand in for it)."""

    def __init__(self, key: str | None = None):
        self.key = (key or os.environ.get("GEMINI_API_KEY", "")).strip()
        if not self.key:
            raise BatchError(t("ttsbatch", "no_key"))

    def _call(self, url: str, body: bytes | None = None, headers: dict | None = None, method: str = "POST") -> tuple[dict, bytes]:
        req = urllib.request.Request(url, data=body, headers={"x-goog-api-key": self.key, **(headers or {})}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                return dict(resp.headers), resp.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300].replace("\n", " ")
            raise BatchError(t("ttsbatch", "api_failed", status=exc.code, detail=detail)) from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise BatchError(t("mediatools", "network_failed", host=req.host, reason=getattr(exc, "reason", exc))) from None

    def upload(self, data: bytes, name: str) -> str:
        """Uploads a JSONL file to the Files API; its name (`files/…`)."""
        headers, _ = self._call(UPLOAD, json.dumps({"file": {"display_name": name}}).encode(), {
            "X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start", "Content-Type": "application/json",
            "X-Goog-Upload-Header-Content-Length": str(len(data)), "X-Goog-Upload-Header-Content-Type": "application/jsonl"})
        url = next((v for k, v in headers.items() if k.lower() == "x-goog-upload-url"), None)
        if not url:
            raise BatchError(t("ttsbatch", "upload_failed"))
        _, body = self._call(url, data, {"X-Goog-Upload-Command": "upload, finalize", "X-Goog-Upload-Offset": "0"})
        return json.loads(body)["file"]["name"]

    def create(self, model: str, file_name: str, name: str) -> dict:
        _, body = self._call(f"{mediatools.GEMINI_API}/models/{model}:batchGenerateContent",
                             json.dumps({"batch": {"display_name": name, "input_config": {"file_name": file_name}}}).encode(),
                             {"Content-Type": "application/json"})
        return json.loads(body)

    def get(self, job: str) -> dict:
        _, body = self._call(f"{mediatools.GEMINI_API}/{job}", method="GET")
        return json.loads(body)

    def download(self, file_name: str) -> bytes:
        _, body = self._call(f"{DOWNLOAD}/{file_name}:download?alt=media", method="GET")
        return body


def _batch(answer: dict) -> dict:
    """The batch of an answer of the API: the answer itself, or its `metadata` (it comes as an operation)."""
    return answer.get("metadata") if isinstance(answer.get("metadata"), dict) and "state" in answer["metadata"] else answer


def _state(answer: dict) -> str:
    return str(_batch(answer).get("state") or "BATCH_STATE_PENDING").removeprefix("BATCH_STATE_").lower()


def _responses_file(answer: dict) -> str | None:
    for source in (_batch(answer), answer.get("response") or {}, answer):
        output = source.get("output") or {}
        name = output.get("responsesFile") or output.get("responses_file") or source.get("responsesFile")
        if name:
            return str(name)
    return None


# ── send, status, collect ────────────────────────────────────────────────────────────────────

def send(course: dict, api: Api | None = None) -> dict:
    """Uploads what is queued and creates the job (one model per job: what has another one waits for the next)."""
    data = load(course)
    if data.get("job") and data.get("state") not in FINISHED + ("collected",):
        raise BatchError(t("ttsbatch", "job_running", job=data["job"], code=course["code"]))
    queued = [i for i in data["items"] if i["state"] == "queued"]
    if not queued:
        raise BatchError(t("ttsbatch", "nothing_queued", code=course["code"]))
    model = queued[0]["model"]
    chosen = [i for i in queued if i["model"] == model]
    limit = int(mediatools.gemini_settings(course)["chunk_bytes"])
    lines = []
    for item in chosen:
        pieces = mediatools.sentence_chunks(item["text"], limit)
        for n, piece in enumerate(pieces):  # no serviceTier: the batch has its own price
            request = mediatools.gemini_request(piece, item["voice"], item["language"], item["style"])
            lines.append(json.dumps({"key": f"{item['id']}#{n}", "request": request}, ensure_ascii=False))
        item["pieces"] = len(pieces)
    api = api or Api()
    name = f"coursekit-{course['code']}-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    file_name = api.upload(("\n".join(lines) + "\n").encode("utf-8"), name)
    answer = api.create(model, file_name, name)
    for item in chosen:
        item["state"] = "sent"
    data.update(job=str(answer.get("name") or _batch(answer).get("name")), state=_state(answer), model=model, sent_at=_now(),
                requests=len(lines))
    save(course, data)
    return {"job": data["job"], "items": len(chosen), "requests": len(lines), "left": len(queued) - len(chosen)}


def status(course: dict, api: Api | None = None) -> dict:
    data = load(course)
    if not data.get("job"):
        return {"state": None, "queued": sum(1 for i in data["items"] if i["state"] == "queued")}
    answer = (api or Api()).get(data["job"])
    data["state"] = _state(answer)
    stats = _batch(answer).get("batchStats") or {}
    save(course, data)
    return {"state": data["state"], "job": data["job"], "stats": {k: int(v) for k, v in stats.items() if str(v).isdigit()}}


def _finish(course: dict, item: dict, pcm: bytes, rate: int, say) -> None:
    """Writes the narration and finishes what it was for."""
    root = course["_project"].root
    out = root / item["out"]
    out.parent.mkdir(parents=True, exist_ok=True)
    mediatools.encode_pcm(pcm, out, rate)
    if item["kind"] == "narrate":
        from coursekit import media as mediamod

        ry, path, manifest = mediamod.load_manifest(course["_dir"])
        asset = next((a for a in manifest["assets"] if a["id"] == item["asset"]), None)
        if asset is not None:
            asset.update(status="produced", file=out.relative_to(course["_dir"]).as_posix(), transcript=item["text"],
                         recipe="coursekit media narrate", note=None)
            with path.open("w", encoding="utf-8", newline="\n") as fh:
                ry.dump(manifest, fh)
    elif item["kind"] == "video":
        from coursekit import video

        video.voice_collected(course, item["asset"], item["scene"], item["voice_key"], out, item["text"], say)
    say(t("ttsbatch", "written", path=item["out"]))


def collect(course: dict, api: Api | None = None, say=print) -> dict:
    """Downloads the results of a finished job, writes each narration and leaves in the queue what failed."""
    data = load(course)
    if not data.get("job"):
        raise BatchError(t("ttsbatch", "no_job", code=course["code"]))
    api = api or Api()
    answer = api.get(data["job"])
    state = _state(answer)
    data["state"] = state
    sent = [i for i in data["items"] if i["state"] == "sent"]
    if state not in FINISHED:
        save(course, data)
        return {"state": state, "done": 0, "failed": 0, "waiting": len(sent)}
    results: dict[str, dict] = {}
    if state == "succeeded":
        name = _responses_file(answer)
        if not name:
            raise BatchError(t("ttsbatch", "no_results", job=data["job"]))
        for line in api.download(name).decode("utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                results[str(row.get("key"))] = row
    done = failed = 0
    for item in sent:
        pieces = [results.get(f"{item['id']}#{n}") for n in range(int(item.get("pieces") or 1))]
        try:
            if not all(p and p.get("response") for p in pieces):
                error = next((p.get("error") for p in pieces if p and p.get("error")), None) or state
                raise BatchError(str(error.get("message") if isinstance(error, dict) else error))
            audio = [mediatools.gemini_audio(p["response"]) for p in pieces]
            _finish(course, item, b"".join(a[0] for a in audio), audio[0][1], say)
            item["state"] = "done"
            done += 1
        except (BatchError, mediatools.ToolError) as exc:
            item.update(state="queued", error=str(exc)[:300])  # back to the queue, to be sent again
            failed += 1
    data["items"] = [i for i in data["items"] if i["state"] != "done"]
    data.update(job=None, state=None, collected_at=_now())
    save(course, data)
    return {"state": state, "done": done, "failed": failed, "waiting": 0}


def listing(course: dict) -> list[str]:
    data = load(course)
    lines = [t("ttsbatch", "job_line", job=data["job"], state=data.get("state") or "?")] if data.get("job") else []
    for item in data["items"]:
        lines.append(t("ttsbatch", "item_line", id=item["id"], kind=item["kind"], state=item["state"], pieces=item.get("pieces", 1),
                       error=f" — {item['error']}" if item.get("error") else ""))
    return lines or [t("ttsbatch", "empty", code=course["code"])]
