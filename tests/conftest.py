"""Isolate global substrate + tenant context between tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_yodmcp_globals():
    yield
    from yodmcp.core.context import clear_context
    from yodmcp.core.tenant import set_tenant

    clear_context()
    try:
        set_tenant("default")
    except Exception:
        pass
