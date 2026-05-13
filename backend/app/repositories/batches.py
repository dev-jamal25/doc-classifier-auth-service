from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Batch as BatchModel
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
        update_values: dict[str, str] = {"state": new_state.value}
        if failure_reason is not None:
            update_values["failure_reason"] = failure_reason

        stmt = (
            update(BatchModel)
            .where(BatchModel.id == batch_id)
            .values(**update_values)
            .returning(BatchModel)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one()
        return Batch.from_orm_row(row)

    async def create_failed(
        self,
        *,
        source_filename: str,
        sftp_user: str | None,
        request_id: UUID,
        failure_reason: str,
    ) -> Batch:
        model = BatchModel(
            source_filename=source_filename,
            source=BatchSource.SFTP_INGEST.value,
            sftp_user=sftp_user,
            blob_key=None,
            state=BatchState.FAILED.value,
            failure_reason=failure_reason,
            request_id=request_id,
            created_by_user_id=None,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return Batch.from_orm_row(model)
