from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi_cache.decorator import cache

from app.api.auth.backend import auth_backend
from app.api.auth.users import current_active_user, fastapi_users
from app.api.deps import get_rbac_service
from app.api.schemas.users import UserRead
from app.db.models import User
from app.infra.cache import CACHE_NAMESPACE_ME, CACHE_TTL_ME_SECONDS
from app.services.rbac import RBACService

router = APIRouter()

router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)
# JWT logout is stateless; the route tells clients to discard their token.
# Public registration is intentionally not mounted: users are admin-invite-only.

current_active_user_dependency = Depends(current_active_user)
rbac_service_dependency = Depends(get_rbac_service)


@router.get("/me", response_model=UserRead, tags=["auth"])
@cache(expire=CACHE_TTL_ME_SECONDS, namespace=CACHE_NAMESPACE_ME)
async def me(
    user: User = current_active_user_dependency,
    rbac_service: RBACService = rbac_service_dependency,
) -> UserRead:
    response = UserRead.model_validate(user)
    response.roles = [role.value for role in await rbac_service.get_roles_for_user(user.id)]
    return response
