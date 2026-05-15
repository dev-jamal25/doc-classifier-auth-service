from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.auth.backend import get_jwt_secrets
from app.api.auth.users import current_active_user
from app.api.deps import get_batch_service, get_db_session, get_rbac_service
from app.api.routers.batches import router as batches_router
from app.db.models import User
from app.domain.batches import Batch
from app.domain.enums import BatchSource, BatchState
from app.infra.vault import JwtSecrets
from tests.unit.cache_helpers import init_test_cache
from tests.unit.fakes import FakeBatchService

JWT_SECRETS = JwtSecrets(secret="route-test-secret" * 3, algorithm="HS256", exp_minutes=30)


def _sample_batch(*, state: BatchState = BatchState.PENDING) -> Batch:
    now = datetime.now(UTC)
    return Batch(
        id=uuid4(),
        source_filename="scan_001.tif",
        source=BatchSource.SFTP_INGEST,
        sftp_user="vendor-1",
        blob_key="batches/2026/05/14/scan_001.tif",
        state=state,
        failure_reason=None,
        request_id=uuid4(),
        created_by_user_id=None,
        created_at=now,
        updated_at=now,
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
        self.calls: list[dict] = []

    async def has_permission(self, user_id, obj, act) -> bool:
        self.calls.append({"user_id": user_id, "obj": obj, "act": act})
        return self.allowed


async def _dummy_db_session():
    yield object()


def _batches_app(
    fake_service: FakeBatchService,
    *,
    allow: bool = True,
    authenticate: bool = True,
    rbac_service: _FakeRBACService | None = None,
) -> FastAPI:
    init_test_cache()
    app = FastAPI()
    app.include_router(batches_router)
    app.dependency_overrides[get_batch_service] = lambda: fake_service
    app.dependency_overrides[get_rbac_service] = lambda: (
        rbac_service or _FakeRBACService(allowed=allow)
    )
    app.dependency_overrides[get_db_session] = _dummy_db_session
    app.dependency_overrides[get_jwt_secrets] = lambda: JWT_SECRETS
    if authenticate:
        app.dependency_overrides[current_active_user] = _sample_user
    return app


@pytest.mark.asyncio
async def test_list_batches_without_token_returns_401() -> None:
    fake = FakeBatchService()
    transport = ASGITransport(app=_batches_app(fake, authenticate=False))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/batches")

    assert response.status_code == 401
    assert fake.calls == []


@pytest.mark.asyncio
async def test_list_batches_forbidden_without_permission() -> None:
    fake = FakeBatchService()
    rbac = _FakeRBACService(allowed=False)
    transport = ASGITransport(app=_batches_app(fake, rbac_service=rbac))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/batches")

    assert response.status_code == 403
    assert fake.calls == []
    assert rbac.calls[0]["obj"] == "batches"
    assert rbac.calls[0]["act"] == "read"


@pytest.mark.asyncio
async def test_list_batches_returns_items_envelope() -> None:
    first = _sample_batch()
    second = _sample_batch(state=BatchState.COMPLETED)
    fake = FakeBatchService(batches=[first, second])
    transport = ASGITransport(app=_batches_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/batches")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["items"][0]["id"] == str(first.id)
    assert body["items"][1]["id"] == str(second.id)


@pytest.mark.asyncio
async def test_list_batches_passes_query_params_to_service() -> None:
    fake = FakeBatchService()
    transport = ASGITransport(app=_batches_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/batches",
            params={"state": "failed", "limit": 10, "offset": 5},
        )

    assert response.status_code == 200
    assert fake.calls == [
        {
            "method": "list_batches",
            "limit": 10,
            "offset": 5,
            "state": BatchState.FAILED,
        }
    ]


@pytest.mark.asyncio
async def test_list_batches_uses_response_cache_on_second_read() -> None:
    first = _sample_batch()
    fake = FakeBatchService(batches=[first])
    transport = ASGITransport(app=_batches_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first_response = await client.get("/batches")
        second_response = await client.get("/batches")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()
    assert fake.calls == [{"method": "list_batches", "limit": 50, "offset": 0, "state": None}]


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [0, 999])
async def test_list_batches_rejects_invalid_limit(limit: int) -> None:
    fake = FakeBatchService()
    transport = ASGITransport(app=_batches_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/batches", params={"limit": limit})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_batch_returns_item_when_found() -> None:
    batch = _sample_batch()
    fake = FakeBatchService(batch_by_id={batch.id: batch})
    transport = ASGITransport(app=_batches_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/batches/{batch.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(batch.id)
    assert fake.calls == [{"method": "get_batch", "batch_id": batch.id}]


@pytest.mark.asyncio
async def test_get_batch_uses_response_cache_on_second_read() -> None:
    batch = _sample_batch()
    fake = FakeBatchService(batch_by_id={batch.id: batch})
    transport = ASGITransport(app=_batches_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first_response = await client.get(f"/batches/{batch.id}")
        second_response = await client.get(f"/batches/{batch.id}")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()
    assert fake.calls == [{"method": "get_batch", "batch_id": batch.id}]


@pytest.mark.asyncio
async def test_get_batch_returns_404_when_missing() -> None:
    batch_id = uuid4()
    fake = FakeBatchService()
    transport = ASGITransport(app=_batches_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/batches/{batch_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Batch not found"}
    assert fake.calls == [{"method": "get_batch", "batch_id": batch_id}]
