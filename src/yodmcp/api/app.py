"""Unified FastAPI app: health, A2A, governance API, billing, OpenAPI."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from yodmcp.a2a.server import create_a2a_app
from yodmcp.core.context import try_get_context
from yodmcp.core.substrate import init_substrate
from yodmcp import __version__


def create_api_app(init_ctx: bool = True) -> FastAPI:
    if init_ctx and try_get_context() is None:
        init_substrate(console_tracing=False)

    app = FastAPI(
        title="YodMCP Server OS API",
        version=__version__,
        description=(
            "Agent Operating System API — MCP-compatible kernel with A2A, "
            "memory, tasks, skills, attestation, and monetization."
        ),
        contact={"name": "YodMCP", "url": "https://github.com/ANAMIZED/YodMCP"},
        license_info={"name": "Apache-2.0"},
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    a2a = create_a2a_app(init_ctx=False)
    for route in a2a.routes:
        app.routes.append(route)

    @app.get("/health")
    async def root_health():
        ctx = try_get_context()
        return {
            "status": "ok",
            "service": "YodMCP",
            "version": __version__,
            "substrate": ctx is not None,
            "surfaces": ["mcp", "a2a", "api", "cli", "sdk", "billing"],
        }

    @app.get("/api/memory")
    async def api_memory():
        ctx = try_get_context()
        if ctx is None:
            return {"error": "substrate not initialized"}
        return await ctx.memory.stats()

    @app.get("/api/audit")
    async def api_audit(limit: int = 30):
        ctx = try_get_context()
        if ctx is None:
            return {"error": "substrate not initialized"}
        events = ctx.audit.recent(limit=limit)
        return {
            "stats": ctx.audit.stats(),
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

    @app.get("/api/skills")
    async def api_skills():
        ctx = try_get_context()
        if ctx is None:
            return {"error": "substrate not initialized"}
        skills = ctx.skills.list_skills()
        return {
            "count": len(skills),
            "skills": [
                {"name": s.name, "uri": s.uri, "description": s.description, "tags": s.tags}
                for s in skills
            ],
        }

    @app.get("/api/attestation")
    async def api_attestation(limit: int = 10):
        ctx = try_get_context()
        if ctx is None:
            return {"error": "substrate not initialized"}
        return {"stats": ctx.attestation.stats(), "claims": ctx.attestation.recent(limit)}

    @app.get("/api/billing/status")
    async def billing_status():
        ctx = try_get_context()
        if ctx is None:
            return {"error": "substrate not initialized"}
        return ctx.billing.status()

    @app.get("/api/billing/plans")
    async def billing_plans():
        ctx = try_get_context()
        if ctx is None:
            from yodmcp.monetization.plans import PLANS
            return {"plans": [p.to_dict() for p in PLANS.values()]}
        return {"plans": ctx.billing.plans_catalog(), "current": ctx.billing.plan.to_dict()}

    @app.post("/api/billing/checkout")
    async def billing_checkout(body: dict):
        ctx = try_get_context()
        if ctx is None:
            return {"error": "substrate not initialized"}
        plan_id = body.get("plan_id", "pro")
        success = body.get("success_url", "http://localhost:8080/billing/success")
        cancel = body.get("cancel_url", "http://localhost:8080/billing/cancel")
        return ctx.billing.create_checkout_stub(plan_id, success, cancel)

    @app.get("/api/usage")
    async def api_usage():
        ctx = try_get_context()
        if ctx is None:
            return {"error": "substrate not initialized"}
        return ctx.billing.meter.summary(ctx.billing.tenant_id)

    return app


def main() -> None:
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="YodMCP Server OS API")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    uvicorn.run(create_api_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
