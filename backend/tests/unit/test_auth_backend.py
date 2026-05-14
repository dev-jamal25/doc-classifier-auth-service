from __future__ import annotations

import inspect
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from fastapi_users.authentication import BearerTransport, JWTStrategy

from app.api.auth.backend import (
    auth_backend,
    bearer_transport,
    get_app_context,
    get_jwt_secrets,
    get_jwt_strategy,
)
from app.core.config import Settings
from app.core.lifespan import AppContext
from app.db.models import User
from app.infra.vault import (
    DbSecrets,
    JwtSecrets,
    MinioSecrets,
    RedisSecrets,
    SftpSecrets,
    VaultSecrets,
)


def _vault_secrets(jwt_secrets: JwtSecrets) -> VaultSecrets:
    return VaultSecrets(
        jwt=jwt_secrets,
        db=DbSecrets(database_url="postgresql+asyncpg://user:pass@db:5432/app"),
        minio=MinioSecrets(access_key="minio-user", secret_key="minio-pass"),
        sftp=SftpSecrets(username="vendor-1", password="vendor-pass"),
        redis=RedisSecrets(url="redis://redis:6379/0"),
    )


def test_get_jwt_strategy_uses_vault_jwt_settings() -> None:
    strategy = get_jwt_strategy(JwtSecrets(secret="s" * 32, algorithm="HS256", exp_minutes=30))
    other = get_jwt_strategy(JwtSecrets(secret="other" * 8, algorithm="HS512", exp_minutes=5))

    assert strategy.secret == "s" * 32
    assert strategy.lifetime_seconds == 1800
    assert strategy.algorithm == "HS256"
    assert other.secret == "other" * 8
    assert other.lifetime_seconds == 300
    assert other.algorithm == "HS512"


def test_auth_backend_and_transport_are_configured_for_jwt() -> None:
    assert auth_backend.name == "jwt"
    assert isinstance(bearer_transport, BearerTransport)


def test_context_dependencies_return_startup_loaded_context() -> None:
    jwt_secrets = JwtSecrets(secret="context-secret", algorithm="HS256", exp_minutes=15)
    context = AppContext(settings=Settings(), secrets=_vault_secrets(jwt_secrets))
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(context=context)))

    assert get_app_context(request) is context
    assert get_jwt_secrets(context) is jwt_secrets


@pytest.mark.asyncio
async def test_jwt_strategy_writes_token_decodable_with_same_secret() -> None:
    jwt_secrets = JwtSecrets(secret="round-trip-secret" * 3, algorithm="HS256", exp_minutes=30)
    strategy = get_jwt_strategy(jwt_secrets)
    user = User(
        id=uuid4(),
        email="admin@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )

    token_result = strategy.write_token(user)
    token = await token_result if inspect.isawaitable(token_result) else token_result
    payload = jwt.decode(
        token,
        jwt_secrets.secret,
        audience=["fastapi-users:auth"],
        algorithms=[jwt_secrets.algorithm],
    )

    assert isinstance(strategy, JWTStrategy)
    assert payload["sub"] == str(user.id)
