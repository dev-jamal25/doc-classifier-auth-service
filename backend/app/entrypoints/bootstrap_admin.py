from __future__ import annotations

import argparse
import asyncio
import logging
import os
from uuid import UUID

from fastapi_users.exceptions import UserAlreadyExists
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

from app.api.auth.manager import UserManager
from app.api.schemas.users import UserCreate
from app.core.lifespan import lifespan
from app.db.models import User

logger = logging.getLogger(__name__)


async def ensure_admin_user(
    user_manager: UserManager,
    *,
    email: str,
    password: str,
) -> User | None:
    user_create = UserCreate(email=email, password=password, is_active=True)
    try:
        user = await user_manager.create(user_create, safe=False)
    except UserAlreadyExists:
        logger.info(
            "Bootstrap admin user already exists.",
            extra={
                "event": "admin_bootstrap_user_exists",
                "email": email,
            },
        )
        return None

    logger.info(
        "Bootstrap user created. Plan 2 (Casbin): grant admin via grouping policy `g, %s, admin`.",
        user.id,
        extra={
            "event": "admin_bootstrapped",
            "user_id": str(user.id),
            "email": user.email,
            "casbin_guidance": f"g, {user.id}, admin",
        },
    )
    return user


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap the first application user.")
    parser.add_argument("--email", default=None)
    parser.add_argument("--password", default=None)
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    email = args.email or os.getenv("BOOTSTRAP_ADMIN_EMAIL")
    password = args.password or os.getenv("BOOTSTRAP_ADMIN_PASSWORD")

    if not email or not password:
        raise SystemExit(
            "Provide --email/--password or BOOTSTRAP_ADMIN_EMAIL/BOOTSTRAP_ADMIN_PASSWORD."
        )

    async with lifespan("bootstrap-admin") as context:
        from app.db.session import async_session_factory

        async with async_session_factory() as session:
            user_db: SQLAlchemyUserDatabase[User, UUID] = SQLAlchemyUserDatabase(session, User)
            user_manager = UserManager(user_db, context.secrets.jwt.secret)
            await ensure_admin_user(user_manager, email=email, password=password)
            await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
