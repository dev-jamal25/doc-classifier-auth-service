# TODO(auth): protect with current_user dependency once fastapi-users/Vault setup is ready.
# TODO(authz): enforce admin/reviewer/auditor permissions through Casbin.

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_audit_log_service
from app.api.schemas.audit_log import AuditLogListResponse
from app.services.audit_log import AuditLogService

audit_log_service_dependency = Depends(get_audit_log_service)
audit_limit_query = Query(100, ge=1, le=200)
audit_offset_query = Query(0, ge=0)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit-log", response_model=AuditLogListResponse)
async def list_audit_log(
    limit: int = audit_limit_query,
    offset: int = audit_offset_query,
    service: AuditLogService = audit_log_service_dependency,
) -> AuditLogListResponse:
    entries = await service.list_entries(limit=limit, offset=offset)
    return AuditLogListResponse.from_domain_list(entries)
