"""Legacy dashboard shim — redirects operators to the WebMCP page."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

app = FastAPI(title="YodMCP Dashboard", version="0.5.0-webmcp")


@app.get("/")
async def index():
    return RedirectResponse(url="/dashboard", status_code=307)


@app.get("/legacy", response_class=HTMLResponse)
async def legacy():
    return """<!DOCTYPE html>
<html><head><title>YodMCP Dashboard</title></head>
<body style="font-family:system-ui;background:#0f172a;color:#e2e8f0;padding:2rem">
  <h1>Use /dashboard</h1>
  <p>WebMCP control plane: <a href="/dashboard">/dashboard</a></p>
  <p>Authenticated API: <code>GET /api/skills</code>, <code>/api/audit</code>, <code>/ready</code></p>
</body></html>"""


@app.get("/api/legacy-status")
async def legacy_status():
    return JSONResponse({"deprecated": True, "use": "/dashboard"})
