"""Input validation and size limits for multi-tenant safety."""

from __future__ import annotations

import os
from typing import Any


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


MAX_MEMORY_CONTENT = _int_env("YODMCP_MAX_MEMORY_CONTENT", 64_000)
MAX_TOOL_ARG_JSON = _int_env("YODMCP_MAX_TOOL_ARG_BYTES", 32_000)
MAX_STRING_ARG = _int_env("YODMCP_MAX_STRING_ARG", 16_000)


class ValidationError(ValueError):
    pass


def validate_memory_content(content: str) -> str:
    if content is None:
        raise ValidationError("content is required")
    if not isinstance(content, str):
        raise ValidationError("content must be a string")
    if len(content) > MAX_MEMORY_CONTENT:
        raise ValidationError(
            f"content exceeds max length {MAX_MEMORY_CONTENT} (got {len(content)})"
        )
    return content


def validate_tool_arguments(arguments: dict[str, Any] | None) -> dict[str, Any]:
    import json

    args = arguments or {}
    try:
        raw = json.dumps(args, default=str)
    except Exception as e:
        raise ValidationError(f"arguments not serializable: {e}") from e
    if len(raw) > MAX_TOOL_ARG_JSON:
        raise ValidationError(
            f"arguments exceed max size {MAX_TOOL_ARG_JSON} bytes (got {len(raw)})"
        )
    for k, v in args.items():
        if isinstance(v, str) and len(v) > MAX_STRING_ARG:
            raise ValidationError(
                f"argument {k!r} exceeds max string length {MAX_STRING_ARG}"
            )
    return args
