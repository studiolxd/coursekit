"""Layered configuration: package defaults ← project ← course.

Each configuration file has a name (`rules`, `directives`, `media`, `delivery`). Its effective
value is the deep merge, in this order, of:

1. `package`  the defaults shipped with coursekit (`coursekit/defaults/<name>.yaml`);
2. `config`   the project file `config/<name>.yaml`, if any;
3. `project`  the `<name>:` section of `project.yaml`, if any;
4. `course`   the `<name>:` section of the course's `course.yaml`, if a course is given.

Mappings merge key by key; any other value (lists included) replaces the previous one. Every
leaf keeps the layer it came from, so `coursekit config` can say where a value is set.
The personal `.env` is not a configuration layer: it only holds keys, models, local paths and
identity, never production rules (those must be the same for the whole team).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from coursekit.i18n import t
from coursekit.project import Project

NAMES = ("rules", "directives", "media", "delivery")
LAYERS = ("package", "config", "project", "course")


def _read_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data or {}


def package_defaults(name: str) -> dict:
    text = resources.files("coursekit.defaults").joinpath(f"{name}.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text) or {}


@dataclass
class Layered:
    """A merged mapping plus, for every leaf path, the layer that set it."""

    value: dict = field(default_factory=dict)
    origin: dict[tuple, str] = field(default_factory=dict)

    def merge(self, data: dict, layer: str) -> None:
        _merge(self.value, data, layer, (), self.origin)

    def get(self, *path: str, default: Any = None) -> Any:
        node: Any = self.value
        for key in path:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node

    def flat(self) -> list[tuple[str, Any, str]]:
        """(dotted.key, value, layer) for every leaf, in file order."""
        out: list[tuple[str, Any, str]] = []
        _flatten(self.value, (), self.origin, out)
        return out


def _merge(base: dict, data: dict, layer: str, prefix: tuple, origin: dict) -> None:
    for key, new in data.items():
        path = (*prefix, key)
        if isinstance(new, dict) and isinstance(base.get(key), dict):
            _merge(base[key], new, layer, path, origin)
            continue
        # A replaced subtree forgets the origins of what it replaces.
        for stale in [p for p in origin if p[: len(path)] == path]:
            del origin[stale]
        base[key] = _copy(new)
        _mark(new, path, layer, origin)


def _mark(value: Any, path: tuple, layer: str, origin: dict) -> None:
    if isinstance(value, dict) and value:
        for key, child in value.items():
            _mark(child, (*path, key), layer, origin)
    else:
        origin[path] = layer


def _copy(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _copy(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_copy(v) for v in value]
    return value


def _flatten(node: Any, prefix: tuple, origin: dict, out: list) -> None:
    if isinstance(node, dict) and node:
        for key, child in node.items():
            _flatten(child, (*prefix, key), origin, out)
    else:
        out.append((".".join(str(p) for p in prefix), node, origin.get(prefix, "?")))


def project_data(project: Project) -> dict:
    return _read_yaml(project.file) if project.file.exists() else {}


# Keys of a course record's section that hold the course's own state, not overrides of the configuration of the same name
# (`media › voice` is the voice chosen for the course; the configuration's `voice` is the list of providers).
COURSE_STATE = {"media": {"voice"}}


def effective(name: str, project: Project | None = None, course: dict | None = None) -> Layered:
    """The effective configuration `name` for the project (and course, if given)."""
    if name not in NAMES:
        raise ValueError(t("config", "unknown_config", name=name, names=", ".join(NAMES)))
    result = Layered()
    result.merge(package_defaults(name), "package")
    if project is not None:
        config_file = project.config_dir / f"{name}.yaml"
        if config_file.exists():
            result.merge(_read_yaml(config_file), "config")
        section = project_data(project).get(name)
        if isinstance(section, dict):
            result.merge(section, "project")
    if course is not None and isinstance(course.get(name), dict):
        result.merge({k: v for k, v in course[name].items() if k not in COURSE_STATE.get(name, ())}, "course")
    return result
