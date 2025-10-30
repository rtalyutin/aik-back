import traceback
from typing import Optional, Any

from pydantic import BaseModel, ConfigDict


class ExceptionData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    exc: Exception
    exc_type: str
    traceback: str

    @classmethod
    def make_exception_data(cls, exc: Exception) -> "ExceptionData":
        return cls(
            exc=exc,
            exc_type=type(exc).__name__,
            traceback="".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            ),
        )


class BaseError(Exception):
    status_code: int = 400
    code: str = "base_error"
    message: str = "Base error"
    details: Optional[Any] = None

    def __init__(
        self,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[Any] = None,
    ):
        if status_code:
            self.status_code = status_code
        if code:
            self.code = code
        if message:
            self.message = message
        if details:
            self.details = details
        if status_code:
            self.status_code = status_code
        super().__init__(self.message)
