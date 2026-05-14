from __future__ import annotations

import asyncio
import logging
import posixpath
import re
import signal
from collections import OrderedDict
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from app.core.config import Settings
from app.core.lifespan import AppContext, lifespan
from app.core.logging import request_id_var
from app.domain.queue import ClassificationJob
from app.domain.sftp import FileInfo
from app.infra.blob import BlobClient, BlobError
from app.infra.queue import QueueClient, QueueError
from app.infra.sftp import SftpClient, SftpError
from app.repositories.batches import BatchRepository
from app.services.batches import BatchService

logger = logging.getLogger(__name__)

_FAILURE_EMPTY_FILE = "empty file"
_FAILURE_UNSUPPORTED_TYPE = "unsupported file type"
_FAILURE_OVERSIZED = "file exceeds 50MB"
_FAILURE_CORRUPTED_TIFF = "corrupted TIFF"


class HasBatchId(Protocol):
    id: UUID


class PendingBatchWriter(Protocol):
    async def __call__(
        self,
        *,
        blob_key: str,
        source_filename: str,
        sftp_user: str | None,
        request_id: UUID,
    ) -> HasBatchId: ...


class FailedBatchWriter(Protocol):
    async def __call__(
        self,
        *,
        source_filename: str,
        sftp_user: str | None,
        request_id: UUID,
        failure_reason: str,
    ) -> HasBatchId: ...


DedupKey = tuple[str | None, str, int, int]


class InMemoryDedupStore:
    def __init__(self, *, max_items: int = 8192) -> None:
        self._max_items = max_items
        self._store: OrderedDict[DedupKey, None] = OrderedDict()

    def seen(self, key: DedupKey) -> bool:
        return key in self._store

    def remember(self, key: DedupKey) -> None:
        self._store[key] = None
        self._store.move_to_end(key)
        if len(self._store) > self._max_items:
            self._store.popitem(last=False)


def is_supported_tiff_extension(filename: str) -> bool:
    lowered = filename.lower()
    return lowered.endswith(".tif") or lowered.endswith(".tiff")


def has_tiff_magic_bytes(payload: bytes) -> bool:
    magic_candidates = (
        b"II*\x00",  # classic little-endian TIFF
        b"MM\x00*",  # classic big-endian TIFF
        b"II+\x00",  # BigTIFF little-endian
        b"MM\x00+",  # BigTIFF big-endian
    )
    return any(payload.startswith(candidate) for candidate in magic_candidates)


_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_filename(filename: str) -> str:
    basename = posixpath.basename(filename)
    cleaned = _SAFE_FILENAME.sub("_", basename)
    return cleaned or "file"


def build_blob_key(file_info: FileInfo) -> str:
    safe_name = _sanitize_filename(file_info.name)
    mtime_epoch = int(file_info.mtime.timestamp())
    day = file_info.mtime.astimezone(UTC)
    return f"sftp/{day:%Y/%m/%d}/{mtime_epoch}-{file_info.size}-{safe_name}"


def build_dedup_key(*, sftp_user: str | None, file_info: FileInfo) -> DedupKey:
    mtime_epoch = int(file_info.mtime.timestamp())
    return (sftp_user, file_info.name, mtime_epoch, file_info.size)


def _metadata_failure_reason(*, file_info: FileInfo, max_size_bytes: int) -> str | None:
    if file_info.size <= 0:
        return _FAILURE_EMPTY_FILE
    if file_info.size > max_size_bytes:
        return _FAILURE_OVERSIZED
    return None


def datetime_now_utc() -> datetime:
    return datetime.now(UTC)


async def _sleep_until_next_poll(stop_event: asyncio.Event, *, interval_seconds: int) -> None:
    if interval_seconds <= 0:
        return
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
    except TimeoutError:
        return


def _register_shutdown_signals(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()

    def _handle_signal(sig_name: str) -> None:
        logger.info(
            "Shutdown signal received.",
            extra={
                "event": "sftp_ingest_shutdown_requested",
                "signal": sig_name,
            },
        )
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal, sig.name)
        except NotImplementedError:

            def _fallback_handler(
                _signum: int,
                _frame: object,
                _sig_name: str = sig.name,
            ) -> None:
                _handle_signal(_sig_name)

            signal.signal(sig, _fallback_handler)


def _load_async_session_factory():
    from app.db.session import async_session_factory

    return async_session_factory


async def write_pending_batch(
    *,
    blob_key: str,
    source_filename: str,
    sftp_user: str | None,
    request_id: UUID,
) -> HasBatchId:
    session_factory = _load_async_session_factory()
    async with session_factory() as session:
        service = BatchService(BatchRepository(session))
        async with session.begin():
            return await service.create_from_sftp_drop(
                blob_key=blob_key,
                source_filename=source_filename,
                sftp_user=sftp_user,
                request_id=request_id,
            )


async def write_failed_batch(
    *,
    source_filename: str,
    sftp_user: str | None,
    request_id: UUID,
    failure_reason: str,
) -> HasBatchId:
    session_factory = _load_async_session_factory()
    async with session_factory() as session:
        service = BatchService(BatchRepository(session))
        async with session.begin():
            return await service.create_failed_batch(
                source_filename=source_filename,
                sftp_user=sftp_user,
                request_id=request_id,
                failure_reason=failure_reason,
            )


async def _handle_malformed_file(
    *,
    file_info: FileInfo,
    request_id: UUID,
    sftp_user: str | None,
    failure_reason: str,
    dedup_key: DedupKey,
    dedup_store: InMemoryDedupStore,
    sftp_client: SftpClient,
    failed_batch_writer: FailedBatchWriter,
) -> None:
    try:
        failed_batch = await failed_batch_writer(
            source_filename=file_info.name,
            sftp_user=sftp_user,
            request_id=request_id,
            failure_reason=failure_reason,
        )
    except Exception:
        logger.exception(
            "Failed to persist malformed batch record.",
            extra={
                "event": "sftp_malformed_batch_persist_failed",
                "source_filename": file_info.name,
                "failure_reason": failure_reason,
            },
        )
        return

    quarantined = False
    try:
        sftp_client.move_to_quarantine(file_info.path, request_id=str(request_id))
        quarantined = True
    except SftpError:
        logger.exception(
            "Failed moving malformed file to quarantine.",
            extra={
                "event": "sftp_quarantine_failed",
                "source_filename": file_info.name,
                "failure_reason": failure_reason,
                "batch_id": str(failed_batch.id),
            },
        )

    dedup_store.remember(dedup_key)
    logger.warning(
        "Rejected malformed SFTP file.",
        extra={
            "event": "sftp_file_rejected",
            "source_filename": file_info.name,
            "failure_reason": failure_reason,
            "batch_id": str(failed_batch.id),
            "quarantined": quarantined,
        },
    )


async def process_sftp_file(
    *,
    file_info: FileInfo,
    sftp_user: str | None,
    sftp_client: SftpClient,
    blob_client: BlobClient,
    queue_client: QueueClient,
    settings: Settings,
    dedup_store: InMemoryDedupStore,
    pending_batch_writer: PendingBatchWriter,
    failed_batch_writer: FailedBatchWriter,
    request_id_factory: Callable[[], UUID] = uuid4,
    received_at_factory: Callable[[], datetime] = datetime_now_utc,
) -> None:
    try:
        latest = sftp_client.stat(file_info.path)
    except SftpError:
        logger.exception(
            "Failed reading SFTP file metadata.",
            extra={
                "event": "sftp_file_stat_failed",
                "source_filename": file_info.name,
                "remote_path": file_info.path,
            },
        )
        return

    dedup_key = build_dedup_key(sftp_user=sftp_user, file_info=latest)
    if dedup_store.seen(dedup_key):
        logger.info(
            "Skipping duplicate SFTP file.",
            extra={
                "event": "sftp_file_dedup_skipped",
                "source_filename": latest.name,
                "remote_path": latest.path,
            },
        )
        return

    request_id = request_id_factory()
    request_token = request_id_var.set(str(request_id))
    try:
        logger.info(
            "Processing SFTP file.",
            extra={
                "event": "sftp_file_processing_started",
                "source_filename": latest.name,
                "remote_path": latest.path,
                "size_bytes": latest.size,
            },
        )

        metadata_reason = _metadata_failure_reason(
            file_info=latest,
            max_size_bytes=settings.max_sftp_file_size_bytes,
        )
        if metadata_reason is not None:
            await _handle_malformed_file(
                file_info=latest,
                request_id=request_id,
                sftp_user=sftp_user,
                failure_reason=metadata_reason,
                dedup_key=dedup_key,
                dedup_store=dedup_store,
                sftp_client=sftp_client,
                failed_batch_writer=failed_batch_writer,
            )
            return

        if not is_supported_tiff_extension(latest.name):
            await _handle_malformed_file(
                file_info=latest,
                request_id=request_id,
                sftp_user=sftp_user,
                failure_reason=_FAILURE_UNSUPPORTED_TYPE,
                dedup_key=dedup_key,
                dedup_store=dedup_store,
                sftp_client=sftp_client,
                failed_batch_writer=failed_batch_writer,
            )
            return

        try:
            payload = sftp_client.download_file(latest.path)
        except SftpError:
            logger.exception(
                "Failed downloading SFTP file.",
                extra={
                    "event": "sftp_download_failed",
                    "source_filename": latest.name,
                    "remote_path": latest.path,
                },
            )
            return

        if not has_tiff_magic_bytes(payload):
            await _handle_malformed_file(
                file_info=latest,
                request_id=request_id,
                sftp_user=sftp_user,
                failure_reason=_FAILURE_CORRUPTED_TIFF,
                dedup_key=dedup_key,
                dedup_store=dedup_store,
                sftp_client=sftp_client,
                failed_batch_writer=failed_batch_writer,
            )
            return

        blob_key = build_blob_key(latest)
        try:
            blob_client.put_object(
                settings.minio_raw_bucket,
                blob_key,
                payload,
                content_type="image/tiff",
            )
        except BlobError:
            logger.exception(
                "Failed uploading SFTP file to blob storage.",
                extra={
                    "event": "blob_upload_failed",
                    "source_filename": latest.name,
                    "blob_key": blob_key,
                },
            )
            return

        try:
            pending_batch = await pending_batch_writer(
                blob_key=blob_key,
                source_filename=latest.name,
                sftp_user=sftp_user,
                request_id=request_id,
            )
        except Exception:
            logger.exception(
                "Failed creating pending batch after blob upload.",
                extra={
                    "event": "pending_batch_persist_failed",
                    "source_filename": latest.name,
                    "blob_key": blob_key,
                },
            )
            return

        job = ClassificationJob(
            batch_id=pending_batch.id,
            blob_key=blob_key,
            source_filename=latest.name,
            sftp_user=sftp_user,
            request_id=request_id,
            received_at=received_at_factory(),
        )

        try:
            queue_job_id = queue_client.enqueue_classification(job)
        except QueueError:
            logger.exception(
                "Failed enqueuing classification job.",
                extra={
                    "event": "queue_enqueue_failed",
                    "source_filename": latest.name,
                    "batch_id": str(pending_batch.id),
                },
            )
            return

        try:
            sftp_client.delete_file(latest.path)
        except SftpError:
            # Job is already accepted; mark dedup to avoid double enqueueing the same file.
            dedup_store.remember(dedup_key)
            logger.exception(
                "Failed deleting source SFTP file after enqueue.",
                extra={
                    "event": "sftp_delete_failed_after_enqueue",
                    "source_filename": latest.name,
                    "batch_id": str(pending_batch.id),
                    "queue_job_id": queue_job_id,
                },
            )
            return

        dedup_store.remember(dedup_key)
        logger.info(
            "SFTP file ingested successfully.",
            extra={
                "event": "sftp_file_ingested",
                "source_filename": latest.name,
                "batch_id": str(pending_batch.id),
                "blob_key": blob_key,
                "queue_job_id": queue_job_id,
            },
        )
    finally:
        request_id_var.reset(request_token)


def _assert_runtime_dependencies(
    *,
    sftp_client: SftpClient,
    blob_client: BlobClient,
    queue_client: QueueClient,
    settings: Settings,
) -> None:
    if not sftp_client.health_check():
        raise RuntimeError("SFTP health check failed at startup.")
    if not blob_client.health_check():
        raise RuntimeError("Blob storage health check failed at startup.")
    blob_client.ensure_bucket(settings.minio_raw_bucket)
    if not queue_client.health_check():
        raise RuntimeError("Queue health check failed at startup.")


async def run_sftp_ingest(context: AppContext) -> None:
    settings = context.settings
    secrets = context.secrets

    sftp_client = SftpClient(
        host=settings.sftp_host,
        port=settings.sftp_port,
        username=secrets.sftp.username,
        password=secrets.sftp.password,
        quarantine_dir=settings.sftp_quarantine_dir,
    )
    blob_client = BlobClient(
        endpoint=settings.minio_endpoint,
        access_key=secrets.minio.access_key,
        secret_key=secrets.minio.secret_key,
    )
    queue_client = QueueClient(
        redis_url=secrets.redis.url,
        queue_name=settings.worker_queue_name,
    )
    dedup_store = InMemoryDedupStore()

    try:
        _assert_runtime_dependencies(
            sftp_client=sftp_client,
            blob_client=blob_client,
            queue_client=queue_client,
            settings=settings,
        )

        stop_event = asyncio.Event()
        _register_shutdown_signals(stop_event)

        logger.info(
            "SFTP ingest started.",
            extra={
                "event": "sftp_ingest_started",
                "poll_interval_seconds": settings.sftp_poll_interval_seconds,
                "remote_dir": settings.sftp_remote_dir,
                "queue_name": settings.worker_queue_name,
                "raw_bucket": settings.minio_raw_bucket,
            },
        )

        while not stop_event.is_set():
            try:
                files = sftp_client.list_new_files(settings.sftp_remote_dir)
            except SftpError:
                logger.exception(
                    "Failed polling SFTP directory.",
                    extra={
                        "event": "sftp_poll_failed",
                        "remote_dir": settings.sftp_remote_dir,
                    },
                )
                await _sleep_until_next_poll(
                    stop_event,
                    interval_seconds=settings.sftp_poll_interval_seconds,
                )
                continue

            if files:
                logger.info(
                    "Discovered files in SFTP input directory.",
                    extra={
                        "event": "sftp_files_discovered",
                        "remote_dir": settings.sftp_remote_dir,
                        "file_count": len(files),
                    },
                )

            for file_info in files:
                if stop_event.is_set():
                    break
                await process_sftp_file(
                    file_info=file_info,
                    sftp_user=secrets.sftp.username,
                    sftp_client=sftp_client,
                    blob_client=blob_client,
                    queue_client=queue_client,
                    settings=settings,
                    dedup_store=dedup_store,
                    pending_batch_writer=write_pending_batch,
                    failed_batch_writer=write_failed_batch,
                )

            await _sleep_until_next_poll(
                stop_event,
                interval_seconds=settings.sftp_poll_interval_seconds,
            )
    finally:
        sftp_client.close()
        logger.info(
            "SFTP ingest stopped.",
            extra={
                "event": "sftp_ingest_stopped",
            },
        )


async def main() -> None:
    async with lifespan("sftp-ingest") as context:
        await run_sftp_ingest(context)


if __name__ == "__main__":
    asyncio.run(main())
