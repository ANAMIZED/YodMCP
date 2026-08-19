"""Request-scoped tenant binding for multi-tenant SaaS.

Use set_tenant / get_tenant around HTTP handlers and tool gates so billing,
audit, and policy are never stuck on process-global YODMCP_TENANT_ID alone.
"""

from __future__ import annotations

import os
from contextvars import ContextVar
from typing import Optional

_tenant: ContextVar[Optional[str]] = ContextVar("yodmcp_tenant", default=None)
_request_id: ContextVar[Optional[str]] = ContextVar("yodmcp_request_id", default=None)


def set_tenant(tenant_id: str) -> None:
    _tenant.set(tenant_id.strip() or "default")


def get_tenant() -> str:
    t = _tenant.get()
    if t:
        return t
    return os.environ.get("YODMCP_TENANT_ID", "default") or "default"


def set_request_id(rid: str) -> None:
    _request_id.set(rid)


def get_request_id() -> str | None:
    return _request_id.get()


def clear_request_scope() -> None:
    _tenant.set(None)
    _request_id.set(None)
