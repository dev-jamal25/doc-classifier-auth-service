from uuid import UUID

from app.domain.predictions import Prediction
from app.repositories.batches import BatchRepository
from app.repositories.predictions import PredictionRepository


class PredictionService:
    def __init__(
        self,
        prediction_repository: PredictionRepository,
        batch_repository: BatchRepository,
    ) -> None:
        self._prediction_repository = prediction_repository
        self._batch_repository = batch_repository

    async def record_prediction(
        self,
        *,
        batch_id: UUID,
        label: str,
        confidence: float,
        top5: list[tuple[str, float]],
        overlay_blob_key: str,
        model_sha256: str,
        request_id: str,
    ) -> Prediction:
        # TODO(impl): insert prediction and update batch state to completed.
        # TODO(cache): invalidate GET /batches/{batch_id} and GET /predictions/recent.
        raise NotImplementedError("PredictionService.record_prediction not yet implemented")

    async def relabel_prediction(
        self,
        *,
        prediction_id: UUID,
        reviewed_label: str,
        reviewed_by_user_id: UUID,
    ) -> Prediction:
        # TODO(authz): enforce reviewer role and confidence < 0.7 constraint.
        # TODO(audit): write relabel audit entry.
        # TODO(cache): invalidate GET /batches/{batch_id} and GET /predictions/recent.
        raise NotImplementedError("PredictionService.relabel_prediction not yet implemented")

    async def list_recent(self, *, limit: int = 50) -> list[Prediction]:
        # TODO(cache): cache GET /predictions/recent with TTL 60s via fastapi-cache2.
        raise NotImplementedError("PredictionService.list_recent not yet implemented")
