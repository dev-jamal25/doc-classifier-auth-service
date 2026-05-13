from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog as AuditLogModel
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
        model = AuditLogModel(
            action=action.value,
            actor_user_id=actor_user_id,
            target_type=target_type,
            target_id=target_id,
            before_value=before_value,
            after_value=after_value,
            request_id=request_id,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return AuditLogEntry.from_orm_row(model)

    async def list(self, *, limit: int = 100, offset: int = 0) -> list[AuditLogEntry]:
        # TODO(impl): SQL listing for audit entries goes here.
        raise NotImplementedError("AuditLogRepository.list not yet implemented")
