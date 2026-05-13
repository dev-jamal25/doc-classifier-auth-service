import io
import json
import logging

from app.core.logging import JsonFormatter, request_id_var


def _build_logger(stream: io.StringIO) -> logging.Logger:
    logger = logging.getLogger("test_json_logger")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter(service="api"))
    logger.addHandler(handler)
    return logger


def test_json_log_line_is_valid_json() -> None:
    stream = io.StringIO()
    logger = _build_logger(stream)

    logger.info("health_check", extra={"event": "health_check"})

    payload = json.loads(stream.getvalue().strip())
    assert payload["event"] == "health_check"
    assert payload["service"] == "api"


def test_json_log_includes_request_id_from_context_var() -> None:
    stream = io.StringIO()
    logger = _build_logger(stream)
    token = request_id_var.set("req-123")

    try:
        logger.info("prediction_write", extra={"event": "prediction_write"})
    finally:
        request_id_var.reset(token)

    payload = json.loads(stream.getvalue().strip())
    assert payload["request_id"] == "req-123"


def test_json_log_omits_user_id_when_not_provided() -> None:
    stream = io.StringIO()
    logger = _build_logger(stream)

    logger.info("batch_list", extra={"event": "batch_list"})

    payload = json.loads(stream.getvalue().strip())
    assert "user_id" not in payload
