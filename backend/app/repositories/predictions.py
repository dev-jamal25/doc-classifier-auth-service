from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.predictions import Prediction


class PredictionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        batch_id: UUID,
        label: str,
        confidence: float,
        top5_labels: list[str],
        top5_confidences: list[float],
        overlay_blob_key: str | None,
        model_sha256: str,
        request_id: UUID,
    ) -> Prediction:
        # TODO(impl): SQL insert and domain model mapping go here.
        raise NotImplementedError("PredictionRepository.create not yet implemented")

    async def get(self, prediction_id: UUID) -> Prediction | None:
        # TODO(impl): SQL select by primary key goes here.
        raise NotImplementedError("PredictionRepository.get not yet implemented")

    async def list_recent(self, *, limit: int = 50) -> list[Prediction]:
        # TODO(impl): SQL listing ordered by created_at DESC goes here.
        raise NotImplementedError("PredictionRepository.list_recent not yet implemented")

    async def update_review(
        self,
        *,
        prediction_id: UUID,
        reviewed_label: str,
        reviewed_by_user_id: UUID,
    ) -> Prediction:
        # TODO(impl): SQL update for reviewer label metadata goes here.
        raise NotImplementedError("PredictionRepository.update_review not yet implemented")
