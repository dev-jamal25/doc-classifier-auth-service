from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.models import AuditLog as AuditLogModel
from app.domain.enums import AuditAction


class AuditLogEntry(BaseModel):
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
    def from_orm_row(cls, row: AuditLogModel) -> "AuditLogEntry":
        return cls(
            id=row.id,
            actor_user_id=row.actor_user_id,
            action=AuditAction(row.action),
            target_type=row.target_type,
            target_id=row.target_id,
            before_value=row.before_value,
            after_value=row.after_value,
            request_id=row.request_id,
            created_at=row.created_at,
        )
