from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.predictions import Prediction

# TODO(api-contract): trim internal fields (blob_key, request_id, created_by_user_id, ...)
# from HTTP responses once the API contract is finalized. Kept 1:1 with domain for now.


class PredictionResponse(BaseModel):
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
    def from_domain(cls, model: Prediction) -> "PredictionResponse":
        return cls(**model.model_dump())


class PredictionListResponse(BaseModel):
    items: list[PredictionResponse]

    @classmethod
    def from_domain_list(cls, models: list[Prediction]) -> "PredictionListResponse":
        return cls(items=[PredictionResponse.from_domain(model) for model in models])
