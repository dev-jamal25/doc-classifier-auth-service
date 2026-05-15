from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_users.exceptions import UserAlreadyExists

from app.api.auth.manager import UserManager, get_user_manager
from app.api.deps import (
    get_audit_log_service,
    get_rbac_service,
    request_id_dependency,
    require_permission,
)
from app.api.schemas.audit_log import AuditLogListResponse
from app.api.schemas.rbac import UserRolesResponse
from app.api.schemas.users import AdminUserInviteRequest, UserCreate, UserRead
from app.db.models import User
from app.domain.errors import LastAdminRoleRemovalError, UserNotFoundError
from app.domain.rbac import Role
from app.services.audit_log import AuditLogService
from app.services.rbac import RBACService

audit_log_service_dependency = Depends(get_audit_log_service)
rbac_service_dependency = Depends(get_rbac_service)
user_manager_dependency = Depends(get_user_manager)
audit_read_dependency = Depends(require_permission("audit", "read"))
manage_roles_dependency = Depends(require_permission("users", "manage_roles"))
audit_limit_query = Query(100, ge=1, le=200)
audit_offset_query = Query(0, ge=0)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit-log", response_model=AuditLogListResponse)
async def list_audit_log(
    limit: int = audit_limit_query,
    offset: int = audit_offset_query,
    _user: User = audit_read_dependency,
    service: AuditLogService = audit_log_service_dependency,
) -> AuditLogListResponse:
    entries = await service.list_entries(limit=limit, offset=offset)
    return AuditLogListResponse.from_domain_list(entries)


@router.post("/users/invite", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def invite_user(
    payload: AdminUserInviteRequest,
    _actor: User = manage_roles_dependency,
    user_manager: UserManager = user_manager_dependency,
) -> UserRead:
    user_create = UserCreate(
        email=payload.email,
        password=payload.temporary_password,
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )
    try:
        user = await user_manager.create(user_create, safe=False)
    except UserAlreadyExists as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        ) from exc
    return UserRead.model_validate(user)


@router.put("/users/{user_id}/roles/{role}", response_model=UserRolesResponse)
async def assign_user_role(
    user_id: UUID,
    role: Role,
    actor: User = manage_roles_dependency,
    request_id: UUID = request_id_dependency,
    service: RBACService = rbac_service_dependency,
) -> UserRolesResponse:
    try:
        result = await service.assign_role(
            actor_user_id=actor.id,
            target_user_id=user_id,
            role=role,
            request_id=request_id,
        )
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from exc
    return UserRolesResponse.from_domain(result)


@router.delete("/users/{user_id}/roles/{role}", response_model=UserRolesResponse)
async def remove_user_role(
    user_id: UUID,
    role: Role,
    actor: User = manage_roles_dependency,
    request_id: UUID = request_id_dependency,
    service: RBACService = rbac_service_dependency,
) -> UserRolesResponse:
    try:
        result = await service.remove_role(
            actor_user_id=actor.id,
            target_user_id=user_id,
            role=role,
            request_id=request_id,
        )
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from exc
    except LastAdminRoleRemovalError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot remove the last admin role",
        ) from exc
    return UserRolesResponse.from_domain(result)
