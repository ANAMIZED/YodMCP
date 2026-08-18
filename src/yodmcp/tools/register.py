"""Core high-level tools for YodMCP - memory, tasks, skills, cache, attestation, A2A."""

from __future__ import annotations

from typing import Any

from mcp.server import MCPServer

from yodmcp.tools.gate import _gated


def register_core_tools(server: MCPServer) -> None:
    @server.tool(name="memory_write", description="Persist into multi-graph hierarchical memory.")
    async def memory_write(
        content: str,
        level: str = "episodic",
        importance: float = 0.5,
        agent_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        causal_parent: str | None = None,
        entities: list[str] | None = None,
    ) -> dict[str, Any]:
        ctx, decision = _gated("memory_write", {"level": level, "importance": importance})
        if not decision.allowed:
            return {"error": decision.reason, "requires_hitl": decision.requires_hitl}
        item_id = await ctx.memory.write(
            content=content, level=level, importance=importance,
            agent_id=agent_id, session_id=session_id, metadata=metadata,
            causal_parent=causal_parent, entities=entities,
        )
        return {"item_id": item_id, "level": level, "status": "written", "requires_hitl": decision.requires_hitl}

    @server.tool(name="memory_read", description="Retrieve from multi-graph memory with embedding similarity.")
    async def memory_read(
        query: str | None = None,
        level: str | None = None,
        limit: int = 5,
        agent_id: str | None = None,
        session_id: str | None = None,
        item_id: str | None = None,
        graph: str | None = None,
    ) -> dict[str, Any]:
        ctx, decision = _gated("memory_read", {"query": query})
        if not decision.allowed:
            return {"error": decision.reason}
        cache_key = f"{query}|{level}|{limit}|{graph}"
        cached = ctx.cache.get_exact("memory_read", cache_key)
        if cached is not None:
            return {"cached": True, **cached}
        items = await ctx.memory.read(
            query=query, level=level, limit=limit, agent_id=agent_id,
            session_id=session_id, item_id=item_id, graph=graph,
        )
        result = {"count": len(items), "items": items, "cached": False}
        ctx.cache.put("memory_read", cache_key, result)
        return result

    @server.tool(name="memory_consolidate", description="Promote high-importance episodic items into semantic graph.")
    async def memory_consolidate(from_level: str = "episodic") -> dict[str, Any]:
        ctx, decision = _gated("memory_consolidate", {})
        if not decision.allowed:
            return {"error": decision.reason}
        count = await ctx.memory.consolidate(from_level=from_level)
        return {"promoted": count, "from_level": from_level}

    @server.tool(name="memory_stats", description="Node and edge counts across memory levels and graphs.")
    async def memory_stats() -> dict[str, Any]:
        ctx, _ = _gated("memory_stats", {})
        return await ctx.memory.stats()

    @server.tool(name="discover_capabilities", description="Progressive discovery of tools, skills, tasks, A2A.")
    async def discover_capabilities(query: str | None = None) -> dict[str, Any]:
        ctx, _ = _gated("discover_capabilities", {"query": query})
        caps = [
            {"name": n, "kind": "tool"} for n in [
                "memory_write", "memory_read", "memory_consolidate", "memory_stats",
                "tasks_create", "tasks_get", "tasks_cancel", "tasks_stats",
                "skills_list", "a2a_card", "plan_cache_get", "plan_cache_put",
                "cache_stats", "attestation_recent", "audit_recent", "echo",
            ]
        ]
        for s in ctx.skills.list_skills():
            caps.append({"name": s.name, "kind": "skill", "uri": s.uri})
        if query:
            q = query.lower()
            caps = [c for c in caps if q in c["name"] or q in c.get("kind", "")]
        return {"capabilities": caps, "count": len(caps)}

    @server.tool(name="echo", description="Connectivity probe.")
    async def echo(message: str = "ping") -> dict[str, Any]:
        return {"echo": message, "server": "YodMCP", "version": "0.2.0"}

    @server.tool(name="tasks_create", description="Create durable async task handle (Tasks extension).")
    async def tasks_create(tool_name: str | None = None, ttl_ms: int = 3600000, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx, decision = _gated("tasks_create", {"tool_name": tool_name})
        if not decision.allowed:
            return {"error": decision.reason}
        rec = await ctx.tasks.create(tool_name=tool_name, ttl_ms=ttl_ms, metadata=metadata)
        return ctx.tasks.to_handle(rec)

    @server.tool(name="tasks_get", description="Poll task status/result.")
    async def tasks_get(task_id: str) -> dict[str, Any]:
        ctx, decision = _gated("tasks_get", {"task_id": task_id})
        if not decision.allowed:
            return {"error": decision.reason}
        rec = await ctx.tasks.get(task_id)
        if not rec:
            return {"error": "task_not_found", "task_id": task_id}
        return ctx.tasks.to_handle(rec)

    @server.tool(name="tasks_cancel", description="Cancel a task.")
    async def tasks_cancel(task_id: str) -> dict[str, Any]:
        ctx, decision = _gated("tasks_cancel", {"task_id": task_id})
        if not decision.allowed:
            return {"error": decision.reason}
        ok = await ctx.tasks.cancel(task_id)
        return {"cancelled": ok, "task_id": task_id}

    @server.tool(name="tasks_stats", description="Task store stats.")
    async def tasks_stats() -> dict[str, Any]:
        ctx, _ = _gated("tasks_stats", {})
        return await ctx.tasks.stats()

    @server.tool(name="skills_list", description="List Agent Skills (skills:// resources).")
    async def skills_list() -> dict[str, Any]:
        ctx, _ = _gated("skills_list", {})
        skills = ctx.skills.list_skills()
        return {
            "count": len(skills),
            "skills": [{"name": s.name, "uri": s.uri, "description": s.description, "tags": s.tags} for s in skills],
            "resources": ctx.skills.as_resources(),
        }

    @server.tool(name="a2a_card", description="YodMCP A2A Agent Card.")
    async def a2a_card() -> dict[str, Any]:
        from yodmcp.a2a.surface import build_agent_card
        _, _ = _gated("a2a_card", {})
        return build_agent_card()

    @server.tool(name="plan_cache_get", description="Semantic plan cache lookup.")
    async def plan_cache_get(task_description: str) -> dict[str, Any]:
        ctx, decision = _gated("plan_cache_get", {})
        if not decision.allowed:
            return {"error": decision.reason}
        plan, score = ctx.cache.get_plan(task_description)
        return {"found": plan is not None, "score": score, "plan": plan}

    @server.tool(name="plan_cache_put", description="Store plan template for reuse.")
    async def plan_cache_put(task_description: str, plan: dict[str, Any]) -> dict[str, Any]:
        ctx, decision = _gated("plan_cache_put", {})
        if not decision.allowed:
            return {"error": decision.reason}
        key = ctx.cache.put_plan(task_description, plan)
        return {"cached": True, "key": key}

    @server.tool(name="cache_stats", description="Cache statistics.")
    async def cache_stats() -> dict[str, Any]:
        ctx, _ = _gated("cache_stats", {})
        return ctx.cache.stats()

    @server.tool(name="audit_recent", description="Recent audit events.")
    async def audit_recent(limit: int = 20) -> dict[str, Any]:
        ctx, _ = _gated("audit_recent", {})
        events = ctx.audit.recent(limit=limit)
        return {
            "count": len(events),
            "events": [{"id": e.id, "ts": e.timestamp, "type": e.event_type, "tool": e.tool_name,
                        "decision": e.decision, "risk": e.risk_tier, "outcome": e.outcome} for e in events],
            "stats": ctx.audit.stats(),
        }

    @server.tool(name="attestation_recent", description="Recent TRACE claims (cMCP-style).")
    async def attestation_recent(limit: int = 10) -> dict[str, Any]:
        ctx, _ = _gated("attestation_recent", {})
        return {"count": len(ctx.attestation.recent(limit)), "claims": ctx.attestation.recent(limit),
                "stats": ctx.attestation.stats()}
