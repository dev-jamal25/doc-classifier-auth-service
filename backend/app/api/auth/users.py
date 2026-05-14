from __future__ import annotations

from uuid import UUID

from fastapi_users import FastAPIUsers

from app.api.auth.backend import auth_backend
from app.api.auth.manager import get_user_manager
from app.db.models import User

fastapi_users = FastAPIUsers[User, UUID](get_user_manager, [auth_backend])
current_active_user = fastapi_users.current_user(active=True)
