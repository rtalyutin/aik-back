from __future__ import annotations

from datetime import datetime

import pytest

httpx = pytest.importorskip("httpx")
app_module = pytest.importorskip("app.main")
app = app_module.app


def _decode_headers(raw_headers: tuple[tuple[bytes, bytes], ...]) -> dict[str, str]:
    return {
        name.decode("latin-1").lower(): value.decode("latin-1")
        for name, value in raw_headers
    }


@pytest.mark.asyncio()
async def test_health_endpoint_returns_up_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_s3() -> dict[str, object]:
        return {"status": "up", "latency_ms": 7}

    async def fake_asr() -> dict[str, object]:
        return {"status": "up", "latency_ms": 9, "version": "1.3.2"}

    async def fake_aligner() -> dict[str, object]:
        return {"status": "up", "latency_ms": 11}

    monkeypatch.setattr(app_module, "check_s3", fake_s3)
    monkeypatch.setattr(app_module, "check_asr", fake_asr)
    monkeypatch.setattr(app_module, "check_aligner", fake_aligner)

    async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/v1/health")

    assert response.status_code == 200
    headers = _decode_headers(response.headers)
    assert headers.get("cache-control") == "no-store"
    body = response.json()
    assert body.get("status") == "up"
    assert set(body.get("deps", {})) == {"s3", "asr", "aligner"}
    assert body["deps"]["asr"].get("version") == "1.3.2"

    timestamp = body.get("time")
    assert isinstance(timestamp, str)
    parsed_ts = timestamp.replace("Z", "+00:00")
    datetime.fromisoformat(parsed_ts)


@pytest.mark.asyncio()
async def test_health_endpoint_degraded_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_s3() -> dict[str, object]:
        return {"status": "up", "latency_ms": 5}

    async def fake_asr() -> dict[str, object]:
        return {"status": "degraded", "latency_ms": 12, "error": "High latency"}

    async def fake_aligner() -> dict[str, object]:
        return {"status": "up", "latency_ms": 8}

    monkeypatch.setattr(app_module, "check_s3", fake_s3)
    monkeypatch.setattr(app_module, "check_asr", fake_asr)
    monkeypatch.setattr(app_module, "check_aligner", fake_aligner)

    async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/v1/health")

    assert response.status_code == 503
    body = response.json()
    assert body.get("status") == "degraded"
    assert body["deps"]["asr"].get("error") == "High latency"


@pytest.mark.asyncio()
async def test_health_endpoint_down_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_s3() -> dict[str, object]:
        return {"status": "down", "latency_ms": 30, "error": "timeout"}

    async def fake_asr() -> dict[str, object]:
        return {"status": "up", "latency_ms": 8}

    async def fake_aligner() -> dict[str, object]:
        return {"status": "up", "latency_ms": 9}

    monkeypatch.setattr(app_module, "check_s3", fake_s3)
    monkeypatch.setattr(app_module, "check_asr", fake_asr)
    monkeypatch.setattr(app_module, "check_aligner", fake_aligner)

    async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/v1/health")

    assert response.status_code == 503
    body = response.json()
    assert body.get("status") == "down"
    assert body["deps"]["s3"].get("error") == "timeout"
