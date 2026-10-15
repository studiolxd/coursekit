import zipfile

import pytest
import yaml

from coursekit import config, exelearning, importer
from coursekit.cli import main
from tests.exe_fixture import node, package, sample
from tests.test_assemble import course  # noqa: F401 — project with a course


def convert(tmp_path, name="a.elp"):
    path = sample(tmp_path / name)
    rules = config.package_defaults("import")["idevices"]
    return exelearning.convert(path, tmp_path / "media", "media", rules, "en")


def test_reads_the_tree_of_pages(tmp_path):
    pkg = exelearning.read(sample(tmp_path / "a.elp"))
    assert pkg.title == "Strong passwords" and pkg.language == "es"
    assert [p.title for p in pkg.root.children] == ["Introduction", "Empty cover", "Practice"]
    assert [i.kind for i in pkg.root.children[0].idevices][:2] == ["text", "Tpl_Click"]


def test_text_images_and_embeds(tmp_path):
    text, report = convert(tmp_path)
    assert text.startswith("# Strong passwords\n\n## Introduction")
    assert "Welcome to **strong** passwords." in text
    assert "![A padlock](media/photo.png)" in text and (tmp_path / "media" / "photo.png").is_file()
    assert report.embeds == [("video", "https://www.youtube.com/embed/abc", "www.youtube.com")]
    assert "Empty cover" not in text and report.empty_pages == ["Empty cover"]


def test_the_notice_before_an_interactive_is_left_out_and_counted(tmp_path):
    text, report = convert(tmp_path)
    assert "Click on the arrows" not in text and "Click the cards" not in text and "Click the areas" not in text
    assert report.dropped["Tpl_Click"] == {"Click on the arrows to see the content.": 1}
    assert set(report.dropped) == {"Tpl_Click", "flipcards-activity", "relaciona-activity", "mapa-activity"}


def test_boxes_become_the_directives_of_their_rules(tmp_path):
    text, _ = convert(tmp_path)
    assert ":::note\ntitle: Attention\nNever reuse a password.\n:::" in text
    assert ":::highlight\n**Definition**\n\nA passphrase is a long password.\n:::" in text


def test_the_effects_of_exelearning_keep_their_kind_of_interactivity(tmp_path):
    text, report = convert(tmp_path)
    assert ":::accordion\n#### Length\nLonger is better.\n#### Variety\nMix kinds of characters.\n:::" in text
    assert ":::tabs\n#### Keyboard\nKeyboard content.\n#### Phone\nPhone content.\n:::" in text
    assert ":::carousel\n#### 1\nFirst slide text.\n#### 2\nSecond slide text.\n:::" in text
    assert report.notes == [("untitled_items", {"kind": "carousel", "count": 2})]
    assert "Tpl_Slider" not in report.unmapped  # its collection was understood


def test_games_and_map(tmp_path):
    text, _ = convert(tmp_path)
    assert ":::flashcards\n#### Passphrase\nA long password made of words.\n:::" in text
    assert ":::match\nquestion: Match each term.\n- Manager :: Stores your passwords\n:::" in text
    assert ":::labelled-graphic\nimage: media/map.png\n#### 1\nPoint one explains the length.\nposition: 25,50\n:::" in text


def test_questions(tmp_path):
    text, report = convert(tmp_path)
    assert (":::single-choice\nquestion: Which is stronger?\n- [ ] 1234\n- [x] three long words\n"
            "feedback-correct: Length wins.\nfeedback-incorrect: Too short.\n:::") in text
    assert ":::true-false\nquestion: Reusing a password is safe.\nanswer: false\nfeedback: Each service needs its own.\n:::" in text
    assert report.questions == 2


def test_no_word_of_the_source_is_lost(tmp_path):
    _, report = convert(tmp_path)
    assert report.missing_words == []
    assert report.words_source > 50


def test_an_idevice_without_a_rule_is_imported_as_text_and_reported(tmp_path):
    page = node("Page", [exelearning_text("Plain words."), exelearning_generic("Odd_Thing", "Label", "<p>Odd words.</p>")])
    path = package(tmp_path / "b.elp", "T", [page])
    text, report = exelearning.convert(path, tmp_path / "m", "m", [], "en")
    assert "Odd words." in text and report.unmapped == {"Odd_Thing": 1}


def exelearning_text(html):
    from tests.exe_fixture import js_text
    return js_text(f"<p>{html}</p>")


def exelearning_generic(title, label, html):
    from tests.exe_fixture import generic
    return generic(title, label, html)


def test_a_package_that_is_not_readable(tmp_path):
    bad = tmp_path / "bad.elp"
    bad.write_text("nope", encoding="utf-8")
    with pytest.raises(exelearning.ExeError):
        exelearning.read(bad)
    v4 = tmp_path / "v4.elp"
    with zipfile.ZipFile(v4, "w") as archive:
        archive.writestr("content.xml", "<ode/>")
    with pytest.raises(exelearning.ExeError, match="eXeLearning 4"):
        exelearning.read(v4)


def test_the_brief_converts_the_packages_of_sources(course):  # noqa: F811
    sample(course / "brief" / "sources" / "unit.elp")
    assert main(["brief", "PWD"]) == 0
    text = (course / "brief" / "text" / "files" / "unit.elp.md").read_text(encoding="utf-8")
    assert ":::accordion" in text and "![A padlock](../media/unit.elp/photo.png)" in text
    assert (course / "brief" / "text" / "media" / "unit.elp" / "photo.png").is_file()
    assert "unit.elp" in (course / "brief" / "index.md").read_text(encoding="utf-8")
    report = (course / "brief" / "import-report.md").read_text(encoding="utf-8")
    assert "Dejado fuera por las reglas" in report and "no falta ninguna palabra del origen" in report  # the language of the course
    (course / "brief" / "sources" / "unit.elp").unlink()
    assert main(["brief", "PWD"]) == 0
    assert not (course / "brief" / "import-report.md").exists()
    assert not (course / "brief" / "text" / "media" / "unit.elp").exists()


def test_the_numbers_of_the_units_in_the_names():
    names = {"UNIT_3_v5.elp": 3, "MOD2.elp": 2, "Unidad 4. Algo_vREV.elp": 4, "1_Intro_V4.elp": 1, "Name 2_vREV.elp": 2,
             "Long title here_3_V5.elp": 3, "Course5_v2.elp": 5, "Title 7.elp": 7, "ECF010_2_Title_V4.elp": 2, "Plain.elp": None}
    assert {n: importer.unit_number(n) for n in names} == names


def make_courses(root):
    for folder, files in {"abc001": ["A2_v1.elp", "A1_v1.elp"], "abc002": ["B1_v1.elp", "B1_v2.elp"], "none": []}.items():
        (root / folder).mkdir(parents=True)
        for name in files:
            package(root / folder / name, name, [node("Page", [exelearning_text(f"Text of {name}.")])])


def test_scan_a_parent_folder(tmp_path):
    make_courses(tmp_path / "parent")
    found = importer.scan(tmp_path / "parent")
    assert [c.code for c in found.courses] == ["ABC001", "ABC002"] and found.empty == ["none"]
    assert [u.path.name for u in found.courses[0].units] == ["A1_v1.elp", "A2_v1.elp"]
    assert len(found.courses[1].duplicates) == 1  # two packages for unit 1
    single = importer.scan(tmp_path / "parent" / "abc001")
    assert [c.code for c in single.courses] == ["ABC001"]


def test_hours_from_a_spreadsheet_and_a_default(tmp_path):
    from openpyxl import Workbook

    make_courses(tmp_path / "parent")
    book = Workbook()
    sheet = book.active
    sheet.append(["Carpeta", "Horas", "Título"])
    sheet.append(["ABC001", "7,5", "First course"])
    sheet.append(["nowhere", 3, ""])
    book.save(tmp_path / "hours.xlsx")
    found = importer.scan(tmp_path / "parent")
    unmatched = importer.resolve(found, {}, importer.read_table(tmp_path / "hours.xlsx"), None)
    first, second = found.courses
    assert (first.title, first.hours, first.problems) == ("First course", 7.5, [])
    assert second.hours is None and any("hours" in p for p in second.problems) and second.title == "abc002"
    assert unmatched == ["nowhere"]
    importer.resolve(found, {}, {}, 20)
    assert first.hours == 20 and second.hours == 20


def test_the_plan_is_written_and_read_back(tmp_path):
    make_courses(tmp_path / "parent")
    found = importer.scan(tmp_path / "parent")
    plan = tmp_path / "import.yaml"
    importer.write_plan(plan, found, {})
    data = yaml.safe_load(plan.read_text(encoding="utf-8"))
    assert [c["folder"] for c in data["courses"]] == ["abc001", "abc002"]
    data["courses"][1]["units"] = ["B1_v2.elp"]
    data["courses"][1]["title"], data["courses"][1]["hours"] = "Second", 4
    plan.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    found = importer.scan(tmp_path / "parent")
    importer.resolve(found, importer.read_plan(plan), {}, 10)
    assert found.courses[1].problems == [] and [u.path.name for u in found.courses[1].units] == ["B1_v2.elp"]
    assert found.courses[1].title == "Second" and found.courses[1].hours == 4


def test_import_a_parent_folder(course, tmp_path, capsys):  # noqa: F811
    make_courses(tmp_path / "parent")
    assert main(["import", str(tmp_path / "parent"), "--default-hours", "6"]) == 0
    out = capsys.readouterr().out
    assert "abc001 → ABC001: 2 units, 6.0 h" in out and "abc002: not imported" in out and "no packages, not imported: none" in out
    folder = course.parent / "ABC001"
    data = yaml.safe_load((folder / "course.yaml").read_text(encoding="utf-8"))
    assert data["design"]["origin"] == "import" and data["design"]["hours"] == 6
    assert sorted(p.name for p in (folder / "brief" / "sources").glob("*.elp")) == ["01-A1_v1.elp", "02-A2_v1.elp"]
    assert (folder / "brief" / "text" / "files" / "01-A1_v1.elp.md").is_file()
    assert not (course.parent / "ABC002").exists()
    assert main(["import", str(tmp_path / "parent"), "--default-hours", "6"]) == 1  # abc002 still waits for a decision
    assert "already exists" in capsys.readouterr().out


def test_import_plan_only_writes_the_plan(course, tmp_path, capsys):  # noqa: F811
    make_courses(tmp_path / "parent")
    assert main(["import", str(tmp_path / "parent"), "--plan"]) == 0
    assert (course.parent.parent / "import.yaml").is_file() and not (course.parent / "ABC001").exists()
    assert "2 courses, 0 ready to import" in capsys.readouterr().out


def test_the_report_names_what_rules_forbidden_asks_to_remove(tmp_path):
    path = sample(tmp_path / "f.elp")
    rules = config.package_defaults("import")["idevices"]
    text, report = exelearning.convert(path, tmp_path / "m", "m", rules, "en",
                                       {"hosts": ["youtube.com"], "terms": ["welcome", "nothing here"]})
    assert "(forbidden host: replace it with a media placeholder)" in text
    assert report.forbidden_embeds == ["https://www.youtube.com/embed/abc"]
    assert report.forbidden_terms == {"welcome": 1}
    assert "welcome" in exelearning.render_report([("f.elp", report)], "en")


def edit_course(course_dir, change):
    path = course_dir / "course.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_verify_reports_what_rules_forbidden_lists(course, capsys):  # noqa: F811
    assert main(["verify", "PWD", "--unit", "1"]) == 0
    edit_course(course, lambda d: d["rules"].update(forbidden={"terms": ["palabra"], "hosts": ["example.com"]}))
    capsys.readouterr()
    assert main(["verify", "PWD", "--unit", "1"]) == 1
    out = capsys.readouterr().out
    assert "“palabra” is forbidden by `rules › forbidden`" in out


def test_an_imported_course_is_warned_not_blocked_about_its_size(course, capsys):  # noqa: F811
    def sizes(data):
        for unit in data["units"]:
            for section in unit["sections"]:
                section["min_words"] = 5000

    edit_course(course, sizes)
    assert main(["verify", "PWD", "--unit", "1"]) == 1  # a new course: too short is an error
    edit_course(course, lambda d: d["design"].update(origin="import"))
    capsys.readouterr()
    assert main(["verify", "PWD", "--unit", "1"]) == 0
    out = capsys.readouterr().out
    assert "WARNING" in out and "unit 1 (imported course)" in out and "falls short" in out


def test_adopt_an_image_that_already_exists(course, capsys):  # noqa: F811
    from tests.exe_fixture import png

    assert main(["media", "extract", "PWD"]) == 0
    source = course / "brief" / "text" / "media" / "unit" / "photo.png"
    source.parent.mkdir(parents=True)
    source.write_bytes(png())
    capsys.readouterr()
    assert main(["media", "adopt", "PWD", "U1-S2-M1", "--file", "brief/text/media/unit/photo.png", "--alt", "A padlock"]) == 0
    assert "U1-S2-M1: produced" in capsys.readouterr().out
    assert (course / "media" / "files" / "U1-S2-M1.png").read_bytes() == png()
    asset = yaml.safe_load((course / "media" / "manifest.yaml").read_text(encoding="utf-8"))["assets"][0]
    assert (asset["status"], asset["file"], asset["alt"], asset["recipe"]) == (
        "produced", "media/files/U1-S2-M1.png", "A padlock", "imported")
    assert main(["media", "adopt", "PWD", "U1-S2-M1", "--file", "nowhere.png"]) == 1
    assert main(["media", "adopt", "PWD", "U1-S2-M1"]) == 2
