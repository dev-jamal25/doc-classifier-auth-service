from enum import StrEnum


class BatchState(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BatchSource(StrEnum):
    SFTP_INGEST = "sftp-ingest"


class AuditAction(StrEnum):
    ROLE_CHANGE = "role_change"
    RELABEL = "relabel"
    BATCH_STATE_CHANGE = "batch_state_change"
