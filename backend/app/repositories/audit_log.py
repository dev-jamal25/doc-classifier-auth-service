from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit_log import AuditLogEntry
from app.domain.enums import AuditAction


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        action: AuditAction,
        actor_user_id: UUID | None,
        target_type: str,
        target_id: UUID,
        before_value: dict | None,
        after_value: dict | None,
        request_id: UUID,
    ) -> AuditLogEntry:
        # TODO(impl): SQL insert and domain model mapping go here.
        raise NotImplementedError("AuditLogRepository.create not yet implemented")

    async def list(self, *, limit: int = 100, offset: int = 0) -> list[AuditLogEntry]:
        # TODO(impl): SQL listing for audit entries goes here.
        raise NotImplementedError("AuditLogRepository.list not yet implemented")
