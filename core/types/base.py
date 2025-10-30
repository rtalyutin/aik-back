import re
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema


class PhoneNumber:
    def __init__(self, value: Any):
        """Инициализация с валидацией"""
        self.value = self.validate(value)

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> str:
        if not v:
            raise ValueError("Телефон обязателен")

        # Нормализация для Telegram
        phone = re.sub(r"[^\d+]", "", str(v))

        if phone.startswith("8") and len(phone) == 11:
            phone = "+7" + phone[1:]
        elif phone.startswith("7") and len(phone) == 11:
            phone = "+" + phone
        elif not phone.startswith("+") and len(phone) == 10:
            phone = "+7" + phone

        # Telegram специфичная валидация
        if not re.match(r"^\+[1-9]\d{6,14}$", phone):
            raise ValueError("Телефон должен быть в международном формате")

        return phone

    def __str__(self) -> str:
        return self.value

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Определяет core схему для Pydantic v2"""
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x),
                return_schema=core_schema.str_schema(),
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema_obj, handler):
        """Pydantic v2 метод для модификации JSON схемы"""
        json_schema = handler(core_schema_obj)
        json_schema.update(
            {
                "type": "string",
                "format": "phone",
                "examples": ["+79123456789"],
                "description": "Телефон в международном формате",
            }
        )
        return json_schema
