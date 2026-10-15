"""`coursekit videos`: videos of forbidden sites are allowed when their channel is official."""

import pytest
import yaml

from coursekit import videos
from coursekit.cli import main
from tests.test_assemble import course  # noqa: F401 — project with a course
from tests.test_exelearning import edit_course

OFFICIAL = "https://www.youtube.com/watch?v=official1"
OTHER = "https://youtu.be/other22"
CHANNELS = {
    "official1": {"name": "Acme Support", "url": "https://www.youtube.com/@AcmeSupport", "title": "Official guide"},
    "other22": {"name": "Some Fan", "url": "https://www.youtube.com/@somefan", "title": "Fan tutorial"},
    "proposed3": {"name": "Acme Training", "url": "https://www.youtube.com/channel/UC123", "title": "Training"},
}


@pytest.fixture
def web(monkeypatch):
    """The site is not asked: each video answers with the channel of the table."""
    monkeypatch.setattr(videos, "oembed", lambda url: CHANNELS.get(videos.key(url).removeprefix("youtube:")))


def with_videos(course_dir, *urls):
    path = course_dir / "content" / "unit-01" / "content.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n\n" + "\n\n".join(f"Mira {u}" for u in urls) + "\n", encoding="utf-8")


def allow(course_dir, **extra):
    forbidden = {"hosts": ["youtube.com", "youtu.be"], "allow_channels": ["@AcmeSupport"], **extra}
    edit_course(course_dir, lambda d: d["rules"].update(forbidden=forbidden))


def registry(course_dir):
    return {videos.key(v["url"]): v for v in yaml.safe_load((course_dir / "media" / "external-videos.yaml").read_text())["videos"]}


def test_the_same_video_has_one_key():
    keys = {videos.key(u) for u in ("https://www.youtube.com/watch?v=abc", "https://youtu.be/abc?t=5", "https://www.youtube.com/embed/abc",
                                    "https://youtube-nocookie.com/embed/abc", "https://www.youtube.com/shorts/abc")}
    assert keys == {"youtube:abc"}


def test_an_official_channel_is_known_by_handle_name_id_or_address():
    channel = {"name": "Acme Support", "url": "https://www.youtube.com/@AcmeSupport"}
    for entry in ("@AcmeSupport", "acmesupport", "Acme Support", "https://www.youtube.com/@AcmeSupport"):
        assert videos.official(channel, [entry])
    assert not videos.official(channel, ["@other"]) and not videos.official(None, ["@AcmeSupport"])
    assert videos.official({"name": "x", "url": "https://www.youtube.com/channel/UC123"}, ["UC123"])


def test_check_approves_official_channels_and_leaves_the_rest_pending(course, web, capsys):  # noqa: F811
    allow(course)
    with_videos(course, OFFICIAL, OTHER)
    assert main(["verify", "PWD", "--unit", "1"]) == 1  # both are on a forbidden site until they are checked
    assert main(["videos", "check", "PWD"]) == 1  # one is left to replace
    found = registry(course)
    assert found["youtube:official1"]["status"] == "approved" and found["youtube:official1"]["channel"]["name"] == "Acme Support"
    assert found["youtube:other22"]["status"] == "pending" and "not in rules" in found["youtube:other22"]["why"]
    out = capsys.readouterr().out
    assert "1 approved, 0 proposed by the agent (to check), 1 to replace, 0 rejected" in out
    assert main(["verify", "PWD", "--unit", "1"]) == 1  # the one that is not official still fails
    out = capsys.readouterr().out
    assert "other22" not in out or "forbidden by `rules › forbidden`" in out
    assert "official1" not in out
    report = (course / "reviews" / "external-videos.md").read_text(encoding="utf-8")
    assert "Por sustituir" in report and "Some Fan" in report  # the language of the course


def test_a_proposed_replacement_is_checked_by_a_person(course, web, capsys, monkeypatch):  # noqa: F811
    allow(course)
    with_videos(course, "https://www.youtube.com/watch?v=proposed3")
    assert main(["videos", "propose", "PWD", "https://www.youtube.com/watch?v=proposed3", "--replaces", OTHER,
                 "--why", "Channel linked from the official site"]) == 0
    assert registry(course)["youtube:proposed3"]["status"] == "proposed"
    capsys.readouterr()
    assert main(["verify", "PWD", "--unit", "1"]) == 0  # the writing is not blocked, but it is told
    assert "proposed by the agent as from an official channel" in capsys.readouterr().out
    assert main(["videos", "propose", "PWD", "https://www.youtube.com/watch?v=proposed3"]) == 1  # the evidence is needed
    with monkeypatch.context() as nobody:
        nobody.setattr(videos.identity, "current", lambda: None)
        assert main(["videos", "approve", "PWD", "https://www.youtube.com/watch?v=proposed3"]) == 1  # a person signs
    assert main(["videos", "approve", "PWD", "https://youtu.be/proposed3"]) == 0  # any form of the address
    entry = registry(course)["youtube:proposed3"]
    assert entry["status"] == "approved" and entry["by"] == "Ana <ana@example.com>"  # the identity of the .env of the project
    capsys.readouterr()
    assert main(["verify", "PWD", "--unit", "1"]) == 0
    assert "proposed by the agent" not in capsys.readouterr().out


def test_a_rejected_video_cannot_stay(course, web, capsys):  # noqa: F811
    allow(course)
    with_videos(course, OFFICIAL)
    assert main(["videos", "check", "PWD"]) == 0
    assert main(["videos", "reject", "PWD", OFFICIAL]) == 1  # a rejected one is left to replace
    capsys.readouterr()
    assert main(["verify", "PWD", "--unit", "1"]) == 1
    assert "rejected by a person" in capsys.readouterr().out
    assert main(["videos", "approve", "PWD", "https://example.com/nothing"]) == 1  # not registered
