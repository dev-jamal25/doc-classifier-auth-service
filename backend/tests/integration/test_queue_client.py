from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from redis import Redis
from rq.job import Job

from app.domain.queue import ClassificationJob
from app.infra.queue import DEFAULT_CLASSIFICATION_HANDLER, QueueClient
from tests.integration._docker_utils import (
    docker_available,
    pick_free_port,
    run_container,
    wait_for_port,
)


@pytest.mark.integration
def test_queue_client_round_trip_against_redis() -> None:
    if not docker_available():
        pytest.skip("Docker is not available for integration tests.")

    host_port = pick_free_port()
    with run_container(image="redis:7-alpine", ports={host_port: 6379}):
        wait_for_port("127.0.0.1", host_port)

        redis_url = f"redis://127.0.0.1:{host_port}/0"
        queue_client = QueueClient(redis_url=redis_url, queue_name="doc-jobs-it")
        assert queue_client.health_check() is True

        payload = ClassificationJob(
            batch_id=uuid4(),
            blob_key="batches/2026/05/13/abc123.tif",
            source_filename="scan_001.tif",
            sftp_user="vendor-1",
            request_id=uuid4(),
            received_at=datetime.now(UTC),
        )
        job_id = queue_client.enqueue_classification(payload)
        assert job_id

        redis = Redis.from_url(redis_url)
        queued_job = Job.fetch(job_id, connection=redis)
        stored_payload = queued_job.args[0]
        assert queued_job.func_name == DEFAULT_CLASSIFICATION_HANDLER
        assert stored_payload["batch_id"] == str(payload.batch_id)
        assert stored_payload["blob_key"] == payload.blob_key
        assert stored_payload["source_filename"] == payload.source_filename
        assert stored_payload["sftp_user"] == payload.sftp_user
        assert stored_payload["request_id"] == str(payload.request_id)
