"""The story bible of a decision-based course: `courses/<CODE>/design/story.md`.

The design agent writes it with the design and the person signs it with the design (`coursekit approve design`). It is
Markdown with a YAML front matter that coursekit reads; the rest is prose for the agents and the people:

    ---
    world: ACME, a mid-sized insurance company in a coastal city, today
    protagonist: {role: new administrative assistant, mission: keep the team's accounts safe during the move to the cloud}
    characters:
      - name: Marta
        role: head of IT security
        personality: calm, direct, dry humour
        speech: short sentences
        look: in her forties, short grey hair, glasses, navy blazer
        expressions: [neutral, worried, satisfied]
        voice: ""                # chosen with the media (one per character)
    ---
    # Story bible — <course title>
    ## World ...  ## Protagonist ...  ## Cast ...  ## Arc ...  ## Simulation map ...
"""

from __future__ import annotations

from pathlib import Path

import yaml

from coursekit.i18n import t

FILE = Path("design") / "story.md"
CHARACTER_KEYS = ("name", "role", "personality", "speech", "look", "expressions", "voice")


def path(course: dict) -> Path:
    return course["_dir"] / FILE


def front_matter(text: str) -> tuple[object, str | None]:
    """(data of the front matter, problem) of a Markdown text."""
    if not text.startswith("---\n"):
        return None, t("story", "no_front_matter")
    end = text.find("\n---", 4)
    if end == -1:
        return None, t("story", "front_matter_not_closed")
    try:
        return yaml.safe_load(text[4:end]), None
    except yaml.YAMLError as exc:
        return None, t("story", "front_matter_not_yaml", problem=getattr(exc, "problem", None) or exc)


def load(course: dict) -> tuple[dict | None, list[str]]:
    """The front matter of the story bible and its problems; (None, [problem]) when it is missing."""
    file = path(course)
    if not file.exists():
        return None, [t("story", "missing", path=FILE.as_posix())]
    data, problem = front_matter(file.read_text(encoding="utf-8"))
    if problem:
        return None, [f"{FILE.as_posix()}: {problem}"]
    if not isinstance(data, dict):
        return None, [f"{FILE.as_posix()}: " + t("story", "not_mapping")]
    problems = []
    for key in ("world", "protagonist", "characters"):
        if not data.get(key):
            problems.append(f"{FILE.as_posix()}: " + t("story", "missing_key", key=key))
    characters = data.get("characters") or []
    if not isinstance(characters, list):
        problems.append(f"{FILE.as_posix()}: " + t("story", "characters_not_list"))
        characters = []
    seen: set[str] = set()
    for i, person in enumerate(characters):
        if not isinstance(person, dict) or not str(person.get("name") or "").strip():
            problems.append(f"{FILE.as_posix()}: " + t("story", "character_without_name", n=i + 1))
            continue
        name = str(person["name"]).strip()
        if name.casefold() in seen:
            problems.append(f"{FILE.as_posix()}: " + t("story", "character_repeated", name=name))
        seen.add(name.casefold())
        for key in sorted(set(person) - set(CHARACTER_KEYS)):
            problems.append(f"{FILE.as_posix()}: " + t("story", "unknown_character_key", name=name, key=key,
                                                       valid=", ".join(CHARACTER_KEYS)))
    return data, problems


def cast(course: dict) -> list[str]:
    """The names of the cast of the story bible of a course, in order (empty without one)."""
    if not path(course).exists():
        return []
    data, _ = load(course)
    return [str(p["name"]).strip() for p in (data or {}).get("characters") or [] if isinstance(p, dict) and p.get("name")]


def canonical(course: dict, name: str) -> str | None:
    """The full name of the cast a speaker refers to: the same name, or the only character whose first name it is
    ("Aisha" for "Aisha Benali"); None when it is not in the cast or is ambiguous."""
    names = cast(course)
    wanted = name.strip().casefold()
    exact = [n for n in names if n.casefold() == wanted]
    if exact:
        return exact[0]
    first = [n for n in names if n.split()[0].casefold() == wanted]
    return first[0] if len(first) == 1 else None


def speakers(course: dict) -> dict:
    """`media.yaml › speakers` of the course: the speakers of the dialogues that get no portrait made for them."""
    from coursekit import config as configmod

    if not course.get("_project"):
        return {}
    return dict(configmod.effective("media", course["_project"], course).value.get("speakers") or {})


def _named(names: object, name: str) -> bool:
    return name.strip().casefold() in {str(n).strip().casefold() for n in names or []}


def is_learner(course: dict, name: str) -> bool:
    """The learner speaking in a dialogue ("Tú", "You", or a name of `speakers › learner`): they have no portrait."""
    from coursekit import course as coursemod

    learner = str(coursemod.tokens(course).get("learner") or "").casefold()
    return name.strip().casefold() == learner or _named(speakers(course).get("learner"), name)


def is_anonymous(course: dict, name: str) -> bool:
    """A speaker that stands for anyone (`speakers › anonymous`: "Person", "Client"): no portrait, not in the cast."""
    return _named(speakers(course).get("anonymous"), name)


def avatar(course: dict, name: str) -> str | None:
    """The image of the brand a speaker is always shown with (`speakers › avatars`: an AI assistant, a mascot), or None."""
    wanted = name.strip().casefold()
    return next((str(path) for who, path in (speakers(course).get("avatars") or {}).items()
                 if str(who).strip().casefold() == wanted and path), None)


def character_names(data: dict | None) -> set[str]:
    """Names of the cast, case-insensitive."""
    return {str(p["name"]).strip().casefold() for p in (data or {}).get("characters") or []
            if isinstance(p, dict) and p.get("name")}
