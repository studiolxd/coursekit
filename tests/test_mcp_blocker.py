"""Why a session without an interface could not use creator, and the connector of the account."""

import json

from coursekit import agents, launch
from coursekit.cli import main
from coursekit.project import find_project
from tests.test_handoff import Agents, data, project  # noqa: F401 — the fake agents and the empty project


def write_log(path, servers, denied=()):
    events = [{"type": "system", "subtype": "init", "mcp_servers": [{"name": n, "status": s} for n, s in servers.items()]}]
    for tool in denied:
        events.append({"type": "user", "message": {"content": [{
            "type": "tool_result", "is_error": True,
            "content": f"Claude requested permissions to use {tool}, but you haven't granted it yet."}]}})
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    return path


def set_connector(root, name):
    path = root / "project.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace('connector: ""', f'connector: "{name}"'), encoding="utf-8")


def test_the_connector_is_allowed_in_sessions_without_an_interface(project):  # noqa: F811
    assert agents.connector_server(find_project(project)) is None
    set_connector(project, "SLXD Creator Studio LXD")
    key = agents.connector_server(find_project(project))
    assert key == "claude_ai_SLXD_Creator_Studio_LXD"
    agent = launch.Agent("design", "claude", "")
    args = launch.headless_args(agent, "x", project / "last.txt", "slxd-creator", key)
    allowed = args[args.index("--allowedTools") + 1:args.index("--disallowedTools")]
    assert "mcp__slxd-creator" in allowed and "mcp__claude_ai_SLXD_Creator_Studio_LXD" in allowed
    plain = launch.headless_args(agent, "x", project / "last.txt", "slxd-creator")
    assert not any(a.startswith("mcp__claude_ai") for a in plain)


def test_the_name_may_come_with_the_prefix(project):  # noqa: F811
    set_connector(project, "claude.ai SLXD Creator Studio LXD")
    assert agents.connector_server(find_project(project)) == "claude_ai_SLXD_Creator_Studio_LXD"


def test_a_server_that_needs_login_is_named(project, tmp_path):  # noqa: F811
    log = write_log(tmp_path / "a.log", {"slxd-creator": "needs-auth", "runpod": "connected"})
    message = launch.mcp_blocker(find_project(project), log)
    assert "slxd-creator" in message and "needs-auth" in message and "/mcp" in message and "platform.slxd.connector" in message


def test_denied_tools_of_the_account_connector_point_to_the_setting(project, tmp_path):  # noqa: F811
    servers = {"slxd-creator": "needs-auth", "claude.ai SLXD Creator Studio LXD": "connected"}
    log = write_log(tmp_path / "b.log", servers, ["mcp__claude_ai_SLXD_Creator_Studio_LXD__design_matrix_list"])
    message = launch.mcp_blocker(find_project(project), log)
    assert 'platform.slxd.connector: "SLXD Creator Studio LXD"' in message and "not allowed" in message


def test_with_the_connector_set_it_must_be_connected(project, tmp_path):  # noqa: F811
    set_connector(project, "SLXD Creator Studio LXD")
    log = write_log(tmp_path / "c.log", {"slxd-creator": "needs-auth", "claude.ai SLXD Creator Studio LXD": "needs-auth"})
    message = launch.mcp_blocker(find_project(project), log)
    assert "claude.ai SLXD Creator Studio LXD" in message and "needs-auth" in message and "log in" in message
    ok = write_log(tmp_path / "d.log", {"slxd-creator": "needs-auth", "claude.ai SLXD Creator Studio LXD": "connected"})
    assert launch.mcp_blocker(find_project(project), ok) is None  # the connector is the way in: the project server does not matter


def test_a_log_that_says_nothing_has_no_blocker(project, tmp_path):  # noqa: F811
    assert launch.mcp_blocker(find_project(project), write_log(tmp_path / "e.log", {"slxd-creator": "connected"})) is None
    assert launch.mcp_blocker(find_project(project), tmp_path / "missing.log") is None


def test_handoff_stops_with_the_cause_and_the_text_of_the_agent(project, monkeypatch, capsys):  # noqa: F811
    fake = Agents(project, monkeypatch)
    real = fake.execute

    def without_creator(project_, agent, text, headless, log_name):
        code, _, _ = real(project_, agent, text, headless, log_name)
        log = project / "session.log"
        write_log(log, {"slxd-creator": "needs-auth"})
        return code, log, "I could not reach slxd."

    fake.skip["new-course"] = 1  # the agent does nothing: no matrix
    monkeypatch.setattr(launch, "execute", without_creator)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 1
    err = capsys.readouterr().err
    assert "not exported" in err and "Cause: the MCP server \"slxd-creator\" is not authorized" in err


def test_without_a_known_cause_the_agent_words_are_shown(project, monkeypatch, capsys):  # noqa: F811
    fake = Agents(project, monkeypatch)
    real = fake.execute

    def talks(project_, agent, text, headless, log_name):
        code, _, _ = real(project_, agent, text, headless, log_name)
        return code, None, "Nothing was created because the server answered 500."

    fake.skip["new-course"] = 1
    monkeypatch.setattr(launch, "execute", talks)
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD"]) == 1
    assert "The agent said: Nothing was created because the server answered 500." in capsys.readouterr().err


def test_resuming_designs_again_when_the_matrix_was_never_created(project, monkeypatch, capsys):  # noqa: F811
    fake = Agents(project, monkeypatch)
    fake.skip["new-course"] = 1
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD", "--no-pause"]) == 1  # the course exists, no matrix
    assert data(project)["slxd"]["matrix_id"] in (None, "")
    fake.calls.clear()
    assert main(["handoff", "PWD"]) == 0
    assert fake.calls[0] == "new-course"  # not an export of a matrix that does not exist


def test_resuming_only_exports_when_the_matrix_exists_in_slxd(project, monkeypatch, capsys):  # noqa: F811
    fake = Agents(project, monkeypatch)
    fake.skip["new-course"] = 1
    assert main(["handoff", "Contraseñas seguras", "1", "--code", "PWD", "--no-pause"]) == 1
    path = project / "courses" / "PWD" / "course.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("matrix_id: null", "matrix_id: m-1", 1), encoding="utf-8")
    assert "matrix_id: m-1" in path.read_text(encoding="utf-8")
    fake.skip["design-change"] = 1
    fake.calls.clear()
    assert main(["handoff", "PWD"]) == 1
    assert fake.calls == ["design-change"]


def write_events(path, events):
    path.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
    return path


def bash(uid, command):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": uid, "name": "Bash", "input": {"command": command}}]}}


def refused(uid, text="This command requires approval"):
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": uid, "is_error": True, "content": text}]}}


def test_the_programs_a_session_could_not_run_are_named(tmp_path):
    log = write_events(tmp_path / "a.log", [
        {"type": "system", "message": "not a dict"}, ["not", "an", "event"],
        bash("1", "cd /x && vhs --version | head -1"), refused("1"),
        bash("2", "blender -b"), refused("2", "This Bash command contains multiple operations. The parts that require approval: blender"),
        bash("3", "ls /elsewhere"), refused("3", "ls was blocked. only list files in the allowed working directories"),
        bash("4", "coursekit status"),
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "4", "content": "ok"}]}},
    ])
    assert launch.blocked_programs(log) == ["vhs", "blender"]


def test_the_stop_names_the_programs_to_add_to_the_rule(project, tmp_path):  # noqa: F811
    log = write_events(tmp_path / "a.log", [bash("1", "vhs a.tape; blender -b; npx remotion render"), refused("1")])
    message = launch.permission_blocker(find_project(project), log, "media")
    assert "blender" in message and "media_tools" in message and "vhs" not in message and "npx" not in message
    assert "media_tools" not in launch.permission_blocker(find_project(project), log, "writer")


def test_the_media_agent_may_run_what_its_recipes_declare(project):  # noqa: F811
    programs = launch.media_programs(find_project(project))
    assert {"npx", "python3", "vhs"} <= set(programs)
    assert not {"node", "bash", "sh"} & set(programs)
    agent = launch.Agent("media", "claude", "")
    args = launch.headless_args(agent, "x", project / "last.txt", "slxd-creator", None, programs, ["/store/workspaces"])
    allowed = args[args.index("--allowedTools") + 1:args.index("--disallowedTools")]
    assert "Bash(vhs:*)" in allowed and "Bash(npx:*)" in allowed and args[args.index("--add-dir") + 1] == "/store/workspaces"
    other = launch.headless_args(launch.Agent("writer", "claude", ""), "x", project / "last.txt", "slxd-creator", None, programs, ["/s"])
    assert "--add-dir" not in other and "Bash(vhs:*)" not in other


def test_the_rule_adds_programs_to_the_media_agent(project):  # noqa: F811
    path = project / "project.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "\nrules:\n  handoff:\n    media_tools: [blender, bash]\n", encoding="utf-8")
    programs = launch.media_programs(find_project(project))
    assert "blender" in programs and "bash" in programs
