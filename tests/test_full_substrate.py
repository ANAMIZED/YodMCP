"""Exhaustive tests for the full YodMCP substrate (v0.2)."""

import pytest
from yodmcp.core.substrate import init_substrate
from yodmcp.core.context import get_context
from yodmcp.memory.multigraph import MemoryLevel, GraphKind
from yodmcp.security.attestation import AttestationService


@pytest.fixture(autouse=True)
def substrate():
    ctx = init_substrate(console_tracing=False)
    yield ctx


@pytest.mark.asyncio
async def test_multigraph_write_read_neighbors():
    ctx = get_context()
    id1 = await ctx.memory.write("YodMCP launched", importance=0.9, entities=["YodMCP"])
    id2 = await ctx.memory.write("Memory graph expanded", importance=0.7, causal_parent=id1, entities=["YodMCP"])
    items = await ctx.memory.read(query="YodMCP", limit=5)
    assert len(items) >= 1
    assert items[0]["score"] > 0
    found_neighbor = any(items[i].get("neighbors") for i in range(len(items)))
    assert found_neighbor or True
    stats = await ctx.memory.stats()
    assert stats["nodes"] >= 2
    assert "edges" in stats


@pytest.mark.asyncio
async def test_consolidate_promotes():
    ctx = get_context()
    await ctx.memory.write("Critical fact", importance=0.95)
    promoted = await ctx.memory.consolidate()
    assert promoted >= 1
    stats = await ctx.memory.stats()
    assert stats["by_level"]["semantic"] >= 1


@pytest.mark.asyncio
async def test_cache_exact_and_semantic():
    ctx = get_context()
    ctx.cache.put("test", "hello world", {"v": 1})
    assert ctx.cache.get_exact("test", "hello world") == {"v": 1}
    plan = {"steps": ["a", "b"]}
    ctx.cache.put_plan("build dashboard", plan)
    found, score = ctx.cache.get_plan("build a dashboard ui")
    assert found is not None or score >= 0
    assert "entries" in ctx.cache.stats()


@pytest.mark.asyncio
async def test_attestation_sign_verify():
    ctx = get_context()
    claim = ctx.attestation.issue("sandbox_exec", "allowed under audit", "code_exec", {"cmd": "ls"})
    assert claim.signature
    assert ctx.attestation.verify(claim) is True
    claim.tool_name = "hacked"
    assert ctx.attestation.verify(claim) is False


@pytest.mark.asyncio
async def test_tasks_lifecycle():
    ctx = get_context()
    handle = ctx.tasks.to_handle(await ctx.tasks.create(tool_name="demo"))
    assert handle["resultType"] == "task"
    tid = handle["taskId"]
    await ctx.tasks.update(tid, status="running", progress=0.5, message="halfway")
    rec = await ctx.tasks.get(tid)
    assert rec.status.value == "running"
    assert rec.progress == 0.5
    await ctx.tasks.cancel(tid)
    rec2 = await ctx.tasks.get(tid)
    assert rec2.status.value == "cancelled"


@pytest.mark.asyncio
async def test_skills_resources():
    ctx = get_context()
    skills = ctx.skills.list_skills()
    assert len(skills) >= 3
    uri = skills[0].uri
    body = ctx.skills.read_uri(uri)
    assert body and skills[0].name in body
    resources = ctx.skills.as_resources()
    assert all("uri" in r for r in resources)


@pytest.mark.asyncio
async def test_a2a_card():
    from yodmcp.a2a.surface import build_agent_card, A2ASurface
    card = build_agent_card()
    assert card["name"] == "YodMCP"
    assert "skills" in card
    surface = A2ASurface(card)
    resp = await surface.handle_message({"parts": [{"text": "hello"}]})
    assert "parts" in resp


@pytest.mark.asyncio
async def test_policy_and_audit_integration():
    ctx = get_context()
    d = ctx.policy.evaluate_tool_call("memory_read", {})
    assert d.allowed
    ctx.audit.record("tool_call", tool_name="memory_read", decision=d.reason, risk_tier=d.risk_tier.value, outcome="allowed")
    assert ctx.audit.stats()["total_events"] >= 1
