"""Lightweight FastAPI stub providing just enough features for the kata tests."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Tuple
import json


JSON_HEADERS: Tuple[Tuple[bytes, bytes], ...] = ((b"content-type", b"application/json"),)


@dataclass
class Route:
    method: str
    path: str
    handler: Callable[..., Any]


class FastAPI:
    """A very small subset of the FastAPI interface.

    The implementation only supports synchronous route handlers and is designed
    to facilitate unit testing without relying on the real `fastapi` package.
    """

    def __init__(self, *, title: str | None = None) -> None:
        self.title = title or "FastAPI"
        self._routes: Dict[Tuple[str, str], Route] = {}

    def get(
        self,
        path: str,
        *,
        response_model: type[Any] | None = None,
        summary: str | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a GET route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._routes[("GET", path)] = Route("GET", path, func)
            return func

        return decorator

    async def __call__(
        self,
        scope: Dict[str, Any],
        receive: Callable[[], Awaitable[Dict[str, Any]]],
        send: Callable[[Dict[str, Any]], Awaitable[None]],
    ) -> None:
        if scope.get("type") != "http":
            raise RuntimeError("Only HTTP scopes are supported by the stub.")

        method = scope.get("method", "").upper()
        path = scope.get("path", "")
        route = self._routes.get((method, path))
        if route is None:
            await send({"type": "http.response.start", "status": 404, "headers": []})
            await send(
                {
                    "type": "http.response.body",
                    "body": b"Not Found",
                    "more_body": False,
                }
            )
            return

        result = route.handler()
        body = self._serialise_body(result)
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": list(JSON_HEADERS),
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})

    @staticmethod
    def _serialise_body(result: Any) -> bytes:
        if hasattr(result, "model_dump_json"):
            return result.model_dump_json().encode("utf-8")
        if hasattr(result, "model_dump"):
            return json.dumps(result.model_dump()).encode("utf-8")
        if isinstance(result, (dict, list, str, int, float, bool)):
            return json.dumps(result).encode("utf-8")
        raise TypeError("Unsupported response type for FastAPI stub")


__all__ = ["FastAPI"]
