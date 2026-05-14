from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_batch_service
from app.api.routers.batches import router as batches_router
from app.domain.batches import Batch
from app.domain.enums import BatchSource, BatchState
from tests.unit.fakes import FakeBatchService


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


def _batches_app(fake_service: FakeBatchService) -> FastAPI:
    app = FastAPI()
    app.include_router(batches_router)
    app.dependency_overrides[get_batch_service] = lambda: fake_service
    return app


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
async def test_get_batch_returns_404_when_missing() -> None:
    batch_id = uuid4()
    fake = FakeBatchService()
    transport = ASGITransport(app=_batches_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/batches/{batch_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Batch not found"}
    assert fake.calls == [{"method": "get_batch", "batch_id": batch_id}]
