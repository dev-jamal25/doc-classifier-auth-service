from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.audit_log import AuditLogEntry
from app.domain.batches import Batch
from app.domain.enums import AuditAction, BatchSource, BatchState
from app.domain.predictions import Prediction
from app.repositories.audit_log import AuditLogRepository
from app.repositories.batches import BatchRepository
from app.repositories.predictions import PredictionRepository


class FakeBatchRepository(BatchRepository):
    def __init__(self, *, batch: Batch | None = None, session: object | None = None) -> None:
        self._session = session if session is not None else object()
        self.calls: list[dict] = []
        self._batch = batch

    async def get(self, batch_id: UUID) -> Batch | None:
        self.calls.append({"method": "get", "batch_id": batch_id})
        return self._batch

    async def create_failed(
        self,
        *,
        source_filename: str,
        sftp_user: str | None,
        request_id: UUID,
        failure_reason: str,
    ) -> Batch:
        self.calls.append(
            {
                "method": "create_failed",
                "source_filename": source_filename,
                "sftp_user": sftp_user,
                "request_id": request_id,
                "failure_reason": failure_reason,
            }
        )
        now = datetime.now(UTC)
        return Batch(
            id=uuid4(),
            source_filename=source_filename,
            source=BatchSource.SFTP_INGEST,
            sftp_user=sftp_user,
            blob_key=None,
            state=BatchState.FAILED,
            failure_reason=failure_reason,
            request_id=request_id,
            created_by_user_id=None,
            created_at=now,
            updated_at=now,
        )

    async def update_state(
        self,
        *,
        batch_id: UUID,
        new_state: BatchState,
        failure_reason: str | None = None,
    ) -> Batch:
        self.calls.append(
            {
                "method": "update_state",
                "batch_id": batch_id,
                "new_state": new_state,
                "failure_reason": failure_reason,
            }
        )
        now = datetime.now(UTC)
        return Batch(
            id=batch_id,
            source_filename="scan_001.tif",
            source=BatchSource.SFTP_INGEST,
            sftp_user="vendor-1",
            blob_key="batches/2026/05/14/scan_001.tif",
            state=new_state,
            failure_reason=failure_reason,
            request_id=uuid4(),
            created_by_user_id=None,
            created_at=now,
            updated_at=now,
        )


class FakePredictionRepository(PredictionRepository):
    def __init__(
        self,
        *,
        existing_prediction: Prediction | None = None,
        session: object | None = None,
    ) -> None:
        self._session = session if session is not None else object()
        self.calls: list[dict] = []
        self._existing_prediction = existing_prediction

    async def create(
        self,
        *,
        batch_id: UUID,
        label: str,
        confidence: float,
        top5_labels: list[str],
        top5_confidences: list[float],
        overlay_blob_key: str | None,
        model_sha256: str,
        request_id: UUID,
    ) -> Prediction:
        self.calls.append(
            {
                "method": "create",
                "batch_id": batch_id,
                "label": label,
                "confidence": confidence,
                "top5_labels": top5_labels,
                "top5_confidences": top5_confidences,
                "overlay_blob_key": overlay_blob_key,
                "model_sha256": model_sha256,
                "request_id": request_id,
            }
        )
        return Prediction(
            id=uuid4(),
            batch_id=batch_id,
            label=label,
            confidence=confidence,
            top5=list(zip(top5_labels, top5_confidences, strict=False)),
            overlay_blob_key=overlay_blob_key,
            model_sha256=model_sha256,
            reviewed_by_user_id=None,
            reviewed_label=None,
            reviewed_at=None,
            request_id=request_id,
            created_at=datetime.now(UTC),
        )

    async def get_by_batch_id(self, batch_id: UUID) -> Prediction | None:
        self.calls.append({"method": "get_by_batch_id", "batch_id": batch_id})
        return self._existing_prediction


class FakeAuditLogRepository(AuditLogRepository):
    def __init__(self, *, session: object | None = None) -> None:
        self._session = session if session is not None else object()
        self.calls: list[dict] = []

    async def create(
        self,
        *,
        action: AuditAction,
        actor_user_id: UUID | None,
        target_type: str,
        target_id: UUID,
        before_value: dict | None,
        after_value: dict | None,
        request_id: UUID,
    ) -> AuditLogEntry:
        self.calls.append(
            {
                "method": "create",
                "action": action,
                "actor_user_id": actor_user_id,
                "target_type": target_type,
                "target_id": target_id,
                "before_value": before_value,
                "after_value": after_value,
                "request_id": request_id,
            }
        )
        return AuditLogEntry(
            id=uuid4(),
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before_value=before_value,
            after_value=after_value,
            request_id=request_id,
            created_at=datetime.now(UTC),
        )
