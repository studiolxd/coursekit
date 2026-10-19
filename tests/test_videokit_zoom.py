"""The zooms of a screen recording are one piece of code: the library of the montages and the Remotion workspace share it."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "src" / "coursekit"


def test_the_workspace_has_the_same_zooms_as_the_library():
    library = (ROOT / "videokit" / "atoms" / "zoom.ts").read_text(encoding="utf-8")
    workspace = (ROOT / "templates" / "remotion" / "src" / "zoom.ts").read_text(encoding="utf-8")
    assert workspace == library, "copy src/coursekit/videokit/atoms/zoom.ts to src/coursekit/templates/remotion/src/zoom.ts"
