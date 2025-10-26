import pytest

httpx = pytest.importorskip("httpx")
app_module = pytest.importorskip("app.main")
app = app_module.app


# pytest's mark.asyncio decorator lacks precise typing information in 7.x stubs.
# Ignore the mismatch to keep the test coroutine annotation intact.
@pytest.mark.asyncio()  # type: ignore[misc]
async def test_health_endpoint_returns_ok_status() -> None:
    async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body.get("status") == "ok"
