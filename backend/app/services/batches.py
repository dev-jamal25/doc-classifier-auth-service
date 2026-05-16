from uuid import UUID

from app.domain.batches import Batch
from app.domain.enums import AuditAction, BatchSource, BatchState
from app.repositories.batches import BatchRepository
from app.services.audit_log import AuditLogService
from app.services.cache import NoOpServiceCacheInvalidator, ServiceCacheInvalidator


class BatchService:
    def __init__(
        self,
        batch_repository: BatchRepository,
        cache_invalidator: ServiceCacheInvalidator | None = None,
        audit_log_service: AuditLogService | None = None,
    ) -> None:
        self._batch_repository = batch_repository
        self._cache_invalidator = cache_invalidator or NoOpServiceCacheInvalidator()
        self._audit_log_service = audit_log_service

    async def create_from_sftp_drop(
        self,
        *,
        blob_key: str,
        source_filename: str,
        sftp_user: str | None,
        request_id: UUID,
    ) -> Batch:
        created = await self._batch_repository.create(
            source_filename=source_filename,
            source=BatchSource.SFTP_INGEST,
            sftp_user=sftp_user,
            blob_key=blob_key,
            state=BatchState.PENDING,
            failure_reason=None,
            request_id=request_id,
            created_by_user_id=None,
        )
        await self._cache_invalidator.invalidate_batches_list()
        return created

    async def create_failed_batch(
        self,
        *,
        source_filename: str,
        sftp_user: str | None,
        request_id: UUID,
        failure_reason: str,
    ) -> Batch:
        created = await self._batch_repository.create_failed(
            source_filename=source_filename,
            sftp_user=sftp_user,
            request_id=request_id,
            failure_reason=failure_reason,
        )
        await self._cache_invalidator.invalidate_batches_list()
        return created

    async def list_batches(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        state: BatchState | None = None,
    ) -> list[Batch]:
        return await self._batch_repository.list(limit=limit, offset=offset, state=state)

    async def get_batch(self, batch_id: UUID) -> Batch | None:
        return await self._batch_repository.get(batch_id)

    async def change_state(
        self,
        *,
        batch_id: UUID,
        new_state: BatchState,
        request_id: UUID,
        failure_reason: str | None = None,
        actor_user_id: UUID | None = None,
    ) -> Batch:
        before_batch = None
        if self._audit_log_service is not None:
            before_batch = await self._batch_repository.get(batch_id)

        updated = await self._batch_repository.update_state(
            batch_id=batch_id,
            new_state=new_state,
            failure_reason=failure_reason,
        )
        if self._audit_log_service is not None:
            await self._audit_log_service.write_entry(
                action=AuditAction.BATCH_STATE_CHANGE,
                actor_user_id=actor_user_id,
                target_type="batch",
                target_id=batch_id,
                before=_batch_state_audit_payload(before_batch),
                after=_batch_state_audit_payload(updated),
                request_id=request_id,
            )

        await self._cache_invalidator.invalidate_batches_list()
        await self._cache_invalidator.invalidate_batch_detail(batch_id)
        return updated


def _batch_state_audit_payload(batch: Batch | None) -> dict | None:
    if batch is None:
        return None
    return {
        "state": batch.state.value,
        "failure_reason": batch.failure_reason,
    }
