from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.db.models import User
from app.domain.enums import AuditAction
from app.domain.errors import LastAdminRoleRemovalError, UserNotFoundError
from app.domain.rbac import Permission, Role
from app.services.cache import ServiceCacheInvalidator
from app.services.rbac import RBACService


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class _FakeUserRepository:
    def __init__(self, users: list[User]) -> None:
        self.session = _FakeSession()
        self._users = {user.id: user for user in users}

    async def get(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)


class _FakeEnforcer:
    def __init__(self) -> None:
        self.roles_by_user: dict[str, set[str]] = {}
        self.enforce_calls: list[tuple[str, str, str]] = []

    def enforce(self, user_id: str, obj: str, act: str) -> bool:
        self.enforce_calls.append((user_id, obj, act))
        permission_by_role = {
            Role.ADMIN.value: {
                (Permission.BATCHES_READ.obj, Permission.BATCHES_READ.act),
                (Permission.PREDICTIONS_READ.obj, Permission.PREDICTIONS_READ.act),
                (Permission.AUDIT_READ.obj, Permission.AUDIT_READ.act),
                (Permission.USERS_MANAGE_ROLES.obj, Permission.USERS_MANAGE_ROLES.act),
            },
            Role.REVIEWER.value: {
                (Permission.BATCHES_READ.obj, Permission.BATCHES_READ.act),
                (Permission.PREDICTIONS_READ.obj, Permission.PREDICTIONS_READ.act),
                (Permission.PREDICTIONS_RELABEL.obj, Permission.PREDICTIONS_RELABEL.act),
            },
        }
        return any(
            (obj, act) in permission_by_role.get(role, set())
            for role in self.roles_by_user.get(user_id, set())
        )

    async def get_roles_for_user(self, user_id: str) -> list[str]:
        return list(self.roles_by_user.get(user_id, set()))

    async def add_role_for_user(self, user_id: str, role: str) -> bool:
        roles = self.roles_by_user.setdefault(user_id, set())
        if role in roles:
            return False
        roles.add(role)
        return True

    async def delete_role_for_user(self, user_id: str, role: str) -> bool:
        roles = self.roles_by_user.setdefault(user_id, set())
        if role not in roles:
            return False
        roles.remove(role)
        return True

    async def get_users_for_role(self, role: str) -> list[str]:
        return [user_id for user_id, roles in self.roles_by_user.items() if role in roles]


class _FakeAuditLogService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def write_entry(self, **kwargs) -> None:
        self.calls.append(kwargs)


class _SpyCacheInvalidator(ServiceCacheInvalidator):
    def __init__(self) -> None:
        self.user_profile_calls: list[UUID] = []

    async def invalidate_user_profile(self, user_id: UUID) -> None:
        self.user_profile_calls.append(user_id)

    async def invalidate_batches_list(self) -> None:
        return None

    async def invalidate_batch_detail(self, batch_id: UUID) -> None:
        return None

    async def invalidate_predictions_recent(self) -> None:
        return None


def _user(user_id: UUID | None = None) -> User:
    return User(
        id=user_id or uuid4(),
        email="user@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )


@pytest.mark.asyncio
async def test_has_permission_uses_casbin_enforcer() -> None:
    user = _user()
    repo = _FakeUserRepository([user])
    enforcer = _FakeEnforcer()
    enforcer.roles_by_user[str(user.id)] = {Role.REVIEWER.value}
    service = RBACService(enforcer, repo, _FakeAuditLogService())

    assert await service.has_permission(user.id, "batches", "read") is True
    assert await service.has_permission(user.id, "audit", "read") is False
    assert enforcer.enforce_calls == [
        (str(user.id), "batches", "read"),
        (str(user.id), "audit", "read"),
    ]


@pytest.mark.asyncio
async def test_assign_role_writes_audit_and_commits() -> None:
    actor = _user()
    target = _user()
    repo = _FakeUserRepository([actor, target])
    enforcer = _FakeEnforcer()
    audit = _FakeAuditLogService()
    cache = _SpyCacheInvalidator()
    service = RBACService(enforcer, repo, audit, cache)
    request_id = uuid4()

    result = await service.assign_role(
        actor_user_id=actor.id,
        target_user_id=target.id,
        role=Role.REVIEWER,
        request_id=request_id,
    )

    assert result.changed is True
    assert result.roles == [Role.REVIEWER]
    assert repo.session.commits == 1
    assert audit.calls[0]["action"] == AuditAction.ROLE_CHANGE
    assert audit.calls[0]["before"] == {"roles": []}
    assert audit.calls[0]["after"] == {"roles": ["reviewer"]}
    assert cache.user_profile_calls == [target.id]


@pytest.mark.asyncio
async def test_assign_role_is_idempotent_without_audit() -> None:
    target = _user()
    repo = _FakeUserRepository([target])
    enforcer = _FakeEnforcer()
    enforcer.roles_by_user[str(target.id)] = {Role.REVIEWER.value}
    audit = _FakeAuditLogService()
    cache = _SpyCacheInvalidator()
    service = RBACService(enforcer, repo, audit, cache)

    result = await service.assign_role(
        actor_user_id=None,
        target_user_id=target.id,
        role=Role.REVIEWER,
        request_id=uuid4(),
    )

    assert result.changed is False
    assert result.roles == [Role.REVIEWER]
    assert repo.session.commits == 0
    assert audit.calls == []
    assert cache.user_profile_calls == []


@pytest.mark.asyncio
async def test_remove_role_blocks_last_admin_removal() -> None:
    target = _user()
    repo = _FakeUserRepository([target])
    enforcer = _FakeEnforcer()
    enforcer.roles_by_user[str(target.id)] = {Role.ADMIN.value}
    service = RBACService(enforcer, repo, _FakeAuditLogService())

    with pytest.raises(LastAdminRoleRemovalError):
        await service.remove_role(
            actor_user_id=target.id,
            target_user_id=target.id,
            role=Role.ADMIN,
            request_id=uuid4(),
        )

    assert enforcer.roles_by_user[str(target.id)] == {Role.ADMIN.value}
    assert repo.session.commits == 0


@pytest.mark.asyncio
async def test_remove_role_allows_admin_removal_when_another_admin_exists() -> None:
    target = _user()
    other_admin = _user()
    repo = _FakeUserRepository([target, other_admin])
    enforcer = _FakeEnforcer()
    enforcer.roles_by_user[str(target.id)] = {Role.ADMIN.value}
    enforcer.roles_by_user[str(other_admin.id)] = {Role.ADMIN.value}
    audit = _FakeAuditLogService()
    cache = _SpyCacheInvalidator()
    service = RBACService(enforcer, repo, audit, cache)

    result = await service.remove_role(
        actor_user_id=other_admin.id,
        target_user_id=target.id,
        role=Role.ADMIN,
        request_id=uuid4(),
    )

    assert result.changed is True
    assert result.roles == []
    assert repo.session.commits == 1
    assert audit.calls[0]["before"] == {"roles": ["admin"]}
    assert audit.calls[0]["after"] == {"roles": []}
    assert cache.user_profile_calls == [target.id]


@pytest.mark.asyncio
async def test_role_change_rejects_missing_user() -> None:
    repo = _FakeUserRepository([])
    service = RBACService(_FakeEnforcer(), repo, _FakeAuditLogService())
    missing_user_id = uuid4()

    with pytest.raises(UserNotFoundError):
        await service.assign_role(
            actor_user_id=None,
            target_user_id=missing_user_id,
            role=Role.REVIEWER,
            request_id=uuid4(),
        )
