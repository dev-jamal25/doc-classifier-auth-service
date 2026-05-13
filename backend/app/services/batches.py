from uuid import UUID

from app.domain.batches import Batch
from app.domain.enums import BatchState
from app.repositories.batches import BatchRepository


class BatchService:
    def __init__(self, batch_repository: BatchRepository) -> None:
        self._batch_repository = batch_repository

    async def create_failed_batch(
        self,
        *,
        source_filename: str,
        sftp_user: str | None,
        request_id: str,
        failure_reason: str,
    ) -> Batch:
        # TODO(impl): set source="sftp-ingest" and created_by_user_id=None per D-008.
        # TODO(cache): invalidate GET /batches after write.
        raise NotImplementedError("BatchService.create_failed_batch not yet implemented")

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
