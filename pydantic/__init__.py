"""Minimal subset of the `pydantic` API required for the exercises."""
from __future__ import annotations

import json
from typing import Any, Dict


class BaseModel:
    """Very small stand-in for `pydantic.BaseModel`."""

    def __init__(self, **data: Any) -> None:
        annotations = getattr(self, "__annotations__", {})
        missing = sorted(set(annotations) - set(data))
        if missing:
            raise TypeError(f"Missing fields for {self.__class__.__name__}: {', '.join(missing)}")
        for field, value in data.items():
            setattr(self, field, value)

    def model_dump(self) -> Dict[str, Any]:
        annotations = getattr(self, "__annotations__", {})
        return {field: getattr(self, field) for field in annotations}

    def model_dump_json(self) -> str:
        return json.dumps(self.model_dump())


__all__ = ["BaseModel"]
