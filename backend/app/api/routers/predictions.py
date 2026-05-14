# TODO(auth): protect with current_user dependency once fastapi-users/Vault setup is ready.
# TODO(authz): enforce admin/reviewer/auditor permissions through Casbin.

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_prediction_service
from app.api.schemas.predictions import PredictionListResponse
from app.services.predictions import PredictionService

prediction_service_dependency = Depends(get_prediction_service)
predictions_limit_query = Query(50, ge=1, le=100)

router = APIRouter(tags=["predictions"])


@router.get("/predictions/recent", response_model=PredictionListResponse)
async def list_recent_predictions(
    limit: int = predictions_limit_query,
    service: PredictionService = prediction_service_dependency,
) -> PredictionListResponse:
    predictions = await service.list_recent(limit=limit)
    return PredictionListResponse.from_domain_list(predictions)
