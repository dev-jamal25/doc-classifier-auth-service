from uuid import uuid4

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from app.db.models import AuditLog, Batch, CasbinRule, Prediction


def test_model_tablenames() -> None:
    assert Batch.__tablename__ == "batches"
    assert Prediction.__tablename__ == "predictions"
    assert AuditLog.__tablename__ == "audit_log"
    assert CasbinRule.__tablename__ == "casbin_rule"


def test_casbin_rule_matches_adapter_shape() -> None:
    assert isinstance(CasbinRule.__table__.c.id.type, Integer)
    assert CasbinRule.__table__.c.id.primary_key is True
    for column_name in ("ptype", "v0", "v1", "v2", "v3", "v4", "v5"):
        column = CasbinRule.__table__.c[column_name]
        assert isinstance(column.type, String)
        assert column.type.length == 255


def test_casbin_rule_serializes_policy_like_adapter() -> None:
    row = CasbinRule(ptype="p", v0="admin", v1="batches", v2="read")

    assert str(row) == "p, admin, batches, read"


def test_casbin_rule_serializes_grouping_policy_like_adapter() -> None:
    user_id = uuid4()
    row = CasbinRule(ptype="g", v0=str(user_id), v1="admin")

    assert str(row) == f"g, {user_id}, admin"


def test_user_reference_columns_are_nullable_without_foreign_keys() -> None:
    assert Batch.__table__.c.created_by_user_id.nullable is True
    assert len(Batch.__table__.c.created_by_user_id.foreign_keys) == 0

    assert Prediction.__table__.c.reviewed_by_user_id.nullable is True
    assert len(Prediction.__table__.c.reviewed_by_user_id.foreign_keys) == 0

    assert AuditLog.__table__.c.actor_user_id.nullable is True
    assert len(AuditLog.__table__.c.actor_user_id.foreign_keys) == 0


def test_jsonb_columns_exist() -> None:
    assert isinstance(Prediction.__table__.c.top5_labels.type, JSONB)
    assert isinstance(Prediction.__table__.c.top5_confidences.type, JSONB)
    assert isinstance(AuditLog.__table__.c.before_value.type, JSONB)
    assert isinstance(AuditLog.__table__.c.after_value.type, JSONB)


def test_models_can_be_instantiated_in_memory() -> None:
    request_id = uuid4()
    batch_id = uuid4()

    batch = Batch(
        source_filename="scan_001.tif",
        source="sftp-ingest",
        sftp_user="vendor-1",
        blob_key="batches/2026/05/13/scan_001.tif",
        state="pending",
        failure_reason=None,
        request_id=request_id,
        created_by_user_id=None,
    )
    prediction = Prediction(
        batch_id=batch_id,
        label="invoice",
        confidence=0.98,
        top5_labels=["invoice", "letter", "memo", "form", "budget"],
        top5_confidences=[0.98, 0.01, 0.005, 0.003, 0.002],
        overlay_blob_key=None,
        model_sha256="abc123",
        reviewed_by_user_id=None,
        reviewed_label=None,
        reviewed_at=None,
        request_id=request_id,
    )
    audit_log = AuditLog(
        actor_user_id=None,
        action="batch_state_change",
        target_type="batch",
        target_id=batch_id,
        before_value={"state": "pending"},
        after_value={"state": "processing"},
        request_id=request_id,
    )

    assert batch.source_filename == "scan_001.tif"
    assert prediction.label == "invoice"
    assert audit_log.action == "batch_state_change"
