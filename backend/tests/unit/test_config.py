from app.core.config import get_settings


def test_settings_defaults_load() -> None:
    settings = get_settings()

    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.request_id_header == "X-Request-ID"


def test_settings_env_override(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("REQUEST_ID_HEADER", "X-Test-Request-ID")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")

    settings = get_settings()

    assert settings.app_env == "staging"
    assert settings.log_level == "DEBUG"
    assert settings.request_id_header == "X-Test-Request-ID"
    assert settings.database_url == "postgresql+asyncpg://test:test@localhost:5432/test"


def test_get_settings_is_cached() -> None:
    first = get_settings()
    second = get_settings()

    assert first is second
