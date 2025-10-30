# Конфигурация логирования

## Переменные окружения

### Основные параметры

- `DEBUG` - режим отладки (true/false). В режиме отладки логи выводятся в текстовом формате, иначе в JSON
- `SERVICE_NAME` - имя сервиса (api, background). Добавляется во все логи
- `LOG_LEVEL` - основной уровень логирования приложения (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Уровни для внешних библиотек

- `LOG_LEVEL_CRITICAL_LIBS` - для критичных библиотек (default: ERROR)
  - telethon.network - сетевые ошибки Telegram
  
- `LOG_LEVEL_NOISY_LIBS` - для шумных библиотек (default: WARNING)
  - sqlalchemy.* - SQL запросы и ORM
  - telethon - основные логи Telegram клиента
  - starlette - внутренние логи веб-фреймворка
  - aiohttp.access, urllib3, httpcore - HTTP клиенты
  
- `LOG_LEVEL_INFO_LIBS` - для информативных библиотек (default: INFO)
  - uvicorn, fastapi - веб-сервер и API
  - alembic - миграции БД
  - aiogram - Telegram бот
  - aiohttp, httpx - HTTP клиенты
  
- `LOG_LEVEL_DEBUG_LIBS` - для отладочных библиотек (default: WARNING)
  - dishka - DI контейнер
  - asyncio - асинхронность
  - passlib, jose - криптография и JWT

## Примеры конфигурации

### Production (минимум логов)

```bash
DEBUG=false
LOG_LEVEL=INFO
LOG_LEVEL_CRITICAL_LIBS=ERROR
LOG_LEVEL_NOISY_LIBS=WARNING
LOG_LEVEL_INFO_LIBS=INFO
LOG_LEVEL_DEBUG_LIBS=WARNING
```