from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Request
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy

from app.core.lifespan import AppContext
from app.db.models import User
from app.infra.vault import JwtSecrets


def get_app_context(request: Request) -> AppContext:
    return request.app.state.context


app_context_dependency = Depends(get_app_context)


def get_jwt_secrets(context: AppContext = app_context_dependency) -> JwtSecrets:
    return context.secrets.jwt


jwt_secrets_dependency = Depends(get_jwt_secrets)


def get_jwt_strategy(jwt: JwtSecrets = jwt_secrets_dependency) -> JWTStrategy:
    return JWTStrategy(
        secret=jwt.secret,
        lifetime_seconds=jwt.exp_minutes * 60,
        algorithm=jwt.algorithm,
    )


bearer_transport = BearerTransport(tokenUrl="auth/login")
auth_backend: AuthenticationBackend[User, UUID] = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)
