from __future__ import annotations

from typing import Any

import pytest

from app.core.config import Settings
from app.infra import vault as vault_module
from app.infra.vault import VaultStartupError, health_check, load_secrets


class _InvalidPath(Exception):
    pass


class _FakeKVV2:
    def __init__(self, store: dict[str, dict[str, Any]]) -> None:
        self._store = store

    def read_secret_version(self, *, path: str, mount_point: str) -> dict[str, Any]:
        if mount_point != "secret":
            raise _InvalidPath(path)
        if path not in self._store:
            raise _InvalidPath(path)
        return {"data": {"data": self._store[path]}}


class _FakeKV:
    def __init__(self, v2: _FakeKVV2) -> None:
        self.v2 = v2


class _FakeSecrets:
    def __init__(self, kv: _FakeKV) -> None:
        self.kv = kv


class _FakeClient:
    def __init__(self, store: dict[str, dict[str, Any]], *, authenticated: bool = True) -> None:
        self._authenticated = authenticated
        self.secrets = _FakeSecrets(_FakeKV(_FakeKVV2(store)))

    def is_authenticated(self) -> bool:
        return self._authenticated


class _FakeHvac:
    class exceptions:
        InvalidPath = _InvalidPath

    def __init__(self, client: _FakeClient) -> None:
        self._client = client

    def Client(self, *, url: str, token: str | None) -> _FakeClient:
        assert url == "http://vault:8200"
        assert token == "dev-root-token"
        return self._client


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


def test_load_secrets_returns_typed_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_hvac = _FakeHvac(_FakeClient(_valid_store()))
    monkeypatch.setattr(vault_module, "hvac", fake_hvac)

    secrets = load_secrets(_settings())

    assert secrets.jwt.secret == "jwt-signing-secret"
    assert secrets.jwt.algorithm == "HS512"
    assert secrets.db.database_url.startswith("postgresql+asyncpg://")
    assert secrets.minio.access_key == "minio-user"
    assert secrets.sftp.username == "vendor-1"
    assert secrets.redis.url == "redis://redis:6379/0"


def test_load_secrets_raises_on_missing_required_path(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _valid_store()
    store.pop("doc-classifier/redis")
    fake_hvac = _FakeHvac(_FakeClient(store))
    monkeypatch.setattr(vault_module, "hvac", fake_hvac)

    with pytest.raises(VaultStartupError, match="secret/doc-classifier/redis"):
        load_secrets(_settings())


def test_load_secrets_raises_on_auth_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_hvac = _FakeHvac(_FakeClient(_valid_store(), authenticated=False))
    monkeypatch.setattr(vault_module, "hvac", fake_hvac)

    with pytest.raises(VaultStartupError, match="authentication failed"):
        load_secrets(_settings())


def test_load_secrets_raises_when_hvac_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vault_module, "hvac", None)

    with pytest.raises(VaultStartupError, match="hvac"):
        load_secrets(_settings())


def test_health_check_returns_false_on_startup_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(_: Settings) -> None:
        raise VaultStartupError("boom")

    monkeypatch.setattr(vault_module, "load_secrets", _raise)

    assert health_check(_settings()) is False
