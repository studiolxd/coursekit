"""The bridge between a package coursekit builds for an EMBED (a simulation, a wrapped SVG) and the lesson of creator that
holds it: creator's `slxd-embed` protocol, version 1.

The package declares what it can do in `slxd-embed.json`, at its root next to `index.html`, and talks to the lesson with
`postMessage` (it runs in a sandboxed iframe with an opaque origin, so it sends to "*" and never anything sensitive):

- `ready` when it has loaded;
- `resize` with the height of its content (CSS px), whenever it changes, so the iframe takes it without a scroll bar of
  its own (capability `resize`);
- `complete` once, when the learner has finished it (capability `complete`: a simulation that reaches an ending). Creator
  completes the brick and, if the author asked for it, lets the learner go on.

State, result and interactions are reserved by the protocol for a later phase: coursekit declares them when creator
handles them.
"""

from __future__ import annotations

import json
from pathlib import Path

PROTOCOL = "slxd-embed"
VERSION = 1
MANIFEST = "slxd-embed.json"


def write_manifest(folder: Path, capabilities: list[str]) -> Path:
    """The manifest of a package: the protocol, its version and what the package can do."""
    path = folder / MANIFEST
    data = {"protocol": PROTOCOL, "version": VERSION, "capabilities": capabilities}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def script() -> str:
    """`__bridge`: says `ready`, reports the height of the content as it changes, and `__bridge.complete()` says `complete`
    (only once)."""
    return f"""const __bridge = (() => {{
  const send = (type, data = {{}}) => {{
    try {{
      window.parent.postMessage({{ channel: "{PROTOCOL}", version: {VERSION}, type, ...data }}, "*");
    }} catch (error) {{
      /* outside creator there is nobody to tell */
    }}
  }};
  let last = -1;
  let done = false;
  const measure = () => {{
    const body = document.body;
    const style = window.getComputedStyle(body);
    const height = Math.ceil(body.getBoundingClientRect().height + parseFloat(style.marginTop || 0) + parseFloat(style.marginBottom || 0));
    if (height !== last) {{
      last = height;
      send("resize", {{ height }});
    }}
  }};
  if (window.ResizeObserver) new window.ResizeObserver(measure).observe(document.body);
  window.addEventListener("load", measure);
  send("ready");
  measure();
  return {{
    complete() {{
      if (done) return;
      done = true;
      send("complete");
    }},
  }};
}})();
"""
