from uuid import UUID, uuid4

import pytest

from app.db.models import User
from app.domain.rbac import Role, UserRoles
from app.entrypoints.bootstrap_admin_role import (
    BootstrapAdminRoleTargetNotFoundError,
    grant_admin_role_to_existing_user,
)


class _FakeUserRepository:
    def __init__(self, users: list[User]) -> None:
        self.calls: list[dict] = []
        self._users_by_id = {user.id: user for user in users}
        self._users_by_email = {user.email.casefold(): user for user in users}

    async def get(self, user_id: UUID) -> User | None:
        self.calls.append({"method": "get", "user_id": user_id})
        return self._users_by_id.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        self.calls.append({"method": "get_by_email", "email": email})
        return self._users_by_email.get(email.casefold())


class _FakeRBACService:
    def __init__(self, *, changed: bool = True) -> None:
        self.changed = changed
        self.calls: list[dict] = []

    async def assign_role(
        self,
        *,
        actor_user_id,
        target_user_id,
        role,
        request_id,
    ) -> UserRoles:
        self.calls.append(
            {
                "actor_user_id": actor_user_id,
                "target_user_id": target_user_id,
                "role": role,
                "request_id": request_id,
            }
        )
        return UserRoles(user_id=target_user_id, roles=[role], changed=self.changed)


def _user() -> User:
    return User(
        id=uuid4(),
        email="admin@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )


@pytest.mark.asyncio
async def test_grant_admin_role_finds_existing_user_by_id() -> None:
    user = _user()
    repo = _FakeUserRepository([user])
    rbac = _FakeRBACService()

    result = await grant_admin_role_to_existing_user(
        user_repository=repo,
        rbac_service=rbac,
        user_id=user.id,
    )

    assert result.user_id == user.id
    assert result.roles == [Role.ADMIN]
    assert rbac.calls[0]["actor_user_id"] is None
    assert rbac.calls[0]["target_user_id"] == user.id
    assert rbac.calls[0]["role"] == Role.ADMIN


@pytest.mark.asyncio
async def test_grant_admin_role_finds_existing_user_by_email() -> None:
    user = _user()
    repo = _FakeUserRepository([user])
    rbac = _FakeRBACService()

    result = await grant_admin_role_to_existing_user(
        user_repository=repo,
        rbac_service=rbac,
        email="ADMIN@example.com",
    )

    assert result.user_id == user.id
    assert repo.calls == [{"method": "get_by_email", "email": "ADMIN@example.com"}]


@pytest.mark.asyncio
async def test_grant_admin_role_is_idempotent_when_service_reports_no_change() -> None:
    user = _user()
    repo = _FakeUserRepository([user])
    rbac = _FakeRBACService(changed=False)

    result = await grant_admin_role_to_existing_user(
        user_repository=repo,
        rbac_service=rbac,
        email=user.email,
    )

    assert result.changed is False
    assert result.roles == [Role.ADMIN]


@pytest.mark.asyncio
async def test_grant_admin_role_does_not_create_missing_user() -> None:
    repo = _FakeUserRepository([])
    rbac = _FakeRBACService()

    with pytest.raises(BootstrapAdminRoleTargetNotFoundError):
        await grant_admin_role_to_existing_user(
            user_repository=repo,
            rbac_service=rbac,
            email="missing@example.com",
        )

    assert rbac.calls == []
    assert not hasattr(repo, "create")


@pytest.mark.asyncio
async def test_grant_admin_role_requires_exactly_one_target_identifier() -> None:
    repo = _FakeUserRepository([])
    rbac = _FakeRBACService()

    with pytest.raises(ValueError):
        await grant_admin_role_to_existing_user(
            user_repository=repo,
            rbac_service=rbac,
        )
