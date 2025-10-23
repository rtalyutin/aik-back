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
