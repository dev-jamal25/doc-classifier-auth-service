from __future__ import annotations

from uuid import UUID

import casbin

from app.domain.enums import AuditAction
from app.domain.errors import LastAdminRoleRemovalError, UserNotFoundError
from app.domain.rbac import Role, UserRoles, known_roles
from app.repositories.users import UserRepository
from app.services.audit_log import AuditLogService
from app.services.cache import NoOpServiceCacheInvalidator, ServiceCacheInvalidator


class RBACService:
    def __init__(
        self,
        enforcer: casbin.AsyncEnforcer,
        user_repository: UserRepository,
        audit_log_service: AuditLogService,
        cache_invalidator: ServiceCacheInvalidator | None = None,
    ) -> None:
        self._enforcer = enforcer
        self._user_repository = user_repository
        self._audit_log_service = audit_log_service
        self._cache_invalidator = cache_invalidator or NoOpServiceCacheInvalidator()

    async def has_permission(self, user_id: UUID, obj: str, act: str) -> bool:
        return bool(self._enforcer.enforce(str(user_id), obj, act))

    async def get_roles_for_user(self, user_id: UUID) -> list[Role]:
        roles = await self._enforcer.get_roles_for_user(str(user_id))
        return known_roles(roles)

    async def assign_role(
        self,
        *,
        actor_user_id: UUID | None,
        target_user_id: UUID,
        role: Role,
        request_id: UUID,
    ) -> UserRoles:
        await self._ensure_user_exists(target_user_id)
        before_roles = await self.get_roles_for_user(target_user_id)
        changed = await self._enforcer.add_role_for_user(str(target_user_id), role.value)
        after_roles = await self.get_roles_for_user(target_user_id)

        if not changed:
            return UserRoles(user_id=target_user_id, roles=after_roles, changed=False)

        try:
            await self._write_role_change_audit(
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                before_roles=before_roles,
                after_roles=after_roles,
                request_id=request_id,
            )
            await self._user_repository.session.commit()
        except Exception:
            await self._user_repository.session.rollback()
            raise

        await self._cache_invalidator.invalidate_user_profile(target_user_id)
        return UserRoles(user_id=target_user_id, roles=after_roles, changed=True)

    async def remove_role(
        self,
        *,
        actor_user_id: UUID | None,
        target_user_id: UUID,
        role: Role,
        request_id: UUID,
    ) -> UserRoles:
        await self._ensure_user_exists(target_user_id)
        before_roles = await self.get_roles_for_user(target_user_id)

        if role == Role.ADMIN and Role.ADMIN in before_roles:
            admin_users = set(await self._enforcer.get_users_for_role(Role.ADMIN.value))
            if str(target_user_id) in admin_users and len(admin_users) <= 1:
                raise LastAdminRoleRemovalError(target_user_id)

        changed = await self._enforcer.delete_role_for_user(str(target_user_id), role.value)
        after_roles = await self.get_roles_for_user(target_user_id)

        if not changed:
            return UserRoles(user_id=target_user_id, roles=after_roles, changed=False)

        try:
            await self._write_role_change_audit(
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                before_roles=before_roles,
                after_roles=after_roles,
                request_id=request_id,
            )
            await self._user_repository.session.commit()
        except Exception:
            await self._user_repository.session.rollback()
            raise

        await self._cache_invalidator.invalidate_user_profile(target_user_id)
        return UserRoles(user_id=target_user_id, roles=after_roles, changed=True)

    async def _ensure_user_exists(self, user_id: UUID) -> None:
        user = await self._user_repository.get(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

    async def _write_role_change_audit(
        self,
        *,
        actor_user_id: UUID | None,
        target_user_id: UUID,
        before_roles: list[Role],
        after_roles: list[Role],
        request_id: UUID,
    ) -> None:
        await self._audit_log_service.write_entry(
            action=AuditAction.ROLE_CHANGE,
            actor_user_id=actor_user_id,
            target_type="user",
            target_id=target_user_id,
            before={"roles": [role.value for role in before_roles]},
            after={"roles": [role.value for role in after_roles]},
            request_id=request_id,
        )
