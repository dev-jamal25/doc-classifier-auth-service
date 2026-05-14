from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Prediction as PredictionModel
from app.domain.predictions import Prediction


class PredictionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

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
        row = PredictionModel(
            batch_id=batch_id,
            label=label,
            confidence=confidence,
            top5_labels=top5_labels,
            top5_confidences=top5_confidences,
            overlay_blob_key=overlay_blob_key,
            model_sha256=model_sha256,
            request_id=request_id,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return Prediction.from_orm_row(row)

    async def get(self, prediction_id: UUID) -> Prediction | None:
        row = await self._session.get(PredictionModel, prediction_id)
        if row is None:
            return None
        return Prediction.from_orm_row(row)

    async def get_by_batch_id(self, batch_id: UUID) -> Prediction | None:
        statement = (
            select(PredictionModel)
            .where(PredictionModel.batch_id == batch_id)
            .order_by(PredictionModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(statement)
        row = result.scalars().first()
        if row is None:
            return None
        return Prediction.from_orm_row(row)

    async def list_recent(self, *, limit: int = 50) -> list[Prediction]:
        statement = select(PredictionModel).order_by(PredictionModel.created_at.desc()).limit(limit)
        result = await self._session.execute(statement)
        rows = result.scalars().all()
        return [Prediction.from_orm_row(row) for row in rows]

    async def update_review(
        self,
        *,
        prediction_id: UUID,
        reviewed_label: str,
        reviewed_by_user_id: UUID,
    ) -> Prediction:
        row = await self._session.get(PredictionModel, prediction_id)
        if row is None:
            raise ValueError(f"Prediction `{prediction_id}` not found.")

        row.reviewed_label = reviewed_label
        row.reviewed_by_user_id = reviewed_by_user_id
        row.reviewed_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(row)
        return Prediction.from_orm_row(row)
