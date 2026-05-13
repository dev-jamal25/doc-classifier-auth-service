from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.models import Prediction as PredictionModel


class Prediction(BaseModel):
    id: UUID
    batch_id: UUID
    label: str
    confidence: float
    top5: list[tuple[str, float]]
    overlay_blob_key: str | None = None
    model_sha256: str
    reviewed_by_user_id: UUID | None = None
    reviewed_label: str | None = None
    reviewed_at: datetime | None = None
    request_id: UUID
    created_at: datetime

    @classmethod
    def from_orm_row(cls, row: PredictionModel) -> "Prediction":
        top5_pairs = list(zip(row.top5_labels, row.top5_confidences, strict=False))
        return cls(
            id=row.id,
            batch_id=row.batch_id,
            label=row.label,
            confidence=row.confidence,
            top5=top5_pairs,
            overlay_blob_key=row.overlay_blob_key,
            model_sha256=row.model_sha256,
            reviewed_by_user_id=row.reviewed_by_user_id,
            reviewed_label=row.reviewed_label,
            reviewed_at=row.reviewed_at,
            request_id=row.request_id,
            created_at=row.created_at,
        )
