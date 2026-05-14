from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.auth.backend import auth_backend
from app.api.auth.users import current_active_user, fastapi_users
from app.api.schemas.users import UserRead
from app.db.models import User

router = APIRouter()

router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)
# JWT logout is stateless; the route tells clients to discard their token.
# Public registration is intentionally not mounted: users are admin-invite-only.

current_active_user_dependency = Depends(current_active_user)


@router.get("/me", response_model=UserRead, tags=["auth"])
async def me(user: User = current_active_user_dependency) -> UserRead:
    return UserRead.model_validate(user)
