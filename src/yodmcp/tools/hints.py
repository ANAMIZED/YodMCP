"""MCP ToolAnnotations helper (camelCase + snake_case across mcp 1.x/2.x)."""

from __future__ import annotations

from typing import Any


def tool_hints(
    title: str,
    *,
    read_only: bool,
    destructive: bool = False,
    idempotent: bool = True,
    open_world: bool = False,
) -> Any:
    try:
        from mcp.types import ToolAnnotations
    except Exception:
        ToolAnnotations = None  # type: ignore[misc, assignment]

    if ToolAnnotations is not None:
        for kwargs in (
            {
                "title": title,
                "read_only_hint": read_only,
                "destructive_hint": destructive,
                "idempotent_hint": idempotent,
                "open_world_hint": open_world,
            },
            {
                "title": title,
                "readOnlyHint": read_only,
                "destructiveHint": destructive,
                "idempotentHint": idempotent,
                "openWorldHint": open_world,
            },
        ):
            try:
                return ToolAnnotations(**kwargs)
            except TypeError:
                continue

    return {
        "title": title,
        "readOnlyHint": read_only,
        "destructiveHint": destructive,
        "idempotentHint": idempotent,
        "openWorldHint": open_world,
    }
