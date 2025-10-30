from functools import lru_cache
from typing import final, List

import enum

from pydantic import PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE_NAME = ".env"


class JobMatcherLLMType(enum.Enum):
    dummy = "dummy"


@final
class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE_NAME, extra="ignore")

    DEBUG: bool = False
    API_PORT: int = 8000

    # ============================================================
    # Logging Configuration
    # ============================================================
    SERVICE_NAME: str = "unknown"  # Переопределяется в точках входа
    LOG_LEVEL: str | None = (
        None  # Опционально: переопределение уровня логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    )

    # Уровни логирования для внешних библиотек (можно переопределить через ENV)
    LOG_LEVEL_CRITICAL_LIBS: str = (
        "ERROR"  # Критичные библиотеки (telethon.network, etc.)
    )
    LOG_LEVEL_NOISY_LIBS: str = (
        "WARNING"  # Шумные библиотеки (sqlalchemy, telethon, starlette, etc.)
    )
    LOG_LEVEL_INFO_LIBS: str = (
        "INFO"  # Информативные библиотеки (alembic, aiogram, fastapi, etc.)
    )
    LOG_LEVEL_DEBUG_LIBS: str = (
        "WARNING"  # Отладочные библиотеки (dishka, asyncio, etc.)
    )

    ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:8000",
        "http://localhost:5173",
    ]

    # Postgres
    POSTGRES_DSN: PostgresDsn | None = None
    # Redis
    REDIS_DSN: RedisDsn | None = None

    TG_BOT_TOKEN: str
    TG_CHANNEL_ID: int

    JOB_MATCHER_LLM: JobMatcherLLMType = JobMatcherLLMType.dummy
    JOB_MATCHER_MIN_SCORE_FOR_RECOMMENDED_MATCH: int = 7
    JOB_MATCHER_MIN_SCORE_FOR_DUPLICATE: int = 7

    AUTH_BASE_LOGIN: str = "admin"
    AUTH_BASE_PASSWORD_HASH: str = (
        "$2a$12$4VLEFdgXE91AvPdM4nw3PuyhaBa74JBHi6RoOGnIEhXLIrTPuSlXm"  # admin_pass
    )
    AUTH_JWT_SECRET: str = "x1rm1hyx4lo81x34z1nesctrjmvbigve"
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # S3 Configuration
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY_ID: str = "minioadmin"
    S3_SECRET_ACCESS_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "aik-back"
    S3_REGION: str = "us-east-1"
    S3_SECURE: bool = False


@lru_cache
def get_config() -> Config:
    return Config()  # type: ignore
