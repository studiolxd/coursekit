"""Tokens derived from the theme of the platform: project and course scope, origin, contrast and the media guard."""

import copy
import json
from pathlib import Path

import pytest
import yaml

from coursekit import theme
from coursekit.cli import main
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture

FIXTURE = Path(__file__).parent / "fixtures" / "creator_theme.json"


def creator() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def tokens_of(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ── the conversion ───────────────────────────────────────────────────────────────────────────


def test_roles_palette_references_and_fonts_are_resolved():
    tokens = theme.from_creator(creator())
    colors = tokens["color"]
    assert colors["background"] == "#FFFFFF" and colors["text"] == "#000000"
    assert colors["headings"] == "#1B365D"  # a palette colour
    assert colors["accent"] == "#0A58CA" and colors["link"] == "#0A58CA"  # a role pointing at another role
    assert colors["on-accent"] == "#FFFFFF"
    assert colors["correct"] == "#14733A" and colors["wrong"] == "#B3261E"
    assert colors["on-correct"] == "#000000"  # the text roles inherit the text colour
    assert tokens["font"]["headings"].startswith("'ACME Sans'")
    assert tokens["font"]["family"] == theme.SYSTEM_FONT
    assert tokens["font"]["size-base"] == "17px" and tokens["font"]["line-height"] == "1.5"
    origin = tokens["origin"]
    assert origin["source"] == "creator" and origin["theme_id"] == "11111111-2222-4333-8444-555555555555"
    assert origin["name"] == "ACME training" and origin["version"] == 3
    assert {"text-soft", "surface", "highlight", "line", "accent-strong"} == set(origin["derived"])


def test_the_soft_colours_stay_readable_and_the_whole_theme_passes_the_check():
    tokens = theme.from_creator(creator())
    assert theme.contrast(tokens["color"]["text-soft"], tokens["color"]["background"]) >= 4.5
    assert all(ok for ok, _ in theme.check(tokens))


def test_a_pale_accent_is_reported_not_hidden():
    response = copy.deepcopy(creator())
    palette = response["theme"]["config"]["colors"]["palette"]
    next(p for p in palette if p["id"] == "accent")["value"] = "#FFE066"
    results = theme.check(theme.from_creator(response))
    assert [line for ok, line in results if not ok]


def test_defaults_when_the_theme_sets_little():
    minimal = {"themeId": "x", "name": "N", "version": 1, "theme": {"config": {"colors": {"palette": [], "semantic": {}}}}}
    tokens = theme.from_creator(minimal)
    assert tokens["color"]["background"] == "#FFFFFF" and tokens["color"]["correct"] == "#1DA34E"
    assert tokens["font"]["size-base"] == "16px" and tokens["font"]["line-height"] == "1.6"


def test_dark_mode_and_unknown_fonts_leave_a_note():
    response = copy.deepcopy(creator())
    config = response["theme"]["config"]
    config["colorMode"] = {"mode": "auto", "toggle": True}
    config["fonts"]["assignments"]["ui"] = "inter"
    notes = " ".join(theme.from_creator(response)["origin"]["notes"])
    assert "dark mode" in notes and "'inter'" in notes


@pytest.mark.parametrize("value", ["#fff", "#FFFFFF80", "rgb(255, 255, 255)", "rgba(255 255 255 / 50%)", "hsl(0, 0%, 100%)", "white"])
def test_css_colours_become_hex(value):
    assert theme.to_hex(value) == "#FFFFFF"


def test_what_cannot_be_resolved_is_none():
    assert theme.to_hex("transparent") is None and theme.to_hex("not-a-colour") is None and theme.to_hex(None) is None


# ── import, scope and show ───────────────────────────────────────────────────────────────────


def test_import_for_the_project_writes_tokens_json_and_css(course, capsys):  # noqa: F811
    root = course.parent.parent
    assert main(["theme", "import", str(FIXTURE)]) == 0
    out = capsys.readouterr().out
    assert "theme/tokens.json" in out and "'ACME training'" in out
    assert tokens_of(root / "theme" / "tokens.json")["origin"]["source"] == "creator"
    css = (root / "theme" / "tokens.css").read_text(encoding="utf-8")
    assert "--color-accent: #0A58CA;" in css and "--font-family-headings: 'ACME Sans'" in css and "--font-size-base: 17px;" in css
    assert main(["theme", "show"]) == 0
    shown = capsys.readouterr().out
    assert "project tokens: theme/tokens.json" in shown and "platform theme 'ACME training'" in shown
    assert main(["theme", "check"]) == 0


def test_a_course_can_have_its_own_theme(course, capsys):  # noqa: F811
    root = course.parent.parent
    assert main(["theme", "import", str(FIXTURE)]) == 0
    other = creator()
    other["themeId"], other["name"] = "99999999-2222-4333-8444-555555555555", "ACME campaign"
    other["theme"]["config"]["colors"]["palette"][3]["value"] = "#7A1FA2"
    file = root / "campaign.json"
    file.write_text(json.dumps(other), encoding="utf-8")
    assert main(["theme", "import", str(file), "--course", "PWD"]) == 0
    assert tokens_of(course / "theme" / "tokens.json")["color"]["accent"] == "#7A1FA2"
    assert (course / "theme" / "tokens.css").exists()
    assert tokens_of(root / "theme" / "tokens.json")["color"]["accent"] == "#0A58CA"  # the project keeps its own
    info = yaml.safe_load((course / "course.yaml").read_text(encoding="utf-8"))
    assert info["slxd"]["theme_id"] == "99999999-2222-4333-8444-555555555555"
    capsys.readouterr()
    assert main(["theme", "show", "--course", "PWD"]) == 0
    assert "tokens of the course: courses/PWD/theme/tokens.json" in capsys.readouterr().out
    assert main(["theme", "show"]) == 0
    assert "project tokens" in capsys.readouterr().out
    assert main(["theme", "tokens", "--course", "PWD"]) == 0
    assert "--color-accent: #7A1FA2;" in (course / "theme" / "tokens.css").read_text(encoding="utf-8")


def test_show_takes_the_course_code_with_or_without_the_option(course, capsys):  # noqa: F811
    assert main(["theme", "import", str(FIXTURE), "--course", "PWD"]) == 0
    capsys.readouterr()
    for args in (["theme", "show", "--course", "PWD"], ["theme", "show", "PWD"]):
        assert main(args) == 0
        assert "tokens of the course: courses/PWD/theme/tokens.json" in capsys.readouterr().out


def test_a_course_without_its_own_theme_uses_the_project_one(course, capsys):  # noqa: F811
    assert main(["theme", "import", str(FIXTURE)]) == 0
    capsys.readouterr()
    assert main(["theme", "show", "--course", "PWD"]) == 0
    assert "project tokens" in capsys.readouterr().out


def test_import_errors_are_messages(course, capsys):  # noqa: F811
    assert main(["theme", "import"]) == 2
    assert "needs the file" in capsys.readouterr().err
    assert main(["theme", "import", "nothing.json"]) == 1
    assert "nothing.json does not exist" in capsys.readouterr().err
    bad = course.parent.parent / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    assert main(["theme", "import", str(bad)]) == 1
    assert "does not look like a get_theme result" in capsys.readouterr().err


def test_show_without_tokens_says_what_to_do(course, capsys):  # noqa: F811
    assert main(["theme", "show"]) == 0
    assert "/define-theme" in capsys.readouterr().out


def test_tokens_written_by_hand_are_reported(course, capsys):  # noqa: F811
    by_hand = {"color": {"text": "#000", "background": "#fff"}}
    (course.parent.parent / "theme" / "tokens.json").write_text(json.dumps(by_hand), encoding="utf-8")
    assert main(["theme", "show"]) == 0
    assert "written by hand" in capsys.readouterr().out


# ── the media guard ──────────────────────────────────────────────────────────────────────────


def test_media_plan_warns_and_set_refuses_without_derived_tokens(course, capsys):  # noqa: F811
    assert main(["media", "extract", "PWD"]) == 0
    capsys.readouterr()
    assert main(["media", "plan", "PWD"]) == 0
    assert "has no theme tokens" in capsys.readouterr().out
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced"]) == 1
    assert "/define-theme" in capsys.readouterr().err
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "scripted"]) == 0  # only producing needs the theme
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced", "--force"]) == 0

    (course.parent.parent / "theme").mkdir(exist_ok=True)
    (course.parent.parent / "theme" / "tokens.json").write_text(json.dumps({"color": {"text": "#000"}}), encoding="utf-8")
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "pending"]) == 0
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced"]) == 1
    assert "written by hand" in capsys.readouterr().err


def test_media_set_remembers_the_tokens_and_plan_notices_a_change(course, capsys):  # noqa: F811
    assert main(["theme", "import", str(FIXTURE)]) == 0
    assert main(["media", "extract", "PWD"]) == 0
    assert main(["media", "set", "PWD", "U1-S2-M1", "--status", "produced"]) == 0
    manifest = yaml.safe_load((course / "media" / "manifest.yaml").read_text(encoding="utf-8"))["assets"][0]
    assert manifest["theme"] == theme.fingerprint(theme.from_creator(creator()))
    capsys.readouterr()
    assert main(["media", "plan", "PWD"]) == 0
    assert "produced with other theme tokens" not in capsys.readouterr().out

    other = creator()
    other["theme"]["config"]["colors"]["palette"][3]["value"] = "#7A1FA2"
    file = course.parent.parent / "other.json"
    file.write_text(json.dumps(other), encoding="utf-8")
    assert main(["theme", "import", str(file)]) == 0
    capsys.readouterr()
    assert main(["media", "plan", "PWD"]) == 0
    assert "U1-S2-M1 was produced with other theme tokens" in capsys.readouterr().out


def test_doctor_reports_the_theme(course, capsys):  # noqa: F811
    assert main(["doctor"]) in (0, 1)
    assert "no design tokens" in capsys.readouterr().out
    assert main(["theme", "import", str(FIXTURE)]) == 0
    capsys.readouterr()
    assert main(["doctor"]) in (0, 1)
    assert "tokens derived from the theme of the platform" in capsys.readouterr().out


def test_the_named_colours_of_the_palette_travel_in_the_tokens_without_changing_the_look():
    response = creator()
    tokens = theme.from_creator(response)
    palette = {p["id"]: p["value"] for p in (response.get("theme") or response)["config"]["colors"]["palette"]}
    assert tokens["palette"] and all(v.startswith("#") and len(v) == 7 for v in tokens["palette"].values())
    first = next(k for k, v in palette.items() if v.startswith("#"))
    assert tokens["palette"][first] == palette[first].upper()
    assert f"--palette-{first}: {palette[first].upper()};" in theme.css(tokens)
    # the media made with the tokens is not stale because the palette is listed: only the look counts
    assert theme.fingerprint(tokens) == theme.fingerprint({k: v for k, v in tokens.items() if k != "palette"})
