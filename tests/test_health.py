from __future__ import annotations

import asyncio
from datetime import datetime

import pytest

httpx = pytest.importorskip("httpx")
app_module = pytest.importorskip("app.main")
app = app_module.app


@pytest.mark.asyncio()
async def test_health_endpoint_all_dependencies_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def stub_s3() -> dict[str, object]:
        await asyncio.sleep(0)
        return {"status": "up", "latency_ms": 12}

    async def stub_asr() -> dict[str, object]:
        await asyncio.sleep(0)
        return {"status": "up", "latency_ms": 17, "version": "1.2.3"}

    async def stub_aligner() -> dict[str, object]:
        await asyncio.sleep(0)
        return {"status": "up", "latency_ms": 21, "version": "0.9.5"}

    monkeypatch.setattr(app_module, "check_s3", stub_s3)
    monkeypatch.setattr(app_module, "check_asr", stub_asr)
    monkeypatch.setattr(app_module, "check_aligner", stub_aligner)

    async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/v1/health")

    assert response.status_code == 200
    headers = response.headers
    if isinstance(headers, tuple):
        header_map = {key.decode(): value.decode() for key, value in headers}
    else:  # pragma: no cover - exercised when using a real HTTP transport
        header_map = {key.lower(): value for key, value in headers.items()}

    assert header_map.get("cache-control") == "no-store"

    payload = response.json()
    assert payload["status"] == "up"
    assert payload["deps"] == {
        "s3": {"status": "up", "latency_ms": 12},
        "asr": {"status": "up", "latency_ms": 17, "version": "1.2.3"},
        "aligner": {"status": "up", "latency_ms": 21, "version": "0.9.5"},
    }

    # Ensure the timestamp is ISO-8601 compatible
    datetime.fromisoformat(payload["time"])


@pytest.mark.asyncio()
async def test_health_endpoint_returns_503_on_critical_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def stub_s3() -> dict[str, object]:
        return {
            "status": "down",
            "latency_ms": 42,
            "error": app_module._truncate("a" * 400),
        }

    async def stub_asr() -> dict[str, object]:
        return {"status": "up", "latency_ms": 10}

    async def stub_aligner() -> dict[str, object]:
        return {"status": "up", "latency_ms": 15}

    monkeypatch.setattr(app_module, "check_s3", stub_s3)
    monkeypatch.setattr(app_module, "check_asr", stub_asr)
    monkeypatch.setattr(app_module, "check_aligner", stub_aligner)

    async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/v1/health")

    assert response.status_code == 503

    payload = response.json()
    assert payload["status"] == "down"
    assert payload["deps"]["s3"]["status"] == "down"
    assert payload["deps"]["s3"]["latency_ms"] == 42
    assert payload["deps"]["s3"]["error"].endswith("...(+truncated)")


@pytest.mark.asyncio()
async def test_health_endpoint_handles_degraded_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def stub_s3() -> dict[str, object]:
        return {"status": "up", "latency_ms": 11}

    async def stub_asr() -> dict[str, object]:
        return {"status": "degraded", "latency_ms": 30, "error": "capacity"}

    async def stub_aligner() -> dict[str, object]:
        return {"status": "up", "latency_ms": 12}

    monkeypatch.setattr(app_module, "check_s3", stub_s3)
    monkeypatch.setattr(app_module, "check_asr", stub_asr)
    monkeypatch.setattr(app_module, "check_aligner", stub_aligner)

    async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/v1/health")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "down"
    assert payload["deps"]["asr"]["status"] == "degraded"


def test_truncate_utility_trims_long_messages() -> None:
    message = "x" * 300
    truncated = app_module._truncate(message, limit=120)
    assert truncated.startswith("x" * 120)
    assert truncated.endswith("...(+truncated)")
