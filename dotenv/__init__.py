"""Stub implementation for `python-dotenv`."""
from __future__ import annotations

from pathlib import Path

def load_dotenv(path: str | None = None, *, override: bool | None = None) -> bool:
    """Pretend to load environment variables from a `.env` file.

    The function searches for the file relative to the provided *path* or the
    current working directory and returns ``True`` if the file exists. No
    environment variables are mutated; the stub merely mirrors the success flag
    of the real implementation to keep application code predictable in offline
    environments.
    """

    candidate = Path(path) if path else Path.cwd() / ".env"
    return candidate.exists()


__all__ = ["load_dotenv"]
