from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.db.models import User

db_session_dependency = Depends(get_db_session)


async def get_user_db(
    session: AsyncSession = db_session_dependency,
) -> AsyncIterator[SQLAlchemyUserDatabase[User, UUID]]:
    yield SQLAlchemyUserDatabase(session, User)
