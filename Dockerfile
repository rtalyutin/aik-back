# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.13.3
FROM python:${PYTHON_VERSION}-slim as builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY ./pyproject.toml /app/pyproject.toml
COPY ./uv.lock /app/uv.lock
RUN uv sync --frozen --no-install-project


# Copy the source code into the container.
COPY . .

# Sync the project
RUN uv sync --frozen

EXPOSE 8000

# Run the application.
CMD ["uv", "run", "python", "-m", "api"]
