from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.audit_log import AuditLogEntry
from app.domain.enums import AuditAction

# TODO(api-contract): trim internal fields (blob_key, request_id, created_by_user_id, ...)
# from HTTP responses once the API contract is finalized. Kept 1:1 with domain for now.


class AuditLogEntryResponse(BaseModel):
    id: UUID
    actor_user_id: UUID | None = None
    action: AuditAction
    target_type: str
    target_id: UUID
    before_value: dict | None = None
    after_value: dict | None = None
    request_id: UUID
    created_at: datetime

    @classmethod
    def from_domain(cls, model: AuditLogEntry) -> "AuditLogEntryResponse":
        return cls(**model.model_dump())


class AuditLogListResponse(BaseModel):
    items: list[AuditLogEntryResponse]

    @classmethod
    def from_domain_list(cls, models: list[AuditLogEntry]) -> "AuditLogListResponse":
        return cls(items=[AuditLogEntryResponse.from_domain(model) for model in models])
