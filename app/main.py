"""ASGI application exposing a /v1/health endpoint with dependency checks."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from urllib import request
from urllib.error import HTTPError

import boto3
from botocore.config import Config as BotoConfig

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]

_TIME_LIMIT_MS = int(os.getenv("HEALTH_TIMEOUT_MS", "1500"))
_TIME_LIMIT_S = _TIME_LIMIT_MS / 1000.0
_S3_ENDPOINT = os.getenv("S3_ENDPOINT")
_S3_REGION = os.getenv("S3_REGION", "us-east-1")
_S3_BUCKET = os.getenv("S3_BUCKET")
_S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
_S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
_ASR_URL = os.getenv("ASR_URL")
_ALIGNER_URL = os.getenv("ALIGNER_URL")
_ERROR_LIMIT = 240


def _truncate_error(message: str) -> str:
    """Limit error messages to a safe length."""
    if len(message) <= _ERROR_LIMIT:
        return message
    return f"{message[:_ERROR_LIMIT]}...(+truncated)"


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")  # noqa: UP017


async def check_s3() -> dict[str, Any]:
    """Check that the configured S3 bucket is reachable."""
    start = perf_counter()

    if not _S3_BUCKET or not _S3_ENDPOINT:
        latency = int((perf_counter() - start) * 1000)
        return {
            "status": "down",
            "latency_ms": latency,
            "error": _truncate_error("S3 configuration is incomplete"),
        }

    def _head_bucket() -> None:
        client = boto3.client(
            "s3",
            endpoint_url=_S3_ENDPOINT,
            region_name=_S3_REGION,
            aws_access_key_id=_S3_ACCESS_KEY,
            aws_secret_access_key=_S3_SECRET_KEY,
            config=BotoConfig(
                connect_timeout=_TIME_LIMIT_S,
                read_timeout=_TIME_LIMIT_S,
                retries={"max_attempts": 1},
                s3={"addressing_style": "path"},
            ),
        )
        client.head_bucket(Bucket=_S3_BUCKET)

    try:
        await asyncio.wait_for(asyncio.to_thread(_head_bucket), timeout=_TIME_LIMIT_S)
        latency = int((perf_counter() - start) * 1000)
        return {"status": "up", "latency_ms": latency}
    except Exception as exc:  # noqa: BLE001 - surface dependency issues directly
        latency = int((perf_counter() - start) * 1000)
        return {
            "status": "down",
            "latency_ms": latency,
            "error": _truncate_error(str(exc)),
        }


def _read_http_response(url: str) -> tuple[int, dict[str, str], bytes]:
    """Perform a blocking GET request and return status, headers and body."""
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=_TIME_LIMIT_S) as response:  # type: ignore[call-arg]
            status_code = int(response.status)
            headers = {k.lower(): v for k, v in response.headers.items()}
            body = response.read()
    except HTTPError as exc:  # HTTP errors include the payload and headers
        status_code = int(exc.code)
        headers = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
        body = exc.read()
    return status_code, headers, body


async def check_http_dependency(name: str, url: str | None) -> dict[str, Any]:
    """Check an HTTP dependency and normalise its status payload."""
    start = perf_counter()
    if not url:
        latency = int((perf_counter() - start) * 1000)
        return {
            "status": "down",
            "latency_ms": latency,
            "error": _truncate_error(f"{name.upper()} URL is not configured"),
        }

    try:
        status_code, headers, payload = await asyncio.wait_for(
            asyncio.to_thread(_read_http_response, url),
            timeout=_TIME_LIMIT_S,
        )
    except Exception as exc:  # noqa: BLE001 - propagate dependency failure details
        latency = int((perf_counter() - start) * 1000)
        return {
            "status": "down",
            "latency_ms": latency,
            "error": _truncate_error(str(exc)),
        }

    latency = int((perf_counter() - start) * 1000)
    data: dict[str, Any] | None = None
    if payload:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            data = None

    remote_status = (data or {}).get("status") if isinstance(data, dict) else None
    normalised_status = "up"
    if isinstance(remote_status, str) and remote_status.lower() in {"down", "degraded"}:
        normalised_status = remote_status.lower()
    elif status_code != 200:
        normalised_status = "down"

    result: dict[str, Any] = {"status": normalised_status, "latency_ms": latency}

    version: str | None = None
    if isinstance(data, dict):
        version_value = data.get("version")
        if isinstance(version_value, str) and version_value:
            version = version_value
    if not version:
        header_version = headers.get("x-service-version")
        if header_version:
            version = header_version
    if version:
        result["version"] = version

    error_text: str | None = None
    if normalised_status != "up":
        if isinstance(data, dict):
            for key in ("error", "detail", "message"):
                value = data.get(key)
                if isinstance(value, str) and value:
                    error_text = value
                    break
        if not error_text and status_code >= 400:
            error_text = f"HTTP {status_code}"
    if error_text:
        result["error"] = _truncate_error(error_text)

    return result


async def check_asr() -> dict[str, Any]:
    """Check the ASR service health endpoint."""
    return await check_http_dependency("asr", _ASR_URL)


async def check_aligner() -> dict[str, Any]:
    """Check the aligner service health endpoint."""
    return await check_http_dependency("aligner", _ALIGNER_URL)


async def _collect_dependency_status() -> dict[str, dict[str, Any]]:
    """Run dependency checks concurrently."""
    s3_task = asyncio.create_task(check_s3())
    asr_task = asyncio.create_task(check_asr())
    aligner_task = asyncio.create_task(check_aligner())
    s3_result, asr_result, aligner_result = await asyncio.gather(
        s3_task, asr_task, aligner_task
    )
    return {"s3": s3_result, "asr": asr_result, "aligner": aligner_result}


def _derive_overall_status(dependencies: dict[str, dict[str, Any]]) -> str:
    """Aggregate dependency statuses into the overall service status."""
    critical = ("s3", "asr", "aligner")
    statuses = [dependencies[name]["status"] for name in critical]
    if any(status == "down" for status in statuses):
        return "down"
    if any(status == "degraded" for status in statuses):
        return "degraded"
    return "up"


async def _send_health_response(send: Send) -> None:
    """Build the health response and send it via the ASGI interface."""
    dependencies = await _collect_dependency_status()
    overall_status = _derive_overall_status(dependencies)
    response_body = json.dumps(
        {"status": overall_status, "time": _utc_now_iso(), "deps": dependencies},
        ensure_ascii=False,
    ).encode("utf-8")

    status_code = 200 if overall_status == "up" else 503
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(response_body)).encode("ascii")),
        (b"cache-control", b"no-store"),
    ]

    await send(
        {"type": "http.response.start", "status": status_code, "headers": headers}
    )
    await send({"type": "http.response.body", "body": response_body})


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    """Handle ASGI requests for the application."""
    if scope.get("type") != "http":
        raise RuntimeError("Unsupported scope type")

    path = scope.get("path", "")
    method = scope.get("method", "").upper()

    if method == "GET" and path == "/v1/health":
        await _send_health_response(send)
        return

    await send({"type": "http.response.start", "status": 404, "headers": []})
    await send({"type": "http.response.body", "body": b""})
