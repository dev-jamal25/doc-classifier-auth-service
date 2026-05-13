from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.models import Batch as BatchModel
from app.domain.enums import BatchSource, BatchState


class Batch(BaseModel):
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
    def from_orm_row(cls, row: BatchModel) -> "Batch":
        return cls(
            id=row.id,
            source_filename=row.source_filename,
            source=BatchSource(row.source),
            sftp_user=row.sftp_user,
            blob_key=row.blob_key,
            state=BatchState(row.state),
            failure_reason=row.failure_reason,
            request_id=row.request_id,
            created_by_user_id=row.created_by_user_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
