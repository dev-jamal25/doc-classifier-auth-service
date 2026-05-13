import contextvars
import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


class JsonFormatter(logging.Formatter):
    def __init__(self, *, service: str = "api") -> None:
        super().__init__()
        self._service = service

    def format(self, record: logging.LogRecord) -> str:
        request_id = request_id_var.get() or getattr(record, "request_id", None)
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "service": getattr(record, "service", self._service),
            "event": getattr(record, "event", record.getMessage()),
            "request_id": request_id,
        }

        user_id = getattr(record, "user_id", None)
        if user_id is not None:
            payload["user_id"] = user_id

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(settings: Settings, *, service: str = "api") -> None:
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(settings.log_level.upper())

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(service=service))
    root_logger.addHandler(handler)
