"""API key / simple AuthN for YodMCP HTTP surfaces.

Production note (P0):
- Today: static API keys from env `YODMCP_API_KEYS` (comma-separated) or single `YODMCP_API_KEY`.
- Request tenant can be overridden via `X-YodMCP-Tenant` header when key is valid.
- Health / agent-card endpoints remain open for liveness & discovery.
- Next: JWT, mTLS, per-key rate limits, request-scoped tenant binding everywhere.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request, status


@dataclass(frozen=True)
class AuthContext:
    """Authenticated caller context attached to the request."""

    api_key_id: str  # truncated key or "anonymous"
    tenant_id: str
    authenticated: bool


def _configured_keys() -> set[str]:
    raw = os.environ.get("YODMCP_API_KEYS") or os.environ.get("YODMCP_API_KEY") or ""
    keys = {k.strip() for k in raw.split(",") if k.strip()}
    return keys


def auth_required() -> bool:
    """If any keys are configured, auth is required on protected routes."""
    return bool(_configured_keys())


async def get_auth_context(
    request: Request,
    authorization: Annotated[Optional[str], Header()] = None,
    x_api_key: Annotated[Optional[str], Header(alias="X-API-Key")] = None,
    x_yodmcp_tenant: Annotated[Optional[str], Header(alias="X-YodMCP-Tenant")] = None,
) -> AuthContext:
    keys = _configured_keys()
    default_tenant = os.environ.get("YODMCP_TENANT_ID", "default")

    # Prefer Authorization: Bearer <key> or X-API-Key
    provided: Optional[str] = None
    if authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()
    elif x_api_key:
        provided = x_api_key.strip()

    if not keys:
        # Open mode (dev / self-hosted without keys configured)
        tenant = (x_yodmcp_tenant or default_tenant).strip() or "default"
        return AuthContext(api_key_id="anonymous", tenant_id=tenant, authenticated=False)

    if not provided or provided not in keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Provide Authorization: Bearer <key> or X-API-Key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Key valid — allow tenant override header for multi-tenant keys later
    tenant = (x_yodmcp_tenant or default_tenant).strip() or "default"
    key_id = provided[:8] + "…" if len(provided) > 8 else provided
    return AuthContext(api_key_id=key_id, tenant_id=tenant, authenticated=True)


# FastAPI dependency aliases
RequireAuth = Annotated[AuthContext, Depends(get_auth_context)]


def require_auth_dependency():
    """Use as Depends(require_auth_dependency()) when you want to force check."""
    return get_auth_context
