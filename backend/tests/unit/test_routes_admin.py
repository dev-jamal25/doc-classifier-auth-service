from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi_users.exceptions import UserAlreadyExists
from httpx import ASGITransport, AsyncClient

from app.api.auth.backend import get_jwt_secrets
from app.api.auth.manager import get_user_manager
from app.api.auth.users import current_active_user
from app.api.deps import get_audit_log_service, get_db_session, get_rbac_service
from app.api.routers.admin import router as admin_router
from app.db.models import User
from app.domain.audit_log import AuditLogEntry
from app.domain.enums import AuditAction
from app.domain.errors import LastAdminRoleRemovalError, UserNotFoundError
from app.domain.rbac import UserRoles
from app.infra.vault import JwtSecrets
from tests.unit.fakes import FakeAuditLogService

JWT_SECRETS = JwtSecrets(secret="route-test-secret" * 3, algorithm="HS256", exp_minutes=30)


def _sample_audit_log_entry() -> AuditLogEntry:
    return AuditLogEntry(
        id=uuid4(),
        actor_user_id=None,
        action=AuditAction.BATCH_STATE_CHANGE,
        target_type="batch",
        target_id=uuid4(),
        before_value=None,
        after_value={"state": "completed"},
        request_id=uuid4(),
        created_at=datetime.now(UTC),
    )


def _sample_user() -> User:
    return User(
        id=uuid4(),
        email="admin@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )


class _FakeRBACService:
    def __init__(
        self,
        *,
        allowed: bool = True,
        assign_result: UserRoles | None = None,
        remove_result: UserRoles | None = None,
        assign_error: Exception | None = None,
        remove_error: Exception | None = None,
    ) -> None:
        self.allowed = allowed
        self.assign_result = assign_result
        self.remove_result = remove_result
        self.assign_error = assign_error
        self.remove_error = remove_error
        self.calls: list[dict] = []

    async def has_permission(self, user_id, obj, act) -> bool:
        self.calls.append({"method": "has_permission", "user_id": user_id, "obj": obj, "act": act})
        return self.allowed

    async def assign_role(self, *, actor_user_id, target_user_id, role, request_id) -> UserRoles:
        self.calls.append(
            {
                "method": "assign_role",
                "actor_user_id": actor_user_id,
                "target_user_id": target_user_id,
                "role": role,
                "request_id": request_id,
            }
        )
        if self.assign_error is not None:
            raise self.assign_error
        return self.assign_result or UserRoles(
            user_id=target_user_id,
            roles=[role],
            changed=True,
        )

    async def remove_role(self, *, actor_user_id, target_user_id, role, request_id) -> UserRoles:
        self.calls.append(
            {
                "method": "remove_role",
                "actor_user_id": actor_user_id,
                "target_user_id": target_user_id,
                "role": role,
                "request_id": request_id,
            }
        )
        if self.remove_error is not None:
            raise self.remove_error
        return self.remove_result or UserRoles(
            user_id=target_user_id,
            roles=[],
            changed=True,
        )


class _FakeUserManager:
    def __init__(self, *, duplicate: bool = False) -> None:
        self.duplicate = duplicate
        self.calls: list[dict] = []

    async def create(self, user_create, safe: bool = True) -> User:
        self.calls.append({"user_create": user_create, "safe": safe})
        if self.duplicate:
            raise UserAlreadyExists()
        return User(
            id=uuid4(),
            email=user_create.email,
            hashed_password=f"hashed:{user_create.password}",
            is_active=user_create.is_active,
            is_superuser=user_create.is_superuser,
            is_verified=user_create.is_verified,
        )


async def _dummy_db_session():
    yield object()


def _admin_app(
    fake_service: FakeAuditLogService,
    *,
    rbac_service: _FakeRBACService | None = None,
    user_manager: _FakeUserManager | None = None,
    authenticate: bool = True,
) -> FastAPI:
    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[get_audit_log_service] = lambda: fake_service
    app.dependency_overrides[get_rbac_service] = lambda: rbac_service or _FakeRBACService()
    app.dependency_overrides[get_user_manager] = lambda: user_manager or _FakeUserManager()
    app.dependency_overrides[get_db_session] = _dummy_db_session
    app.dependency_overrides[get_jwt_secrets] = lambda: JWT_SECRETS
    if authenticate:
        app.dependency_overrides[current_active_user] = _sample_user
    return app


@pytest.mark.asyncio
async def test_list_audit_log_without_token_returns_401() -> None:
    fake = FakeAuditLogService()
    transport = ASGITransport(app=_admin_app(fake, authenticate=False))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/admin/audit-log")

    assert response.status_code == 401
    assert fake.calls == []


@pytest.mark.asyncio
async def test_list_audit_log_forbidden_without_permission() -> None:
    fake = FakeAuditLogService()
    rbac = _FakeRBACService(allowed=False)
    transport = ASGITransport(app=_admin_app(fake, rbac_service=rbac))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/admin/audit-log")

    assert response.status_code == 403
    assert fake.calls == []


@pytest.mark.asyncio
async def test_list_audit_log_returns_items_envelope() -> None:
    entry = _sample_audit_log_entry()
    fake = FakeAuditLogService(entries=[entry])
    transport = ASGITransport(app=_admin_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/admin/audit-log")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(entry.id)


@pytest.mark.asyncio
async def test_list_audit_log_passes_query_params_to_service() -> None:
    fake = FakeAuditLogService()
    transport = ASGITransport(app=_admin_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/admin/audit-log", params={"limit": 50, "offset": 5})

    assert response.status_code == 200
    assert fake.calls == [{"method": "list_entries", "limit": 50, "offset": 5}]


@pytest.mark.asyncio
async def test_list_audit_log_rejects_limit_over_ceiling() -> None:
    fake = FakeAuditLogService()
    transport = ASGITransport(app=_admin_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/admin/audit-log", params={"limit": 999})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_audit_log_rejects_negative_offset() -> None:
    fake = FakeAuditLogService()
    transport = ASGITransport(app=_admin_app(fake))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/admin/audit-log", params={"offset": -1})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_assign_user_role_returns_role_state() -> None:
    target_user_id = uuid4()
    rbac = _FakeRBACService()
    transport = ASGITransport(app=_admin_app(FakeAuditLogService(), rbac_service=rbac))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.put(f"/admin/users/{target_user_id}/roles/reviewer")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": str(target_user_id),
        "roles": ["reviewer"],
        "changed": True,
    }
    assert any(call["method"] == "assign_role" for call in rbac.calls)


@pytest.mark.asyncio
async def test_remove_user_role_returns_role_state() -> None:
    target_user_id = uuid4()
    rbac = _FakeRBACService()
    transport = ASGITransport(app=_admin_app(FakeAuditLogService(), rbac_service=rbac))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.delete(f"/admin/users/{target_user_id}/roles/reviewer")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": str(target_user_id),
        "roles": [],
        "changed": True,
    }
    assert any(call["method"] == "remove_role" for call in rbac.calls)


@pytest.mark.asyncio
async def test_assign_user_role_rejects_unknown_role() -> None:
    target_user_id = uuid4()
    transport = ASGITransport(app=_admin_app(FakeAuditLogService()))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.put(f"/admin/users/{target_user_id}/roles/owner")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_assign_user_role_returns_404_when_target_missing() -> None:
    target_user_id = uuid4()
    rbac = _FakeRBACService(assign_error=UserNotFoundError(target_user_id))
    transport = ASGITransport(app=_admin_app(FakeAuditLogService(), rbac_service=rbac))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.put(f"/admin/users/{target_user_id}/roles/reviewer")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_remove_user_role_returns_409_for_last_admin() -> None:
    target_user_id = uuid4()
    rbac = _FakeRBACService(remove_error=LastAdminRoleRemovalError(target_user_id))
    transport = ASGITransport(app=_admin_app(FakeAuditLogService(), rbac_service=rbac))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.delete(f"/admin/users/{target_user_id}/roles/admin")

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_role_change_rejects_malformed_request_id() -> None:
    target_user_id = uuid4()
    transport = ASGITransport(app=_admin_app(FakeAuditLogService()))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.put(
            f"/admin/users/{target_user_id}/roles/reviewer",
            headers={"X-Request-ID": "not-a-uuid"},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_invite_user_creates_active_plain_user_without_returning_password() -> None:
    fake_audit = FakeAuditLogService()
    rbac = _FakeRBACService()
    user_manager = _FakeUserManager()
    transport = ASGITransport(
        app=_admin_app(fake_audit, rbac_service=rbac, user_manager=user_manager)
    )

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/admin/users/invite",
            json={
                "email": "reviewer@example.com",
                "temporary_password": "TempPass123!",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "reviewer@example.com"
    assert body["is_active"] is True
    assert body["is_superuser"] is False
    assert body["roles"] == []
    assert "password" not in body
    assert "temporary_password" not in body
    assert "hashed_password" not in body
    assert user_manager.calls[0]["safe"] is False
    created = user_manager.calls[0]["user_create"]
    assert created.is_active is True
    assert created.is_superuser is False
    assert not any(call.get("method") == "assign_role" for call in rbac.calls)


@pytest.mark.asyncio
async def test_invite_user_returns_409_for_duplicate_email() -> None:
    user_manager = _FakeUserManager(duplicate=True)
    transport = ASGITransport(app=_admin_app(FakeAuditLogService(), user_manager=user_manager))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/admin/users/invite",
            json={
                "email": "reviewer@example.com",
                "temporary_password": "TempPass123!",
            },
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "User already exists"}


@pytest.mark.asyncio
async def test_invite_user_without_token_returns_401() -> None:
    user_manager = _FakeUserManager()
    transport = ASGITransport(
        app=_admin_app(
            FakeAuditLogService(),
            user_manager=user_manager,
            authenticate=False,
        )
    )

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/admin/users/invite",
            json={
                "email": "reviewer@example.com",
                "temporary_password": "TempPass123!",
            },
        )

    assert response.status_code == 401
    assert user_manager.calls == []


@pytest.mark.asyncio
async def test_invite_user_forbidden_without_manage_roles_permission() -> None:
    rbac = _FakeRBACService(allowed=False)
    user_manager = _FakeUserManager()
    transport = ASGITransport(
        app=_admin_app(
            FakeAuditLogService(),
            rbac_service=rbac,
            user_manager=user_manager,
        )
    )

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/admin/users/invite",
            json={
                "email": "reviewer@example.com",
                "temporary_password": "TempPass123!",
            },
        )

    assert response.status_code == 403
    assert user_manager.calls == []
