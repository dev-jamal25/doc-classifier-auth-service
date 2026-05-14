from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.audit_log import AuditLogEntry
from app.domain.batches import Batch
from app.domain.enums import AuditAction, BatchSource, BatchState
from app.domain.predictions import Prediction
from app.services.audit_log import AuditLogService
from app.services.batches import BatchService
from app.services.predictions import PredictionService
from tests.unit.fakes import (
    FakeAuditLogRepository,
    FakeBatchRepository,
    FakePredictionRepository,
)


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


def _sample_audit() -> AuditLogEntry:
    return AuditLogEntry(
        id=uuid4(),
        actor_user_id=None,
        action=AuditAction.BATCH_STATE_CHANGE,
        target_type="batch",
        target_id=uuid4(),
        before_value=None,
        after_value={"state": "completed"},
        request_id=uuid4(),
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_list_batches_delegates_to_repository() -> None:
    first = _sample_batch()
    second = _sample_batch(state=BatchState.COMPLETED)
    repo = FakeBatchRepository(batches=[first, second])
    service = BatchService(repo)

    result = await service.list_batches(limit=25, offset=10)

    assert result == [first, second]
    assert repo.calls == [{"method": "list", "limit": 25, "offset": 10, "state": None}]


@pytest.mark.asyncio
async def test_list_batches_passes_state_filter() -> None:
    repo = FakeBatchRepository(batches=[])
    service = BatchService(repo)

    await service.list_batches(state=BatchState.FAILED)

    assert repo.calls[0]["state"] == BatchState.FAILED


@pytest.mark.asyncio
async def test_get_batch_returns_domain_model() -> None:
    batch = _sample_batch()
    repo = FakeBatchRepository(batch_by_id={batch.id: batch})
    service = BatchService(repo)

    result = await service.get_batch(batch.id)

    assert result is batch
    assert repo.calls == [{"method": "get", "batch_id": batch.id}]


@pytest.mark.asyncio
async def test_get_batch_returns_none_when_missing() -> None:
    missing_id = uuid4()
    repo = FakeBatchRepository()
    service = BatchService(repo)

    result = await service.get_batch(missing_id)

    assert result is None
    assert repo.calls == [{"method": "get", "batch_id": missing_id}]


@pytest.mark.asyncio
async def test_list_recent_predictions_delegates_to_repository() -> None:
    prediction = _sample_prediction()
    prediction_repo = FakePredictionRepository(recent=[prediction])
    service = PredictionService(
        prediction_repo,
        FakeBatchRepository(),
        AuditLogService(FakeAuditLogRepository()),
    )

    result = await service.list_recent(limit=10)

    assert result == [prediction]
    assert prediction_repo.calls == [{"method": "list_recent", "limit": 10}]


@pytest.mark.asyncio
async def test_list_audit_entries_delegates_to_repository() -> None:
    entry = _sample_audit()
    repo = FakeAuditLogRepository(entries=[entry])
    service = AuditLogService(repo)

    result = await service.list_entries(limit=20, offset=5)

    assert result == [entry]
    assert repo.calls == [{"method": "list", "limit": 20, "offset": 5}]
