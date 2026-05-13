from uuid import UUID

from app.domain.enums import AuditAction, BatchState
from app.domain.predictions import Prediction
from app.repositories.audit_log import AuditLogRepository
from app.repositories.batches import BatchRepository
from app.repositories.predictions import PredictionRepository
from app.services.cache import NoOpServiceCacheInvalidator, ServiceCacheInvalidator


class PredictionService:
    def __init__(
        self,
        prediction_repository: PredictionRepository,
        batch_repository: BatchRepository,
        audit_log_repository: AuditLogRepository,
        cache_invalidator: ServiceCacheInvalidator | None = None,
    ) -> None:
        self._prediction_repository = prediction_repository
        self._batch_repository = batch_repository
        self._audit_log_repository = audit_log_repository
        self._cache_invalidator = cache_invalidator or NoOpServiceCacheInvalidator()

    # TODO(@bmislol, Phase 5): idempotency check. If existing_batch.state ==
    # BatchState.COMPLETED, this method is being called again for a batch that
    # already has a prediction. Likely cause: RQ retry of a job that succeeded
    # but failed during post-commit cache invalidation. Either short-circuit
    # and return the existing prediction, or raise BatchAlreadyCompletedError.

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
        if (
            self._prediction_repository.session is not self._batch_repository.session
            or self._prediction_repository.session is not self._audit_log_repository.session
        ):
            raise ValueError("Repositories must share the same AsyncSession instance.")

        top5_labels = [label_name for (label_name, _) in top5]
        top5_confidences = [score for (_, score) in top5]
        session = self._prediction_repository.session

        async with session.begin():
            existing_batch = await self._batch_repository.get(batch_id)
            if existing_batch is None:
                raise ValueError(f"Batch `{batch_id}` not found for prediction write.")

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

            await self._audit_log_repository.create(
                action=AuditAction.BATCH_STATE_CHANGE,
                actor_user_id=None,
                target_type="batch",
                target_id=batch_id,
                before_value={"state": existing_batch.state.value},
                after_value={"state": BatchState.COMPLETED.value},
                request_id=request_id,
            )

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
        # TODO(cache): cache GET /predictions/recent with TTL 60s via fastapi-cache2.
        raise NotImplementedError("PredictionService.list_recent not yet implemented")
