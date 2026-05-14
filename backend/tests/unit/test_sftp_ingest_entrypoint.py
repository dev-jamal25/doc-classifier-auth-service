from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.domain.queue import ClassificationJob
from app.domain.sftp import FileInfo
from app.entrypoints.sftp_ingest import (
    InMemoryDedupStore,
    build_dedup_key,
    has_tiff_magic_bytes,
    process_sftp_file,
)
from app.infra.blob import BlobError
from app.infra.queue import QueueError


class _FakeSftpClient:
    def __init__(self, *, stat_info: FileInfo, payload: bytes, steps: list[str]) -> None:
        self._stat_info = stat_info
        self._payload = payload
        self._steps = steps
        self.deleted_paths: list[str] = []
        self.quarantined: list[tuple[str, str | None]] = []

    def stat(self, remote_path: str) -> FileInfo:
        self._steps.append("stat")
        assert remote_path == self._stat_info.path
        return self._stat_info

    def download_file(self, remote_path: str) -> bytes:
        self._steps.append("download")
        assert remote_path == self._stat_info.path
        return self._payload

    def delete_file(self, remote_path: str) -> None:
        self._steps.append("delete")
        self.deleted_paths.append(remote_path)

    def move_to_quarantine(self, remote_path: str, *, request_id: str | None = None) -> None:
        self._steps.append("quarantine")
        self.quarantined.append((remote_path, request_id))


class _FakeBlobClient:
    def __init__(self, *, steps: list[str], should_fail: bool = False) -> None:
        self._steps = steps
        self._should_fail = should_fail
        self.put_calls: list[tuple[str, str, bytes, str]] = []

    def put_object(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        self._steps.append("upload")
        if self._should_fail:
            raise BlobError("upload failed")
        self.put_calls.append((bucket, key, data, content_type))


class _FakeQueueClient:
    def __init__(self, *, steps: list[str], should_fail: bool = False) -> None:
        self._steps = steps
        self._should_fail = should_fail
        self.jobs: list[ClassificationJob] = []

    def enqueue_classification(self, job: ClassificationJob) -> str:
        self._steps.append("enqueue")
        if self._should_fail:
            raise QueueError("queue down")
        self.jobs.append(job)
        return "rq-job-1"


def _settings_stub() -> SimpleNamespace:
    return SimpleNamespace(
        max_sftp_file_size_bytes=50 * 1024 * 1024,
        minio_raw_bucket="documents-raw",
    )


def _sample_file(name: str = "scan_001.tif", size: int = 128) -> FileInfo:
    return FileInfo(
        name=name,
        path=f"/incoming/{name}",
        size=size,
        mtime=datetime(2026, 5, 14, 8, 30, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_process_sftp_file_success_runs_required_write_order() -> None:
    steps: list[str] = []
    file_info = _sample_file()
    sftp = _FakeSftpClient(stat_info=file_info, payload=b"II*\x00payload", steps=steps)
    blob = _FakeBlobClient(steps=steps)
    queue = _FakeQueueClient(steps=steps)
    dedup = InMemoryDedupStore()

    request_id = UUID("11111111-1111-1111-1111-111111111111")
    batch_id = UUID("22222222-2222-2222-2222-222222222222")
    received_at = datetime(2026, 5, 14, 9, 0, tzinfo=UTC)

    async def pending_writer(**kwargs):
        steps.append("create_batch")
        assert kwargs["source_filename"] == "scan_001.tif"
        return SimpleNamespace(id=batch_id)

    async def failed_writer(**kwargs):
        raise AssertionError("failed_writer should not be called on happy path")

    await process_sftp_file(
        file_info=file_info,
        sftp_user="vendor-1",
        sftp_client=sftp,
        blob_client=blob,
        queue_client=queue,
        settings=_settings_stub(),
        dedup_store=dedup,
        pending_batch_writer=pending_writer,
        failed_batch_writer=failed_writer,
        request_id_factory=lambda: request_id,
        received_at_factory=lambda: received_at,
    )

    assert steps == ["stat", "download", "upload", "create_batch", "enqueue", "delete"]
    assert sftp.deleted_paths == ["/incoming/scan_001.tif"]
    assert len(blob.put_calls) == 1
    assert blob.put_calls[0][0] == "documents-raw"
    assert blob.put_calls[0][3] == "image/tiff"

    assert len(queue.jobs) == 1
    queued = queue.jobs[0]
    assert queued.batch_id == batch_id
    assert queued.source_filename == "scan_001.tif"
    assert queued.sftp_user == "vendor-1"
    assert queued.request_id == request_id
    assert queued.received_at == received_at

    dedup_key = build_dedup_key(sftp_user="vendor-1", file_info=file_info)
    assert dedup.seen(dedup_key) is True


@pytest.mark.asyncio
async def test_process_sftp_file_rejects_unsupported_extension_as_failed_batch() -> None:
    steps: list[str] = []
    file_info = _sample_file(name="scan_001.pdf", size=1024)
    sftp = _FakeSftpClient(stat_info=file_info, payload=b"not-used", steps=steps)
    blob = _FakeBlobClient(steps=steps)
    queue = _FakeQueueClient(steps=steps)
    dedup = InMemoryDedupStore()

    request_id = UUID("33333333-3333-3333-3333-333333333333")
    failed_reasons: list[str] = []

    async def pending_writer(**kwargs):
        raise AssertionError("pending_writer should not be called for malformed files")

    async def failed_writer(**kwargs):
        steps.append("create_failed_batch")
        failed_reasons.append(kwargs["failure_reason"])
        return SimpleNamespace(id=UUID("44444444-4444-4444-4444-444444444444"))

    await process_sftp_file(
        file_info=file_info,
        sftp_user="vendor-1",
        sftp_client=sftp,
        blob_client=blob,
        queue_client=queue,
        settings=_settings_stub(),
        dedup_store=dedup,
        pending_batch_writer=pending_writer,
        failed_batch_writer=failed_writer,
        request_id_factory=lambda: request_id,
    )

    assert steps == ["stat", "create_failed_batch", "quarantine"]
    assert failed_reasons == ["unsupported file type"]
    assert sftp.quarantined == [("/incoming/scan_001.pdf", str(request_id))]
    assert sftp.deleted_paths == []
    assert queue.jobs == []
    assert blob.put_calls == []

    dedup_key = build_dedup_key(sftp_user="vendor-1", file_info=file_info)
    assert dedup.seen(dedup_key) is True


@pytest.mark.asyncio
async def test_process_sftp_file_blob_failure_does_not_delete_source_or_mark_dedup() -> None:
    steps: list[str] = []
    file_info = _sample_file()
    sftp = _FakeSftpClient(stat_info=file_info, payload=b"II*\x00payload", steps=steps)
    blob = _FakeBlobClient(steps=steps, should_fail=True)
    queue = _FakeQueueClient(steps=steps)
    dedup = InMemoryDedupStore()

    async def pending_writer(**kwargs):
        raise AssertionError("pending_writer should not be reached when upload fails")

    async def failed_writer(**kwargs):
        raise AssertionError("failed_writer should not be called for transient upload errors")

    await process_sftp_file(
        file_info=file_info,
        sftp_user="vendor-1",
        sftp_client=sftp,
        blob_client=blob,
        queue_client=queue,
        settings=_settings_stub(),
        dedup_store=dedup,
        pending_batch_writer=pending_writer,
        failed_batch_writer=failed_writer,
        request_id_factory=uuid4,
    )

    assert steps == ["stat", "download", "upload"]
    assert sftp.deleted_paths == []
    assert queue.jobs == []

    dedup_key = build_dedup_key(sftp_user="vendor-1", file_info=file_info)
    assert dedup.seen(dedup_key) is False


@pytest.mark.asyncio
async def test_process_sftp_file_queue_failure_does_not_delete_source_or_mark_dedup() -> None:
    steps: list[str] = []
    file_info = _sample_file()
    sftp = _FakeSftpClient(stat_info=file_info, payload=b"II*\x00payload", steps=steps)
    blob = _FakeBlobClient(steps=steps)
    queue = _FakeQueueClient(steps=steps, should_fail=True)
    dedup = InMemoryDedupStore()

    async def pending_writer(**kwargs):
        steps.append("create_batch")
        return SimpleNamespace(id=UUID("55555555-5555-5555-5555-555555555555"))

    async def failed_writer(**kwargs):
        raise AssertionError("failed_writer should not be called for queue failures")

    await process_sftp_file(
        file_info=file_info,
        sftp_user="vendor-1",
        sftp_client=sftp,
        blob_client=blob,
        queue_client=queue,
        settings=_settings_stub(),
        dedup_store=dedup,
        pending_batch_writer=pending_writer,
        failed_batch_writer=failed_writer,
        request_id_factory=uuid4,
    )

    assert steps == ["stat", "download", "upload", "create_batch", "enqueue"]
    assert sftp.deleted_paths == []

    dedup_key = build_dedup_key(sftp_user="vendor-1", file_info=file_info)
    assert dedup.seen(dedup_key) is False


@pytest.mark.asyncio
async def test_process_sftp_file_skips_when_dedup_key_seen() -> None:
    steps: list[str] = []
    file_info = _sample_file()
    dedup = InMemoryDedupStore()
    dedup.remember(build_dedup_key(sftp_user="vendor-1", file_info=file_info))

    sftp = _FakeSftpClient(stat_info=file_info, payload=b"II*\x00payload", steps=steps)
    blob = _FakeBlobClient(steps=steps)
    queue = _FakeQueueClient(steps=steps)

    async def pending_writer(**kwargs):
        raise AssertionError("pending_writer should not be called for dedup hits")

    async def failed_writer(**kwargs):
        raise AssertionError("failed_writer should not be called for dedup hits")

    await process_sftp_file(
        file_info=file_info,
        sftp_user="vendor-1",
        sftp_client=sftp,
        blob_client=blob,
        queue_client=queue,
        settings=_settings_stub(),
        dedup_store=dedup,
        pending_batch_writer=pending_writer,
        failed_batch_writer=failed_writer,
    )

    assert steps == ["stat"]
    assert blob.put_calls == []
    assert queue.jobs == []


def test_has_tiff_magic_bytes_recognizes_classic_and_bigtiff_headers() -> None:
    assert has_tiff_magic_bytes(b"II*\x00payload") is True
    assert has_tiff_magic_bytes(b"MM\x00*payload") is True
    assert has_tiff_magic_bytes(b"II+\x00payload") is True
    assert has_tiff_magic_bytes(b"MM\x00+payload") is True
    assert has_tiff_magic_bytes(b"NOTTIFF") is False
