from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_log import AuditLogRepository
from app.repositories.batches import BatchRepository
from app.repositories.predictions import PredictionRepository
from app.services.audit_log import AuditLogService
from app.services.batches import BatchService
from app.services.predictions import PredictionService


async def get_db_session() -> AsyncIterator[AsyncSession]:
    # Deferred import: app.db.session resolves Vault secrets at import time.
    # Importing it at module scope would trigger a Vault network call during
    # router import / test collection.
    from app.db.session import get_session

    async for session in get_session():
        yield session


db_session_dependency = Depends(get_db_session)


def get_batch_service(
    session: AsyncSession = db_session_dependency,
) -> BatchService:
    return BatchService(BatchRepository(session))


def get_prediction_service(
    session: AsyncSession = db_session_dependency,
) -> PredictionService:
    # PredictionService.__init__ requires audit_log_service for its write path.
    # list_recent does not use it, but the constructor requires it.
    audit_log_service = AuditLogService(AuditLogRepository(session))
    return PredictionService(
        PredictionRepository(session),
        BatchRepository(session),
        audit_log_service,
    )


def get_audit_log_service(
    session: AsyncSession = db_session_dependency,
) -> AuditLogService:
    return AuditLogService(AuditLogRepository(session))
