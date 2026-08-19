"""LEGACY dashboard — NOT the multi-tenant control plane.

This module still imports legacy ``core.runtime`` and is **not** wired to the
current substrate (auth, entitlements, HITL, request-scoped tenants).

Prefer:
  - GET  /api/*          (authenticated governance API)
  - GET  /api/hitl/pending
  - POST /api/hitl/{id}/decide
  - GET  /ready

This file is retained only so existing imports do not break; it may be removed
in 0.6. Do not deploy it as an operator UI.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="YodMCP Dashboard (LEGACY — do not use)", version="0.1.0-legacy")


@app.get("/", response_class=HTMLResponse)
async def index():
    return """<!DOCTYPE html>
<html><head><title>YodMCP Legacy Dashboard</title></head>
<body style="font-family:system-ui;background:#0f172a;color:#e2e8f0;padding:2rem">
  <h1>Legacy dashboard (deprecated)</h1>
  <p>Use the authenticated API control plane instead:</p>
  <ul>
    <li><code>GET /api/skills</code>, <code>/api/audit</code>, <code>/api/billing/status</code></li>
    <li><code>GET /api/hitl/pending</code> · <code>POST /api/hitl/{id}/decide</code></li>
    <li><code>GET /ready</code></li>
  </ul>
  <p>See <code>docs/PRODUCTION.md</code>.</p>
</body></html>"""


@app.get("/api/legacy-status")
async def legacy_status():
    return JSONResponse(
        {
            "deprecated": True,
            "message": "Use yodmcp-api substrate endpoints, not this dashboard",
        }
    )
