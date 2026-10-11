"""Simulations of decision-based courses: the `:::scenario` and `:::conversation` directives.

The body of a simulation is YAML with a fixed schema in English (the texts are in the language of the course):

    id: call                       # unique in the course; the content refers to its state as `call.risk`
    title: The support call
    skin: phone                    # optional: the application it happens in (SKINS)
    character: Technician          # conversation: the person you talk to (required)
    objective: U1.2                # or a list: the objectives it practises
    scored: true                   # counts for the grade (default false)
    weight: 2                      # weight of its score among the scored ones (default 1)
    state: {risk: 0, called: false}
    start: begin                   # first scene (default: the first one)
    scenes:
      begin:
        background: <title of a media placeholder>
        layers: [{image: <title>, area: [x, y, w, h], if: "risk > 2"}]
        characters: [{name: Technician, expression: hurried}]
        text: |
          ...
        variants: [{if: "risk >= 4", text: "..."}]
        checkpoint: true           # the learner can come back here (rules › decision_based › rewind)
        choices:
          - {text: "...", goto: leak, effects: {risk: 3}, set: {called: true}, score: -2, feedback: "...", if: "trust >= 2"}
        hotspots:
          - {label: "...", area: [62, 30, 8, 6], goto: note, effects: {risk: 1}, score: 1}
        next: [{if: "risk >= 3", goto: leak}, {goto: calm}]   # moves on by itself (no decision)
      leak:
        text: ...
        ending: bad                # good | mixed | bad
        debriefing: |
          ...

Conditions use code syntax, the same in every language: `risk >= 3 && !called || trust < 2`, with numbers, `true`,
`false`, `+`, `-`, comparisons and parentheses. `effects` add to a variable; `set` gives it a value. Each decision may add or
subtract points (`score`); the grade of a scored simulation is the points of its path over the maximum reachable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import yaml

from coursekit.i18n import t

KINDS = ("scenario", "conversation")
SKINS = ("mail-desktop", "mail-web", "chat-workspace", "messenger", "phone", "browser")
ENDINGS = ("good", "mixed", "bad")
ID_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
VAR_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
OBJECTIVE_RE = re.compile(r"^U\d+\.\d+$")
MAX_STATES = 20000  # states explored per simulation before giving up (a loop that keeps changing the state)
MAX_PATHS = 500  # complete paths listed for the review


class ExpressionError(Exception):
    pass


# ── Conditions ──────────────────────────────────────────────────────────────────────────────

TOKEN_RE = re.compile(r"\s*(?:(\d+(?:\.\d+)?)|([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)|(&&|\|\||==|!=|<=|>=|[<>!()+-]))")


def _tokens(text: str) -> list[tuple[str, object]]:
    out: list[tuple[str, object]] = []
    pos, text = 0, text.strip()
    while pos < len(text):
        m = TOKEN_RE.match(text, pos)
        if not m or m.end() == pos:
            raise ExpressionError(t("simulation", "expr_bad_char", char=text[pos:].strip()[:1], text=text))
        number, name, op = m.groups()
        if number is not None:
            out.append(("num", float(number) if "." in number else int(number)))
        elif name is not None:
            if name in ("true", "false"):
                out.append(("num", name == "true"))
            else:
                out.append(("var", name))
        else:
            out.append(("op", op))
        pos = m.end()
    return out


class _Parser:
    def __init__(self, text: str):
        self.text = text
        self.items = _tokens(text)
        self.i = 0

    def peek(self) -> tuple[str, object] | None:
        return self.items[self.i] if self.i < len(self.items) else None

    def take(self, *ops: str) -> str | None:
        item = self.peek()
        if item and item[0] == "op" and item[1] in ops:
            self.i += 1
            return str(item[1])
        return None

    def parse(self) -> tuple:
        if not self.items:
            raise ExpressionError(t("simulation", "expr_empty"))
        node = self.or_()
        if self.peek() is not None:
            raise ExpressionError(t("simulation", "expr_unexpected", token=self.peek()[1], text=self.text))
        return node

    def or_(self) -> tuple:
        node = self.and_()
        while self.take("||"):
            node = ("||", node, self.and_())
        return node

    def and_(self) -> tuple:
        node = self.not_()
        while self.take("&&"):
            node = ("&&", node, self.not_())
        return node

    def not_(self) -> tuple:
        if self.take("!"):
            return ("!", self.not_())
        return self.compare()

    def compare(self) -> tuple:
        node = self.sum_()
        op = self.take("==", "!=", "<", "<=", ">", ">=")
        if op:
            node = (op, node, self.sum_())
        return node

    def sum_(self) -> tuple:
        node = self.unary()
        while True:
            op = self.take("+", "-")
            if not op:
                return node
            node = (op, node, self.unary())

    def unary(self) -> tuple:
        if self.take("-"):
            return ("neg", self.unary())
        item = self.peek()
        if item is None:
            raise ExpressionError(t("simulation", "expr_incomplete", text=self.text))
        if self.take("("):
            node = self.or_()
            if not self.take(")"):
                raise ExpressionError(t("simulation", "expr_parenthesis", text=self.text))
            return node
        if item[0] == "op":
            raise ExpressionError(t("simulation", "expr_unexpected", token=item[1], text=self.text))
        self.i += 1
        return item


def parse_expression(text: object) -> tuple:
    """The tree of a condition; ExpressionError when it is not valid."""
    if isinstance(text, bool):
        return ("num", text)
    if not isinstance(text, str):
        raise ExpressionError(t("simulation", "expr_not_text", value=text))
    return _Parser(text).parse()


def names(node: tuple) -> set[str]:
    """The variables a condition reads."""
    if node[0] == "var":
        return {str(node[1])}
    if node[0] == "num":
        return set()
    return set().union(*(names(child) for child in node[1:]))


def evaluate(node: tuple, env: dict) -> object:
    kind = node[0]
    if kind == "num":
        return node[1]
    if kind == "var":
        return env.get(str(node[1]), 0)
    if kind == "!":
        return not evaluate(node[1], env)
    if kind == "neg":
        return -evaluate(node[1], env)
    if kind == "&&":
        return bool(evaluate(node[1], env)) and bool(evaluate(node[2], env))
    if kind == "||":
        return bool(evaluate(node[1], env)) or bool(evaluate(node[2], env))
    a, b = evaluate(node[1], env), evaluate(node[2], env)
    return {"==": lambda: a == b, "!=": lambda: a != b, "<": lambda: a < b, "<=": lambda: a <= b, ">": lambda: a > b,
            ">=": lambda: a >= b, "+": lambda: a + b, "-": lambda: a - b}[kind]()


def test(condition: object, env: dict) -> bool:
    return True if condition is None else bool(evaluate(parse_expression(condition), env))


# ── Schema ──────────────────────────────────────────────────────────────────────────────────

TOP_KEYS = {"id", "title", "skin", "character", "objective", "scored", "weight", "state", "start", "scenes", "screen"}
SCENE_KEYS = {"text", "background", "layers", "characters", "variants", "checkpoint", "choices", "hotspots", "next", "ending",
              "debriefing", "expression", "screen"}
CHOICE_KEYS = {"text", "goto", "if", "effects", "set", "score", "feedback"}
HOTSPOT_KEYS = CHOICE_KEYS - {"text"} | {"label", "area", "target"}

# What the screen of each skin shows (`screen` of the simulation, completed by the `screen` of each scene), and the parts of
# it a hotspot can point at (`target`; `<part>:N` counts from 1).
MAIL_KEYS = {"app", "account", "folder", "inbox", "message"}
SCREEN_KEYS = {
    "mail-desktop": MAIL_KEYS, "mail-web": MAIL_KEYS,
    "chat-workspace": {"app", "team", "channel", "channels", "messages"},
    "messenger": {"contact", "status", "messages"},
    "phone": {"caller", "number", "state", "time", "messages"},
    "browser": {"url", "title", "secure", "body"},
}
LIST_KEYS = {"inbox": {"from", "subject", "preview", "time", "unread"}, "messages": {"from", "time", "text", "me"},
             "message": {"from", "address", "to", "subject", "time", "body", "attachments"}}
PHONE_STATES = ("incoming", "call", "sms")
TARGETS = {
    "mail-desktop": ("sender", "address", "subject", "attachment:", "link:", "inbox:"),
    "mail-web": ("sender", "address", "subject", "attachment:", "link:", "inbox:"),
    "chat-workspace": ("message:", "link:"),
    "messenger": ("message:", "link:"),
    "phone": ("caller", "number", "message:", "link:"),
    "browser": ("url", "lock", "link:"),
}


@dataclass
class Simulation:
    kind: str
    id: str
    data: dict
    line: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reached_endings: list[str] = field(default_factory=list)
    max_score: float = 0
    min_score: float = 0
    longest: tuple[int, int] = (0, 0)  # (scenes, decisions) of the longest path
    paths: list[dict] = field(default_factory=list)
    truncated: bool = False

    @property
    def objectives(self) -> list[str]:
        value = self.data.get("objective")
        return [str(v) for v in (value if isinstance(value, list) else [value] if value else [])]

    @property
    def state(self) -> dict:
        return dict(self.data.get("state") or {})

    @property
    def scored(self) -> bool:
        return self.data.get("scored") is True

    def minutes(self, cfg: dict) -> float:
        """Time of the longest path with rules › decision_based › minutes."""
        scenes, decisions = self.longest
        return scenes * float(cfg.get("scene", 0)) + decisions * float(cfg.get("decision", 0)) + float(cfg.get("debriefing", 0))


def _decisions(scene: dict) -> list[dict]:
    return [c for c in (scene.get("choices") or []) if isinstance(c, dict)] + [h for h in (scene.get("hotspots") or [])
                                                                                 if isinstance(h, dict)]


def parse(kind: str, body: list[str], where: str, line: int = 0) -> Simulation:
    """Read and check one simulation (`body`: the lines between `:::<kind>` and `:::`)."""
    sim = Simulation(kind=kind, id="", data={}, line=line)
    err = lambda message, /, **v: sim.errors.append(f"{where}: " + t("simulation", message, **v))  # noqa: E731
    try:
        data = yaml.safe_load("\n".join(body))
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        err("not_yaml", line=(line + 1 + mark.line) if mark else line, problem=getattr(exc, "problem", None) or str(exc))
        return sim
    if not isinstance(data, dict):
        err("not_mapping")
        return sim
    sim.data = data
    sim.id = str(data.get("id") or "")
    for key in sorted(set(data) - TOP_KEYS):
        err("unknown_key", key=key, valid=", ".join(sorted(TOP_KEYS)))
    if not ID_RE.match(sim.id):
        err("bad_id", value=data.get("id"))
    if not str(data.get("title") or "").strip():
        err("missing", key="title")
    if data.get("skin") is not None and data.get("skin") not in SKINS:
        err("bad_skin", value=data.get("skin"), valid=", ".join(SKINS))
    _check_screen(data.get("screen"), data.get("skin"), "screen", err)
    if kind == "conversation" and not str(data.get("character") or "").strip():
        err("missing", key="character")
    for objective in sim.objectives:
        if not OBJECTIVE_RE.match(objective):
            err("bad_objective", value=objective)
    if "scored" in data and not isinstance(data["scored"], bool):
        err("not_bool", key="scored")
    if "weight" in data and (isinstance(data["weight"], bool) or not isinstance(data["weight"], (int, float)) or data["weight"] <= 0):
        err("bad_weight", value=data["weight"])
    state = data.get("state") or {}
    if not isinstance(state, dict):
        err("bad_state")
        state = {}
    for var, value in state.items():
        if not VAR_RE.match(str(var)):
            err("bad_variable", name=var)
        if not isinstance(value, (int, float)):
            err("bad_initial", name=var, value=value)
    scenes = data.get("scenes")
    if not isinstance(scenes, dict) or not scenes:
        err("no_scenes")
        return sim
    for sid, scene in scenes.items():
        _check_scene(str(sid), scene, scenes, state, kind, err, data.get("skin"))
    start = data.get("start", next(iter(scenes)))
    if start not in scenes:
        err("bad_start", scene=start)
        return sim
    if not sim.errors:
        _walk(sim, scenes, str(start), state, err)
        if sim.scored and sim.max_score <= 0:
            err("no_points")
    return sim


def _check_condition(value: object, variables: dict, err, where: str) -> None:
    try:
        node = parse_expression(value)
    except ExpressionError as exc:
        err("bad_condition", place=where, problem=exc)
        return
    for name in sorted(names(node) - set(variables)):
        err("undeclared", place=where, name=name)


def _check_scene(sid: str, scene: object, scenes: dict, state: dict, kind: str, err, skin: object = None) -> None:
    where = f"scenes.{sid}"
    if not ID_RE.match(sid):
        err("bad_scene_id", value=sid)
    if not isinstance(scene, dict):
        err("scene_not_mapping", scene=sid)
        return
    for key in sorted(set(scene) - SCENE_KEYS):
        err("unknown_key", key=f"{where}.{key}", valid=", ".join(sorted(SCENE_KEYS)))
    if not str(scene.get("text") or "").strip():
        err("missing", key=f"{where}.text")
    for i, variant in enumerate(scene.get("variants") or []):
        if not isinstance(variant, dict) or "if" not in variant or not str(variant.get("text") or "").strip():
            err("bad_variant", place=f"{where}.variants[{i}]")
        else:
            _check_condition(variant["if"], state, err, f"{where}.variants[{i}].if")
    for i, layer in enumerate(scene.get("layers") or []):
        if not isinstance(layer, dict) or not str(layer.get("image") or "").strip():
            err("bad_layer", place=f"{where}.layers[{i}]")
            continue
        if "area" in layer:
            _check_area(layer["area"], f"{where}.layers[{i}].area", err)
        if "if" in layer:
            _check_condition(layer["if"], state, err, f"{where}.layers[{i}].if")
    for i, person in enumerate(scene.get("characters") or []):
        if not isinstance(person, dict) or not str(person.get("name") or "").strip():
            err("bad_character", place=f"{where}.characters[{i}]")
    ways = [k for k in ("choices", "hotspots", "next", "ending") if scene.get(k)]
    if "ending" in ways and len(ways) > 1:
        err("ending_and_more", scene=sid)
    elif not ways:
        err("no_way_out", scene=sid)
    if scene.get("ending") is not None:
        if scene["ending"] not in ENDINGS:
            err("bad_ending", scene=sid, value=scene["ending"], valid=", ".join(ENDINGS))
        if not str(scene.get("debriefing") or "").strip():
            err("ending_without_debriefing", scene=sid)
    elif scene.get("debriefing"):
        err("debriefing_without_ending", scene=sid)
    if scene.get("next") and (scene.get("choices") or scene.get("hotspots")):
        err("next_and_decisions", scene=sid)
    for i, choice in enumerate(scene.get("choices") or []):
        _check_decision(choice, f"{where}.choices[{i}]", CHOICE_KEYS, "text", scenes, state, err)
    for i, spot in enumerate(scene.get("hotspots") or []):
        _check_decision(spot, f"{where}.hotspots[{i}]", HOTSPOT_KEYS, "label", scenes, state, err)
        if isinstance(spot, dict):
            if "target" in spot:
                _check_target(spot["target"], skin, f"{where}.hotspots[{i}].target", err)
            else:
                _check_area(spot.get("area"), f"{where}.hotspots[{i}].area", err)
    _check_screen(scene.get("screen"), skin, f"{where}.screen", err)
    for i, step in enumerate(scene.get("next") or []):
        place = f"{where}.next[{i}]"
        if not isinstance(step, dict) or set(step) - {"if", "goto"}:
            err("bad_next", place=place)
            continue
        _check_goto(step.get("goto"), place, scenes, err)
        if "if" in step:
            _check_condition(step["if"], state, err, f"{place}.if")


def _check_screen(screen: object, skin: object, place: str, err) -> None:
    """The `screen` of a skin: only the keys of that skin, lists of mappings with their keys."""
    if screen is None:
        return
    if skin not in SCREEN_KEYS:
        err("screen_without_skin", place=place)
        return
    if not isinstance(screen, dict):
        err("bad_screen", place=place)
        return
    valid = SCREEN_KEYS[skin]
    for key in sorted(set(screen) - valid):
        err("unknown_key", key=f"{place}.{key}", valid=", ".join(sorted(valid)))
    for key in ("inbox", "messages", "channels", "attachments"):
        if key in screen and not isinstance(screen[key], list):
            err("screen_not_list", place=f"{place}.{key}")
    for key in ("inbox", "messages"):
        for i, item in enumerate(screen.get(key) or [] if isinstance(screen.get(key), list) else []):
            if not isinstance(item, dict):
                err("bad_screen", place=f"{place}.{key}[{i}]")
                continue
            for extra in sorted(set(item) - LIST_KEYS[key]):
                err("unknown_key", key=f"{place}.{key}[{i}].{extra}", valid=", ".join(sorted(LIST_KEYS[key])))
    message = screen.get("message")
    if message is not None:
        if not isinstance(message, dict):
            err("bad_screen", place=f"{place}.message")
        else:
            for extra in sorted(set(message) - LIST_KEYS["message"]):
                err("unknown_key", key=f"{place}.message.{extra}", valid=", ".join(sorted(LIST_KEYS["message"])))
    if skin == "phone" and screen.get("state") is not None and screen.get("state") not in PHONE_STATES:
        err("bad_phone_state", place=f"{place}.state", value=screen.get("state"), valid=", ".join(PHONE_STATES))


def _check_target(value: object, skin: object, place: str, err) -> None:
    targets = TARGETS.get(str(skin)) if skin else None
    if targets is None:
        err("target_without_skin", place=place)
        return
    text = str(value or "")
    ok = any(text == t_ if not t_.endswith(":") else (text.startswith(t_) and text[len(t_):].isdigit() and int(text[len(t_):]) > 0)
             for t_ in targets)
    if not ok:
        err("bad_target", place=place, value=value, valid=", ".join(f"{t_}N" if t_.endswith(":") else t_ for t_ in targets))


def _check_area(value: object, place: str, err) -> None:
    if (not isinstance(value, list) or len(value) not in (2, 4)
            or not all(isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 100 for v in value)):
        err("bad_area", place=place)


def _check_goto(target: object, place: str, scenes: dict, err) -> None:
    if not target:
        err("missing", key=f"{place}.goto")
    elif target not in scenes:
        err("unknown_scene", place=place, scene=target)


def _check_decision(item: object, place: str, keys: set, label: str, scenes: dict, state: dict, err) -> None:
    if not isinstance(item, dict):
        err("bad_decision", place=place)
        return
    for key in sorted(set(item) - keys):
        err("unknown_key", key=f"{place}.{key}", valid=", ".join(sorted(keys)))
    if not str(item.get(label) or "").strip():
        err("missing", key=f"{place}.{label}")
    _check_goto(item.get("goto"), place, scenes, err)
    if "if" in item:
        _check_condition(item["if"], state, err, f"{place}.if")
    for key in ("effects", "set"):
        changes = item.get(key) or {}
        if not isinstance(changes, dict):
            err("bad_changes", place=f"{place}.{key}")
            continue
        for var, value in changes.items():
            if var not in state:
                err("undeclared", place=f"{place}.{key}", name=var)
            if not isinstance(value, (int, float)) or (key == "effects" and isinstance(value, bool)):
                err("bad_change_value", place=f"{place}.{key}.{var}", value=value)
    if "score" in item and (isinstance(item["score"], bool) or not isinstance(item["score"], (int, float))):
        err("bad_score", place=place, value=item["score"])


# ── Paths ───────────────────────────────────────────────────────────────────────────────────

def _apply(decision: dict, env: dict) -> dict:
    env = dict(env)
    for var, value in (decision.get("effects") or {}).items():
        env[var] = env.get(var, 0) + value
    env.update(decision.get("set") or {})
    return env


def options(scene: dict, env: dict) -> list[dict]:
    """The decisions the learner sees in a scene with that state."""
    return [d for d in _decisions(scene) if test(d.get("if"), env)]


def _next_states(scene: dict, env: dict) -> list[tuple[str, dict, float, str | None]] | None:
    """Where the learner can go from a scene with that state: (scene, state, points, decision); None at a dead end."""
    if scene.get("next"):
        for step in scene["next"]:
            if test(step.get("if"), env):
                return [(step["goto"], env, 0.0, None)]
        return None
    available = options(scene, env)
    if not available:
        return None
    return [(d["goto"], _apply(d, env), float(d.get("score") or 0), str(d.get("text") or d.get("label"))) for d in available]


def _walk(sim: Simulation, scenes: dict, start: str, state: dict, err) -> None:
    """Every state reachable from the start: unreachable scenes, dead ends, endings and points; then the paths themselves."""
    reached: set[str] = set()
    endings: set[str] = set()
    scores: list[float] = []
    dead: set[str] = set()
    seen: set = set()
    stack = [(start, dict(state), 0.0)]
    while stack:
        sid, env, score = stack.pop()
        key = (sid, tuple(sorted(env.items())), score)
        if key in seen:
            continue
        seen.add(key)
        if len(seen) > MAX_STATES:
            sim.truncated = True
            sim.warnings.append(t("simulation", "too_many_states", id=sim.id, limit=MAX_STATES))
            break
        reached.add(sid)
        scene = scenes[sid]
        if scene.get("ending"):
            endings.add(sid)
            scores.append(score)
            continue
        moves = _next_states(scene, env)
        if moves is None:
            dead.add(sid)
            continue
        stack.extend((target, after, score + points) for target, after, points, _ in moves)
    if not sim.truncated:
        for sid in scenes:
            if sid not in reached:
                err("unreachable", scene=sid)
        if not endings:
            err("no_ending")
    for sid in sorted(dead):
        err("dead_end", scene=sid)
    sim.reached_endings = sorted(endings)
    sim.max_score = max(scores) if scores else 0
    sim.min_score = min(scores) if scores else 0
    _paths(sim, scenes, start, state)


def _paths(sim: Simulation, scenes: dict, start: str, state: dict) -> None:
    """The complete paths, in the order of the decisions (up to MAX_PATHS), and the longest one. A path that comes back to a
    scene with the same state is a loop and is not followed."""
    longest = (0, 0)
    stack = [(start, dict(state), 0.0, (), frozenset())]
    while stack:
        sid, env, score, steps, visited = stack.pop()
        key = (sid, tuple(sorted(env.items())))
        if key in visited:
            continue
        scene = scenes[sid]
        if scene.get("ending"):
            decisions = sum(1 for _, label in steps if label is not None)
            longest = max(longest, (len(steps) + 1, decisions))
            if len(sim.paths) >= MAX_PATHS:
                sim.truncated = True
                break
            sim.paths.append({"steps": list(steps), "ending": sid, "kind": scene["ending"], "score": score, "state": env})
            continue
        moves = _next_states(scene, env) or []
        for target, after, points, label in reversed(moves):
            stack.append((target, after, score + points, steps + ((sid, label),), visited | {key}))
    sim.longest = longest


def grade(sim: Simulation, points: float) -> float:
    """Percentage of a path's points over the maximum reachable (0 when below zero)."""
    return 0.0 if sim.max_score <= 0 else max(0.0, min(100.0, 100.0 * points / sim.max_score))


# ── Adaptive content ────────────────────────────────────────────────────────────────────────

IF_RE = re.compile(r"^:::if\s+(.+?)\s*$")
ELSE_RE = re.compile(r"^:::else\s*$")
OPEN_RE = re.compile(r"^:::([a-z][a-z-]*)\s*$")
CLOSE_RE = re.compile(r"^:::\s*$")


@dataclass
class Conditional:
    line: int
    condition: str
    else_line: int | None = None
    end_line: int | None = None


def scan_conditionals(lines: list[str], start: int = 1) -> tuple[list[Conditional], list[tuple[int, str]]]:
    """The `:::if` blocks of some content (outside code fences and directives) and the problems found:
    (line, message key)."""
    found: list[Conditional] = []
    problems: list[tuple[int, str]] = []
    current: Conditional | None = None
    in_code = in_directive = False
    for i, line in enumerate(lines, start):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if in_directive:
            if CLOSE_RE.match(stripped):
                in_directive = False
            continue
        if IF_RE.match(stripped):
            if current is not None:
                problems.append((i, "nested_if"))
                continue
            current = Conditional(line=i, condition=IF_RE.match(stripped).group(1))
        elif ELSE_RE.match(stripped):
            if current is None:
                problems.append((i, "else_without_if"))
            elif current.else_line is not None:
                problems.append((i, "two_else"))
            else:
                current.else_line = i
        elif CLOSE_RE.match(stripped):
            if current is None:
                problems.append((i, "close_without_open"))
            else:
                current.end_line = i
                if current.else_line is None:
                    problems.append((current.line, "if_without_else"))
                found.append(current)
                current = None
        elif OPEN_RE.match(stripped):
            in_directive = True
    if current is not None:
        problems.append((current.line, "if_not_closed"))
    return found, problems


def adaptive_lines(lines: list[str], start: int = 1) -> set[int]:
    """Line numbers that only some learners see: the `:::if` branch and the fences of the blocks."""
    found, _ = scan_conditionals(lines, start)
    hidden: set[int] = set()
    for block in found:
        last = block.else_line if block.else_line is not None else block.end_line
        hidden.update(range(block.line, (last or block.line) + 1))
        if block.end_line is not None:
            hidden.add(block.end_line)
    return hidden


# ── Media of a simulation ───────────────────────────────────────────────────────────────────

def background_id(description: str) -> str:
    from coursekit.util import slugify

    return "BG-" + slugify(description).upper()


def layer_id(description: str) -> str:
    from coursekit.util import slugify

    return "LAYER-" + slugify(description).upper()


def portrait_id(name: str, expression: object = None) -> str:
    """`CHAR-<NAME>` (the portrait of a character, shared with the dialogues) or `CHAR-<NAME>-<EXPRESSION>`."""
    from coursekit.util import character_asset_id, slugify

    base = character_asset_id(name)
    return f"{base}-{slugify(str(expression), 24).upper()}" if expression else base


def media_refs(data: dict) -> list[dict]:
    """The images a simulation uses, with the id of their asset in the manifest (one per image in the whole course):
    backgrounds `BG-<description>`, layers `LAYER-<description>`, portraits `CHAR-<NAME>` and, with an expression,
    `CHAR-<NAME>-<EXPRESSION>`. Each: {id, kind, description, character, expression}."""
    found: dict[str, dict] = {}

    def add(asset_id: str, kind: str, description: str = "", character: str = "", expression: str = "") -> None:
        found.setdefault(asset_id, {"id": asset_id, "kind": kind, "description": description, "character": character,
                                    "expression": expression})

    def portrait(name: object, expression: object = None) -> None:
        name = str(name or "").strip()
        if not name:
            return
        add(portrait_id(name), "portrait", character=name)
        if expression:
            add(portrait_id(name, expression), "portrait", character=name, expression=str(expression))

    portrait(data.get("character"))
    for scene in (data.get("scenes") or {}).values():
        if not isinstance(scene, dict):
            continue
        if scene.get("background"):
            add(background_id(str(scene["background"])), "background", str(scene["background"]))
        for layer in scene.get("layers") or []:
            if isinstance(layer, dict) and layer.get("image"):
                add(layer_id(str(layer["image"])), "layer", str(layer["image"]))
        for person in scene.get("characters") or []:
            if isinstance(person, dict):
                portrait(person.get("name"), person.get("expression"))
        if data.get("character") and scene.get("expression"):
            portrait(data["character"], scene["expression"])
    return list(found.values())
