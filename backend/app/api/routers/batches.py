from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_batch_service, require_permission
from app.api.schemas.batches import BatchListResponse, BatchResponse
from app.db.models import User
from app.domain.enums import BatchState
from app.services.batches import BatchService

batch_service_dependency = Depends(get_batch_service)
batches_read_dependency = Depends(require_permission("batches", "read"))
batches_limit_query = Query(50, ge=1, le=100)
batches_offset_query = Query(0, ge=0)
batches_state_query = Query(None)

router = APIRouter(tags=["batches"])


@router.get("/batches", response_model=BatchListResponse)
async def list_batches(
    limit: int = batches_limit_query,
    offset: int = batches_offset_query,
    state: BatchState | None = batches_state_query,
    _user: User = batches_read_dependency,
    service: BatchService = batch_service_dependency,
) -> BatchListResponse:
    batches = await service.list_batches(limit=limit, offset=offset, state=state)
    return BatchListResponse.from_domain_list(batches)


@router.get("/batches/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: UUID,
    _user: User = batches_read_dependency,
    service: BatchService = batch_service_dependency,
) -> BatchResponse:
    batch = await service.get_batch(batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    return BatchResponse.from_domain(batch)
