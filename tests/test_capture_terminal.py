"""`coursekit capture` in terminal mode: a shell of its own in a stage of the course, recorded as it goes."""

import json
import os
import shutil

import pytest
import yaml

from coursekit import capture, capture_stage
from coursekit import capture_terminal as term
from coursekit.cli import main
from coursekit.project import find_project
from tests.test_assemble import course  # noqa: F401 — the approved sample course fixture
from tests.test_capture import no_script_gate  # noqa: F401 — the script gate is tested elsewhere
from tests.test_media import prepare_asset

real = pytest.mark.skipif(not (term.supported() and term.emulator_available() and term.find_font() and shutil.which("bash")),
                          reason="needs a pseudo-terminal, pyte, a monospaced font and bash")


# ── what needs no terminal ───────────────────────────────────────────────────────────────────

def test_the_keys_become_what_a_terminal_receives():
    assert term.key_bytes("Enter") == "\r" and term.key_bytes("ctrl+c") == "\x03" and term.key_bytes("Control+D") == "\x04"
    assert term.key_bytes("shift+tab") == "\x1b[Z" and term.key_bytes("ArrowUp") == "\x1b[A" and term.key_bytes("alt+b") == "\x1bb"
    assert term.key_bytes("Escape") == "\x1b" and term.key_bytes("F2") == "\x1bOQ" and term.key_bytes("shift+a") == "A"
    with pytest.raises(term.ToolError, match="not a key"):
        term.key_bytes("ctrl+Enter")


def test_personal_data_is_covered_in_the_text_never_in_the_escape_sequences():
    covered = term.cover_text("\x1b[38;2;10;20;30mAna 600123456\x1b[0m done", lambda text: text.replace("Ana", "Eva").replace("6", "9"))
    assert covered == "\x1b[38;2;10;20;30mEva 900123459\x1b[0m done"


def test_the_output_waits_for_a_word_or_an_escape_sequence_to_be_whole():
    assert term.safe_cut("hello wor") == len("hello ")
    assert term.safe_cut("done\x1b[38;2") == len("done")
    assert term.safe_cut("done\x1b[0m") == len("done\x1b[0m")


def test_the_recording_keeps_its_stretches_and_shortens_the_pauses():
    events = [(0.0, "a"), (1.0, "b"), (10.0, "c"), (10.5, "d"), (30.0, "e"), (31.0, "f"), (50.0, "g")]
    marks = [(5.0, {"kind": "record", "on": True}), (10.2, {"kind": "point", "x": 1, "y": 2}),
             (12.0, {"kind": "record", "on": False}), (29.0, {"kind": "record", "on": True}),
             (32.0, {"kind": "record", "on": False})]
    recording = term.cut(events, marks, 60.0, 2.0)
    # before the first stretch: at once; 5 → 10 is shortened to 2; the end of a stretch holds (10.5 → 12: 1.5); the gap is
    # joined (29 → 30: 1); what comes after the last stretch is left out
    assert recording.events == [(0.0, "a"), (0.0, "b"), (2.0, "c"), (2.5, "d"), (5.0, "e"), (6.0, "f")]
    assert recording.points == [(2.2, {"kind": "point", "x": 1, "y": 2})] and recording.duration == 7.0
    whole = term.cut([(0.0, "a"), (20.0, "b")], [], 21.0, 1.5)
    assert whole.events == [(0.0, "a"), (1.5, "b")] and whole.duration == 2.5


def test_a_cast_is_asciicast_v2_with_the_palette_it_is_drawn_with():
    palette = {"background": "#ffffff", "foreground": "#000000", "ansi": [f"#00000{n:x}" for n in range(16)]}
    text = term.cast_text(term.Cut([(0.0, "hola"), (1.0, " mundo")], [], 3.0), 80, 24, palette)
    lines = [json.loads(line) for line in text.splitlines()]
    assert lines[0]["version"] == 2 and lines[0]["width"] == 80 and lines[0]["theme"]["bg"] == "#ffffff"
    assert lines[1:] == [[0.0, "o", "hola"], [1.0, "o", " mundo"], [3.0, "o", ""]]


def test_a_grant_in_terminal_mode_names_no_window_and_no_profile(course, capsys):  # noqa: F811
    terminal_course(course, capsys, "asciinema")
    grant = capture.active_grant(find_project(), "PWD", "U1-S2-M1")
    assert grant["mode"] == "terminal" and grant["window"] is None and grant["profile"] is None
    assert capture.capturable(load()) == ["U1-S2-M1"]


def test_the_plan_says_the_agent_records_what_the_grant_lets_it(course, capsys):  # noqa: F811
    from coursekit import handoff

    terminal_course(course, capsys, "asciinema")
    assert main(["media", "plan", "PWD"]) == 0
    assert "lets the media agent record it" in capsys.readouterr().out
    loaded = load()
    assert handoff._pending_media(loaded) == [] and [a["id"] for a in handoff.capturable(loaded)] == ["U1-S2-M1"]
    assert main(["capture", "revoke", "PWD"]) == 0
    assert handoff.capturable(load()) == []  # without the permission it waits for a person again


def test_a_replay_is_not_for_a_terminal(course, capsys):  # noqa: F811
    terminal_course(course, capsys, "asciinema")
    assert main(["capture", "replay", "PWD", "U1-S2-M1"]) == 1
    assert "recorded while it happens" in capsys.readouterr().err


# ── the stages ───────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def home(tmp_path, monkeypatch):
    folder = tmp_path / "home"
    folder.mkdir()
    monkeypatch.setenv("HOME", str(folder))
    return folder


def load():
    from coursekit import course as coursemod

    return coursemod.load(find_project(), "PWD")


def write_stage(course_dir, name="recipes", **spec):
    folder = course_dir / "media" / "stages" / name
    (folder / "files").mkdir(parents=True, exist_ok=True)
    (folder / "files" / "recipes.json").write_text('[{"name": "Lemon chicken"}]\n', encoding="utf-8")
    data = {"title": "Recipe website", "folder": "projects", **spec}
    (folder / "stage.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return folder


def terminal_course(course_dir, capsys, recipe, block=None):
    root = course_dir.parent.parent
    (root / "config" / "capture.yaml").write_text(yaml.safe_dump({"enabled": True, "terminal": {"cols": 60, "rows": 12,
                                                                                                "width": 640}}), encoding="utf-8")
    prepare_asset(course_dir, capsys)
    assert main(["media", "set", "PWD", "U1-S2-M1", "--depicts", "interface", "--status", "scripted", "--recipe", recipe]) == 0
    brief = course_dir / "media" / "scripts" / "U1-S2-M1.md"
    brief.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(block or {"mode": "terminal", "stage": "recipes"}, allow_unicode=True)
    brief.write_text(f"# U1-S2-M1\n\nWhat it shows.\n\n```capture\n{body}```\n", encoding="utf-8")
    assert main(["capture", "allow", "PWD", "--mode", "terminal"]) == 0
    capsys.readouterr()


def test_a_stage_needs_the_permission_to_capture_in_terminal_mode(course, home, capsys):  # noqa: F811
    root = course.parent.parent
    (root / "config" / "capture.yaml").write_text(yaml.safe_dump({"enabled": True}), encoding="utf-8")
    write_stage(course)
    assert main(["capture", "stage", "PWD", "recipes"]) == 1
    assert "needs a permission to capture in terminal mode" in capsys.readouterr().err


@real
def test_a_stage_is_mounted_from_scratch_with_its_setup_and_never_over_a_folder_of_the_person(course, home, capsys):  # noqa: F811
    terminal_course(course, capsys, "asciinema")
    write_stage(course, setup=["git init -q && git add -A && git commit -qm First"], hide=["git-lfs-not-there"])
    assert main(["capture", "stage", "PWD", "recipes", "--prepare", "touch prepared.txt"]) == 0
    assert "stage recipes mounted in" in capsys.readouterr().out
    folder = home / "projects" / "recipes"
    assert (folder / "recipes.json").exists() and (folder / "prepared.txt").exists() and (folder / ".git").is_dir()
    log = capture_stage.subprocess.run(["git", "log", "--format=%an <%ae>"], cwd=folder, capture_output=True, text=True).stdout
    assert "@" in log and os.environ.get("USER", "nobody") not in log  # an invented author
    (folder / "left-over.txt").write_text("x", encoding="utf-8")
    assert main(["capture", "stage", "PWD", "recipes"]) == 0  # from scratch again
    assert not (folder / "left-over.txt").exists() and not (folder / "prepared.txt").exists()
    other = home / "projects" / "mine"
    other.mkdir()
    write_stage(course, "mine")
    assert main(["capture", "stage", "PWD", "mine"]) == 1
    assert "coursekit did not make it" in capsys.readouterr().err and other.exists()
    write_stage(course, "broken", setup=["exit 3"])
    assert main(["capture", "stage", "PWD", "broken"]) == 1
    assert "failed (code 3)" in capsys.readouterr().err


@real
def test_a_clean_stage_has_an_empty_home_and_hides_the_commands_it_says(course, home, capsys):  # noqa: F811
    terminal_course(course, capsys, "asciinema")
    write_stage(course, home="clean", hide=["git"])
    workspace = capture_stage.mount(find_project(), load(), "recipes")
    assert workspace.home != home and not any(workspace.home.glob(".*rc"))
    found = capture_stage.subprocess.run(["bash", "--noprofile", "--norc", "-c", "command -v git || echo none"],
                                         env=workspace.env, capture_output=True, text=True).stdout.strip()
    assert found == "none"
    assert capture_stage.subprocess.run(["bash", "--noprofile", "--norc", "-c", "command -v ls"], env=workspace.env,
                                        capture_output=True, text=True).stdout.strip()


# ── a whole session ──────────────────────────────────────────────────────────────────────────

def tools():
    from coursekit.capture_session import Manager

    return {tool.name: tool for tool in Manager(find_project()).tools()}


def call(tools, name, **args):
    return tools[name].run(args)


@real
def test_a_terminal_session_becomes_a_cast_with_the_secrets_covered(course, home, capsys, monkeypatch):  # noqa: F811
    monkeypatch.setenv("ACME_API_TOKEN", "sk-live-0123456789")
    terminal_course(course, capsys, "asciinema")
    write_stage(course)
    t = tools()
    started = call(t, "session_start", code="PWD", asset_id="U1-S2-M1")
    assert "in the stage recipes" in started[0]["text"] and started[1]["type"] == "image"
    call(t, "record_start")
    call(t, "type", text="cat recipes.json; echo $ACME_API_TOKEN")
    call(t, "key", key="Enter")
    waited = call(t, "wait_for", text="Lemon chicken", timeout_ms=5000)
    assert "is on screen" in waited[0]["text"] and "sk-live-0123456789" not in waited[0]["text"]
    call(t, "point_text", text="Lemon chicken", note="the recipe")
    call(t, "record_stop")
    with pytest.raises(term.ToolError, match="no pointer"):
        call(t, "left_click", x=10, y=10)
    ended = call(t, "session_end", notes="")
    assert "U1-S2-M1.cast" in ended[0]["text"]
    cast = (course / "media" / "recordings" / "U1-S2-M1.cast").read_text(encoding="utf-8")
    assert "Lemon chicken" in cast and "sk-live-0123456789" not in cast and str(home) not in cast
    asset = yaml.safe_load((course / "media" / "manifest.yaml").read_text(encoding="utf-8"))["assets"][0]
    assert asset["capture"]["state"] == "captured" and asset["capture"]["engine"] == "terminal"
    block = yaml.safe_load((course / "media" / "scripts" / "U1-S2-M1.md").read_text(encoding="utf-8")
                           .split("```capture\n")[1].split("```")[0])
    assert block["mode"] == "terminal" and block["stage"] == "recipes" and {"key": "Enter"} in block["steps"]


@real
@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_a_terminal_video_is_drawn_with_the_places_its_narration_names(course, home, capsys):  # noqa: F811
    terminal_course(course, capsys, "screen-recording")
    write_stage(course)
    t = tools()
    call(t, "session_start", code="PWD", asset_id="U1-S2-M1")
    call(t, "type", text="ls")
    call(t, "key", key="Enter")
    call(t, "wait_for", text="recipes.json", timeout_ms=5000)
    call(t, "point_text", text="recipes.json", note="the data")
    call(t, "type", text="printf '\\x6fne\\ntwo longer line\\nthr\\x65e\\n'")  # the command line does not hold them
    call(t, "key", key="Enter")
    call(t, "wait_for", text="three", timeout_ms=5000)
    call(t, "point_text", text="one", until="three", note="the block", shape="rect")
    with pytest.raises(term.ToolError, match="not a shape"):
        call(t, "point_text", text="one", shape="star")
    call(t, "session_end", notes="")
    recordings = course / "media" / "recordings"
    assert (recordings / "U1-S2-M1.mp4").stat().st_size > 0
    events = json.loads((recordings / "U1-S2-M1.events.json").read_text(encoding="utf-8"))
    assert events["video"] == "U1-S2-M1.mp4" and events["events"][0]["label"] == "the data"
    assert 0 < events["events"][0]["fx"] < 1 and 0 < events["events"][0]["fy"] < 1
    word, block = events["events"]
    assert word["shape"] == "round" and word["tone"] == "light"  # the light palette of capture.yaml › terminal
    x, y, w, h = block["box"]
    assert block["shape"] == "rect" and w > word["box"][2] and h > 2 * word["box"][3]  # three lines, as wide as the longest
    assert 0 <= x and x + w <= 1 and 0 <= y and y + h <= 1


@real
def test_a_terminal_capture_saves_the_screen_as_it_is(course, home, capsys):  # noqa: F811
    terminal_course(course, capsys, "screenshot")
    write_stage(course)
    t = tools()
    call(t, "session_start", code="PWD", asset_id="U1-S2-M1")
    call(t, "type", text="echo ready")
    call(t, "key", key="Enter")
    call(t, "wait_for", text="ready", timeout_ms=5000)
    call(t, "save_shot")
    call(t, "session_end", notes="")
    from PIL import Image

    with Image.open(course / "media" / "recordings" / "U1-S2-M1.png") as image:
        assert image.width > 500


def test_a_capture_block_written_as_yaml_with_a_capture_key_is_read_the_same(course, capsys):  # noqa: F811
    from coursekit import capture_session, mediascript

    terminal_course(course, capsys, "asciinema")
    brief = course / "media" / "scripts" / "U1-S2-M1.md"
    block = "```yaml\ncapture:\n  mode: terminal\n  stage: recipes\n  prepare: [\"rm -f a\"]\n```\n"
    brief.write_text(f"# U1-S2-M1\n\nWhat it shows.\n\n{block}", encoding="utf-8")
    loaded = load()
    assert capture_session.read_block(loaded, "U1-S2-M1") == {"mode": "terminal", "stage": "recipes", "prepare": ["rm -f a"]}
    before = mediascript.fingerprint(loaded, "U1-S2-M1")
    brief.write_text(brief.read_text(encoding="utf-8").replace("rm -f a", "rm -f b"), encoding="utf-8")
    assert mediascript.fingerprint(load(), "U1-S2-M1") == before  # the block is not what a person signs


def test_the_handoff_signs_the_scripts_of_what_its_agent_may_capture(course, capsys, monkeypatch):  # noqa: F811
    from coursekit import handoff, mediascript

    monkeypatch.setattr(mediascript, "required", lambda _course: True)
    terminal_course(course, capsys, "asciinema")
    assert mediascript.state(load(), "U1-S2-M1") == "pending"
    lines = []
    handoff._sign_capture_scripts(handoff.Context(find_project(), "PWD", 2, lines.append, lambda: None))
    assert mediascript.state(load(), "U1-S2-M1") == "approved" and "U1-S2-M1" in lines[0]
