import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routers.health import router as health_router


def _health_app() -> FastAPI:
    app = FastAPI()
    app.include_router(health_router)
    return app


@pytest.mark.asyncio
async def test_healthz_returns_ok() -> None:
    transport = ASGITransport(app=_health_app())
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
