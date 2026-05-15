from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.domain.batches import Batch
from app.domain.queue import ClassificationJob
from app.infra.blob import BlobClient, BlobError
from app.infra.queue import QueueClient, QueueError
from app.services.batches import BatchService

_MAX_FILE_SIZE = 50 * 1024 * 1024
_ALLOWED_EXTENSIONS = {".tif", ".tiff"}
_ALLOWED_CONTENT_TYPES = {"image/tiff", "image/tif"}


class DemoIngestError(ValueError):
    """Raised for file validation failures — maps to HTTP 400."""


class DemoIngestService:
    def __init__(
        self,
        batch_service: BatchService,
        blob_client: BlobClient,
        queue_client: QueueClient,
        raw_bucket: str,
    ) -> None:
        self._batch_service = batch_service
        self._blob_client = blob_client
        self._queue_client = queue_client
        self._raw_bucket = raw_bucket

    async def ingest(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        user_id: UUID,
        request_id: UUID,
    ) -> Batch:
        if len(file_bytes) == 0:
            raise DemoIngestError("File is empty.")
        if len(file_bytes) > _MAX_FILE_SIZE:
            mb = len(file_bytes) / (1024 * 1024)
            raise DemoIngestError(f"File is {mb:.1f} MB — exceeds the 50 MB limit.")

        ext = f".{filename.rsplit('.', 1)[-1].lower()}" if "." in filename else ""
        if ext not in _ALLOWED_EXTENSIONS and content_type not in _ALLOWED_CONTENT_TYPES:
            raise DemoIngestError("Unsupported file type. Upload a TIFF (.tif or .tiff) file.")

        today = datetime.now(UTC).strftime("%Y/%m/%d")
        blob_key = f"batches/{today}/{request_id}/{filename}"

        try:
            self._blob_client.put_object(self._raw_bucket, blob_key, file_bytes, "image/tiff")
        except BlobError as exc:
            raise RuntimeError("Failed to upload file to storage.") from exc

        batch = await self._batch_service.create_from_demo_upload(
            blob_key=blob_key,
            source_filename=filename,
            user_id=user_id,
            request_id=request_id,
        )

        job = ClassificationJob(
            batch_id=batch.id,
            blob_key=blob_key,
            source_filename=filename,
            sftp_user=None,
            request_id=request_id,
            received_at=datetime.now(UTC),
        )
        try:
            self._queue_client.enqueue_classification(job)
        except QueueError as exc:
            raise RuntimeError("Failed to enqueue classification job.") from exc

        return batch
