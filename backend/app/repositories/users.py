from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.db.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def get(self, user_id: UUID) -> User | None:
        id_matches = cast(ColumnElement[bool], User.__table__.c.id == user_id)
        statement = select(User).where(id_matches)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        email_matches = cast(
            ColumnElement[bool],
            func.lower(User.__table__.c.email) == email.casefold(),
        )
        statement = select(User).where(email_matches)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
