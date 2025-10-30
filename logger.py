import logging
import logging.config
from typing import Optional

from pythonjsonlogger import jsonlogger

from config import Config


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Кастомный JSON форматтер с поддержкой tracing"""

    def __init__(self, *args, service_name: str = "unknown", **kwargs):
        super().__init__(*args, **kwargs)
        self.service_name = service_name

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        # Добавляем имя сервиса (api/background)
        log_record["service"] = self.service_name

        # Переименовываем поля для удобства
        if "levelname" in log_record:
            log_record["level"] = log_record.pop("levelname")
        if "name" in log_record:
            log_record["logger"] = log_record.pop("name")

        # Добавляем trace_id, если есть (для distributed tracing)
        if hasattr(record, "trace_id"):
            log_record["trace_id"] = record.trace_id

        # Добавляем span_id, если есть
        if hasattr(record, "span_id"):
            log_record["span_id"] = record.span_id

        # Добавляем request_id, если есть
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id


def _get_log_level(level_str: str) -> int:
    """Преобразует строку уровня логирования в константу logging"""
    return getattr(logging, level_str.upper(), logging.INFO)


def setup_logging(config: Config, service_name: Optional[str] = None) -> None:
    """
    Настройка логирования для приложения.

    Args:
        config: Объект конфигурации Pydantic
        service_name: Имя сервиса (api, background, etc.).
                     Если не указано, берется из config.SERVICE_NAME
    """
    # Определяем уровень логирования приложения
    if config.LOG_LEVEL:
        # Если явно указан уровень в конфиге
        logging_level = _get_log_level(config.LOG_LEVEL)
    else:
        # Иначе используем DEBUG/INFO в зависимости от режима
        logging_level = logging.DEBUG if config.DEBUG else logging.INFO

    # Определяем имя сервиса
    if service_name is None:
        service_name = config.SERVICE_NAME

    # Получаем уровни для внешних библиотек из конфига
    critical_libs_level = _get_log_level(config.LOG_LEVEL_CRITICAL_LIBS)
    noisy_libs_level = _get_log_level(config.LOG_LEVEL_NOISY_LIBS)
    info_libs_level = _get_log_level(config.LOG_LEVEL_INFO_LIBS)
    debug_libs_level = _get_log_level(config.LOG_LEVEL_DEBUG_LIBS)

    # Специальный уровень для access логов
    access_log_level = logging.INFO if not config.DEBUG else logging.DEBUG

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": CustomJsonFormatter,
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                    "service_name": service_name,
                },
                "console": {
                    "format": "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "json" if not config.DEBUG else "console",
                    "stream": "ext://sys.stdout",
                }
            },
            # Root logger - все логи идут через него
            "root": {"handlers": ["console"], "level": logging_level},
            # Переопределяем только уровни для специфичных логгеров
            "loggers": {
                # ============================================================
                # Web Framework & ASGI Server (INFO_LIBS)
                # ============================================================
                "uvicorn": {
                    "level": info_libs_level,
                },
                "uvicorn.access": {
                    "level": access_log_level,
                },
                "uvicorn.error": {
                    "level": info_libs_level,
                },
                "fastapi": {
                    "level": info_libs_level,
                },
                "starlette": {
                    "level": noisy_libs_level,  # Много внутренних логов
                },
                # ============================================================
                # Database & ORM (NOISY_LIBS)
                # ============================================================
                "sqlalchemy.engine": {
                    "level": noisy_libs_level,  # SQL запросы
                },
                "sqlalchemy.pool": {
                    "level": noisy_libs_level,  # Connection pool events
                },
                "sqlalchemy.dialects": {
                    "level": noisy_libs_level,
                },
                "sqlalchemy.orm": {
                    "level": noisy_libs_level,
                },
                "alembic": {
                    "level": info_libs_level,  # Миграции важны
                },
                "alembic.runtime.migration": {
                    "level": info_libs_level,
                },
                # ============================================================
                # Telegram Libraries
                # ============================================================
                "telethon": {
                    "level": noisy_libs_level,  # Много технических логов
                },
                "telethon.network": {
                    "level": critical_libs_level,  # Только критичные ошибки сети
                },
                "telethon.client": {
                    "level": noisy_libs_level,
                },
                "aiogram": {
                    "level": info_libs_level,
                },
                "aiogram.event": {
                    "level": noisy_libs_level,  # Много событий
                },
                # ============================================================
                # HTTP & Network (INFO_LIBS / NOISY_LIBS)
                # ============================================================
                "aiohttp": {
                    "level": info_libs_level,
                },
                "aiohttp.access": {
                    "level": noisy_libs_level,
                },
                "aiohttp.client": {
                    "level": info_libs_level,
                },
                "urllib3": {
                    "level": noisy_libs_level,
                },
                "httpx": {
                    "level": info_libs_level,
                },
                "httpcore": {
                    "level": noisy_libs_level,
                },
                # ============================================================
                # Auth & Security (DEBUG_LIBS)
                # ============================================================
                "passlib": {
                    "level": debug_libs_level,
                },
                "jose": {
                    "level": debug_libs_level,
                },
                # ============================================================
                # DI & Framework (DEBUG_LIBS)
                # ============================================================
                "dishka": {
                    "level": debug_libs_level,  # DI контейнер
                },
                # ============================================================
                # Python Standard Library (DEBUG_LIBS)
                # ============================================================
                "asyncio": {
                    "level": debug_libs_level,
                },
                # ============================================================
                # Application Loggers (используют основной уровень)
                # ============================================================
                "application": {
                    "level": logging_level,
                },
                "application.job_matcher": {
                    "level": logging_level,
                },
                "application.tg": {
                    "level": logging_level,
                },
                "core": {
                    "level": logging_level,
                },
                "core.auth": {
                    "level": logging_level,
                },
                "core.database": {
                    "level": logging_level,
                },
                "core.notifier": {
                    "level": logging_level,
                },
            },
        }
    )

    # Логируем старт с информацией о конфигурации
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "service": service_name,
            "debug_mode": config.DEBUG,
            "log_level": logging.getLevelName(logging_level),
            "critical_libs_level": logging.getLevelName(critical_libs_level),
            "noisy_libs_level": logging.getLevelName(noisy_libs_level),
            "info_libs_level": logging.getLevelName(info_libs_level),
            "debug_libs_level": logging.getLevelName(debug_libs_level),
        },
    )
