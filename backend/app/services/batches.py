from uuid import UUID

from app.domain.batches import Batch
from app.domain.enums import BatchSource, BatchState
from app.repositories.batches import BatchRepository
from app.services.cache import NoOpServiceCacheInvalidator, ServiceCacheInvalidator


class BatchService:
    def __init__(
        self,
        batch_repository: BatchRepository,
        cache_invalidator: ServiceCacheInvalidator | None = None,
    ) -> None:
        self._batch_repository = batch_repository
        self._cache_invalidator = cache_invalidator or NoOpServiceCacheInvalidator()

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
        # TODO(cache): cache GET /batches with TTL 60s via fastapi-cache2.
        raise NotImplementedError("BatchService.list_batches not yet implemented")

    async def get_batch(self, batch_id: UUID) -> Batch | None:
        # TODO(cache): cache GET /batches/{batch_id} with TTL 60s via fastapi-cache2.
        raise NotImplementedError("BatchService.get_batch not yet implemented")

    async def change_state(self, *, batch_id: UUID, new_state: BatchState) -> Batch:
        # TODO(cache): invalidate GET /batches and GET /batches/{batch_id}.
        # TODO(audit): write batch_state_change audit entry.
        raise NotImplementedError("BatchService.change_state not yet implemented")
