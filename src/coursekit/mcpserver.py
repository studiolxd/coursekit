"""A minimal MCP server over stdio (JSON-RPC 2.0, one message per line), with no dependency.

It answers what an agent needs to use tools: `initialize`, `tools/list`, `tools/call` and `ping`; notifications get no answer.
A tool is a function that takes the arguments of the call and returns a list of contents (`text(...)`, `image(...)`); a
`ToolError` it raises becomes a result with `isError`, which the model reads, and never ends the server.
"""

from __future__ import annotations

import base64
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import IO, Any

PROTOCOL = "2025-06-18"


class ToolError(Exception):
    pass


@dataclass
class Tool:
    name: str
    description: str
    schema: dict
    run: Callable[[dict], list[dict]]


def text(value: str) -> dict:
    return {"type": "text", "text": value}


def image(data: bytes, mime: str = "image/png") -> dict:
    return {"type": "image", "data": base64.b64encode(data).decode("ascii"), "mimeType": mime}


def schema(properties: dict | None = None, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": properties or {}, "required": required or [], "additionalProperties": False}


class Server:
    def __init__(self, name: str, version: str, tools: list[Tool], instructions: str = ""):
        self.name, self.version, self.instructions = name, version, instructions
        self.tools = {tool.name: tool for tool in tools}

    def handle(self, message: dict) -> dict | None:
        """The answer to one message (None for a notification)."""
        method, ident = message.get("method"), message.get("id")
        if ident is None:
            return None
        try:
            result = self._dispatch(method, message.get("params") or {})
        except _RpcError as exc:
            return {"jsonrpc": "2.0", "id": ident, "error": {"code": exc.code, "message": str(exc)}}
        return {"jsonrpc": "2.0", "id": ident, "result": result}

    def _dispatch(self, method: str | None, params: dict) -> dict:
        if method == "initialize":
            info = {"protocolVersion": params.get("protocolVersion") or PROTOCOL, "capabilities": {"tools": {}},
                    "serverInfo": {"name": self.name, "version": self.version}}
            if self.instructions:
                info["instructions"] = self.instructions
            return info
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [{"name": t.name, "description": t.description, "inputSchema": t.schema} for t in self.tools.values()]}
        if method == "tools/call":
            tool = self.tools.get(str(params.get("name")))
            if tool is None:
                raise _RpcError(-32602, f"unknown tool: {params.get('name')}")
            try:
                return {"content": tool.run(dict(params.get("arguments") or {})), "isError": False}
            except ToolError as exc:
                return {"content": [text(str(exc))], "isError": True}
            except Exception as exc:  # noqa: BLE001 — a fault of the tool is told to the agent, never a server that dies
                import traceback

                traceback.print_exc(file=sys.stderr)  # the AI tool keeps the log of the server
                return {"content": [text(f"internal error of {tool.name}: {type(exc).__name__}: {exc}")], "isError": True}
        raise _RpcError(-32601, f"method not found: {method}")

    def serve(self, stdin: IO[str] = sys.stdin, stdout: IO[str] = sys.stdout) -> None:
        for line in stdin:
            if not line.strip():
                continue
            try:
                message: Any = json.loads(line)
            except ValueError:
                answer = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
            else:
                answer = self.handle(message) if isinstance(message, dict) else None
            if answer is not None:
                stdout.write(json.dumps(answer, ensure_ascii=False) + "\n")
                stdout.flush()


class _RpcError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
