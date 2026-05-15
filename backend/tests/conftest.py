import pytest
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

from app.core.config import get_settings

SETTINGS_ENV_KEYS = (
    "APP_ENV",
    "LOG_LEVEL",
    "REQUEST_ID_HEADER",
    "SFTP_HOST",
    "SFTP_PORT",
    "SFTP_REMOTE_DIR",
    "SFTP_QUARANTINE_DIR",
    "SFTP_POLL_INTERVAL_SECONDS",
    "MAX_SFTP_FILE_SIZE_BYTES",
    "MINIO_ENDPOINT",
    "MINIO_RAW_BUCKET",
    "MINIO_OVERLAY_BUCKET",
    "REDIS_URL",
    "WORKER_QUEUE_NAME",
    "WORKER_MAX_CONCURRENCY",
    "WORKER_POLL_INTERVAL_SECONDS",
    "VAULT_ADDR",
    "VAULT_TOKEN",
    "VAULT_KV_MOUNT",
    "VAULT_KV_BASE_PATH",
    "CLASSIFIER_MODEL_PATH",
    "CLASSIFIER_MODEL_CARD_PATH",
    "CLASSIFIER_MIN_TEST_TOP1",
    "USE_MOCK_CLASSIFIER",
)


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def clear_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_key in SETTINGS_ENV_KEYS:
        monkeypatch.delenv(env_key, raising=False)


@pytest.fixture(autouse=True)
def reset_fastapi_cache() -> None:
    FastAPICache.reset()
    InMemoryBackend._store.clear()
    yield
    FastAPICache.reset()
    InMemoryBackend._store.clear()
