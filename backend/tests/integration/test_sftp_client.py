from __future__ import annotations

import time
from datetime import UTC, datetime

import paramiko
import pytest

from app.infra.sftp import SftpClient
from tests.integration._docker_utils import (
    docker_available,
    pick_free_port,
    run_container,
    wait_for_port,
)


def _wait_for_sftp_login(port: int, *, timeout_seconds: float = 30.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname="127.0.0.1",
                port=port,
                username="ituser",
                password="itpass",
                timeout=2.0,
                look_for_keys=False,
                allow_agent=False,
            )
            return
        except Exception:
            time.sleep(0.5)
        finally:
            client.close()
    raise TimeoutError("Timed out waiting for SFTP server login readiness.")


def _seed_remote_file(port: int, *, path: str, payload: bytes) -> None:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname="127.0.0.1",
        port=port,
        username="ituser",
        password="itpass",
        timeout=5.0,
        look_for_keys=False,
        allow_agent=False,
    )
    try:
        sftp = client.open_sftp()
        with sftp.open(path, mode="wb") as remote_file:
            remote_file.write(payload)
    finally:
        client.close()


@pytest.mark.integration
def test_sftp_client_list_download_move_delete() -> None:
    if not docker_available():
        pytest.skip("Docker is not available for integration tests.")

    host_port = pick_free_port()
    with run_container(
        image="atmoz/sftp:latest",
        ports={host_port: 22},
        command=["ituser:itpass:::upload"],
    ):
        wait_for_port("127.0.0.1", host_port)
        _wait_for_sftp_login(host_port)

        payload = b"sample-bytes"
        remote_path = "/upload/scan_001.tif"
        _seed_remote_file(host_port, path=remote_path, payload=payload)

        sftp = SftpClient(
            host="127.0.0.1",
            port=host_port,
            username="ituser",
            password="itpass",
            quarantine_dir="/upload/quarantine",
        )
        assert sftp.health_check() is True

        listed = sftp.list_new_files("/upload")
        assert any(item.name == "scan_001.tif" and item.size == len(payload) for item in listed)

        stat_info = sftp.stat(remote_path)
        assert stat_info.name == "scan_001.tif"
        assert stat_info.size == len(payload)

        downloaded = sftp.download_file(remote_path)
        assert downloaded == payload

        sftp.move_to_quarantine(remote_path)
        quarantined = sftp.list_new_files("/upload/quarantine")
        assert any(item.name.startswith("scan_001.") and item.name.endswith(".tif") for item in quarantined)

        quarantined_file = next(item for item in quarantined if item.name.startswith("scan_001."))
        sftp.delete_file(quarantined_file.path)
        quarantined_after_delete = sftp.list_new_files("/upload/quarantine")
        assert all(not item.name.startswith("scan_001.") for item in quarantined_after_delete)
