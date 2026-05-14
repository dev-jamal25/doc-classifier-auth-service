from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Settings holds NON-SECRET bootstrap and runtime config only.
# Secrets (JWT, DB credentials, MinIO keys, SFTP credentials, Redis auth)
# resolve from Vault at startup via app/infra/vault.py and are accessed
# through AppContext.secrets, never through AppContext.settings.


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    request_id_header: str = "X-Request-ID"

    # SFTP ingest
    sftp_host: str = "localhost"
    sftp_port: int = 22
    sftp_remote_dir: str = "/upload"
    sftp_quarantine_dir: str = "/quarantine"
    sftp_poll_interval_seconds: int = 5
    max_sftp_file_size_bytes: int = 50 * 1024 * 1024

    # Blob / MinIO
    minio_endpoint: str = "http://localhost:9000"
    minio_raw_bucket: str = "documents-raw"
    minio_overlay_bucket: str = "documents-overlays"

    # Queue / Redis
    # NOTE: If Redis auth is introduced, move redis_url to Vault secrets.
    redis_url: str = "redis://localhost:6379/0"
    worker_queue_name: str = "doc-jobs"
    worker_max_concurrency: int = 2
    worker_poll_interval_seconds: int = 5

    # Vault
    vault_addr: str = "http://localhost:8200"
    vault_token: str = ""
    vault_kv_mount: str = "secret"
    vault_kv_base_path: str = "doc-classifier"

    # Classifier
    classifier_model_path: str = "app/classifier/models/classifier.pt"
    classifier_model_card_path: str = "app/classifier/models/model_card.json"
    classifier_min_test_top1: float = 0.70
    use_mock_classifier: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
