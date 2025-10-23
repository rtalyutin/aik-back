"""FastAPI application entry point."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .api.routes.jobs import router as jobs_router
from .api.routes.webhooks import router as webhooks_router
from .core.config import get_settings
from .db import init_db

settings = get_settings()

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(jobs_router)
app.include_router(webhooks_router)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialise database and persist OpenAPI specification."""

    await init_db()
    openapi_schema = app.openapi()
    output_path = Path("app/static/openapi.json")
    output_path.write_text(json.dumps(openapi_schema, indent=2))
    logger.info("OpenAPI schema written to %s", output_path)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning("Validation error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error for %s", request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/health", tags=["system"])
async def healthcheck() -> dict[str, Any]:
    """Simple healthcheck endpoint."""

    return {"status": "ok"}
