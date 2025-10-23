"""Tiny subset of the `httpx` API tailored for exercising ASGI apps."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlparse


@dataclass
class Response:
    status_code: int
    _body: bytes

    def json(self) -> Any:
        return json.loads(self._body.decode("utf-8"))


class ASGITransport:
    """Dispatches requests directly to an ASGI application."""

    def __init__(self, *, app: Any) -> None:
        self._app = app

    async def request(self, method: str, path: str) -> Response:
        body_chunks: list[bytes] = []
        status: Optional[int] = None

        async def receive() -> Dict[str, Any]:
            await asyncio.sleep(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: Dict[str, Any]) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message.get("status", 500)
            elif message["type"] == "http.response.body":
                body_chunks.append(message.get("body", b""))

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": method.upper(),
            "path": path,
            "headers": [],
        }

        await self._app(scope, receive, send)
        return Response(status or 500, b"".join(body_chunks))


class AsyncClient:
    """Very small async client supporting context management and ``get``."""

    def __init__(self, *, transport: ASGITransport, base_url: str = "") -> None:
        self._transport = transport
        self._base_url = base_url

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        return None

    async def get(self, url: str) -> Response:
        path = self._extract_path(url)
        return await self._transport.request("GET", path)

    def _extract_path(self, url: str) -> str:
        if url.startswith("/"):
            return url
        if self._base_url:
            parsed = urlparse(url)
            if parsed.scheme and parsed.netloc:
                return parsed.path or "/"
            parsed_base = urlparse(self._base_url)
            if not parsed.path:
                return "/"
            return parsed.path
        parsed = urlparse(url)
        return parsed.path or "/"


__all__ = ["ASGITransport", "AsyncClient", "Response"]
