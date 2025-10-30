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

## 🐇 Setup for local start
1. Create `.env` file from `.env.dist` and fill it.
2. Create `password.txt` in `db` folder and fill it.
3. Run `docker compose up --build -d db redis`
4. Install dependencies with `uv sync`
5. Create `.venv` with `uv venv --seed`
6. Activate virtual environment with `source .venv/bin/activate`
7. Run migrations with `uv run alembic upgrade head`

## How To?

### Run migrations
```shell
uv run alembic upgrade head
```

### Generate new migration
```shell
uv run alembic revision -m "<migration_name>"
```
