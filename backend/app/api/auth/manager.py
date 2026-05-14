from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator

from fastapi import Depends, Request
from fastapi_users import BaseUserManager
from fastapi_users.manager import UUIDIDMixin
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

from app.api.auth.backend import get_jwt_secrets
from app.api.auth.user_db import get_user_db
from app.db.models import User
from app.infra.vault import JwtSecrets

logger = logging.getLogger(__name__)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    def __init__(
        self,
        user_db: SQLAlchemyUserDatabase[User, uuid.UUID],
        token_secret: str,
    ) -> None:
        # Reset and verification routes are out of scope for Plan 1.
        self.reset_password_token_secret = token_secret
        self.verification_token_secret = token_secret
        super().__init__(user_db)

    async def on_after_register(self, user: User, request: Request | None = None) -> None:
        logger.info(
            "User registered.",
            extra={
                "event": "user_registered",
                "user_id": str(user.id),
            },
        )


user_db_dependency = Depends(get_user_db)
jwt_secrets_dependency = Depends(get_jwt_secrets)


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase[User, uuid.UUID] = user_db_dependency,
    jwt: JwtSecrets = jwt_secrets_dependency,
) -> AsyncIterator[UserManager]:
    yield UserManager(user_db, jwt.secret)
