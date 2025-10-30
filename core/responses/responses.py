from pydantic import BaseModel
from typing import Optional, List, Any, Generic, TypeVar

# Объявляем обобщенный тип T
T = TypeVar("T")


class BaseDataResponse(BaseModel, Generic[T]):
    data: T

    class Config:
        arbitrary_types_allowed = True


class BaseListDataResponse(BaseModel, Generic[T]):
    data: List[T]

    class Config:
        arbitrary_types_allowed = True


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None
