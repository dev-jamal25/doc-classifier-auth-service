from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.auth.backend import get_jwt_secrets
from app.api.auth.manager import UserManager
from app.api.auth.user_db import get_user_db
from app.api.deps import get_rbac_service
from app.api.routers.auth import router as auth_router
from app.api.schemas.users import UserCreate
from app.domain.rbac import Role
from app.infra.vault import JwtSecrets
from tests.unit.cache_helpers import init_test_cache
from tests.unit.fakes import FakeUserDatabase

JWT_SECRETS = JwtSecrets(secret="route-test-secret" * 3, algorithm="HS256", exp_minutes=30)


class _FakeRBACService:
    def __init__(self, *, roles: list[Role]) -> None:
        self.roles = roles
        self.calls = 0

    async def get_roles_for_user(self, user_id) -> list[Role]:
        self.calls += 1
        return self.roles


def _auth_app(
    fake_user_db: FakeUserDatabase,
    *,
    roles: list[Role] | None = None,
    rbac_service: _FakeRBACService | None = None,
) -> FastAPI:
    init_test_cache()
    app = FastAPI()
    app.include_router(auth_router)
    app.dependency_overrides[get_jwt_secrets] = lambda: JWT_SECRETS
    app.dependency_overrides[get_user_db] = lambda: fake_user_db
    app.dependency_overrides[get_rbac_service] = lambda: (
        rbac_service
        if rbac_service is not None
        else _FakeRBACService(roles=roles if roles is not None else [Role.ADMIN])
    )
    return app


async def _seed_user(
    fake_user_db: FakeUserDatabase,
    *,
    email: str = "admin@example.com",
    password: str = "TempPass123!",
) -> None:
    manager = UserManager(fake_user_db, JWT_SECRETS.secret)
    await manager.create(
        UserCreate(email=email, password=password, is_active=True),
        safe=False,
    )


@pytest.mark.asyncio
async def test_me_without_token_returns_401() -> None:
    fake_user_db = FakeUserDatabase()
    transport = ASGITransport(app=_auth_app(fake_user_db))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_token_can_access_me() -> None:
    fake_user_db = FakeUserDatabase()
    await _seed_user(fake_user_db)
    transport = ASGITransport(app=_auth_app(fake_user_db))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login_response = await client.post(
            "/auth/login",
            data={
                "username": "admin@example.com",
                "password": "TempPass123!",
            },
        )
        token = login_response.json()["access_token"]
        me_response = await client.get(
            "/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert login_response.status_code == 200
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "admin@example.com"
    assert me_response.json()["roles"] == ["admin"]


@pytest.mark.asyncio
async def test_me_uses_response_cache_on_second_read() -> None:
    fake_user_db = FakeUserDatabase()
    await _seed_user(fake_user_db)
    rbac = _FakeRBACService(roles=[Role.ADMIN])
    transport = ASGITransport(app=_auth_app(fake_user_db, rbac_service=rbac))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login_response = await client.post(
            "/auth/login",
            data={
                "username": "admin@example.com",
                "password": "TempPass123!",
            },
        )
        token = login_response.json()["access_token"]
        first_response = await client.get(
            "/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        second_response = await client.get(
            "/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()
    assert rbac.calls == 1


@pytest.mark.asyncio
async def test_me_returns_empty_roles_when_user_has_no_casbin_roles() -> None:
    fake_user_db = FakeUserDatabase()
    await _seed_user(fake_user_db)
    transport = ASGITransport(app=_auth_app(fake_user_db, roles=[]))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login_response = await client.post(
            "/auth/login",
            data={
                "username": "admin@example.com",
                "password": "TempPass123!",
            },
        )
        token = login_response.json()["access_token"]
        me_response = await client.get(
            "/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert me_response.status_code == 200
    assert me_response.json()["roles"] == []


def test_public_register_route_is_not_mounted() -> None:
    app = _auth_app(FakeUserDatabase())

    assert "/auth/register" not in {route.path for route in app.routes}
