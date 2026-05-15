from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi_users.exceptions import UserAlreadyExists

from app.db.models import User
from app.entrypoints.bootstrap_admin import ensure_admin_user


class _FakeUserManager:
    def __init__(self, *, raise_existing: bool = False) -> None:
        self.raise_existing = raise_existing
        self.calls: list[dict] = []

    async def create(self, user_create, safe: bool = True) -> User:
        self.calls.append({"user_create": user_create, "safe": safe})
        if self.raise_existing:
            raise UserAlreadyExists()
        return User(
            id=uuid4(),
            email=user_create.email,
            hashed_password="hashed",
            is_active=user_create.is_active,
            is_superuser=user_create.is_superuser,
            is_verified=user_create.is_verified,
        )


@pytest.mark.asyncio
async def test_ensure_admin_user_creates_active_plain_user() -> None:
    manager = _FakeUserManager()

    user = await ensure_admin_user(
        manager,
        email="admin@example.com",
        password="TempPass123!",
    )

    assert user is not None
    assert user.email == "admin@example.com"
    assert user.is_active is True
    assert user.is_superuser is False
    assert not hasattr(user, "role")
    assert manager.calls[0]["safe"] is False


@pytest.mark.asyncio
async def test_ensure_admin_user_is_idempotent_when_user_exists() -> None:
    manager = _FakeUserManager(raise_existing=True)

    user = await ensure_admin_user(
        manager,
        email="admin@example.com",
        password="TempPass123!",
    )

    assert user is None
    assert manager.calls[0]["safe"] is False
