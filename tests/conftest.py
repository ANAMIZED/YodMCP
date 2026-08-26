"""Isolate global substrate + tenant context between tests."""

from __future__ import annotations

import pytest


async def _close_sqlite(obj) -> None:
    if obj is None:
        return
    closer = getattr(obj, "close", None)
    if closer is not None:
        try:
            result = closer()
            if hasattr(result, "__await__"):
                await result
        except Exception:
            pass
    sqlite = getattr(obj, "_sqlite", None)
    if sqlite is not None and sqlite is not obj:
        await _close_sqlite(sqlite)


@pytest.fixture(autouse=True)
async def _isolate_yodmcp_globals():
    yield
    from yodmcp.core.context import clear_context, try_get_context
    from yodmcp.core.tenant import set_tenant

    ctx = try_get_context()
    if ctx is not None:
        await _close_sqlite(getattr(ctx, "memory", None))
        await _close_sqlite(getattr(ctx, "tasks", None))
        await _close_sqlite(getattr(ctx, "audit", None))
        billing = getattr(ctx, "billing", None)
        if billing is not None:
            await _close_sqlite(getattr(billing, "meter", None))
            await _close_sqlite(getattr(billing, "entitlements", None))
        await _close_sqlite(getattr(ctx, "entitlements", None))
    clear_context()
    try:
        set_tenant("default")
    except Exception:
        pass
