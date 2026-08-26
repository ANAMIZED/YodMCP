"""Core high-level tools for YodMCP - memory, tasks, skills, cache, attestation, A2A."""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server import MCPServer
from pydantic import Field

from yodmcp.tools.gate import _gated
from yodmcp.tools.hints import tool_hints

_RO = dict(read_only=True, destructive=False, idempotent=True, open_world=False)
_WR = dict(read_only=False, destructive=False, idempotent=False, open_world=False)
_DEL = dict(read_only=False, destructive=True, idempotent=True, open_world=False)


def register_core_tools(server: MCPServer) -> None:
    @server.tool(
        name="memory_write",
        title="Write a memory node",
        description=(
            "Insert one node into the multi-graph memory store (episodic/semantic/procedural) "
            "and optionally add causal or entity edges. Use to remember facts, decisions, or "
            "session state the host should own. Do not use for reusable task plans — that is "
            "plan_cache_put. Mutating and not idempotent: each call creates a new item_id. "
            "Gated by plan quota. Nodes with importance >= 0.8 are what memory_consolidate later "
            "promotes. Auth: tool policy gate; no network I/O."
        ),
        annotations=tool_hints("Write a memory node", **_WR),
    )
    async def memory_write(
        content: Annotated[str, Field(description="Plaintext body stored as the memory node.")],
        level: Annotated[str, Field(description="Memory level: episodic, semantic, or procedural. Default episodic.")] = "episodic",
        importance: Annotated[float, Field(description="Salience 0–1. Values >= 0.8 are eligible for memory_consolidate.")] = 0.5,
        agent_id: Annotated[str | None, Field(description="Optional agent owner used for later filtered reads.")] = None,
        session_id: Annotated[str | None, Field(description="Optional session scope used for later filtered reads.")] = None,
        metadata: Annotated[dict[str, Any] | None, Field(description="Optional JSON metadata attached to the node.")] = None,
        causal_parent: Annotated[str | None, Field(description="Existing node id to link as a causal parent.")] = None,
        entities: Annotated[list[str] | None, Field(description="Entity names to index. If omitted, capitalized tokens are extracted.")] = None,
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

    @server.tool(
        name="memory_read",
        title="Read memory nodes",
        description=(
            "Retrieve memory nodes by embedding similarity and/or exact item_id, optionally "
            "filtered by level, agent, session, or graph kind. Use to recall stored facts. "
            "Do not use for reusable plan templates — that is plan_cache_get. Read-only and "
            "idempotent. Returns scored items plus neighbor ids. Auth: tool policy gate."
        ),
        annotations=tool_hints("Read memory nodes", **_RO),
    )
    async def memory_read(
        query: Annotated[str | None, Field(description="Free-text query embedded for similarity ranking. Omit when using item_id.")] = None,
        level: Annotated[str | None, Field(description="Optional level filter: episodic, semantic, or procedural.")] = None,
        limit: Annotated[int, Field(description="Maximum nodes to return. Default 5.")] = 5,
        agent_id: Annotated[str | None, Field(description="If set, only nodes owned by this agent or unscoped nodes.")] = None,
        session_id: Annotated[str | None, Field(description="If set, only nodes in this session or unscoped nodes.")] = None,
        item_id: Annotated[str | None, Field(description="Fetch a single node by id instead of searching.")] = None,
        graph: Annotated[str | None, Field(description="If set, only return neighbors for this graph kind (temporal/causal/semantic/entity).")] = None,
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

    @server.tool(
        name="memory_delete",
        title="Delete a memory node",
        description=(
            "Permanently delete one memory node and its incident edges/entity index rows. "
            "Use when a fact must be forgotten. Do not use to hide a node while keeping it — "
            "there is no soft-delete. Destructive and idempotent: missing ids return deleted=false. "
            "Prefer memory_read first to confirm the id. Auth: policy gate; may require HITL."
        ),
        annotations=tool_hints("Delete a memory node", **_DEL),
    )
    async def memory_delete(
        item_id: Annotated[str, Field(description="Id of the memory node to delete (from memory_write or memory_read).")],
    ) -> dict[str, Any]:
        ctx, decision = _gated("memory_delete", {"item_id": item_id})
        if not decision.allowed:
            return {"error": decision.reason, "requires_hitl": decision.requires_hitl}
        deleted = await ctx.memory.delete(item_id)
        return {"deleted": deleted, "item_id": item_id, "requires_hitl": decision.requires_hitl}

    @server.tool(
        name="memory_consolidate",
        title="Consolidate episodic memory",
        description=(
            "Promote high-importance nodes (importance >= 0.8) from from_level into new semantic "
            "summary nodes. Use after a burst of memory_write calls to compress working memory. "
            "Do not use as a delete — source nodes remain. Mutating, not idempotent (re-running "
            "creates additional summaries). Auth: tool policy gate."
        ),
        annotations=tool_hints("Consolidate episodic memory", **_WR),
    )
    async def memory_consolidate(
        from_level: Annotated[str, Field(description="Source level to promote from. Default episodic.")] = "episodic",
    ) -> dict[str, Any]:
        ctx, decision = _gated("memory_consolidate", {})
        if not decision.allowed:
            return {"error": decision.reason}
        count = await ctx.memory.consolidate(from_level=from_level)
        return {"promoted": count, "from_level": from_level}

    @server.tool(
        name="memory_stats",
        title="Memory graph statistics",
        description=(
            "Return node counts by level plus edge and entity-index sizes for the memory store. "
            "Use for capacity/health checks. Do not use to read node content — that is memory_read. "
            "Read-only, idempotent, no parameters. Auth: tool policy gate."
        ),
        annotations=tool_hints("Memory graph statistics", **_RO),
    )
    async def memory_stats() -> dict[str, Any]:
        ctx, _ = _gated("memory_stats", {})
        return await ctx.memory.stats()

    @server.tool(
        name="discover_capabilities",
        title="Discover tools and skills",
        description=(
            "List this kernel's MCP tools and loaded Agent Skills, optionally filtered by a "
            "substring query. Use at session start or when unsure which tool to call. Do not use "
            "to fetch the A2A interoperability card — that is a2a_card — or skill bodies "
            "(read skills:// resources after skills_list). Read-only and idempotent. Auth: gate."
        ),
        annotations=tool_hints("Discover tools and skills", **_RO),
    )
    async def discover_capabilities(
        query: Annotated[str | None, Field(description="Optional case-insensitive substring filter on name or kind (tool|skill).")] = None,
    ) -> dict[str, Any]:
        ctx, _ = _gated("discover_capabilities", {"query": query})
        caps = [
            {"name": n, "kind": "tool"} for n in [
                "memory_write", "memory_read", "memory_delete", "memory_consolidate", "memory_stats",
                "tasks_create", "tasks_get", "tasks_list", "tasks_update", "tasks_cancel", "tasks_stats",
                "skills_list", "a2a_card", "plan_cache_get", "plan_cache_put", "plan_cache_delete",
                "cache_stats", "attestation_recent", "audit_recent", "echo",
            ]
        ]
        for s in ctx.skills.list_skills():
            caps.append({"name": s.name, "kind": "skill", "uri": s.uri})
        if query:
            q = query.lower()
            caps = [c for c in caps if q in c["name"] or q in c.get("kind", "")]
        return {"capabilities": caps, "count": len(caps)}

    @server.tool(
        name="echo",
        title="Echo a connectivity probe",
        description=(
            "Return the provided message plus server name/version to confirm the MCP session is "
            "alive. Use as a liveness probe. Do not use to discover tools (discover_capabilities) "
            "or to persist state. Read-only, idempotent, no network I/O, no quota side effects "
            "beyond the standard tool gate. message defaults to 'ping'."
        ),
        annotations=tool_hints("Echo a connectivity probe", **_RO),
    )
    async def echo(
        message: Annotated[str, Field(description="Payload echoed back unchanged. Default 'ping'.")] = "ping",
    ) -> dict[str, Any]:
        from yodmcp import __version__
        return {"echo": message, "server": "YodMCP", "version": __version__}

    @server.tool(
        name="tasks_create",
        title="Create a durable task",
        description=(
            "Create a durable async task handle (pending) that survives process restart when the "
            "sqlite tasks backend is enabled. Use to start long-running work you will poll with "
            "tasks_get or list with tasks_list. Do not use to store facts (memory_write) or plans "
            "(plan_cache_put). Mutating, not idempotent. ttl_ms controls handle expiry hint. "
            "Auth: tool policy gate + plan quota."
        ),
        annotations=tool_hints("Create a durable task", **_WR),
    )
    async def tasks_create(
        tool_name: Annotated[str | None, Field(description="Optional originating tool or job label stored on the handle.")] = None,
        ttl_ms: Annotated[int, Field(description="Suggested time-to-live in milliseconds. Default 3600000 (1 hour).")] = 3600000,
        metadata: Annotated[dict[str, Any] | None, Field(description="Optional JSON metadata stored with the task.")] = None,
    ) -> dict[str, Any]:
        ctx, decision = _gated("tasks_create", {"tool_name": tool_name})
        if not decision.allowed:
            return {"error": decision.reason}
        rec = await ctx.tasks.create(tool_name=tool_name, ttl_ms=ttl_ms, metadata=metadata)
        return ctx.tasks.to_handle(rec)

    @server.tool(
        name="tasks_get",
        title="Get a task by id",
        description=(
            "Fetch one task handle by task_id (status, progress, result, error). Use to poll after "
            "tasks_create. Do not use for aggregate counts — that is tasks_stats — or to list many "
            "tasks (tasks_list). Read-only and idempotent. Missing ids return task_not_found. "
            "Auth: tool policy gate."
        ),
        annotations=tool_hints("Get a task by id", **_RO),
    )
    async def tasks_get(
        task_id: Annotated[str, Field(description="Task id returned by tasks_create / tasks_list.")],
    ) -> dict[str, Any]:
        ctx, decision = _gated("tasks_get", {"task_id": task_id})
        if not decision.allowed:
            return {"error": decision.reason}
        rec = await ctx.tasks.get(task_id)
        if not rec:
            return {"error": "task_not_found", "task_id": task_id}
        return ctx.tasks.to_handle(rec)

    @server.tool(
        name="tasks_list",
        title="List recent tasks",
        description=(
            "List task handles, newest updated first, optionally filtered by status. Use to recover "
            "ids after restart. Do not use to poll a known id (tasks_get) or to mutate state. "
            "Read-only and idempotent. Auth: tool policy gate."
        ),
        annotations=tool_hints("List recent tasks", **_RO),
    )
    async def tasks_list(
        limit: Annotated[int, Field(description="Maximum handles to return. Default 20.")] = 20,
        status: Annotated[str | None, Field(description="Optional status filter: pending, running, input_required, completed, failed, cancelled.")] = None,
    ) -> dict[str, Any]:
        ctx, decision = _gated("tasks_list", {"status": status})
        if not decision.allowed:
            return {"error": decision.reason}
        recs = await ctx.tasks.list(limit=limit, status=status)
        return {"count": len(recs), "tasks": [ctx.tasks.to_handle(r) for r in recs]}

    @server.tool(
        name="tasks_update",
        title="Update a task",
        description=(
            "Patch status, progress, message, result, or error on an existing task. Use while a "
            "worker is running. Do not use to cancel — that is tasks_cancel — or to create a new "
            "handle (tasks_create). Mutating; last write wins. Missing ids return task_not_found. "
            "Auth: tool policy gate."
        ),
        annotations=tool_hints("Update a task", **_WR),
    )
    async def tasks_update(
        task_id: Annotated[str, Field(description="Task id to patch.")],
        status: Annotated[str | None, Field(description="New status if changing: pending, running, input_required, completed, failed, cancelled.")] = None,
        progress: Annotated[float | None, Field(description="Progress 0–1 if reporting advancement.")] = None,
        message: Annotated[str | None, Field(description="Human-readable status message.")] = None,
        result: Annotated[Any | None, Field(description="Structured result payload when completing.")] = None,
        error: Annotated[str | None, Field(description="Error string when failing.")] = None,
    ) -> dict[str, Any]:
        ctx, decision = _gated("tasks_update", {"task_id": task_id})
        if not decision.allowed:
            return {"error": decision.reason}
        rec = await ctx.tasks.update(
            task_id, status=status, progress=progress, message=message, result=result, error=error
        )
        if not rec:
            return {"error": "task_not_found", "task_id": task_id}
        return ctx.tasks.to_handle(rec)

    @server.tool(
        name="tasks_cancel",
        title="Cancel a task",
        description=(
            "Mark a task cancelled. Use to stop polling a handle you no longer need. Does not kill "
            "an external worker process — it only updates kernel state. Destructive relative to "
            "the handle, idempotent if already cancelled. Missing ids return cancelled=false. "
            "Prefer tasks_get first. Auth: tool policy gate."
        ),
        annotations=tool_hints("Cancel a task", **_DEL),
    )
    async def tasks_cancel(
        task_id: Annotated[str, Field(description="Task id to mark cancelled.")],
    ) -> dict[str, Any]:
        ctx, decision = _gated("tasks_cancel", {"task_id": task_id})
        if not decision.allowed:
            return {"error": decision.reason}
        ok = await ctx.tasks.cancel(task_id)
        return {"cancelled": ok, "task_id": task_id}

    @server.tool(
        name="tasks_stats",
        title="Task store statistics",
        description=(
            "Return total task count and counts by status for the task store. Use for dashboards. "
            "Do not use to read a specific handle (tasks_get) or to list handles (tasks_list). "
            "Read-only, idempotent, no parameters. Auth: tool policy gate."
        ),
        annotations=tool_hints("Task store statistics", **_RO),
    )
    async def tasks_stats() -> dict[str, Any]:
        ctx, _ = _gated("tasks_stats", {})
        return await ctx.tasks.stats()

    @server.tool(
        name="skills_list",
        title="List Agent Skills",
        description=(
            "List loaded Agent Skills with name, skills:// URI, description, and tags. Use to find "
            "skill resources to read next. Does not return skill markdown bodies — fetch those via "
            "the skills://{name} resource. Do not use for the A2A card (a2a_card). Read-only. "
            "Auth: tool policy gate."
        ),
        annotations=tool_hints("List Agent Skills", **_RO),
    )
    async def skills_list() -> dict[str, Any]:
        ctx, _ = _gated("skills_list", {})
        skills = ctx.skills.list_skills()
        return {
            "count": len(skills),
            "skills": [{"name": s.name, "uri": s.uri, "description": s.description, "tags": s.tags} for s in skills],
            "resources": ctx.skills.as_resources(),
        }

    @server.tool(
        name="a2a_card",
        title="Get A2A Agent Card",
        description=(
            "Return this process's A2A Agent Card JSON (name, skills, endpoints) for agent-to-agent "
            "interop. Use when another agent needs the card. Do not use to list MCP tools or skills "
            "— that is discover_capabilities or skills_list. Read-only, no parameters, no side "
            "effects. Auth: tool policy gate."
        ),
        annotations=tool_hints("Get A2A Agent Card", **_RO),
    )
    async def a2a_card() -> dict[str, Any]:
        from yodmcp.a2a.surface import build_agent_card
        _, _ = _gated("a2a_card", {})
        return build_agent_card()

    @server.tool(
        name="plan_cache_get",
        title="Lookup a cached plan",
        description=(
            "Semantic lookup of a previously stored plan template keyed by task_description. Use "
            "to reuse a multi-step plan. Do not use to recall facts from memory (memory_read) or "
            "to write a plan (plan_cache_put). Read-only. Returns found, similarity score, and plan. "
            "Default similarity threshold is 0.68. Auth: tool policy gate."
        ),
        annotations=tool_hints("Lookup a cached plan", **_RO),
    )
    async def plan_cache_get(
        task_description: Annotated[str, Field(description="Natural-language task used as the semantic lookup key.")],
    ) -> dict[str, Any]:
        ctx, decision = _gated("plan_cache_get", {})
        if not decision.allowed:
            return {"error": decision.reason}
        plan, score = ctx.cache.get_plan(task_description)
        return {"found": plan is not None, "score": score, "plan": plan}

    @server.tool(
        name="plan_cache_put",
        title="Store a plan template",
        description=(
            "Store a structured plan template keyed by task_description for later semantic reuse. "
            "Use after you have a working plan. Do not use for episodic facts (memory_write). "
            "Mutating; same task_description overwrites the exact key. Auth: tool policy gate."
        ),
        annotations=tool_hints("Store a plan template", **_WR),
    )
    async def plan_cache_put(
        task_description: Annotated[str, Field(description="Natural-language key the plan is stored and later looked up under.")],
        plan: Annotated[dict[str, Any], Field(description="Structured plan object, typically including a steps list.")],
    ) -> dict[str, Any]:
        ctx, decision = _gated("plan_cache_put", {})
        if not decision.allowed:
            return {"error": decision.reason}
        key = ctx.cache.put_plan(task_description, plan)
        return {"cached": True, "key": key}

    @server.tool(
        name="plan_cache_delete",
        title="Delete a cached plan",
        description=(
            "Delete the exact plan-cache entry for task_description. Use to drop a stale template. "
            "Does not delete memory nodes (that is memory_delete). Destructive and idempotent: "
            "missing keys return deleted=false. Auth: tool policy gate."
        ),
        annotations=tool_hints("Delete a cached plan", **_DEL),
    )
    async def plan_cache_delete(
        task_description: Annotated[str, Field(description="Exact task_description key previously passed to plan_cache_put.")],
    ) -> dict[str, Any]:
        ctx, decision = _gated("plan_cache_delete", {})
        if not decision.allowed:
            return {"error": decision.reason, "requires_hitl": decision.requires_hitl}
        deleted = ctx.cache.delete_plan(task_description)
        return {"deleted": deleted, "task_description": task_description}

    @server.tool(
        name="cache_stats",
        title="Cache statistics",
        description=(
            "Return entry counts and hit totals for the in-process result/plan cache. Use for "
            "diagnostics. Do not use to read a plan (plan_cache_get) or memory (memory_read). "
            "Read-only, idempotent, no parameters. Auth: tool policy gate."
        ),
        annotations=tool_hints("Cache statistics", **_RO),
    )
    async def cache_stats() -> dict[str, Any]:
        ctx, _ = _gated("cache_stats", {})
        return ctx.cache.stats()

    @server.tool(
        name="audit_recent",
        title="List recent audit events",
        description=(
            "Return the newest Decision-System-of-Record audit events (tool calls, policy "
            "allow/deny, risk tier, outcome), newest first. Use to inspect what the kernel just "
            "decided. Do not use for attestation evidence (attestation_recent) or cache metrics "
            "(cache_stats). Read-only. limit caps the list (default 20). Auth: tool policy gate."
        ),
        annotations=tool_hints("List recent audit events", **_RO),
    )
    async def audit_recent(
        limit: Annotated[int, Field(description="Maximum events to return, newest first. Default 20.")] = 20,
    ) -> dict[str, Any]:
        ctx, _ = _gated("audit_recent", {})
        events = ctx.audit.recent(limit=limit)
        return {
            "count": len(events),
            "events": [{"id": e.id, "ts": e.timestamp, "type": e.event_type, "tool": e.tool_name,
                        "decision": e.decision, "risk": e.risk_tier, "outcome": e.outcome} for e in events],
            "stats": ctx.audit.stats(),
        }

    @server.tool(
        name="attestation_recent",
        title="List recent attestation claims",
        description=(
            "Return recent attestation claims issued by this kernel (TRACE-style provenance: tool, "
            "allow/deny, risk tier, evidence mode). Use to verify a prior sandbox/TEE decision. "
            "Do not use for the policy/audit trail — that is audit_recent. This tool does not issue "
            "new claims. Read-only. limit is max claims, newest first (default 10). Auth: gate."
        ),
        annotations=tool_hints("List recent attestation claims", **_RO),
    )
    async def attestation_recent(
        limit: Annotated[int, Field(description="Maximum attestation claims to return, newest first. Default 10.")] = 10,
    ) -> dict[str, Any]:
        ctx, _ = _gated("attestation_recent", {})
        return {"count": len(ctx.attestation.recent(limit)), "claims": ctx.attestation.recent(limit),
                "stats": ctx.attestation.stats()}
