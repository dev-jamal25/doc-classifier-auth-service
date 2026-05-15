from app.core.config import get_settings


def test_settings_defaults_load() -> None:
    settings = get_settings()

    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.request_id_header == "X-Request-ID"
    assert settings.sftp_poll_interval_seconds == 5
    assert settings.sftp_quarantine_dir == "/upload/quarantine"
    assert settings.classifier_min_test_top1 == 0.70


def test_settings_env_override(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("REQUEST_ID_HEADER", "X-Test-Request-ID")
    monkeypatch.setenv("SFTP_POLL_INTERVAL_SECONDS", "7")
    monkeypatch.setenv("USE_MOCK_CLASSIFIER", "true")

    settings = get_settings()

    assert settings.app_env == "staging"
    assert settings.log_level == "DEBUG"
    assert settings.request_id_header == "X-Test-Request-ID"
    assert settings.sftp_poll_interval_seconds == 7
    assert settings.use_mock_classifier is True


def test_get_settings_is_cached() -> None:
    first = get_settings()
    second = get_settings()

    assert first is second
