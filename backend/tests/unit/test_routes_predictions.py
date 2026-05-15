from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.auth.backend import get_jwt_secrets
from app.api.auth.users import current_active_user
from app.api.deps import get_db_session, get_prediction_service, get_rbac_service
from app.api.routers.predictions import router as predictions_router
from app.db.models import User
from app.domain.errors import PredictionNotFoundError
from app.domain.predictions import Prediction
from app.infra.vault import JwtSecrets
from tests.unit.cache_helpers import init_test_cache
from tests.unit.fakes import FakePredictionService

JWT_SECRETS = JwtSecrets(secret="route-test-secret" * 3, algorithm="HS256", exp_minutes=30)


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


def _sample_user() -> User:
    return User(
        id=uuid4(),
        email="reviewer@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )


class _FakeRBACService:
    def __init__(self, *, allowed: bool = True) -> None:
        self.allowed = allowed

    async def has_permission(self, user_id, obj, act) -> bool:
        return self.allowed


async def _dummy_db_session():
    yield object()


def _predictions_app(
    fake_service: FakePredictionService,
    *,
    allow: bool = True,
    authenticate: bool = True,
) -> FastAPI:
    init_test_cache()
    app = FastAPI()
    app.include_router(predictions_router)
    app.dependency_overrides[get_prediction_service] = lambda: fake_service
    app.dependency_overrides[get_rbac_service] = lambda: _FakeRBACService(allowed=allow)
    app.dependency_overrides[get_db_session] = _dummy_db_session
    app.dependency_overrides[get_jwt_secrets] = lambda: JWT_SECRETS
    if authenticate:
        app.dependency_overrides[current_active_user] = _sample_user
    return app


@pytest.mark.asyncio
async def test_list_recent_predictions_without_token_returns_401() -> None:
    fake = FakePredictionService()
    transport = ASGITransport(app=_predictions_app(fake, authenticate=False))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/predictions/recent")

    assert response.status_code == 401
    assert fake.calls == []


@pytest.mark.asyncio
async def test_list_recent_predictions_forbidden_without_permission() -> None:
    fake = FakePredictionService()
    transport = ASGITransport(app=_predictions_app(fake, allow=False))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/predictions/recent")

    assert response.status_code == 403
    assert fake.calls == []


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
async def test_list_recent_predictions_uses_response_cache_on_second_read() -> None:
    prediction = _sample_prediction()
    fake = FakePredictionService(predictions=[prediction])
    transport = ASGITransport(app=_predictions_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first_response = await client.get("/predictions/recent")
        second_response = await client.get("/predictions/recent")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()
    assert fake.calls == [{"method": "list_recent", "limit": 50}]


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


@pytest.mark.asyncio
async def test_review_prediction_without_token_returns_401() -> None:
    fake = FakePredictionService()
    prediction_id = uuid4()
    transport = ASGITransport(app=_predictions_app(fake, authenticate=False))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.patch(
            f"/predictions/{prediction_id}/review",
            json={"reviewed_label": "invoice"},
        )

    assert response.status_code == 401
    assert fake.calls == []


@pytest.mark.asyncio
async def test_review_prediction_forbidden_without_permission() -> None:
    fake = FakePredictionService()
    prediction_id = uuid4()
    transport = ASGITransport(app=_predictions_app(fake, allow=False))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.patch(
            f"/predictions/{prediction_id}/review",
            json={"reviewed_label": "invoice"},
        )

    assert response.status_code == 403
    assert fake.calls == []


@pytest.mark.asyncio
async def test_review_prediction_with_permission_returns_updated_prediction() -> None:
    prediction_id = uuid4()
    fake = FakePredictionService()
    transport = ASGITransport(app=_predictions_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.patch(
            f"/predictions/{prediction_id}/review",
            json={"reviewed_label": "invoice"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(prediction_id)
    assert body["reviewed_label"] == "invoice"
    assert body["reviewed_by_user_id"] is not None
    assert fake.calls[0]["method"] == "relabel_prediction"
    assert fake.calls[0]["prediction_id"] == prediction_id
    assert fake.calls[0]["reviewed_label"] == "invoice"


@pytest.mark.asyncio
async def test_review_prediction_returns_404_when_prediction_missing() -> None:
    prediction_id = uuid4()
    fake = FakePredictionService(relabel_error=PredictionNotFoundError(prediction_id))
    transport = ASGITransport(app=_predictions_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.patch(
            f"/predictions/{prediction_id}/review",
            json={"reviewed_label": "invoice"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Prediction not found"}


@pytest.mark.asyncio
async def test_review_prediction_rejects_invalid_label() -> None:
    prediction_id = uuid4()
    fake = FakePredictionService()
    transport = ASGITransport(app=_predictions_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.patch(
            f"/predictions/{prediction_id}/review",
            json={"reviewed_label": "not_a_document_label"},
        )

    assert response.status_code == 422
    assert fake.calls == []
