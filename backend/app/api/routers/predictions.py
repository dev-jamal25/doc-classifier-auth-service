from fastapi import APIRouter, Depends, Query
from fastapi_cache.decorator import cache

from app.api.deps import get_prediction_service, require_permission
from app.api.schemas.predictions import PredictionListResponse
from app.db.models import User
from app.infra.cache import CACHE_NAMESPACE_PREDICTIONS_RECENT, CACHE_TTL_PREDICTIONS_SECONDS
from app.services.predictions import PredictionService

prediction_service_dependency = Depends(get_prediction_service)
predictions_read_dependency = Depends(require_permission("predictions", "read"))
predictions_limit_query = Query(50, ge=1, le=100)

router = APIRouter(tags=["predictions"])


@router.get("/predictions/recent", response_model=PredictionListResponse)
@cache(expire=CACHE_TTL_PREDICTIONS_SECONDS, namespace=CACHE_NAMESPACE_PREDICTIONS_RECENT)
async def list_recent_predictions(
    limit: int = predictions_limit_query,
    _user: User = predictions_read_dependency,
    service: PredictionService = prediction_service_dependency,
) -> PredictionListResponse:
    predictions = await service.list_recent(limit=limit)
    return PredictionListResponse.from_domain_list(predictions)
