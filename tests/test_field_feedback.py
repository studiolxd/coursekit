"""Robustness and checks added after producing a whole course: the lock of the manifest, the summary of a headless run, the
documents linked in the brief, the notes of the media style guide and the new warnings of `verify`."""

import json
import subprocess
import sys
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler

import pytest

from coursekit import brief, launch, mediastyle, simulation, util, verify
from coursekit import course as coursemod

COUNTER = """
import sys
from pathlib import Path
from coursekit import util
path = Path(sys.argv[1])
for _ in range(25):
    with util.file_lock(path.with_name(".lock")):
        ry = util.roundtrip_yaml()
        data = ry.load(path.read_text(encoding="utf-8"))
        data["n"] += 1
        util.save_yaml_atomic(ry, data, path)
"""


def test_lock_keeps_every_write_of_processes_in_parallel(tmp_path):
    counter = tmp_path / "counter.yaml"
    counter.write_text("n: 0\n", encoding="utf-8")
    script = tmp_path / "count.py"
    script.write_text(COUNTER, encoding="utf-8")
    workers = [subprocess.Popen([sys.executable, str(script), str(counter)]) for _ in range(4)]
    assert all(w.wait(timeout=120) == 0 for w in workers)
    assert counter.read_text(encoding="utf-8").strip() == "n: 100"


def test_lock_is_reentrant_and_times_out(tmp_path):
    lock = tmp_path / ".lock"
    with util.file_lock(lock), util.file_lock(lock):
        pass
    holder = subprocess.Popen([sys.executable, "-c", "import sys, time\nfrom pathlib import Path\nfrom coursekit import util\n"
                               "with util.file_lock(Path(sys.argv[1])):\n    print('held', flush=True)\n    time.sleep(30)",
                               str(lock)], stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "held"
        with pytest.raises(util.LockTimeout), util.file_lock(lock, timeout=0.3):
            pass
    finally:
        holder.kill()
        holder.wait()


def test_error_decisions_need_a_consequence():
    scenes = {
        "start": {"text": "x", "choices": [
            {"text": "Report it", "goto": "next"},
            {"text": "Ignore it", "goto": "next", "error": "ignore"},
            {"text": "Reply", "goto": "happy", "error": "reply"},
            {"text": "Forward it", "goto": "next", "error": "forward", "set": {"forwarded": 1}},
        ]},
        "next": {"text": "y", "ending": "mixed", "debriefing": "d"},
        "happy": {"text": "z", "ending": "good", "debriefing": "d"},
    }
    warnings = simulation.consequence_warnings(scenes)
    assert len(warnings) == 2
    assert '"Ignore it"' in warnings[0] and "no consequence" in warnings[0]
    assert '"Reply"' in warnings[1] and "good ending" in warnings[1]


def test_activity_written_with_a_directive_of_its_type():
    unit = {"activities": {"learning": [
        {"title": "Spot the error", "type": "analisis_hotspots", "section": 2},
        {"title": "Sort them", "type": "classification"},
        {"title": "Quiz", "type": "self_assessed", "section": 2},
    ]}}
    by_n = {2: verify.Section(n=2, title="", line=1, directives=["multi-select"]),
            3: verify.Section(n=3, title="", line=1, directives=["sorting-groups"])}
    report = verify.Report()
    verify.check_activity_types(unit, by_n, 3, {"activity_types": {"hotspot_analysis": ["scenario"],
                                                                    "classification": ["sorting-groups"]}}, report)
    assert len(report.warnings) == 1
    assert "Spot the error" in report.warnings[0] and "hotspot_analysis" in report.warnings[0]


def test_bank_question_that_repeats_a_practice_situation():
    course = {"language": "en"}
    syntax = verify.Syntax.for_tokens(coursemod.tokens(course))
    stem = "Laura receives an email from the bank asking her to confirm her password through a link before Friday"
    practice = [(10, "single-choice", ["objective: U1.1", f"question: {stem}", "- [x] Delete it", "- [ ] Click the link ‹trust›",
                                        "feedback: The bank never asks for passwords"])]
    same = [(5, "single-choice", ["objective: U1.1", f"question: {stem}", "- [x] Report it", "- [ ] Answer it"])]
    new = [(5, "single-choice", ["objective: U1.1", "question: A colleague shares a spreadsheet of customer phone numbers "
                                 "through a personal cloud folder", "- [x] Use the company drive", "- [ ] Leave it"])]
    rules = {"bank_practice_overlap": 0.5, "question_directives": ["single-choice"]}
    report = verify.Report()
    verify.check_bank_overlap(course, practice, same, rules, syntax, report)
    assert len(report.warnings) == 1 and "assessment.md:5" in report.warnings[0] and "content.md:10" in report.warnings[0]
    report = verify.Report()
    verify.check_bank_overlap(course, practice, new, rules, syntax, report)
    assert report.warnings == []


def test_headless_summary_takes_the_last_summary_block(tmp_path):
    log = tmp_path / "run.log"
    events = [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Done.\n<summary>Wrote 3 sections. Pending: "
                                                                                   "one VERIFICAR.</summary>"}]}},
        {"type": "result", "result": "A background search has finished."},
    ]
    log.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
    assert launch.final_message("claude", log, tmp_path / "none.txt") == "Wrote 3 sections. Pending: one VERIFICAR."
    log.write_text(json.dumps({"type": "result", "result": "Only this."}), encoding="utf-8")
    assert launch.final_message("claude", log, tmp_path / "none.txt") == "Only this."


def test_review_summary_comes_from_the_report(tmp_path):
    reviews = tmp_path / "reviews"
    reviews.mkdir()
    (reviews / "unit-02-ai-review.md").write_text("# AI review\n\n## Summary\nReady with changes.\n\n## Findings\n| # |\n",
                                                  encoding="utf-8")
    assert launch.report_summary({"_dir": tmp_path}, 2) == "Summary\nReady with changes."
    assert launch.report_summary({"_dir": tmp_path}, 3) == ""


@pytest.fixture
def server(tmp_path):
    folder = tmp_path / "site"
    folder.mkdir()
    httpd = HTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(folder)))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield folder, f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def test_a_linked_pdf_is_a_document(server, tmp_path):
    folder, base = server
    (folder / "report.pdf").write_bytes(b"%PDF-1.4\n" + b"0" * 100)
    (folder / "page.html").write_text("<html><body>Hello</body></html>", encoding="utf-8")
    found = brief.fetch_document(f"{base}/report.pdf")
    assert found is not None and found[1] == ".pdf" and found[0].startswith(b"%PDF")
    assert brief.fetch_document(f"{base}/page.html") is None
    assert brief.fetch_document("http://127.0.0.1:1/nothing.pdf") is None


def test_save_document_writes_markdown(tmp_path, monkeypatch):
    monkeypatch.setattr(brief, "markitdown", lambda src: ("# Report\n\nThe text.", None))
    assert brief.save_document("https://example.com/files/annual-report.pdf", b"%PDF", ".pdf", tmp_path / "web") is None
    text = (tmp_path / "web" / "annual-report.md").read_text(encoding="utf-8")
    assert text.startswith("<!-- https://example.com/files/annual-report.pdf -->") and "The text." in text
    monkeypatch.setattr(brief, "markitdown", lambda src: ("   ", None))
    assert brief.save_document("https://example.com/scan.pdf", b"%PDF", ".pdf", tmp_path / "scan") == ("document_no_text", {})


def test_guide_quotes_every_indication_of_the_notes(tmp_path):
    guide = tmp_path / "media-style.md"
    (tmp_path / "notes.md").write_text("# Notes\n\n<!-- comment -->\n- No dashed lines.\n- Icons in **outline** only\n"
                                       "- Never use the mascot\n", encoding="utf-8")
    guide.write_text("# Guide\n\n| Indication | Where |\n|---|---|\n| No dashed lines | Shape |\n"
                     "| Icons in outline only. | Icons |\n", encoding="utf-8")
    assert mediastyle.notes(guide) == ["No dashed lines.", "Icons in **outline** only", "Never use the mascot"]
    assert mediastyle.missing_notes(guide) == ["Never use the mascot"]
    (tmp_path / "notes.md").unlink()
    assert mediastyle.missing_notes(guide) == []
