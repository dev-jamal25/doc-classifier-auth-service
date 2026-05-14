from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings

try:
    import hvac
except ImportError:  # pragma: no cover - exercised when dependency is missing.
    hvac = None


class VaultStartupError(RuntimeError):
    """Raised when Vault bootstrapping fails and service startup must abort."""


class JwtSecrets(BaseModel):
    model_config = ConfigDict(extra="ignore")

    secret: str
    algorithm: str = "HS256"
    exp_minutes: int = 60


class DbSecrets(BaseModel):
    model_config = ConfigDict(extra="ignore")

    database_url: str = Field(validation_alias=AliasChoices("database_url", "url"))


class MinioSecrets(BaseModel):
    model_config = ConfigDict(extra="ignore")

    access_key: str
    secret_key: str


class SftpSecrets(BaseModel):
    model_config = ConfigDict(extra="ignore")

    username: str
    password: str


class RedisSecrets(BaseModel):
    model_config = ConfigDict(extra="ignore")

    url: str


class VaultSecrets(BaseModel):
    model_config = ConfigDict(extra="ignore")

    jwt: JwtSecrets
    db: DbSecrets
    minio: MinioSecrets
    sftp: SftpSecrets
    redis: RedisSecrets


def _build_kv_path(settings: Settings, group: str) -> str:
    base = settings.vault_kv_base_path.strip("/")
    return f"{base}/{group}"


def _build_client(settings: Settings) -> Any:
    if hvac is None:
        raise VaultStartupError("Vault client dependency missing: install `hvac`.")

    try:
        client = hvac.Client(url=settings.vault_addr, token=settings.vault_token or None)
    except Exception as exc:  # pragma: no cover - defensive guard around client init.
        raise VaultStartupError("Failed to initialize Vault client.") from exc

    try:
        if not client.is_authenticated():
            raise VaultStartupError("Vault authentication failed.")
    except VaultStartupError:
        raise
    except Exception as exc:
        raise VaultStartupError("Vault authentication check failed.") from exc

    return client


def _read_secret_group(client: Any, settings: Settings, group: str) -> dict[str, Any]:
    path = _build_kv_path(settings, group)
    full_path = f"{settings.vault_kv_mount}/{path}"

    try:
        response = client.secrets.kv.v2.read_secret_version(
            path=path,
            mount_point=settings.vault_kv_mount,
        )
    except Exception as exc:
        invalid_path_exc = getattr(getattr(hvac, "exceptions", None), "InvalidPath", None)
        if invalid_path_exc is not None and isinstance(exc, invalid_path_exc):
            raise VaultStartupError(f"Missing Vault secret path: `{full_path}`.") from exc
        raise VaultStartupError(f"Unable to read Vault secret path: `{full_path}`.") from exc

    data = response.get("data", {}).get("data")
    if not isinstance(data, dict) or not data:
        raise VaultStartupError(f"Vault secret path returned empty data: `{full_path}`.")
    return data


def load_secrets(settings: Settings) -> VaultSecrets:
    client = _build_client(settings)

    try:
        jwt_data = _read_secret_group(client, settings, "jwt")
        db_data = _read_secret_group(client, settings, "db")
        minio_data = _read_secret_group(client, settings, "minio")
        sftp_data = _read_secret_group(client, settings, "sftp")
        redis_data = _read_secret_group(client, settings, "redis")
        return VaultSecrets(
            jwt=JwtSecrets.model_validate(jwt_data),
            db=DbSecrets.model_validate(db_data),
            minio=MinioSecrets.model_validate(minio_data),
            sftp=SftpSecrets.model_validate(sftp_data),
            redis=RedisSecrets.model_validate(redis_data),
        )
    except ValidationError as exc:
        raise VaultStartupError("Vault secret payload validation failed.") from exc


def health_check(settings: Settings) -> bool:
    try:
        load_secrets(settings)
    except VaultStartupError:
        return False
    return True
