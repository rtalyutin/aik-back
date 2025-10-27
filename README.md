# aik-back

mvp back ai караоке

## Внесение изменений

### Ветвление

- Для новых возможностей используйте ветки вида `feature/<краткое-описание>`.
- Для исправлений используйте ветки вида `bugfix/<краткое-описание>`.
- Каждая задача оформляется отдельной веткой от актуальной `main`.

### Pull Request и ревью

- Любые изменения проходят через Pull Request, прямые пуши в `main` запрещены.
- Перед merge необходимо минимум два подтверждения (approve). Для малых команд (≤3 разработчиков) достаточно одного подтверждения.

## Настройка инструментов качества

1. Установите зависимости для разработки:

   ```bash
   pip install -r requirements-dev.txt
   ```

2. Установите git-хуки:

   ```bash
   pre-commit install
   ```

3. При необходимости обновите хуки до актуальных версий:

   ```bash
   pre-commit autoupdate
   ```

### Локальные проверки перед Pull Request

В проекте настроены git-хуки через [pre-commit](https://pre-commit.com/). Они автоматически запускают форматирование `black`, линтер `ruff`, статическую типизацию `mypy` и тесты `pytest` при каждом коммите.

Перед созданием PR выполните полный набор проверок вручную:

```bash
pre-commit run --all-files
pytest
pip-audit -r requirements.txt -r requirements-dev.txt
```

`pip-audit` запускает проверку зависимостей (SCA) и использует базу уязвимостей PyPI. Если найдены проблемы, обновите пакет до безопасной версии или зафиксируйте исключение (см. документацию инструмента).

### Инструменты SAST/SCA

- **Ruff** и **mypy** анализируют код на потенциальные ошибки до выполнения.
- **pip-audit** проверяет зависимости на известные уязвимости. Он также интегрирован в `pre-commit` как ручной хук: выполните `pre-commit run pip-audit --all-files` для проверки перед релизом.

### CI/CD

В CI запускаются линтер `ruff`, статическая типизация `mypy`, проверка форматирования `black --check` и тесты `pytest`. Только после успешного прохождения всех этапов возможен merge изменений.

### Полезные ссылки

- [pre-commit](https://pre-commit.com/)
- [Ruff](https://docs.astral.sh/ruff/)
- [Mypy](https://mypy.readthedocs.io/en/stable/)
- [Black](https://black.readthedocs.io/en/stable/)
- [Pytest](https://docs.pytest.org/en/stable/)
- [pip-audit](https://pypi.org/project/pip-audit/)

## Тесты

```bash
pytest
```

## API

### `GET /v1/health`

Возвращает агрегированный статус критичных зависимостей (S3, ASR, Aligner).

- Ответ `200 OK`, если все зависимости в состоянии `up`.
- Ответ `503 Service Unavailable`, если хотя бы одна зависимость в состоянии `down` или `degraded`.

```json
{
  "status": "up",
  "time": "2025-10-27T00:00:00Z",
  "deps": {
    "s3": { "status": "up", "latency_ms": 12 },
    "asr": { "status": "up", "latency_ms": 41, "version": "1.3.2" },
    "aligner": { "status": "up", "latency_ms": 37, "version": "0.9.5" }
  }
}
```

Ответ содержит `latency_ms` для каждой проверки, усечённые сообщения об ошибках и, если сервис их сообщает, `version`.
