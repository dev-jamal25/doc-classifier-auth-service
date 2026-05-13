from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.batches import Batch
from app.domain.enums import BatchSource, BatchState


class BatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        source_filename: str,
        source: BatchSource,
        sftp_user: str | None,
        blob_key: str | None,
        state: BatchState,
        failure_reason: str | None,
        request_id: UUID,
        created_by_user_id: UUID | None,
    ) -> Batch:
        # TODO(impl): SQL insert and domain model mapping go here.
        raise NotImplementedError("BatchRepository.create not yet implemented")

    async def get(self, batch_id: UUID) -> Batch | None:
        # TODO(impl): SQL select by primary key goes here.
        raise NotImplementedError("BatchRepository.get not yet implemented")

    async def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        state: BatchState | None = None,
    ) -> list[Batch]:
        # TODO(impl): SQL listing with optional state filter goes here.
        raise NotImplementedError("BatchRepository.list not yet implemented")

    async def update_state(
        self,
        *,
        batch_id: UUID,
        new_state: BatchState,
        failure_reason: str | None = None,
    ) -> Batch:
        # TODO(impl): SQL state update and return mapped domain model.
        raise NotImplementedError("BatchRepository.update_state not yet implemented")

    async def create_failed(
        self,
        *,
        source_filename: str,
        sftp_user: str | None,
        request_id: UUID,
        failure_reason: str,
    ) -> Batch:
        # TODO(impl): SQL insert for failed SFTP-originated batch goes here.
        raise NotImplementedError("BatchRepository.create_failed not yet implemented")
