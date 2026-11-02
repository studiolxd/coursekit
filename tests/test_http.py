import io
import urllib.error
import urllib.request

import pytest

from coursekit import http
from coursekit.util import USER_AGENT


class Answer(io.BytesIO):
    status = 200
    url = "https://api.example/final"
    headers: dict = {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def error(code, body=b""):
    return urllib.error.HTTPError("https://api.example/x", code, "Too Many", {}, io.BytesIO(body))


def answering(monkeypatch, *outcomes):
    """urlopen gives each outcome in turn (an exception is raised); the requests are kept."""
    seen, queue = [], list(outcomes)

    def urlopen(req, timeout=None):
        seen.append((req, timeout))
        outcome = queue.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return Answer(outcome)

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    return seen


def test_a_request_carries_the_user_agent_of_the_package_and_a_timeout(monkeypatch):
    seen = answering(monkeypatch, b"hello")
    resp = http.request("https://api.example/x", timeout=12)
    assert resp.body == b"hello" and resp.status == 200 and resp.url == "https://api.example/final"
    req, timeout = seen[0]
    assert req.get_header("User-agent") == USER_AGENT and timeout == 12


def test_the_caller_can_give_its_own_agent_and_a_request_already_made(monkeypatch):
    seen = answering(monkeypatch, b"a", b"b")
    http.request("https://site.example", agent=http.BROWSER)
    http.request(urllib.request.Request("https://site.example", headers={"User-Agent": "mine"}))
    assert seen[0][0].get_header("User-agent") == http.BROWSER
    assert seen[1][0].get_header("User-agent") == "mine"


def test_no_retry_unless_asked(monkeypatch):
    seen = answering(monkeypatch, error(503))
    with pytest.raises(http.HttpError) as exc:
        http.request("https://api.example/x")
    assert exc.value.status == 503 and len(seen) == 1


def test_retries_wait_between_attempts_and_give_up_with_the_last_error(monkeypatch):
    waits = []
    monkeypatch.setattr("time.sleep", waits.append)
    answering(monkeypatch, error(429), error(500), b"done")
    assert http.request("https://api.example/x", retry_waits=(2, 8)).body == b"done"
    assert waits == [2, 8]
    waits.clear()
    answering(monkeypatch, error(429), error(429), error(429, b'{"error":\n "slow down"}'))
    with pytest.raises(http.HttpError) as exc:
        http.request("https://api.example/x", retry_waits=(1, 1))
    assert exc.value.status == 429 and exc.value.detail() == '{"error":  "slow down"}' and waits == [1, 1]


def test_an_error_status_outside_the_retry_list_is_not_retried(monkeypatch):
    seen = answering(monkeypatch, error(401))
    with pytest.raises(http.HttpError):
        http.request("https://api.example/x", retry_waits=(1,))
    assert len(seen) == 1


def test_an_unreachable_address_is_a_network_error_with_the_host(monkeypatch):
    answering(monkeypatch, urllib.error.URLError("no route"))
    with pytest.raises(http.NetworkError) as exc:
        http.request("https://down.example/x")
    assert exc.value.host == "down.example" and exc.value.reason == "no route"


def test_limit_reads_only_the_start(monkeypatch):
    answering(monkeypatch, b"0123456789")
    assert http.request("https://site.example", limit=4).body == b"0123"


def test_a_failed_download_leaves_no_file(monkeypatch, tmp_path):
    target = tmp_path / "package.zip.part"
    answering(monkeypatch, b"PK" + b"x" * 10)
    http.download("https://cdn.example/p.zip", target)
    assert target.read_bytes().startswith(b"PK")
    answering(monkeypatch, error(404))
    with pytest.raises(http.HttpError):
        http.download("https://cdn.example/p.zip", target)
    assert not target.exists()
