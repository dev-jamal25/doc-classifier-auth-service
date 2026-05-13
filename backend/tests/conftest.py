import pytest

from app.core.config import get_settings

SETTINGS_ENV_KEYS = (
    "APP_ENV",
    "LOG_LEVEL",
    "REQUEST_ID_HEADER",
    "DATABASE_URL",
    "API_AUTH_JWT_SECRET",
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
