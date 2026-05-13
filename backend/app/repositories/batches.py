from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Batch as BatchModel
from app.domain.batches import Batch
from app.domain.enums import BatchSource, BatchState


class BatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

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
        # OWNED BY @dev-jamal25, implemented by @bmislol as ingestion dependency
        row = BatchModel(
            source_filename=source_filename,
            source=source.value,
            sftp_user=sftp_user,
            blob_key=blob_key,
            state=state.value,
            failure_reason=failure_reason,
            request_id=request_id,
            created_by_user_id=created_by_user_id,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return Batch.from_orm_row(row)

    async def get(self, batch_id: UUID) -> Batch | None:
        row = await self._session.get(BatchModel, batch_id)
        if row is None:
            return None
        return Batch.from_orm_row(row)

    async def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        state: BatchState | None = None,
    ) -> list[Batch]:
        statement = (
            select(BatchModel).offset(offset).limit(limit).order_by(BatchModel.created_at.desc())
        )
        if state is not None:
            statement = statement.where(BatchModel.state == state.value)
        result = await self._session.execute(statement)
        rows = result.scalars().all()
        return [Batch.from_orm_row(row) for row in rows]

    async def update_state(
        self,
        *,
        batch_id: UUID,
        new_state: BatchState,
        failure_reason: str | None = None,
    ) -> Batch:
        # OWNED BY @dev-jamal25, implemented by @bmislol as ingestion dependency
        row = await self._session.get(BatchModel, batch_id)
        if row is None:
            raise ValueError(f"Batch `{batch_id}` not found.")

        row.state = new_state.value
        if failure_reason is not None:
            row.failure_reason = failure_reason
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(row)
        return Batch.from_orm_row(row)

    async def create_failed(
        self,
        *,
        source_filename: str,
        sftp_user: str | None,
        request_id: UUID,
        failure_reason: str,
    ) -> Batch:
        # OWNED BY @dev-jamal25, implemented by @bmislol as ingestion dependency
        return await self.create(
            source_filename=source_filename,
            source=BatchSource.SFTP_INGEST,
            sftp_user=sftp_user,
            blob_key=None,
            state=BatchState.FAILED,
            failure_reason=failure_reason,
            request_id=request_id,
            created_by_user_id=None,
        )
