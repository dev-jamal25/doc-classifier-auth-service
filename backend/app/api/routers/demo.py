from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.users import current_active_user
from app.api.deps import (
    cache_invalidator_dependency,
    db_session_dependency,
    request_id_dependency,
)
from app.core.lifespan import AppContext
from app.db.models import User
from app.infra.blob import BlobClient
from app.infra.queue import QueueClient
from app.repositories.batches import BatchRepository
from app.services.batches import BatchService
from app.services.cache import ServiceCacheInvalidator
from app.services.demo_ingest import DemoIngestError, DemoIngestService


def _get_demo_ingest_service(
    request: Request,
    session: AsyncSession = db_session_dependency,
    cache_invalidator: ServiceCacheInvalidator = cache_invalidator_dependency,
) -> DemoIngestService:
    context: AppContext = request.app.state.context
    blob_client = BlobClient(
        endpoint=context.settings.minio_endpoint,
        access_key=context.secrets.minio.access_key,
        secret_key=context.secrets.minio.secret_key,
    )
    queue_client = QueueClient(
        redis_url=context.secrets.redis.url,
        queue_name=context.settings.worker_queue_name,
    )
    batch_service = BatchService(BatchRepository(session), cache_invalidator)
    return DemoIngestService(
        batch_service, blob_client, queue_client, context.settings.minio_raw_bucket
    )


class IngestResponse(BaseModel):
    batch_id: str
    state: str


router = APIRouter(tags=["demo"])

current_active_user_dependency = Depends(current_active_user)
demo_ingest_service_dependency = Depends(_get_demo_ingest_service)
file_upload = File(...)


@router.post("/demo/ingest", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def demo_ingest(
    file: UploadFile = file_upload,
    user: User = current_active_user_dependency,
    request_id: UUID = request_id_dependency,
    service: DemoIngestService = demo_ingest_service_dependency,
) -> IngestResponse:
    file_bytes = await file.read()
    filename = file.filename or "upload.tiff"
    content_type = file.content_type or "image/tiff"

    try:
        batch = await service.ingest(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
            user_id=user.id,
            request_id=request_id,
        )
    except DemoIngestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc

    return IngestResponse(batch_id=str(batch.id), state=batch.state)
