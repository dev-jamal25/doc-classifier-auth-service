from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_audit_log_service
from app.api.routers.admin import router as admin_router
from app.domain.audit_log import AuditLogEntry
from app.domain.enums import AuditAction
from tests.unit.fakes import FakeAuditLogService


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


def _admin_app(fake_service: FakeAuditLogService) -> FastAPI:
    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[get_audit_log_service] = lambda: fake_service
    return app


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
