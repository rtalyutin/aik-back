# AIK Backend

Базовый каркас backend-сервиса для AI Karaoke с использованием FastAPI.

## Быстрый старт

1. Создайте и активируйте виртуальное окружение (пример для Unix-подобных ОС):

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   Для Windows используйте `.\.venv\\Scripts\\activate`.

2. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```

3. Для установки инструментов разработки выполните:

   ```bash
   pip install -r requirements-dev.txt
   ```

4. Запустите приложение:

   ```bash
   uvicorn app.main:app --reload
   ```

5. Перейдите по адресу [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs), чтобы открыть автогенерируемую документацию FastAPI (Swagger UI).

## Тестирование

После установки зависимостей разработки запустите тесты командой:

```bash
pytest
```
