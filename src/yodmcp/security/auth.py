"""API key AuthN for YodMCP HTTP surfaces + request-scoped tenant binding."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request, status

from yodmcp.core.tenant import set_request_id, set_tenant


@dataclass(frozen=True)
class AuthContext:
    api_key_id: str
    tenant_id: str
    authenticated: bool
    request_id: str = ""


def _configured_keys() -> set[str]:
    raw = os.environ.get("YODMCP_API_KEYS") or os.environ.get("YODMCP_API_KEY") or ""
    return {k.strip() for k in raw.split(",") if k.strip()}


def auth_required() -> bool:
    return bool(_configured_keys())


async def get_auth_context(
    request: Request,
    authorization: Annotated[Optional[str], Header()] = None,
    x_api_key: Annotated[Optional[str], Header(alias="X-API-Key")] = None,
    x_yodmcp_tenant: Annotated[Optional[str], Header(alias="X-YodMCP-Tenant")] = None,
    x_request_id: Annotated[Optional[str], Header(alias="X-Request-ID")] = None,
) -> AuthContext:
    keys = _configured_keys()
    default_tenant = os.environ.get("YODMCP_TENANT_ID", "default")
    rid = (x_request_id or str(uuid.uuid4())).strip()
    set_request_id(rid)

    provided: Optional[str] = None
    if authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()
    elif x_api_key:
        provided = x_api_key.strip()

    if not keys:
        tenant = (x_yodmcp_tenant or default_tenant).strip() or "default"
        set_tenant(tenant)
        return AuthContext(
            api_key_id="anonymous", tenant_id=tenant, authenticated=False, request_id=rid
        )

    if not provided or provided not in keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Provide Authorization: Bearer <key> or X-API-Key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tenant = (x_yodmcp_tenant or default_tenant).strip() or "default"
    set_tenant(tenant)
    key_id = provided[:8] + "…" if len(provided) > 8 else provided
    return AuthContext(
        api_key_id=key_id, tenant_id=tenant, authenticated=True, request_id=rid
    )


RequireAuth = Annotated[AuthContext, Depends(get_auth_context)]


def require_auth_dependency():
    return get_auth_context


def check_api_key_headers(headers: dict[str, str]) -> bool:
    """Non-FastAPI check for Starlette/MCP HTTP middleware."""
    keys = _configured_keys()
    if not keys:
        return True
    auth = headers.get("authorization") or headers.get("Authorization") or ""
    xkey = headers.get("x-api-key") or headers.get("X-API-Key") or ""
    provided = ""
    if auth.lower().startswith("bearer "):
        provided = auth[7:].strip()
    elif xkey:
        provided = xkey.strip()
    return provided in keys
