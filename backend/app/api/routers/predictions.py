from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_prediction_service, request_id_dependency, require_permission
from app.api.schemas.predictions import (
    PredictionListResponse,
    PredictionResponse,
    PredictionReviewRequest,
)
from app.db.models import User
from app.domain.errors import PredictionNotFoundError, PredictionReviewNotAllowedError
from app.services.predictions import PredictionService

prediction_service_dependency = Depends(get_prediction_service)
predictions_read_dependency = Depends(require_permission("predictions", "read"))
predictions_relabel_dependency = Depends(require_permission("predictions", "relabel"))
predictions_limit_query = Query(50, ge=1, le=100)

router = APIRouter(tags=["predictions"])


@router.get("/predictions/recent", response_model=PredictionListResponse)
async def list_recent_predictions(
    limit: int = predictions_limit_query,
    _user: User = predictions_read_dependency,
    service: PredictionService = prediction_service_dependency,
) -> PredictionListResponse:
    predictions = await service.list_recent(limit=limit)
    return PredictionListResponse.from_domain_list(predictions)


@router.patch("/predictions/{prediction_id}/review", response_model=PredictionResponse)
async def review_prediction(
    prediction_id: UUID,
    payload: PredictionReviewRequest,
    user: User = predictions_relabel_dependency,
    request_id: UUID = request_id_dependency,
    service: PredictionService = prediction_service_dependency,
) -> PredictionResponse:
    try:
        prediction = await service.relabel_prediction(
            prediction_id=prediction_id,
            reviewed_label=payload.reviewed_label,
            reviewed_by_user_id=user.id,
            request_id=request_id,
        )
    except PredictionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found",
        ) from exc
    except PredictionReviewNotAllowedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Prediction is not eligible for review",
        ) from exc

    return PredictionResponse.from_domain(prediction)
