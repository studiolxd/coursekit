"""HTTP for every module of coursekit: the User-Agent of the package unless the caller gives its own, a timeout always, retries
only when the caller asks for them (an API that answers 429 or 5xx), and failures as two exceptions, `HttpError` (the server
answered with an error) and `NetworkError` (it could not be reached). Each module turns them into its own message.

The tests stand in for the network by replacing `urllib.request.urlopen`; this module always calls it through the module, so
that replacement reaches it.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from coursekit.util import USER_AGENT

# A User-Agent of a browser, for the pages that refuse the one of a program (the page of a video channel, a web page).
BROWSER = f"Mozilla/5.0 (compatible; {USER_AGENT})"
RETRY_STATUS = frozenset({429, 500, 502, 503, 504})


class HttpError(Exception):
    """The server answered with an error status."""

    def __init__(self, host: str, status: int, reason: str, body: bytes = b"") -> None:
        super().__init__(f"{host}: {status} {reason}")
        self.host, self.status, self.reason, self.body = host, status, reason, body

    def detail(self, size: int = 300) -> str:
        """The start of what the server said, on one line (an API explains its error there)."""
        return self.body.decode("utf-8", "replace")[:size].replace("\n", " ")


class NetworkError(Exception):
    """The address could not be reached: no network, a name that does not resolve, a timeout, an address that is not HTTP."""

    def __init__(self, host: str, reason: Any) -> None:
        super().__init__(f"{host}: {reason}")
        self.host, self.reason = host, reason


@dataclass
class Response:
    status: int
    url: str
    body: bytes
    headers: Any = field(default_factory=dict)  # an email.message.Message: get_content_type(), get(name)


def _request(target: str | urllib.request.Request, data: bytes | None, method: str | None, headers: dict | None,
             agent: str) -> urllib.request.Request:
    req = target if isinstance(target, urllib.request.Request) else urllib.request.Request(target, data=data, method=method)
    for name, value in (headers or {}).items():
        req.add_header(name, value)
    if not req.has_header("User-agent"):
        req.add_header("User-Agent", agent)
    return req


def host_of(target: str | urllib.request.Request) -> str:
    url = target.full_url if isinstance(target, urllib.request.Request) else target
    return urllib.parse.urlsplit(url).hostname or url


def request(target: str | urllib.request.Request, *, data: bytes | None = None, method: str | None = None,
            headers: dict | None = None, timeout: float = 60, agent: str = USER_AGENT, limit: int | None = None,
            retry_waits: Sequence[float] = (), retry_status: frozenset[int] = RETRY_STATUS) -> Response:
    """What an address answers. `limit` reads only the first bytes (the head of a page). With `retry_waits`, an answer in
    `retry_status` is asked again after each wait; only the caller knows whether asking again is safe."""
    req = _request(target, data, method, headers, agent)
    host = host_of(req)
    for attempt in range(len(retry_waits) + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read() if limit is None else resp.read(limit)
                return Response(getattr(resp, "status", 200), getattr(resp, "url", req.full_url) or req.full_url, body,
                                getattr(resp, "headers", {}))
        except urllib.error.HTTPError as exc:
            if exc.code in retry_status and attempt < len(retry_waits):
                time.sleep(retry_waits[attempt])
                continue
            try:
                body = exc.read() or b""
            except Exception:  # noqa: BLE001 — the body of an error is only an explanation
                body = b""
            raise HttpError(host, exc.code, str(exc.reason), body) from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise NetworkError(host, getattr(exc, "reason", exc)) from None
    raise AssertionError("unreachable")  # the loop always returns or raises


def download(url: str, path: Path, *, headers: dict | None = None, timeout: float = 300) -> None:
    """Saves what an address serves in `path`, read in pieces (a SCORM package can be large). On a failure nothing is left."""
    req = _request(url, None, None, headers, USER_AGENT)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, path.open("wb") as out:
            while chunk := resp.read(1 << 20):
                out.write(chunk)
    except urllib.error.HTTPError as exc:
        path.unlink(missing_ok=True)
        raise HttpError(host_of(req), exc.code, str(exc.reason)) from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        path.unlink(missing_ok=True)
        raise NetworkError(host_of(req), getattr(exc, "reason", exc)) from None
