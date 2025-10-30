from typing import Annotated, Optional
import datetime
import uuid

from sqlalchemy import UUID, BigInteger, text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from sqlalchemy.types import TypeDecorator
from pydantic import BaseModel
from typing import Type, Any, List, TypeVar


uuid_pk = Annotated[
    uuid.UUID,
    mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        unique=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    ),
]


unique_bigint = Annotated[int, mapped_column(BigInteger(), unique=True)]
optional_date_time_tz = Annotated[
    Optional[datetime], mapped_column(DateTime(timezone=True))
]

T = TypeVar("T", bound=BaseModel)


class PydanticType(TypeDecorator):
    """Кастомный тип для работы с Pydantic моделями в SQLAlchemy"""

    impl = JSONB  # Базовый тип для хранения в БД

    def __init__(self, model: Type[T], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model

    def process_bind_param(self, value: Optional[T], dialect: Any) -> Optional[dict]:
        if value is None:
            return None
        if not isinstance(value, self.model):
            raise TypeError(f"Ожидается {self.model}, получен {type(value)}")
        return value.model_dump()  # Для Pydantic v2 используйте model_dump()

    def process_result_value(self, value: Optional[dict], dialect: Any) -> Optional[T]:
        if value is None:
            return None
        return self.model.model_validate(
            value
        )  # Для Pydantic v2 используйте model_validate()


class PydanticListType(TypeDecorator):
    """Кастомный тип для работы со списками Pydantic моделей в SQLAlchemy"""

    impl = JSONB  # Базовый тип для хранения в БД

    def __init__(self, model: Type[T], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model

    def process_bind_param(
        self, value: Optional[List[T]], dialect: Any
    ) -> Optional[List[dict]]:
        if value is None:
            return None

        if not isinstance(value, list):
            raise TypeError(f"Ожидается список {self.model}, получен {type(value)}")

        # Сериализуем каждую модель в словарь
        return [item.model_dump() for item in value]

    def process_result_value(
        self, value: Optional[List[dict]], dialect: Any
    ) -> Optional[List[T]]:
        if value is None:
            return None

        # Десериализуем каждый словарь в Pydantic модель
        return [self.model.model_validate(item) for item in value]
