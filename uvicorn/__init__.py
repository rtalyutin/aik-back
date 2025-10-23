"""Stub module exposing a `run` helper compatible with the real `uvicorn`."""
from __future__ import annotations

from typing import Any


def run(app: Any, host: str = "127.0.0.1", port: int = 8000, **_: Any) -> None:
    """Simulate starting the ASGI server.

    The function simply prints an informational message so manual invocation
    mirrors the original development workflow without starting a network
    service.
    """

    print(f"[uvicorn] Serving {app!r} on {host}:{port}")


__all__ = ["run"]
