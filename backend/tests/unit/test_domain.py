from datetime import UTC, datetime
from uuid import uuid4

from app.domain.audit_log import AuditLogEntry
from app.domain.batches import Batch
from app.domain.enums import AuditAction, BatchSource, BatchState
from app.domain.predictions import Prediction


def test_enum_contract_values() -> None:
    assert BatchSource.SFTP_INGEST == "sftp-ingest"
    assert {state.value for state in BatchState} == {
        "pending",
        "processing",
        "completed",
        "failed",
    }
    assert {action.value for action in AuditAction} == {
        "role_change",
        "relabel",
        "batch_state_change",
    }


def test_batch_roundtrip_dump_and_validate() -> None:
    now = datetime.now(UTC)
    batch = Batch(
        id=uuid4(),
        source_filename="scan_001.tif",
        source=BatchSource.SFTP_INGEST,
        sftp_user="vendor-1",
        blob_key="batches/2026/05/13/scan_001.tif",
        state=BatchState.PENDING,
        failure_reason=None,
        request_id=uuid4(),
        created_by_user_id=None,
        created_at=now,
        updated_at=now,
    )

    payload = batch.model_dump(mode="json")
    restored = Batch.model_validate(payload)

    assert restored.source == BatchSource.SFTP_INGEST
    assert restored.state == BatchState.PENDING


def test_prediction_roundtrip_dump_and_validate() -> None:
    prediction = Prediction(
        id=uuid4(),
        batch_id=uuid4(),
        label="invoice",
        confidence=0.95,
        top5=[
            ("invoice", 0.95),
            ("letter", 0.02),
            ("memo", 0.01),
            ("form", 0.01),
            ("budget", 0.01),
        ],
        overlay_blob_key="overlays/abc.png",
        model_sha256="abc123",
        reviewed_by_user_id=None,
        reviewed_label=None,
        reviewed_at=None,
        request_id=uuid4(),
        created_at=datetime.now(UTC),
    )

    payload = prediction.model_dump(mode="json")
    restored = Prediction.model_validate(payload)

    assert restored.top5[0][0] == "invoice"
    assert restored.confidence == 0.95


def test_audit_log_roundtrip_dump_and_validate() -> None:
    audit = AuditLogEntry(
        id=uuid4(),
        actor_user_id=None,
        action=AuditAction.BATCH_STATE_CHANGE,
        target_type="batch",
        target_id=uuid4(),
        before_value={"state": "pending"},
        after_value={"state": "processing"},
        request_id=uuid4(),
        created_at=datetime.now(UTC),
    )

    payload = audit.model_dump(mode="json")
    restored = AuditLogEntry.model_validate(payload)

    assert restored.action == AuditAction.BATCH_STATE_CHANGE
    assert restored.before_value == {"state": "pending"}
