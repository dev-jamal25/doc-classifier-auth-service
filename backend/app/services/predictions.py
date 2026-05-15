from uuid import UUID

from app.domain.enums import AuditAction, BatchState
from app.domain.errors import BatchAlreadyCompletedError, BatchNotFoundError
from app.domain.predictions import Prediction
from app.repositories.batches import BatchRepository
from app.repositories.predictions import PredictionRepository
from app.services.audit_log import AuditLogService
from app.services.cache import NoOpServiceCacheInvalidator, ServiceCacheInvalidator


class PredictionService:
    def __init__(
        self,
        prediction_repository: PredictionRepository,
        batch_repository: BatchRepository,
        audit_log_service: AuditLogService,
        cache_invalidator: ServiceCacheInvalidator | None = None,
    ) -> None:
        self._prediction_repository = prediction_repository
        self._batch_repository = batch_repository
        self._audit_log_service = audit_log_service
        self._cache_invalidator = cache_invalidator or NoOpServiceCacheInvalidator()

    async def record_prediction(
        self,
        *,
        batch_id: UUID,
        label: str,
        confidence: float,
        top5: list[tuple[str, float]],
        overlay_blob_key: str,
        model_sha256: str,
        request_id: UUID,
    ) -> Prediction:
        if self._prediction_repository.session is not self._batch_repository.session:
            raise ValueError("Repositories must share the same AsyncSession instance.")

        top5_labels: list[str] = [label_name for (label_name, _) in top5]
        top5_confidences: list[float] = [score for (_, score) in top5]
        session = self._prediction_repository.session

        async with session.begin():
            existing_batch = await self._batch_repository.get(batch_id)
            if existing_batch is None:
                raise BatchNotFoundError(batch_id)

            if existing_batch.state == BatchState.COMPLETED:
                existing_prediction = await self._prediction_repository.get_by_batch_id(batch_id)
                if existing_prediction is not None:
                    return existing_prediction

                # TODO(decision): add a future migration with UNIQUE(predictions.batch_id)
                # to prevent concurrent duplicate inserts. Intentionally deferred in this branch.
                raise BatchAlreadyCompletedError(batch_id)

            prediction = await self._prediction_repository.create(
                batch_id=batch_id,
                label=label,
                confidence=confidence,
                top5_labels=top5_labels,
                top5_confidences=top5_confidences,
                overlay_blob_key=overlay_blob_key,
                model_sha256=model_sha256,
                request_id=request_id,
            )

            await self._batch_repository.update_state(
                batch_id=batch_id,
                new_state=BatchState.COMPLETED,
                failure_reason=None,
            )

            await self._audit_log_service.write_entry(
                action=AuditAction.BATCH_STATE_CHANGE,
                actor_user_id=None,
                target_type="batch",
                target_id=batch_id,
                before=None,
                after={"state": BatchState.COMPLETED.value},
                request_id=request_id,
            )

        await self._cache_invalidator.invalidate_batches_list()
        await self._cache_invalidator.invalidate_batch_detail(batch_id)
        await self._cache_invalidator.invalidate_predictions_recent()
        return prediction

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
        return await self._prediction_repository.list_recent(limit=limit)
