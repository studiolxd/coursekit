"""Robustness and checks added after producing a whole course: the lock of the manifest, the summary of a headless run, the
documents linked in the brief, the notes of the media style guide and the new warnings of `verify`."""

import json
import subprocess
import sys
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler

import pytest

from coursekit import brief, launch, simulation, util, verify
from coursekit import course as coursemod
from coursekit.media import style as mediastyle

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


@pytest.mark.parametrize(("language", "line", "wrong"), [
    ("es", "feedback-correcto: La respuesta correcta es la tercera.", True),
    ("es", "feedback-incorrecto: Las correctas son la primera y la segunda.", True),
    ("es", "feedback-incorrecto: Las opciones a y c no protegen la cuenta.", True),
    ("es", "feedback: Ninguna de las anteriores protege la cuenta.", True),
    ("es", "feedback-incorrecto: Las tres primeras son correctas; la cuarta reutiliza la clave.", True),
    ("es", "feedback-correcto: La respuesta correcta es la que dice que una frase larga resiste más.", False),
    ("es", "feedback-correcto: Correcto: la primera vez que entras te pide cambiarla.", False),
    ("en", "feedback-correct: The correct answer is the third one.", True),
    ("en", "feedback-incorrect: Options b and c reuse the password.", True),
    ("en", "feedback: None of the above protects the account.", True),
    ("en", "feedback-correct: Right: the first time you log in it asks you to change it.", False),
])
def test_feedback_never_names_an_option_by_its_position(language, line, wrong):
    tokens = coursemod.tokens({"language": language})
    rules = {"shuffled_options": ["single-choice"]}
    question = (7, "single-choice", ["- [x] A long phrase", "- [ ] A short word ‹short›", line])
    report = verify.Report()
    verify.check_positional_feedback(verify.Path("content.md"), [question], rules, tokens, report)
    assert bool(report.errors) == wrong
    if wrong:
        assert "content.md:10" in report.errors[0]
    report = verify.Report()
    verify.check_positional_feedback(verify.Path("content.md"), [(7, "short-answer", [line])], rules, tokens, report)
    assert report.errors == []


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


def test_the_text_of_the_learner_never_names_an_objective_by_its_id():
    syntax = verify.Syntax.for_tokens(coursemod.tokens({"language": "es"}))
    rules = {"simulation_directives": ["scenario"]}
    text = """## Apartado 1 — Introducción y objetivos

Al terminar la unidad podrás:

- U6.1 — Descomponer un proyecto en encargos pequeños.
- Gestionar el contexto de una sesión larga.

<!-- objetivos: U6.1, U6.2 -->
*[Objetivo U6.1 — Descomponer]*

:::single-choice
objetivo: U6.2
pregunta: ¿Qué haces?
- [x] Compactar
:::

:::scenario
objective: [U6.1, U6.2]
:::
"""
    report = verify.Report()
    verify.check_objective_ids(verify.Path("content.md"), text, rules, syntax, report)
    assert len(report.errors) == 1 and "content.md:5" in report.errors[0] and "U6.1" in report.errors[0]


def test_a_list_of_titled_items_is_laid_out_as_tabs_or_an_accordion_and_a_process_as_a_carousel():
    two = """Dos proyectos para practicar:

- El planificador de menús. Añadir a la web de recetas una página donde eliges una receta para cada comida.

- El programa de fotos. Terminar la lista del programa que ordena las fotos por fecha, desde el primer encargo.
"""
    three = "\n".join(f"{n}. **Paso {n}.** Abre el gestor de contraseñas y crea una entrada nueva." for n in (1, 2, 3))
    plain = "- Abre el gestor.\n- Crea una entrada.\n- 1234: la contraseña más usada de todas las que se filtran cada año."
    report = verify.Report()
    verify.check_lists(verify.Path("content.md"), two + "\n" + "Texto.\n\n" + three + "\n\nOtro.\n\n" + plain, report)
    assert len(report.warnings) == 2
    assert "content.md:3" in report.warnings[0] and ":::tabs" in report.warnings[0]
    assert ":::carousel" in report.warnings[1]  # numbered: a process
    report = verify.Report()
    verify.check_lists(verify.Path("content.md"), ":::tabs\n" + two + ":::\n", report)
    assert report.warnings == []


def test_a_list_of_more_than_two_titled_items_is_an_accordion():
    items = "\n".join(f"- **Proyecto {n}.** Una web de recetas con una página para cada comida de la semana." for n in (1, 2, 3))
    report = verify.Report()
    verify.check_lists(verify.Path("content.md"), items, report)
    assert len(report.warnings) == 1 and ":::accordion" in report.warnings[0]


def test_a_card_that_does_not_fit_asks_for_an_accordion():
    long = " ".join(["palabra"] * 40)
    cards = [(3, "flashcard-gallery", ["#### Gestor", "Programa que guarda las claves.", "#### Frase", long]),
             (9, "accordion", ["#### Frase", long])]
    report = verify.Report()
    verify.check_card_lengths(verify.Path("content.md"), cards, {"card_max_words": 35}, report)
    assert len(report.warnings) == 1 and "content.md:3" in report.warnings[0] and "Frase" in report.warnings[0]
    assert "Gestor" not in report.warnings[0] and ":::accordion" in report.warnings[0]
