from __future__ import annotations

import argparse
import asyncio
import logging
from uuid import UUID, uuid4

from app.core.lifespan import lifespan
from app.db.models import User
from app.domain.rbac import Role, UserRoles
from app.infra.rbac import build_enforcer
from app.repositories.audit_log import AuditLogRepository
from app.repositories.users import UserRepository
from app.services.audit_log import AuditLogService
from app.services.rbac import RBACService

logger = logging.getLogger(__name__)


class BootstrapAdminRoleTargetNotFoundError(RuntimeError):
    """Raised when the requested bootstrap target user does not exist."""


async def grant_admin_role_to_existing_user(
    *,
    user_repository: UserRepository,
    rbac_service: RBACService,
    user_id: UUID | None = None,
    email: str | None = None,
    request_id: UUID | None = None,
) -> UserRoles:
    if (user_id is None) == (email is None):
        raise ValueError("Provide exactly one of user_id or email.")

    user = await _find_existing_user(user_repository, user_id=user_id, email=email)
    return await rbac_service.assign_role(
        actor_user_id=None,
        target_user_id=user.id,
        role=Role.ADMIN,
        request_id=request_id or uuid4(),
    )


async def _find_existing_user(
    user_repository: UserRepository,
    *,
    user_id: UUID | None,
    email: str | None,
) -> User:
    if user_id is not None:
        user = await user_repository.get(user_id)
        target = str(user_id)
    else:
        user = await user_repository.get_by_email(email or "")
        target = email or ""

    if user is None:
        raise BootstrapAdminRoleTargetNotFoundError(f"User `{target}` not found.")
    return user


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Grant the Casbin admin role to an existing user.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--user-id", type=UUID, default=None)
    target.add_argument("--email", default=None)
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()

    async with lifespan("bootstrap-admin-role"):
        from app.db.session import async_session_factory

        async with async_session_factory() as session:
            user_repository = UserRepository(session)
            audit_log_service = AuditLogService(AuditLogRepository(session))
            enforcer = await build_enforcer(session)
            rbac_service = RBACService(enforcer, user_repository, audit_log_service)
            try:
                result = await grant_admin_role_to_existing_user(
                    user_repository=user_repository,
                    rbac_service=rbac_service,
                    user_id=args.user_id,
                    email=args.email,
                )
            except BootstrapAdminRoleTargetNotFoundError as exc:
                raise SystemExit(str(exc)) from exc

    logger.info(
        "Bootstrap admin role ensured.",
        extra={
            "event": "admin_role_bootstrapped",
            "user_id": str(result.user_id),
            "changed": result.changed,
            "roles": [role.value for role in result.roles],
        },
    )


if __name__ == "__main__":
    asyncio.run(main())
