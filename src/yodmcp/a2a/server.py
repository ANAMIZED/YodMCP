"""Fuller A2A HTTP surface for YodMCP.

Endpoints (A2A-aligned)
-----------------------
GET  /a2a/.well-known/agent.json   – Agent Card (open)
GET  /a2a/card                    – Agent Card (alias, open)
POST /a2a/message                 – message/send (auth when keys configured)
GET  /a2a/tasks/{task_id}         – poll task (auth)
POST /a2a/tasks                   – create long-running task (auth)
GET  /a2a/health                  – liveness (open)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from yodmcp.a2a.surface import A2ASurface, build_agent_card
from yodmcp.core.context import get_context, try_get_context
from yodmcp.core.substrate import init_substrate
from yodmcp.security.auth import RequireAuth, auth_required
from yodmcp.security.rate_limit import RateLimitMiddleware
from yodmcp import __version__

logger = logging.getLogger("yodmcp.a2a")


class MessagePart(BaseModel):
    type: str = "text"
    text: str | None = None


class A2AMessage(BaseModel):
    role: str = "user"
    parts: list[MessagePart] = Field(default_factory=list)
    content: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateTaskBody(BaseModel):
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    ttl_ms: int = 3_600_000


def create_a2a_app(
    card_url: str = "http://localhost:9000/a2a",
    init_ctx: bool = True,
) -> FastAPI:
    if init_ctx and try_get_context() is None:
        init_substrate(console_tracing=False)

    surface = A2ASurface(build_agent_card(url=card_url, version=__version__))
    app = FastAPI(
        title="YodMCP A2A",
        version=__version__,
        description="Agent2Agent surface for YodMCP Agent Operating System",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)

    @app.get("/a2a/.well-known/agent.json")
    @app.get("/a2a/card")
    async def agent_card() -> dict[str, Any]:
        return surface.get_card()

    @app.get("/a2a/health")
    async def health() -> dict[str, Any]:
        ctx = try_get_context()
        return {
            "status": "ok",
            "service": "YodMCP-A2A",
            "version": __version__,
            "substrate": ctx is not None,
            "auth_required": auth_required(),
        }

    @app.post("/a2a/message")
    async def message_send(msg: A2AMessage, auth: RequireAuth) -> dict[str, Any]:
        payload = msg.model_dump()
        if msg.content and not msg.parts:
            payload["parts"] = [{"type": "text", "text": msg.content}]

        text = msg.content or ""
        for p in msg.parts:
            if p.text:
                text += p.text

        if text.lower().startswith("task:"):
            ctx = try_get_context()
            if ctx is None:
                raise HTTPException(503, "substrate not initialized")
            desc = text[5:].strip()
            rec = await ctx.tasks.create(tool_name="a2a_message", metadata={"description": desc, "tenant": auth.tenant_id})
            handle = ctx.tasks.to_handle(rec)
            return {
                "role": "agent",
                "parts": [{"type": "text", "text": f"Task created: {handle['taskId']}"}],
                "metadata": {"routed": "tasks_create", "task": handle, "tenant": auth.tenant_id},
            }

        return await surface.handle_message(payload)

    @app.post("/a2a/tasks")
    async def create_task(body: CreateTaskBody, auth: RequireAuth) -> dict[str, Any]:
        ctx = try_get_context()
        if ctx is None:
            raise HTTPException(503, "substrate not initialized")
        rec = await ctx.tasks.create(
            tool_name="a2a_task",
            ttl_ms=body.ttl_ms,
            metadata={"description": body.description, "tenant": auth.tenant_id, **body.metadata},
        )
        return ctx.tasks.to_handle(rec)

    @app.get("/a2a/tasks/{task_id}")
    async def get_task(task_id: str, auth: RequireAuth) -> dict[str, Any]:
        ctx = try_get_context()
        if ctx is None:
            raise HTTPException(503, "substrate not initialized")
        rec = await ctx.tasks.get(task_id)
        if rec is None:
            raise HTTPException(404, f"task {task_id} not found")
        return ctx.tasks.to_handle(rec)

    return app


def main() -> None:
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="YodMCP A2A HTTP server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()
    app = create_a2a_app(card_url=f"http://{args.host}:{args.port}/a2a")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
