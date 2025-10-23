"""Minimal ASGI application exposing a health-check endpoint."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    """Handle ASGI requests for the application."""
    if scope.get("type") != "http":
        raise RuntimeError("Unsupported scope type")

    path = scope.get("path", "")
    method = scope.get("method", "").upper()

    if method == "GET" and path == "/health":
        payload = json.dumps({"status": "ok"}).encode()
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(payload)).encode()),
        ]
        await send({"type": "http.response.start", "status": 200, "headers": headers})
        await send({"type": "http.response.body", "body": payload})
        return

    await send({"type": "http.response.start", "status": 404, "headers": []})
    await send({"type": "http.response.body", "body": b""})
