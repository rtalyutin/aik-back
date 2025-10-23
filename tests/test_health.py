from __future__ import annotations

import unittest

from httpx import ASGITransport, AsyncClient

from app.main import app


class HealthEndpointTest(unittest.IsolatedAsyncioTestCase):
    async def test_health_endpoint_returns_ok_status(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
