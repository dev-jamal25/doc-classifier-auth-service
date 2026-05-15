from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI

from app.core import lifespan as lifespan_module
from app.core.config import Settings
from app.core.lifespan import AppContext, build_fastapi_lifespan
from app.infra import cache as cache_module
from app.infra import vault as vault_module
from app.infra.vault import VaultStartupError


class _InvalidPath(Exception):
    pass


class _FakeKVV2:
    def __init__(self, store: dict[str, dict[str, Any]]) -> None:
        self._store = store

    def read_secret_version(self, *, path: str, mount_point: str) -> dict[str, Any]:
        if mount_point != "secret" or path not in self._store:
            raise _InvalidPath(path)
        return {"data": {"data": self._store[path]}}


class _FakeKV:
    def __init__(self, v2: _FakeKVV2) -> None:
        self.v2 = v2


class _FakeSecrets:
    def __init__(self, kv: _FakeKV) -> None:
        self.kv = kv


class _FakeClient:
    def __init__(self, store: dict[str, dict[str, Any]]) -> None:
        self.secrets = _FakeSecrets(_FakeKV(_FakeKVV2(store)))

    def is_authenticated(self) -> bool:
        return True


class _FakeHvac:
    class exceptions:
        InvalidPath = _InvalidPath

    def __init__(self, client: _FakeClient) -> None:
        self._client = client

    def Client(self, *, url: str, token: str | None) -> _FakeClient:
        return self._client


class _FakeCacheClient:
    async def aclose(self) -> None:
        return None


async def _fake_initialize_api_cache(redis_url: str) -> _FakeCacheClient:
    return _FakeCacheClient()


def _settings() -> Settings:
    return Settings(
        vault_addr="http://vault:8200",
        vault_token="dev-root-token",
        vault_kv_mount="secret",
        vault_kv_base_path="doc-classifier",
    )


def _valid_store() -> dict[str, dict[str, Any]]:
    return {
        "doc-classifier/jwt": {
            "secret": "jwt-signing-secret",
            "algorithm": "HS512",
            "exp_minutes": 120,
        },
        "doc-classifier/db": {
            "database_url": "postgresql+asyncpg://doc_user:secret@db:5432/doc_classifier",
        },
        "doc-classifier/minio": {
            "access_key": "minio-user",
            "secret_key": "minio-pass",
        },
        "doc-classifier/sftp": {
            "username": "vendor-1",
            "password": "vendor-pass",
        },
        "doc-classifier/redis": {
            "url": "redis://redis:6379/0",
        },
    }


@pytest.mark.asyncio
async def test_fastapi_lifespan_stashes_app_context(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop_validate_api_startup() -> None:
        return None

    monkeypatch.setattr(lifespan_module, "get_settings", _settings)
    monkeypatch.setattr(vault_module, "hvac", _FakeHvac(_FakeClient(_valid_store())))
    monkeypatch.setattr(lifespan_module, "validate_api_startup", _noop_validate_api_startup)
    monkeypatch.setattr(cache_module, "initialize_api_cache", _fake_initialize_api_cache)
    app = FastAPI()

    async with build_fastapi_lifespan("api")(app):
        assert isinstance(app.state.context, AppContext)
        assert app.state.context.secrets.jwt.secret == "jwt-signing-secret"


@pytest.mark.asyncio
async def test_api_lifespan_runs_rbac_startup_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def _fake_validate_api_startup() -> None:
        nonlocal calls
        calls += 1

    monkeypatch.setattr(lifespan_module, "get_settings", _settings)
    monkeypatch.setattr(vault_module, "hvac", _FakeHvac(_FakeClient(_valid_store())))
    monkeypatch.setattr(lifespan_module, "validate_api_startup", _fake_validate_api_startup)
    monkeypatch.setattr(cache_module, "initialize_api_cache", _fake_initialize_api_cache)
    app = FastAPI()

    async with build_fastapi_lifespan("api")(app):
        pass

    assert calls == 1


@pytest.mark.asyncio
async def test_non_api_lifespan_skips_rbac_startup_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def _fake_validate_api_startup() -> None:
        nonlocal calls
        calls += 1

    monkeypatch.setattr(lifespan_module, "get_settings", _settings)
    monkeypatch.setattr(vault_module, "hvac", _FakeHvac(_FakeClient(_valid_store())))
    monkeypatch.setattr(lifespan_module, "validate_api_startup", _fake_validate_api_startup)

    async with lifespan_module.lifespan("bootstrap-admin-role"):
        pass

    assert calls == 0


@pytest.mark.asyncio
async def test_fastapi_lifespan_keeps_jwt_refuse_to_start_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _valid_store()
    store.pop("doc-classifier/jwt")
    monkeypatch.setattr(lifespan_module, "get_settings", _settings)
    monkeypatch.setattr(vault_module, "hvac", _FakeHvac(_FakeClient(store)))
    app = FastAPI()

    with pytest.raises(VaultStartupError, match="secret/doc-classifier/jwt"):
        async with build_fastapi_lifespan("api")(app):
            pass
