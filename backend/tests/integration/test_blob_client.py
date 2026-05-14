from __future__ import annotations

import pytest

from app.infra.blob import BlobClient
from tests.integration._docker_utils import (
    docker_available,
    pick_free_port,
    run_container,
    wait_for_http,
    wait_for_port,
)


@pytest.mark.integration
def test_blob_client_round_trip_against_minio() -> None:
    if not docker_available():
        pytest.skip("Docker is not available for integration tests.")

    host_port = pick_free_port()
    env = {
        "MINIO_ROOT_USER": "minioadmin",
        "MINIO_ROOT_PASSWORD": "minioadmin",
    }
    with run_container(
        image="minio/minio:latest",
        ports={host_port: 9000},
        env=env,
        command=["server", "/data"],
    ):
        wait_for_port("127.0.0.1", host_port)
        wait_for_http(f"http://127.0.0.1:{host_port}/minio/health/live")

        blob = BlobClient(
            endpoint=f"http://127.0.0.1:{host_port}",
            access_key="minioadmin",
            secret_key="minioadmin",
        )
        assert blob.health_check() is True

        bucket = "phase2-minio-it"
        key = "samples/payload.bin"
        payload = b"0123456789"
        blob.ensure_bucket(bucket)
        blob.put_object(bucket, key, payload, "application/octet-stream")

        downloaded = blob.download_file(bucket, key)
        assert downloaded == payload
