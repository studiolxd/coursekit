"""The batch of the Gemini voice (`coursekit tts-batch`): narrations queued by `video voice`, `media narrate` and `tts` with
`--batch`, sent in one job, collected hours later. The API is stood in for: these tests never reach Google."""

import base64
import json

import pytest
import yaml

from coursekit import handoff, mediatools, ttsbatch, video
from coursekit.cli import main
from coursekit.course import load as load_course
from coursekit.project import find_project
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture
from tests.test_media import prepare_asset
from tests.test_video import montage


@pytest.fixture(autouse=True)
def no_script_gate(monkeypatch):
    from coursekit import mediascript

    monkeypatch.setattr(mediascript, "required", lambda _course: False)


class FakeApi:
    """The Gemini API of a batch: it keeps what was uploaded and answers each request with its own audio (or an error)."""

    def __init__(self, fail=()):
        self.lines, self.state, self.fail, self.created = [], "BATCH_STATE_PENDING", set(fail), 0

    def upload(self, data, name):
        self.lines = [json.loads(line) for line in data.decode("utf-8").splitlines()]
        return "files/in"

    def create(self, model, file_name, name):
        self.created += 1
        self.model = model
        return {"name": "batches/1", "metadata": {"state": self.state, "name": "batches/1"}}

    def get(self, job):
        answer = {"name": job, "metadata": {"state": self.state, "batchStats": {"requestCount": str(len(self.lines))}}}
        if self.state == "BATCH_STATE_SUCCEEDED":
            answer.update(done=True, response={"responsesFile": "files/out"})
        return answer

    def download(self, file_name):
        rows = []
        for line in self.lines:
            if line["key"] in self.fail:
                rows.append({"key": line["key"], "error": {"code": 500, "message": "internal"}})
                continue
            audio = base64.b64encode(b"\x01\x00" * 4).decode()
            part = {"inlineData": {"mimeType": "audio/L16;codec=pcm;rate=24000", "data": audio}}
            rows.append({"key": line["key"], "response": {"candidates": [{"content": {"parts": [part]}}]}})
        return ("\n".join(json.dumps(r) for r in rows) + "\n").encode()


@pytest.fixture
def gemini(course, capsys, monkeypatch):  # noqa: F811
    """A course with the Gemini voice, its theme and a montage; encoding and the alignment of words are stood in for."""
    monkeypatch.setenv("GEMINI_API_KEY", "gm")
    prepare_asset(course, capsys)
    assert main(["voice", "set", "PWD", "gemini"]) == 0
    encoded = []

    def run(cmd, **kw):
        encoded.append(kw.get("input"))
        open(cmd[-1], "wb").write(b"ID3")

    def subtitles(audio, text_path, out, model_name="base", language="es"):
        words = text_path.read_text(encoding="utf-8").split()
        mediatools.write_words([{"w": w, "start": i * 0.5, "end": i * 0.5 + 0.4} for i, w in enumerate(words)], mediatools.words_path(out))

    monkeypatch.setattr(mediatools, "run", run)
    monkeypatch.setattr(mediatools, "subtitles", subtitles)
    monkeypatch.setattr(video.mediacheck, "duration", lambda path: 4.0)
    monkeypatch.setattr(mediatools, "tts", lambda *a, **k: pytest.fail("a batch never voices at once"))
    capsys.readouterr()
    return encoded


def queue(course_dir):
    path = course_dir / "media" / "tts-batch.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None


def test_a_montage_is_voiced_in_batch_and_goes_on_when_it_is_collected(gemini, course):  # noqa: F811
    data = montage(course)
    assert video.voice(data, "U1-S2-M1", lambda m: None, batch=True) == 2
    assert video.voice(data, "U1-S2-M1", lambda m: None, batch=True) == 0  # the same text: already queued
    items = queue(course)["items"]
    assert [i["id"] for i in items] == ["U1-S2-M1#opening", "U1-S2-M1#length"] and {i["state"] for i in items} == {"queued"}
    assert items[0]["voice"] == "Aoede" and items[0]["model"] == "gemini-3.8-flash-tts" and items[0]["asset"] == "U1-S2-M1"
    assert ttsbatch.waiting(data) == {"U1-S2-M1"}
    assert handoff._pending_media(data) == []  # its voice is on its way: nothing for the media agent

    api = FakeApi()
    sent = ttsbatch.send(data, api)
    assert sent == {"job": "batches/1", "items": 2, "requests": 2, "left": 0} and api.model == "gemini-3.8-flash-tts"
    assert [line["key"] for line in api.lines] == ["U1-S2-M1#opening#0", "U1-S2-M1#length#0"]
    request = api.lines[0]["request"]
    assert "serviceTier" not in request and request["generationConfig"]["speechConfig"]
    with pytest.raises(ttsbatch.BatchError, match="not idempotent"):
        ttsbatch.send(data, api)
    with pytest.raises(ttsbatch.BatchError, match="already sent"):  # its text cannot change while it is in a job
        ttsbatch.add(data, "video", "U1-S2-M1#opening", "Otro texto.", course / "media" / "x.mp3")

    api.state = "BATCH_STATE_RUNNING"
    assert ttsbatch.status(data, api)["state"] == "running"
    assert ttsbatch.collect(data, api, say=lambda m: None) == {"state": "running", "done": 0, "failed": 0, "waiting": 2}
    with pytest.raises(video.VideoError, match="has no voice yet"):
        video.resolve(data, "U1-S2-M1")

    api.state = "BATCH_STATE_SUCCEEDED"
    assert ttsbatch.collect(data, api, say=lambda m: None)["done"] == 2
    assert queue(course) is None  # nothing left: the queue goes away
    assert len(gemini) == 2 and gemini[0] == b"\x01\x00" * 4
    resolved = video.resolve(data, "U1-S2-M1")
    assert [s["frames"] for s in resolved["scenes"]] == [135, 135, 90]
    assert video.voice(data, "U1-S2-M1", lambda m: None, batch=True) == 0  # collected is as good as voiced


def test_a_scene_that_fails_goes_back_to_the_queue_and_the_rest_are_written(gemini, course, capsys):  # noqa: F811
    ry_path = course / "media" / "manifest.yaml"
    data = yaml.safe_load(ry_path.read_text(encoding="utf-8"))
    data["assets"] += [{"id": f"VO-{n}", "type": "audio", "kind": "voice", "narration": f"Escena {n}.", "status": "pending",
                        "character": None} for n in (1, 2)]
    ry_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    assert main(["media", "narrate", "PWD", "--batch"]) == 0
    assert "2 scene narration(s) in the batch queue" in capsys.readouterr().out
    c = load_course(find_project(), "PWD")
    assert {"VO-1", "VO-2"} <= ttsbatch.waiting(c) and not {"VO-1", "VO-2"} & {a["id"] for a in handoff._pending_media(c)}

    api = FakeApi(fail={"VO-2#0"})
    ttsbatch.send(c, api)
    api.state = "BATCH_STATE_SUCCEEDED"
    assert ttsbatch.collect(c, api, say=lambda m: None) == {"state": "succeeded", "done": 1, "failed": 1, "waiting": 0}
    assets = {a["id"]: a for a in yaml.safe_load(ry_path.read_text(encoding="utf-8"))["assets"]}
    assert assets["VO-1"]["status"] == "produced" and assets["VO-1"]["file"] == "media/files/VO-1.mp3"
    assert assets["VO-2"]["status"] == "pending"
    left = queue(course)
    assert left["job"] is None and [(i["id"], i["state"], i["error"]) for i in left["items"]] == [("VO-2", "queued", "internal")]
    assert main(["tts-batch", "list", "PWD"]) == 0
    assert "VO-2 (narrate, 1 piece(s)): queued — internal" in capsys.readouterr().out


def test_an_expired_job_leaves_everything_in_the_queue(gemini, course):  # noqa: F811
    c = montage(course)
    video.voice(c, "U1-S2-M1", lambda m: None, batch=True)
    api = FakeApi()
    ttsbatch.send(c, api)
    api.state = "BATCH_STATE_EXPIRED"
    assert ttsbatch.collect(c, api, say=lambda m: None)["failed"] == 2
    assert {i["state"] for i in queue(course)["items"]} == {"queued"}
    assert ttsbatch.send(c, api)["items"] == 2 and api.created == 2  # sent again, in a new job


def test_tts_puts_a_script_in_the_queue_of_a_course_and_only_with_the_gemini_voice(gemini, course, capsys, tmp_path, monkeypatch):  # noqa: F811
    script = tmp_path / "s.txt"
    script.write_text("Hola. Adiós.", encoding="utf-8")
    out = course / "media" / "files" / "U1-S2-M1.mp3"
    assert main(["tts", "--in", str(script), "--out", str(out), "--batch"]) == 2
    assert "--batch needs --course" in capsys.readouterr().err
    assert main(["tts", "--course", "PWD", "--in", str(script), "--out", str(out), "--batch"]) == 0
    assert "in the batch queue of PWD" in capsys.readouterr().out
    item = queue(course)["items"][0]
    assert item["kind"] == "tts" and item["asset"] == "U1-S2-M1" and item["out"].endswith("media/files/U1-S2-M1.mp3")
    assert main(["tts", "--course", "PWD", "--in", str(script), "--out", str(out), "--batch"]) == 0
    assert "already in the queue" in capsys.readouterr().out
    monkeypatch.setenv("PIPER_VOICE", "es_ES-x")
    assert main(["voice", "set", "PWD", "piper", "--voice", "es_ES-x"]) == 0
    capsys.readouterr()
    assert main(["tts", "--course", "PWD", "--in", str(script), "--out", str(course / "media" / "b.mp3"), "--batch"]) == 1
    assert "only with the Gemini voice" in capsys.readouterr().err


def test_the_handoff_collects_a_finished_job_and_stops_while_one_waits(gemini, course, monkeypatch):  # noqa: F811
    c = montage(course)
    video.voice(c, "U1-S2-M1", lambda m: None, batch=True)
    api = FakeApi()
    monkeypatch.setattr(ttsbatch, "Api", lambda: api)

    class Ctx:
        code, log, mirror = "PWD", staticmethod(lambda m: None), staticmethod(lambda: None)
        project = find_project()

        def course(self):
            return load_course(find_project(), "PWD")

    with pytest.raises(handoff.HandoffError, match="in the Gemini batch"):
        handoff._tts_batch(Ctx(), c, send=True)  # what the agent queued is sent, and the handoff waits for it
    assert queue(course)["job"] == "batches/1"
    with pytest.raises(handoff.HandoffError, match="in the Gemini batch"):
        handoff._tts_batch(Ctx(), c, send=False)
    api.state = "BATCH_STATE_SUCCEEDED"
    handoff._tts_batch(Ctx(), c, send=True)
    assert queue(course) is None and video.resolve(c, "U1-S2-M1")["frames"] == 360
