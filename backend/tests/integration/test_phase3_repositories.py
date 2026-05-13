from __future__ import annotations

import asyncio
import time
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import AuditLog, Batch, Prediction  # noqa: F401
from app.domain.enums import AuditAction, BatchSource, BatchState
from app.repositories.audit_log import AuditLogRepository
from app.repositories.batches import BatchRepository
from app.repositories.predictions import PredictionRepository
from tests.integration._docker_utils import (
    docker_available,
    pick_free_port,
    run_container,
    wait_for_port,
)


async def _wait_for_postgres_ready(database_url: str, *, timeout_seconds: float = 30.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        engine = create_async_engine(database_url)
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                return
        except Exception:
            await asyncio.sleep(0.5)
        finally:
            await engine.dispose()
    raise TimeoutError("Timed out waiting for PostgreSQL readiness.")


# TODO(@bmislol): switch to `alembic upgrade head` once integration test
# infra supports it. create_all bypasses migrations and can mask drift
# between ORM models and migration files.


async def _run_repository_scenario(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
            await conn.run_sync(Base.metadata.create_all)

        async with session_factory() as session:
            batch_repo = BatchRepository(session)
            prediction_repo = PredictionRepository(session)
            audit_repo = AuditLogRepository(session)

            request_id = uuid4()
            created = await batch_repo.create(
                source_filename="scan_001.tif",
                source=BatchSource.SFTP_INGEST,
                sftp_user="vendor-1",
                blob_key="batches/2026/05/13/scan_001.tif",
                state=BatchState.PENDING,
                failure_reason=None,
                request_id=request_id,
                created_by_user_id=None,
            )
            await session.commit()

            fetched = await batch_repo.get(created.id)
            assert fetched is not None
            assert fetched.source == BatchSource.SFTP_INGEST

            failed = await batch_repo.create_failed(
                source_filename="bad.tif",
                sftp_user=None,
                request_id=uuid4(),
                failure_reason="invalid_image",
            )
            await session.commit()
            assert failed.state == BatchState.FAILED

            updated = await batch_repo.update_state(
                batch_id=created.id,
                new_state=BatchState.PROCESSING,
                failure_reason=None,
            )
            await session.commit()
            assert updated.state == BatchState.PROCESSING

            prediction = await prediction_repo.create(
                batch_id=created.id,
                label="memo",
                confidence=0.88,
                top5_labels=["memo", "invoice", "letter", "form", "budget"],
                top5_confidences=[0.88, 0.05, 0.03, 0.02, 0.02],
                overlay_blob_key="overlays/sample.png",
                model_sha256="abc123",
                request_id=uuid4(),
            )
            await session.commit()
            assert prediction.top5[0] == ("memo", 0.88)

            audit = await audit_repo.create(
                action=AuditAction.BATCH_STATE_CHANGE,
                actor_user_id=None,
                target_type="batch",
                target_id=created.id,
                before_value={"state": "pending"},
                after_value={"state": "processing"},
                request_id=uuid4(),
            )
            await session.commit()
            assert audit.action == AuditAction.BATCH_STATE_CHANGE

            listed_batches = await batch_repo.list(limit=20, offset=0)
            assert len(listed_batches) >= 2
            recent_predictions = await prediction_repo.list_recent(limit=10)
            assert len(recent_predictions) >= 1
            listed_audits = await audit_repo.list(limit=10, offset=0)
            assert len(listed_audits) >= 1
    finally:
        await engine.dispose()


@pytest.mark.integration
def test_phase3_repository_methods_against_postgres() -> None:
    if not docker_available():
        pytest.skip("Docker is not available for integration tests.")

    host_port = pick_free_port()
    env = {
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "postgres",
        "POSTGRES_DB": "postgres",
    }
    with run_container(
        image="postgres:16-alpine",
        ports={host_port: 5432},
        env=env,
    ):
        wait_for_port("127.0.0.1", host_port)
        database_url = f"postgresql+asyncpg://postgres:postgres@127.0.0.1:{host_port}/postgres"
        asyncio.run(_wait_for_postgres_ready(database_url))
        asyncio.run(_run_repository_scenario(database_url))
