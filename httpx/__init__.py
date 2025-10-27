"""Minimal local implementation of the parts of httpx used in tests."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from types import TracebackType
from typing import Any, ItemsView, TypeVar, overload
from urllib.parse import urlparse

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


_T = TypeVar("_T")


class Headers(Mapping[str, str]):
    """Case-insensitive header mapping compatible with httpx."""

    def __init__(self, items: Iterable[tuple[bytes, bytes]]) -> None:
        self._items = tuple((bytes(name), bytes(value)) for name, value in items)
        self._store = {
            name.decode("latin-1").lower(): value.decode("latin-1")
            for name, value in self._items
        }

    def __getitem__(self, key: str) -> str:
        return self._store[key.lower()]

    def __iter__(self) -> Iterator[str]:
        return iter(self._store)

    def __len__(self) -> int:
        return len(self._store)

    @overload
    def get(self, key: str, default: None = None) -> str | None: ...

    @overload
    def get(self, key: str, default: _T = ...) -> str | _T: ...

    def get(self, key: str, default: _T | None = None) -> str | _T | None:
        return self._store.get(key.lower(), default)

    def items(self) -> ItemsView[str, str]:
        return self._store.items()


@dataclass(slots=True)
class Response:
    """Simplified HTTP response object compatible with the test suite."""

    status_code: int
    raw_headers: tuple[tuple[bytes, bytes], ...]
    content: bytes

    @property
    def headers(self) -> Headers:
        return Headers(self.raw_headers)

    def json(self) -> Any:
        """Parse the JSON response body."""
        return json.loads(self.content.decode("utf-8"))


class AsyncClient:
    """Very small subset of httpx.AsyncClient used for tests."""

    def __init__(
        self,
        *,
        app: Callable[[Scope, Receive, Send], Awaitable[None]] | None = None,
        base_url: str = "",
        timeout: float | None = None,
    ) -> None:
        self._app = app
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def get(
        self, url: str, *, headers: Iterable[tuple[bytes, bytes]] | None = None
    ) -> Response:
        return await self._request("GET", url, headers=headers)

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Iterable[tuple[bytes, bytes]] | None = None,
        body: bytes | None = None,
    ) -> Response:
        path = self._resolve_path(url)
        scope: Scope = {
            "type": "http",
            "http_version": "1.1",
            "method": method.upper(),
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": b"",
            "scheme": "http",
            "headers": list(headers or []),
        }
        body_bytes = body or b""

        message_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        await message_queue.put(
            {"type": "http.request", "body": body_bytes, "more_body": False}
        )
        await message_queue.put({"type": "http.disconnect"})

        async def receive() -> dict[str, Any]:
            return await message_queue.get()

        response_data = ResponseBuilder()

        async def send(message: dict[str, Any]) -> None:
            response_data.consume(message)

        if self._app is None:
            raise RuntimeError("No ASGI app configured for AsyncClient")

        await self._app(scope, receive, send)

        return response_data.build()

    def _resolve_path(self, url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return urlparse(url).path or "/"

        if url.startswith("/"):
            return url

        if not self._base_url:
            return f"/{url}" if not url.startswith("/") else url

        base_path = urlparse(self._base_url).path.rstrip("/")
        if url:
            return f"{base_path}/{url}" if not url.startswith("/") else url
        return base_path or "/"


class ResponseBuilder:
    """Collects ASGI messages and converts them into a Response."""

    def __init__(self) -> None:
        self.status_code = 500
        self.headers: tuple[tuple[bytes, bytes], ...] = ()
        self.body_parts: list[bytes] = []

    def consume(self, message: dict[str, Any]) -> None:
        message_type = message.get("type")
        if message_type == "http.response.start":
            self.status_code = int(message.get("status", 500))
            raw_headers = message.get("headers", [])
            self.headers = tuple(
                (bytes(name), bytes(value)) for name, value in raw_headers
            )
        elif message_type == "http.response.body":
            body = message.get("body", b"")
            if body:
                self.body_parts.append(bytes(body))

    def build(self) -> Response:
        content = b"".join(self.body_parts)
        return Response(
            status_code=self.status_code,
            raw_headers=self.headers,
            content=content,
        )


__all__ = ["AsyncClient", "Response"]
