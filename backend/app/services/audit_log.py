from uuid import UUID

from app.domain.audit_log import AuditLogEntry
from app.domain.enums import AuditAction
from app.repositories.audit_log import AuditLogRepository


class AuditLogService:
    def __init__(self, audit_log_repository: AuditLogRepository) -> None:
        self._audit_log_repository = audit_log_repository

    async def write_entry(
        self,
        *,
        action: AuditAction,
        actor_user_id: UUID | None,
        target_type: str,
        target_id: UUID,
        before: dict | None,
        after: dict | None,
        request_id: UUID,
    ) -> AuditLogEntry:
        # TODO(impl): persist an auditable system action row.
        raise NotImplementedError("AuditLogService.write_entry not yet implemented")

    async def list_entries(self, *, limit: int = 100, offset: int = 0) -> list[AuditLogEntry]:
        # TODO(impl): read paginated audit trail rows.
        raise NotImplementedError("AuditLogService.list_entries not yet implemented")
