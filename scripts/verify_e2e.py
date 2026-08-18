#!/usr/bin/env python3
"""Exhaustive end-to-end verification of YodMCP substrate."""

from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "src")

from yodmcp import __version__
from yodmcp.core.substrate import init_substrate
from yodmcp.core.context import get_context
from yodmcp.core.server import create_server
from yodmcp.a2a.surface import build_agent_card


async def main() -> None:
    print(f"=== YodMCP v{__version__} Exhaustive E2E Verification ===\n")
    init_substrate(console_tracing=False)
    server = create_server()
    ctx = get_context()

    tools_result = await server.list_tools()
    tools = getattr(tools_result, "tools", tools_result)
    names = sorted(t.name for t in tools)
    print(f"1. Tools ({len(names)}): {names}")
    required = {
        "memory_write",
        "memory_read",
        "memory_consolidate",
        "memory_stats",
        "tasks_create",
        "tasks_get",
        "tasks_cancel",
        "skills_list",
        "a2a_card",
        "plan_cache_get",
        "plan_cache_put",
        "attestation_recent",
        "audit_recent",
        "cache_stats",
        "echo",
        "discover_capabilities",
    }
    missing = required - set(names)
    assert not missing, f"Missing tools: {missing}"

    id1 = await ctx.memory.write("YodMCP multi-graph online", importance=0.95, entities=["YodMCP"])
    id2 = await ctx.memory.write("Causal follow-up", importance=0.8, causal_parent=id1)
    items = await ctx.memory.read(query="multi-graph", limit=3)
    print(f"2. Memory write/read → {len(items)} hits, nodes={(await ctx.memory.stats())['nodes']}")
    assert len(items) >= 1
    promoted = await ctx.memory.consolidate()
    print(f"3. Consolidate → promoted {promoted}")

    ctx.cache.put_plan("deploy yodmcp", {"steps": ["build", "test", "ship"]})
    plan, score = ctx.cache.get_plan("deploy the yodmcp service")
    print(f"4. Plan cache → found={plan is not None}, score={score:.3f}")
    assert plan is not None, f"plan cache miss score={score}"

    handle = ctx.tasks.to_handle(await ctx.tasks.create(tool_name="e2e"))
    assert handle["resultType"] == "task"
    await ctx.tasks.update(handle["taskId"], status="completed", progress=1.0, result={"ok": True})
    got = await ctx.tasks.get(handle["taskId"])
    print(f"5. Tasks → status={got.status.value}")

    skills = ctx.skills.list_skills()
    print(f"6. Skills → {len(skills)} registered, sample={skills[0].name}")
    assert ctx.skills.read_uri(skills[0].uri)

    card = build_agent_card()
    print(f"7. A2A card → name={card['name']}, skills={len(card['skills'])}")

    claim = ctx.attestation.issue("sandbox_exec", "allowed", "code_exec", {"x": 1})
    assert ctx.attestation.verify(claim)
    print(f"8. Attestation → claim verified, total={ctx.attestation.stats()['claims_issued']}")

    ctx.audit.record("e2e", tool_name="verify", decision="pass", outcome="success")
    print(f"9. Audit → events={ctx.audit.stats()['total_events']}")

    print(f"\n✅ ALL E2E CHECKS PASSED — YodMCP v{__version__} substrate is operational.")


if __name__ == "__main__":
    asyncio.run(main())
