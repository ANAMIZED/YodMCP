"""Core YodMCP server — MCP 2026-07-28 compliant Agent OS runtime."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp.server import MCPServer
from mcp.types import Icon

from yodmcp.core.substrate import init_substrate
from yodmcp.core.context import get_context
from yodmcp.tools import register_core_tools
from yodmcp.a2a.surface import build_agent_card

logger = logging.getLogger("yodmcp.core")


@asynccontextmanager
async def lifespan(server: MCPServer) -> AsyncIterator[dict[str, Any]]:
    ctx = init_substrate(console_tracing=False)
    logger.info("YodMCP substrate ready")
    yield {
        "memory": ctx.memory,
        "policy": ctx.policy,
        "audit": ctx.audit,
        "cache": ctx.cache,
        "attestation": ctx.attestation,
        "tasks": ctx.tasks,
        "skills": ctx.skills,
    }
    await ctx.memory.close()
    logger.info("YodMCP substrate shutdown complete")


def create_server() -> MCPServer:
    server = MCPServer(
        name="YodMCP",
        title="YodMCP — Ultimate Autonomous MCP Server",
        description=(
            "Agent Operating System on MCP 2026-07-28. Multi-graph memory, "
            "Tasks, Skills-over-MCP, A2A, semantic/plan cache, cMCP attestation, OTEL."
        ),
        version="0.4.0",
        instructions=(
            "Prefer high-level tools. Use memory_* , tasks_* , skills_list, "
            "a2a_card, plan_cache_*. High-risk actions emit TRACE claims."
        ),
        website_url="https://github.com/ANAMIZED/YodMCP",
        icons=[Icon(src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0iIzAwN2JmZiIgZD0iTTEyIDJMMiA3djEwYzAgNS41IDMuODQgMTAuNzQgOSAxMiA1LjE2LTEuMjYgOS02LjUgOS0xMlY3bC0xMC01eiIvPjwvc3ZnPg==")],
        lifespan=lifespan,
        debug=False,
        log_level="INFO",
    )
    register_core_tools(server)

    @server.resource("skills://{name}")
    async def skill_resource(name: str) -> str:
        ctx = get_context()
        content = ctx.skills.read_uri(f"skills://{name}")
        return content if content is not None else f"# Skill not found: {name}\n"

    @server.resource("yodmcp://agent-card")
    async def agent_card_resource() -> str:
        return json.dumps(build_agent_card(), indent=2)

    return server


server = create_server()
