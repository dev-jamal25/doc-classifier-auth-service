from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.batches import Batch
from app.domain.enums import BatchSource, BatchState

# TODO(api-contract): trim internal fields (blob_key, request_id, created_by_user_id, ...)
# from HTTP responses once the API contract is finalized. Kept 1:1 with domain for now.


class BatchResponse(BaseModel):
    id: UUID
    source_filename: str
    source: BatchSource
    sftp_user: str | None = None
    blob_key: str | None = None
    state: BatchState
    failure_reason: str | None = None
    request_id: UUID
    created_by_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, model: Batch) -> "BatchResponse":
        return cls(**model.model_dump())


class BatchListResponse(BaseModel):
    items: list[BatchResponse]

    @classmethod
    def from_domain_list(cls, models: list[Batch]) -> "BatchListResponse":
        return cls(items=[BatchResponse.from_domain(model) for model in models])
