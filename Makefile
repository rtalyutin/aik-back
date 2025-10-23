.PHONY: format lint typecheck check

format:
	black .
	ruff format .

lint:
	ruff check .

format-check:
	black --check .
	ruff format --check .

lint-fix:
	ruff check --fix .

typecheck:
	mypy .

check: format-check lint typecheck
