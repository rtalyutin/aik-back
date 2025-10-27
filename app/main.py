"""ASGI application exposing the health-check endpoint for AIK services."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

import boto3
from botocore.config import Config as BotoConfig

import httpx

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


def _truncate(error_message: str, limit: int = 240) -> str:
    """Return a truncated representation of ``error_message`` if necessary."""

    if len(error_message) <= limit:
        return error_message
    return f"{error_message[:limit]}...(+truncated)"


def _timeout_seconds() -> float:
    timeout_ms = int(os.getenv("HEALTH_TIMEOUT_MS", "1500"))
    return max(timeout_ms, 1) / 1000


async def check_s3() -> dict[str, Any]:
    """Validate access to the configured S3 bucket."""

    start = perf_counter()
    bucket = os.getenv("S3_BUCKET")
    region = os.getenv("S3_REGION", "us-east-1")
    endpoint = os.getenv("S3_ENDPOINT")
    access_key = os.getenv("S3_ACCESS_KEY")
    secret_key = os.getenv("S3_SECRET_KEY")

    if not bucket:
        latency = int((perf_counter() - start) * 1000)
        return {
            "status": "down",
            "latency_ms": latency,
            "error": _truncate("S3_BUCKET is not configured"),
        }

    def _head_bucket() -> None:
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=BotoConfig(
                s3={"addressing_style": "path"}, retries={"max_attempts": 1}
            ),
        )
        client.head_bucket(Bucket=bucket)

    try:
        await asyncio.wait_for(asyncio.to_thread(_head_bucket), _timeout_seconds())
        latency = int((perf_counter() - start) * 1000)
        return {"status": "up", "latency_ms": latency}
    except Exception as exc:  # pragma: no cover - exercised in tests via mocking
        latency = int((perf_counter() - start) * 1000)
        return {
            "status": "down",
            "latency_ms": latency,
            "error": _truncate(str(exc)),
        }


async def _check_http_service(name: str, url: str | None) -> dict[str, Any]:
    """Perform a health check for an HTTP dependency."""

    start = perf_counter()
    if not url:
        latency = int((perf_counter() - start) * 1000)
        return {
            "status": "down",
            "latency_ms": latency,
            "error": _truncate(f"{name} URL is not configured"),
        }

    try:
        async with httpx.AsyncClient(timeout=_timeout_seconds()) as client:
            response = await client.get(url)
        latency = int((perf_counter() - start) * 1000)

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        version = None
        if isinstance(payload, dict):
            version = payload.get("version")
            status_hint = payload.get("status")
        else:
            status_hint = None

        version = version or response.headers.get("X-Service-Version")
        normalized_hint = (
            status_hint.lower()
            if isinstance(status_hint, str)
            and status_hint.lower() in {"up", "down", "degraded"}
            else None
        )

        if normalized_hint:
            status = normalized_hint
        else:
            status = "up" if response.status_code == 200 else "down"

        details: dict[str, Any] = {"status": status, "latency_ms": latency}

        if version:
            details["version"] = str(version)

        if status != "up":
            error_value: Any | None = None
            if isinstance(payload, dict):
                error_value = payload.get("error")
            if error_value:
                details["error"] = _truncate(str(error_value))
            elif response.status_code >= 400:
                details["error"] = _truncate(f"HTTP {response.status_code}")

        return details
    except Exception as exc:  # pragma: no cover - exercised in tests via mocking
        latency = int((perf_counter() - start) * 1000)
        return {
            "status": "down",
            "latency_ms": latency,
            "error": _truncate(str(exc)),
        }


async def check_asr() -> dict[str, Any]:
    """Check the ASR service health."""

    return await _check_http_service("asr", os.getenv("ASR_URL"))


async def check_aligner() -> dict[str, Any]:
    """Check the aligner service health."""

    return await _check_http_service("aligner", os.getenv("ALIGNER_URL"))


async def _health_payload() -> tuple[int, list[tuple[bytes, bytes]], bytes]:
    """Assemble the health payload and HTTP metadata."""

    timestamp = datetime.now(UTC).isoformat()

    s3_result, asr_result, aligner_result = await asyncio.gather(
        check_s3(),
        check_asr(),
        check_aligner(),
    )

    dependencies = {"s3": s3_result, "asr": asr_result, "aligner": aligner_result}
    critical = ("s3", "asr", "aligner")
    any_issue = any(dependencies[name]["status"] != "up" for name in critical)

    status = "up" if not any_issue else "down"

    body = {
        "status": status,
        "time": timestamp,
        "deps": dependencies,
    }

    payload = json.dumps(body, ensure_ascii=False).encode()
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(payload)).encode()),
        (b"cache-control", b"no-store"),
    ]
    http_status = 200 if status == "up" else 503
    return http_status, headers, payload


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    """Handle ASGI requests for the application."""

    if scope.get("type") != "http":
        raise RuntimeError("Unsupported scope type")

    path = scope.get("path", "")
    method = scope.get("method", "").upper()

    if method == "GET" and path == "/v1/health":
        status_code, headers, payload = await _health_payload()
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": headers,
            }
        )
        await send({"type": "http.response.body", "body": payload})
        return

    await send({"type": "http.response.start", "status": 404, "headers": []})
    await send({"type": "http.response.body", "body": b""})
