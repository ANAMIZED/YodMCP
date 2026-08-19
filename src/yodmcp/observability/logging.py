"""Structured JSON logging for multi-tenant ops."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any

from yodmcp.core.tenant import get_request_id, get_tenant


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.time(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "tenant_id": get_tenant(),
            "request_id": get_request_id(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key in ("tool", "decision", "risk", "path", "status_code"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, default=str)


def configure_logging(level: str | None = None) -> None:
    """Install JSON formatter on root when YODMCP_LOG_FORMAT=json."""
    fmt = (os.environ.get("YODMCP_LOG_FORMAT") or "text").lower()
    log_level = getattr(logging, (level or os.environ.get("YODMCP_LOG_LEVEL", "INFO")).upper(), logging.INFO)
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
    root.addHandler(handler)
    root.setLevel(log_level)
