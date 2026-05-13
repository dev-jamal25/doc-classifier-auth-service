from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ClassificationJob(BaseModel):
    batch_id: UUID
    blob_key: str
    source_filename: str
    sftp_user: str | None = None
    request_id: UUID
    received_at: datetime
