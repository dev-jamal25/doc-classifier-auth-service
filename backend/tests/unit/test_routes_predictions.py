from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_prediction_service
from app.api.routers.predictions import router as predictions_router
from app.domain.predictions import Prediction
from tests.unit.fakes import FakePredictionService


def _sample_prediction() -> Prediction:
    return Prediction(
        id=uuid4(),
        batch_id=uuid4(),
        label="memo",
        confidence=0.92,
        top5=[("memo", 0.92), ("invoice", 0.08)],
        overlay_blob_key="overlays/sample.png",
        model_sha256="abc123",
        reviewed_by_user_id=None,
        reviewed_label=None,
        reviewed_at=None,
        request_id=uuid4(),
        created_at=datetime.now(UTC),
    )


def _predictions_app(fake_service: FakePredictionService) -> FastAPI:
    app = FastAPI()
    app.include_router(predictions_router)
    app.dependency_overrides[get_prediction_service] = lambda: fake_service
    return app


@pytest.mark.asyncio
async def test_list_recent_predictions_returns_items_envelope() -> None:
    prediction = _sample_prediction()
    fake = FakePredictionService(predictions=[prediction])
    transport = ASGITransport(app=_predictions_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/predictions/recent")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(prediction.id)


@pytest.mark.asyncio
async def test_list_recent_predictions_passes_limit_to_service() -> None:
    fake = FakePredictionService()
    transport = ASGITransport(app=_predictions_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/predictions/recent", params={"limit": 25})

    assert response.status_code == 200
    assert fake.calls == [{"method": "list_recent", "limit": 25}]


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [0, 999])
async def test_list_recent_predictions_rejects_invalid_limit(limit: int) -> None:
    fake = FakePredictionService()
    transport = ASGITransport(app=_predictions_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/predictions/recent", params={"limit": limit})

    assert response.status_code == 422
