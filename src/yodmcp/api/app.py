"""Unified FastAPI app: health, A2A, governance API, billing, HITL, OpenAPI."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from yodmcp.a2a.server import create_a2a_app
from yodmcp.core.context import try_get_context
from yodmcp.core.substrate import init_substrate
from yodmcp.security.auth import RequireAuth, auth_required
from yodmcp.security.rate_limit import RateLimitMiddleware
from yodmcp import __version__


def create_api_app(init_ctx: bool = True) -> FastAPI:
    if init_ctx and try_get_context() is None:
        init_substrate(console_tracing=False)

    app = FastAPI(
        title="YodMCP Server OS API",
        version=__version__,
        description=(
            "Agent Operating System API — multi-tenant MCP kernel with A2A, "
            "memory, tasks, skills, attestation, HITL, and monetization. "
            "When YODMCP_API_KEY(S) is set, protected routes require Bearer or X-API-Key."
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
    app.add_middleware(RateLimitMiddleware)

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
            "auth_required": auth_required(),
            "surfaces": ["mcp", "a2a", "api", "cli", "sdk", "billing", "hitl"],
        }

    @app.get("/ready")
    async def ready():
        ctx = try_get_context()
        if ctx is None:
            return {"status": "not_ready", "reason": "substrate not initialized"}
        checks = {"substrate": True}
        try:
            await ctx.memory.stats()
            checks["memory"] = True
        except Exception as e:
            checks["memory"] = False
            return {"status": "not_ready", "checks": checks, "error": str(e)}
        try:
            await ctx.tasks.stats()
            checks["tasks"] = True
        except Exception:
            checks["tasks"] = False
        return {"status": "ready", "checks": checks, "version": __version__}

    @app.get("/api/memory")
    async def api_memory(auth: RequireAuth):
        ctx = try_get_context()
        if ctx is None:
            return {"error": "substrate not initialized"}
        return await ctx.memory.stats()

    @app.get("/api/audit")
    async def api_audit(auth: RequireAuth, limit: int = 30):
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
    async def api_skills(auth: RequireAuth):
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
    async def api_attestation(auth: RequireAuth, limit: int = 10):
        ctx = try_get_context()
        if ctx is None:
            return {"error": "substrate not initialized"}
        return {"stats": ctx.attestation.stats(), "claims": ctx.attestation.recent(limit)}

    @app.get("/api/billing/status")
    async def billing_status(auth: RequireAuth):
        ctx = try_get_context()
        if ctx is None:
            return {"error": "substrate not initialized"}
        ctx.billing.tenant_id = auth.tenant_id
        await ctx.billing.refresh_plan_from_entitlement()
        return ctx.billing.status()

    @app.get("/api/billing/plans")
    async def billing_plans(auth: RequireAuth):
        ctx = try_get_context()
        if ctx is None:
            from yodmcp.monetization.plans import PLANS

            return {"plans": [p.to_dict() for p in PLANS.values()]}
        return {"plans": ctx.billing.plans_catalog(), "current": ctx.billing.plan.to_dict()}

    @app.post("/api/billing/checkout")
    async def billing_checkout(auth: RequireAuth, body: dict):
        ctx = try_get_context()
        if ctx is None:
            return {"error": "substrate not initialized"}
        plan_id = body.get("plan_id", "pro")
        success = body.get("success_url", "http://localhost:8080/billing/success")
        cancel = body.get("cancel_url", "http://localhost:8080/billing/cancel")
        ctx.billing.tenant_id = auth.tenant_id
        return ctx.billing.create_checkout_stub(plan_id, success, cancel)

    @app.get("/api/usage")
    async def api_usage(auth: RequireAuth):
        ctx = try_get_context()
        if ctx is None:
            return {"error": "substrate not initialized"}
        return ctx.billing.meter.summary(auth.tenant_id)

    @app.post("/api/billing/webhook")
    async def billing_webhook(request: Request):
        ctx = try_get_context()
        if ctx is None:
            return {"error": "substrate not initialized"}
        body = await request.body()
        sig = request.headers.get("stripe-signature")
        return await ctx.billing.handle_stripe_webhook(body, sig)

    # --- HITL control plane ---
    @app.get("/api/hitl/pending")
    async def hitl_pending(auth: RequireAuth, limit: int = 50):
        ctx = try_get_context()
        if ctx is None:
            return {"error": "substrate not initialized"}
        hitl = getattr(ctx, "hitl", None)
        if hitl is None:
            return {"pending": [], "stats": {}}
        items = hitl.list_pending(tenant_id=auth.tenant_id, limit=limit)
        return {
            "pending": [
                {
                    "id": r.id,
                    "tenant_id": r.tenant_id,
                    "tool_name": r.tool_name,
                    "arguments_summary": r.arguments_summary,
                    "risk_tier": r.risk_tier,
                    "status": r.status.value,
                    "created_at": r.created_at,
                }
                for r in items
            ],
            "stats": hitl.stats(),
        }

    @app.post("/api/hitl/{request_id}/decide")
    async def hitl_decide(request_id: str, auth: RequireAuth, body: dict):
        ctx = try_get_context()
        if ctx is None:
            return {"error": "substrate not initialized"}
        hitl = getattr(ctx, "hitl", None)
        if hitl is None:
            return {"error": "hitl not available"}
        approve = bool(body.get("approve", False))
        reason = body.get("reason")
        req = hitl.decide(
            request_id, approve=approve, decided_by=auth.api_key_id, reason=reason
        )
        if req is None:
            return {"error": "not found", "id": request_id}
        return {
            "id": req.id,
            "status": req.status.value,
            "decided_by": req.decided_by,
            "reason": req.reason,
        }

    # --- Policy admin (tenant allow/deny) ---
    @app.post("/api/policy/allowlist")
    async def policy_allowlist(auth: RequireAuth, body: dict):
        ctx = try_get_context()
        if ctx is None:
            return {"error": "substrate not initialized"}
        tools = body.get("tools") or []
        tenant = body.get("tenant_id") or auth.tenant_id
        ctx.policy.set_tenant_allowlist(tenant, list(tools))
        return {"tenant_id": tenant, "allowlist": tools}

    @app.post("/api/policy/denylist")
    async def policy_denylist(auth: RequireAuth, body: dict):
        ctx = try_get_context()
        if ctx is None:
            return {"error": "substrate not initialized"}
        tools = body.get("tools") or []
        tenant = body.get("tenant_id") or auth.tenant_id
        ctx.policy.set_tenant_denylist(tenant, list(tools))
        return {"tenant_id": tenant, "denylist": tools}

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
