"""`coursekit init`: create a project, or refresh what coursekit generated in it.

Two kinds of files:

- seed files (`project.yaml`, `brief/notes.md`, `brief/links.md`): written once, then they
  belong to the project; `--update` never touches them;
- managed files (`AGENTS.md`, `CLAUDE.md`, `.env.example`, `.gitignore`): `--update` rewrites
  them with the current templates, unless the person edited them since coursekit wrote them
  (then they are left alone and reported). What was written is recorded, with its hash, in
  `.coursekit/generated.json`.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

import yaml

from coursekit.project import PROJECT_FILE

STATE_FILE = Path(".coursekit") / "generated.json"

# template name (inside coursekit/templates/project) → path in the project
SEED = {
    "project.yaml": "project.yaml",
    "brief/notes.md": "brief/notes.md",
    "brief/links.md": "brief/links.md",
}
MANAGED = {
    "AGENTS.md": "AGENTS.md",
    "CLAUDE.md": "CLAUDE.md",
    "env.example": ".env.example",
    "gitignore": ".gitignore",
}
FOLDERS = ("courses", "brief/sources", "config", "theme", ".agents")

LANGUAGES = ("es", "en")
BACKENDS = ("creator", "html")
MIRRORS = ("sharepoint", "onedrive", "google-drive", "nextcloud", "folder", "none")
ADDRESS = {"es": ("tu", "usted"), "en": ("you",)}


@dataclass
class Answers:
    name: str
    client: str = ""
    content_language: str = "es"
    ui_language: str = "es"
    tone: str = ""
    address: str = ""
    backend: str = "creator"
    mirror: str = "none"

    def values(self) -> dict[str, str]:
        address = self.address or ADDRESS[self.content_language][0]
        return {
            "name": self.name,
            "client": self.client,
            "content_language": self.content_language,
            "ui_language": self.ui_language,
            "tone": self.tone,
            "address": address,
            "backend": self.backend,
            "mirror": self.mirror,
        }


@dataclass
class Report:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    kept_edited: list[str] = field(default_factory=list)


def _template(name: str) -> str:
    return resources.files("coursekit.templates.project").joinpath(name).read_text(encoding="utf-8")


def render(text: str, values: dict[str, str]) -> str:
    """Replace {key} tokens without touching other braces."""
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return text


def _yaml_values(values: dict[str, str]) -> dict[str, str]:
    """Free-text values as YAML-safe quoted scalars (a name may contain quotes or colons)."""
    free = ("name", "client", "tone")
    return {k: (json.dumps(v, ensure_ascii=False) if k in free else v) for k, v in values.items()}


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_state(root: Path) -> dict:
    path = root / STATE_FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"files": {}}


def _save_state(root: Path, state: dict) -> None:
    path = root / STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def values_from_project(root: Path) -> dict[str, str]:
    """Template values from an existing project.yaml (for --update)."""
    data = yaml.safe_load((root / PROJECT_FILE).read_text(encoding="utf-8")) or {}
    lang = data.get("content_language") or "es"
    return Answers(
        name=str(data.get("name") or root.name),
        client=str(data.get("client") or ""),
        content_language=lang,
        ui_language=data.get("ui_language") or lang,
        tone=str(data.get("tone") or ""),
        address=str(data.get("address") or ""),
        backend=(data.get("assembly") or {}).get("backend") or "creator",
        mirror=(data.get("mirror") or {}).get("provider") or "none",
    ).values()


def create(root: Path, answers: Answers, git: bool = True) -> Report:
    if (root / PROJECT_FILE).exists():
        raise FileExistsError(f"{root / PROJECT_FILE} already exists (use `coursekit init --update`)")
    values = answers.values()
    report = Report()
    state = {"files": {}}
    for folder in FOLDERS:
        (root / folder).mkdir(parents=True, exist_ok=True)
    for template, target in SEED.items():
        path = root / target
        if path.exists():
            report.unchanged.append(target)
            continue
        seed_values = _yaml_values(values) if target.endswith(".yaml") else values
        _write(path, render(_template(template), seed_values))
        report.created.append(target)
    for template, target in MANAGED.items():
        text = render(_template(template), values)
        path = root / target
        if path.exists():
            report.kept_edited.append(target)  # not ours: never overwrite a file we did not write
            continue
        _write(path, text)
        state["files"][target] = _hash(text)
        report.created.append(target)
    _save_state(root, state)
    if git and not (root / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=root, check=False)
    return report


def update(root: Path) -> Report:
    values = values_from_project(root)
    state = _load_state(root)
    report = Report()
    for template, target in MANAGED.items():
        text = render(_template(template), values)
        path = root / target
        recorded = state["files"].get(target)
        if not path.exists():
            _write(path, text)
            state["files"][target] = _hash(text)
            report.created.append(target)
            continue
        current = _hash(path.read_text(encoding="utf-8"))
        if current == _hash(text):
            state["files"][target] = current
            report.unchanged.append(target)
        elif recorded is not None and current == recorded:
            _write(path, text)
            state["files"][target] = _hash(text)
            report.updated.append(target)
        else:
            report.kept_edited.append(target)
    for folder in FOLDERS:
        (root / folder).mkdir(parents=True, exist_ok=True)
    _save_state(root, state)
    return report


def ask(prompt: str, default: str = "", choices: tuple[str, ...] | None = None) -> str:
    hint = f" [{'/'.join(choices)}]" if choices else ""
    shown = f" ({default})" if default else ""
    while True:
        value = input(f"{prompt}{hint}{shown}: ").strip() or default
        if not choices or value in choices:
            return value
        print(f"  choose one of: {', '.join(choices)}", file=sys.stderr)
