from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.domain.audit_log import AuditLogEntry
from app.domain.batches import Batch
from app.domain.enums import AuditAction, BatchSource, BatchState
from app.domain.errors import BatchAlreadyCompletedError, BatchNotFoundError
from app.domain.predictions import Prediction
from app.services.batches import BatchService
from app.services.cache import ServiceCacheInvalidator
from app.services.predictions import PredictionService


class _SpyInvalidator(ServiceCacheInvalidator):
    def __init__(self) -> None:
        self.batches_list_calls = 0
        self.batch_detail_calls: list[UUID] = []
        self.predictions_recent_calls = 0

    async def invalidate_batches_list(self) -> None:
        self.batches_list_calls += 1

    async def invalidate_batch_detail(self, batch_id: UUID) -> None:
        self.batch_detail_calls.append(batch_id)

    async def invalidate_predictions_recent(self) -> None:
        self.predictions_recent_calls += 1


class _FakeTxn:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class _FakeSession:
    def begin(self) -> _FakeTxn:
        return _FakeTxn()


def _sample_batch(*, state: BatchState = BatchState.PENDING, batch_id: UUID | None = None) -> Batch:
    now = datetime.now(UTC)
    return Batch(
        id=batch_id or uuid4(),
        source_filename="scan_001.tif",
        source=BatchSource.SFTP_INGEST,
        sftp_user="vendor-1",
        blob_key="batches/2026/05/13/scan_001.tif",
        state=state,
        failure_reason=None,
        request_id=uuid4(),
        created_by_user_id=None,
        created_at=now,
        updated_at=now,
    )


def _sample_prediction(batch_id: UUID) -> Prediction:
    return Prediction(
        id=uuid4(),
        batch_id=batch_id,
        label="memo",
        confidence=0.92,
        top5=[
            ("memo", 0.92),
            ("invoice", 0.03),
            ("letter", 0.02),
            ("form", 0.02),
            ("budget", 0.01),
        ],
        overlay_blob_key="overlays/sample.png",
        model_sha256="abc123",
        reviewed_by_user_id=None,
        reviewed_label=None,
        reviewed_at=None,
        request_id=uuid4(),
        created_at=datetime.now(UTC),
    )


def _sample_audit(batch_id: UUID) -> AuditLogEntry:
    return AuditLogEntry(
        id=uuid4(),
        actor_user_id=None,
        action=AuditAction.BATCH_STATE_CHANGE,
        target_type="batch",
        target_id=batch_id,
        before_value=None,
        after_value={"state": "completed"},
        request_id=uuid4(),
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_create_from_sftp_drop_inserts_pending_batch_and_invalidates_list() -> None:
    created_batch = _sample_batch(state=BatchState.PENDING)
    repo = SimpleNamespace(create=AsyncMock(return_value=created_batch))
    cache = _SpyInvalidator()
    service = BatchService(repo, cache)

    request_id = uuid4()
    result = await service.create_from_sftp_drop(
        blob_key="batches/2026/05/13/scan_001.tif",
        source_filename="scan_001.tif",
        sftp_user="vendor-1",
        request_id=request_id,
    )

    assert result.id == created_batch.id
    repo.create.assert_awaited_once_with(
        source_filename="scan_001.tif",
        source=BatchSource.SFTP_INGEST,
        sftp_user="vendor-1",
        blob_key="batches/2026/05/13/scan_001.tif",
        state=BatchState.PENDING,
        failure_reason=None,
        request_id=request_id,
        created_by_user_id=None,
    )
    assert cache.batches_list_calls == 1


@pytest.mark.asyncio
async def test_create_failed_batch_calls_repo_and_invalidates_list() -> None:
    failed_batch = _sample_batch(state=BatchState.FAILED)
    repo = SimpleNamespace(create_failed=AsyncMock(return_value=failed_batch))
    cache = _SpyInvalidator()
    service = BatchService(repo, cache)

    request_id = uuid4()
    result = await service.create_failed_batch(
        source_filename="broken.tif",
        sftp_user=None,
        request_id=request_id,
        failure_reason="invalid_image",
    )

    assert result.state == BatchState.FAILED
    repo.create_failed.assert_awaited_once_with(
        source_filename="broken.tif",
        sftp_user=None,
        request_id=request_id,
        failure_reason="invalid_image",
    )
    assert cache.batches_list_calls == 1


@pytest.mark.asyncio
async def test_record_prediction_writes_prediction_updates_batch_audits_and_invalidates() -> None:
    session = _FakeSession()
    batch_id = uuid4()
    pending_batch = _sample_batch(state=BatchState.PENDING, batch_id=batch_id)
    created_prediction = _sample_prediction(batch_id)
    created_audit = _sample_audit(batch_id)

    prediction_repo = SimpleNamespace(
        session=session,
        create=AsyncMock(return_value=created_prediction),
        get_by_batch_id=AsyncMock(return_value=None),
    )
    batch_repo = SimpleNamespace(
        session=session,
        get=AsyncMock(return_value=pending_batch),
        update_state=AsyncMock(
            return_value=_sample_batch(state=BatchState.COMPLETED, batch_id=batch_id)
        ),
    )
    audit_service = SimpleNamespace(write_entry=AsyncMock(return_value=created_audit))
    cache = _SpyInvalidator()
    service = PredictionService(prediction_repo, batch_repo, audit_service, cache)

    request_id = uuid4()
    top5 = [
        ("memo", 0.92),
        ("invoice", 0.03),
        ("letter", 0.02),
        ("form", 0.02),
        ("budget", 0.01),
    ]
    result = await service.record_prediction(
        batch_id=batch_id,
        label="memo",
        confidence=0.92,
        top5=top5,
        overlay_blob_key="overlays/sample.png",
        model_sha256="abc123",
        request_id=request_id,
    )

    assert result.id == created_prediction.id
    batch_repo.get.assert_awaited_once_with(batch_id)
    prediction_repo.get_by_batch_id.assert_not_awaited()
    prediction_repo.create.assert_awaited_once_with(
        batch_id=batch_id,
        label="memo",
        confidence=0.92,
        top5_labels=["memo", "invoice", "letter", "form", "budget"],
        top5_confidences=[0.92, 0.03, 0.02, 0.02, 0.01],
        overlay_blob_key="overlays/sample.png",
        model_sha256="abc123",
        request_id=request_id,
    )
    batch_repo.update_state.assert_awaited_once_with(
        batch_id=batch_id,
        new_state=BatchState.COMPLETED,
        failure_reason=None,
    )
    audit_service.write_entry.assert_awaited_once_with(
        action=AuditAction.BATCH_STATE_CHANGE,
        actor_user_id=None,
        target_type="batch",
        target_id=batch_id,
        before=None,
        after={"state": "completed"},
        request_id=request_id,
    )
    assert cache.batch_detail_calls == [batch_id]
    assert cache.predictions_recent_calls == 1


@pytest.mark.asyncio
async def test_record_prediction_raises_batch_not_found_for_missing_batch() -> None:
    session = _FakeSession()
    batch_id = uuid4()
    prediction_repo = SimpleNamespace(
        session=session,
        create=AsyncMock(),
        get_by_batch_id=AsyncMock(),
    )
    batch_repo = SimpleNamespace(
        session=session,
        get=AsyncMock(return_value=None),
        update_state=AsyncMock(),
    )
    audit_service = SimpleNamespace(write_entry=AsyncMock())
    cache = _SpyInvalidator()
    service = PredictionService(prediction_repo, batch_repo, audit_service, cache)

    with pytest.raises(BatchNotFoundError, match=str(batch_id)):
        await service.record_prediction(
            batch_id=batch_id,
            label="memo",
            confidence=0.92,
            top5=[("memo", 0.92)],
            overlay_blob_key="overlays/sample.png",
            model_sha256="abc123",
            request_id=uuid4(),
        )

    prediction_repo.create.assert_not_awaited()
    prediction_repo.get_by_batch_id.assert_not_awaited()
    batch_repo.update_state.assert_not_awaited()
    audit_service.write_entry.assert_not_awaited()
    assert cache.batch_detail_calls == []
    assert cache.predictions_recent_calls == 0


@pytest.mark.asyncio
async def test_record_prediction_returns_existing_prediction_for_completed_batch() -> None:
    session = _FakeSession()
    batch_id = uuid4()
    completed_batch = _sample_batch(state=BatchState.COMPLETED, batch_id=batch_id)
    existing_prediction = _sample_prediction(batch_id)

    prediction_repo = SimpleNamespace(
        session=session,
        create=AsyncMock(),
        get_by_batch_id=AsyncMock(return_value=existing_prediction),
    )
    batch_repo = SimpleNamespace(
        session=session,
        get=AsyncMock(return_value=completed_batch),
        update_state=AsyncMock(),
    )
    audit_service = SimpleNamespace(write_entry=AsyncMock())
    cache = _SpyInvalidator()
    service = PredictionService(prediction_repo, batch_repo, audit_service, cache)

    result = await service.record_prediction(
        batch_id=batch_id,
        label="memo",
        confidence=0.92,
        top5=[("memo", 0.92)],
        overlay_blob_key="overlays/sample.png",
        model_sha256="abc123",
        request_id=uuid4(),
    )

    assert result.id == existing_prediction.id
    prediction_repo.get_by_batch_id.assert_awaited_once_with(batch_id)
    prediction_repo.create.assert_not_awaited()
    batch_repo.update_state.assert_not_awaited()
    audit_service.write_entry.assert_not_awaited()
    assert cache.batch_detail_calls == [batch_id]
    assert cache.predictions_recent_calls == 1


@pytest.mark.asyncio
async def test_record_prediction_raises_when_completed_batch_has_no_prediction() -> None:
    session = _FakeSession()
    batch_id = uuid4()
    completed_batch = _sample_batch(state=BatchState.COMPLETED, batch_id=batch_id)

    prediction_repo = SimpleNamespace(
        session=session,
        create=AsyncMock(),
        get_by_batch_id=AsyncMock(return_value=None),
    )
    batch_repo = SimpleNamespace(
        session=session,
        get=AsyncMock(return_value=completed_batch),
        update_state=AsyncMock(),
    )
    audit_service = SimpleNamespace(write_entry=AsyncMock())
    cache = _SpyInvalidator()
    service = PredictionService(prediction_repo, batch_repo, audit_service, cache)

    with pytest.raises(BatchAlreadyCompletedError, match=str(batch_id)):
        await service.record_prediction(
            batch_id=batch_id,
            label="memo",
            confidence=0.92,
            top5=[("memo", 0.92)],
            overlay_blob_key="overlays/sample.png",
            model_sha256="abc123",
            request_id=uuid4(),
        )

    prediction_repo.get_by_batch_id.assert_awaited_once_with(batch_id)
    prediction_repo.create.assert_not_awaited()
    batch_repo.update_state.assert_not_awaited()
    audit_service.write_entry.assert_not_awaited()
    assert cache.batch_detail_calls == []
    assert cache.predictions_recent_calls == 0


@pytest.mark.asyncio
async def test_record_prediction_skips_invalidation_when_write_fails() -> None:
    session = _FakeSession()
    batch_id = uuid4()
    pending_batch = _sample_batch(state=BatchState.PENDING, batch_id=batch_id)
    prediction_repo = SimpleNamespace(
        session=session,
        create=AsyncMock(side_effect=RuntimeError("db write failed")),
        get_by_batch_id=AsyncMock(return_value=None),
    )
    batch_repo = SimpleNamespace(
        session=session,
        get=AsyncMock(return_value=pending_batch),
        update_state=AsyncMock(),
    )
    audit_service = SimpleNamespace(write_entry=AsyncMock())
    cache = _SpyInvalidator()
    service = PredictionService(prediction_repo, batch_repo, audit_service, cache)

    with pytest.raises(RuntimeError, match="db write failed"):
        await service.record_prediction(
            batch_id=batch_id,
            label="memo",
            confidence=0.92,
            top5=[("memo", 0.92)],
            overlay_blob_key="overlays/sample.png",
            model_sha256="abc123",
            request_id=uuid4(),
        )

    prediction_repo.get_by_batch_id.assert_not_awaited()
    batch_repo.update_state.assert_not_awaited()
    audit_service.write_entry.assert_not_awaited()
    assert cache.batch_detail_calls == []
    assert cache.predictions_recent_calls == 0
