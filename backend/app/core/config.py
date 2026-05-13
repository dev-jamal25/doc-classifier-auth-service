from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    request_id_header: str = "X-Request-ID"
    database_url: str = (
        "postgresql+asyncpg://doc_user:example-password@localhost:5432/doc_classifier"
    )
    # TODO(vault): resolve from Vault at startup once infra/vault adapter is available.
    api_auth_jwt_secret: str = "replace-me"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
