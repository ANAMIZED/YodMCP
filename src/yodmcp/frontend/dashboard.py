"""Lightweight governance & observability dashboard for YodMCP.

Serves a minimal HTML UI + JSON API over the same process.
In production this becomes a full control plane with auth, multi-tenant
views, and OpenTelemetry integration.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from yodmcp.core.runtime import get_runtime, init_runtime

app = FastAPI(title="YodMCP Dashboard", version="0.1.0")


@app.on_event("startup")
async def startup():
    init_runtime()


@app.get("/", response_class=HTMLResponse)
async def index():
    rt = get_runtime()
    stats = await rt.memory.stats()
    audit_stats = rt.audit.stats()
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>YodMCP Dashboard</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #0f172a; color: #e2e8f0; }}
    h1 {{ color: #38bdf8; }}
    .card {{ background: #1e293b; border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; }}
    .metric {{ font-size: 1.75rem; font-weight: 700; color: #7dd3fc; }}
    a {{ color: #38bdf8; }}
    code {{ background: #334155; padding: 0.15rem 0.4rem; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>YodMCP — Agent Operating System</h1>
  <p>Ultimate Autonomous MCP Server (prototype 0.1.0) · MCP 2026-07-28</p>

  <div class="card">
    <h2>Memory Substrate</h2>
    <div class="grid">
      <div><div class="metric">{stats.get("working", 0)}</div>Working</div>
      <div><div class="metric">{stats.get("episodic", 0)}</div>Episodic</div>
      <div><div class="metric">{stats.get("semantic", 0)}</div>Semantic</div>
      <div><div class="metric">{stats.get("procedural", 0)}</div>Procedural</div>
    </div>
  </div>

  <div class="card">
    <h2>Audit / Decision System of Record</h2>
    <p>Total events: <strong>{audit_stats.get("total_events", 0)}</strong></p>
    <p>Log path: <code>{audit_stats.get("log_path")}</code></p>
    <p><a href="/api/audit">JSON recent events</a> · <a href="/api/memory">JSON memory stats</a></p>
  </div>

  <div class="card">
    <h2>Core Tools</h2>
    <ul>
      <li><code>memory_write</code> / <code>memory_read</code> / <code>memory_consolidate</code> / <code>memory_stats</code></li>
      <li><code>discover_capabilities</code></li>
      <li><code>echo</code></li>
      <li><code>audit_recent</code></li>
    </ul>
  </div>

  <div class="card">
    <h2>Transports</h2>
    <p>stdio (local hosts) · Streamable HTTP (scale-out)</p>
    <p>Run: <code>python -m yodmcp</code> or <code>python -m yodmcp --http --port 8000</code></p>
  </div>
</body>
</html>"""
    return HTMLResponse(html)


@app.get("/api/memory")
async def api_memory():
    rt = get_runtime()
    return await rt.memory.stats()


@app.get("/api/audit")
async def api_audit(limit: int = 30):
    rt = get_runtime()
    events = rt.audit.recent(limit=limit)
    return {
        "stats": rt.audit.stats(),
        "events": [
            {
                "id": e.id,
                "ts": e.timestamp,
                "type": e.event_type,
                "tool": e.tool_name,
                "decision": e.decision,
                "risk": e.risk_tier,
                "outcome": e.outcome,
            }
            for e in events
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "YodMCP", "version": "0.1.0"}
