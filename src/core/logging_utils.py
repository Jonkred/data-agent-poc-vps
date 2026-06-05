"""Logging estruturado em JSON para rastreabilidade."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "structured", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_root_logger(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.setLevel(level)
    root.addHandler(handler)


def get_logger(name: str, **context: Any) -> logging.LoggerAdapter:
    configure_root_logger()
    logger = logging.getLogger(name)

    class StructuredAdapter(logging.LoggerAdapter):
        def process(
            self,
            msg: str,
            kwargs: dict[str, Any],
        ) -> tuple[str, dict[str, Any]]:
            structured = dict(self.extra or {})
            structured.update(kwargs.pop("extra", {}) or {})
            structured["event"] = msg
            kwargs["extra"] = {"structured": structured}
            return msg, kwargs

    return StructuredAdapter(logger, context)
