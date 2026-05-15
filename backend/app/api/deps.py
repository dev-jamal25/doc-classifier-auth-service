from collections.abc import AsyncIterator
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import User
from app.infra.rbac import build_enforcer
from app.repositories.audit_log import AuditLogRepository
from app.repositories.batches import BatchRepository
from app.repositories.predictions import PredictionRepository
from app.repositories.users import UserRepository
from app.services.audit_log import AuditLogService
from app.services.batches import BatchService
from app.services.cache import NoOpServiceCacheInvalidator, ServiceCacheInvalidator
from app.services.predictions import PredictionService
from app.services.rbac import RBACService


async def get_db_session() -> AsyncIterator[AsyncSession]:
    # Deferred import: app.db.session resolves Vault secrets at import time.
    # Importing it at module scope would trigger a Vault network call during
    # router import / test collection.
    from app.db.session import get_session

    async for session in get_session():
        yield session


db_session_dependency = Depends(get_db_session)


def get_cache_invalidator(request: Request) -> ServiceCacheInvalidator:
    invalidator = getattr(getattr(request.app, "state", None), "cache_invalidator", None)
    if invalidator is None:
        return NoOpServiceCacheInvalidator()
    return invalidator


cache_invalidator_dependency = Depends(get_cache_invalidator)


def get_batch_service(
    session: AsyncSession = db_session_dependency,
    cache_invalidator: ServiceCacheInvalidator = cache_invalidator_dependency,
) -> BatchService:
    return BatchService(BatchRepository(session), cache_invalidator)


def get_prediction_service(
    session: AsyncSession = db_session_dependency,
    cache_invalidator: ServiceCacheInvalidator = cache_invalidator_dependency,
) -> PredictionService:
    # PredictionService.__init__ requires audit_log_service for its write path.
    # list_recent does not use it, but the constructor requires it.
    audit_log_service = AuditLogService(AuditLogRepository(session))
    return PredictionService(
        PredictionRepository(session),
        BatchRepository(session),
        audit_log_service,
        cache_invalidator,
    )


def get_audit_log_service(
    session: AsyncSession = db_session_dependency,
) -> AuditLogService:
    return AuditLogService(AuditLogRepository(session))


async def get_rbac_service(
    session: AsyncSession = db_session_dependency,
    cache_invalidator: ServiceCacheInvalidator = cache_invalidator_dependency,
) -> RBACService:
    enforcer = await build_enforcer(session)
    audit_log_service = AuditLogService(AuditLogRepository(session))
    return RBACService(enforcer, UserRepository(session), audit_log_service, cache_invalidator)


async def get_request_id(request: Request) -> UUID:
    context = getattr(getattr(request.app, "state", None), "context", None)
    settings = getattr(context, "settings", None) or get_settings()
    raw_request_id = request.headers.get(settings.request_id_header)

    if raw_request_id is None:
        return uuid4()

    try:
        return UUID(raw_request_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {settings.request_id_header} header.",
        ) from exc


request_id_dependency = Depends(get_request_id)


def require_permission(obj: str, act: str):
    from app.api.auth.users import current_active_user

    current_user_dependency = Depends(current_active_user)
    rbac_service_dependency = Depends(get_rbac_service)

    async def _require_permission(
        user: User = current_user_dependency,
        rbac_service: RBACService = rbac_service_dependency,
    ) -> User:
        if not await rbac_service.has_permission(user.id, obj, act):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )
        return user

    return _require_permission
