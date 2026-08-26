"""Audit tool definitions for Glama TDQS + new CRUD tools."""

from __future__ import annotations

import pytest

from yodmcp.core.server import create_server
from yodmcp.core.substrate import init_substrate
from yodmcp.core.context import get_context

REQUIRED = {
    "memory_write",
    "memory_read",
    "memory_delete",
    "memory_consolidate",
    "memory_stats",
    "tasks_create",
    "tasks_get",
    "tasks_list",
    "tasks_update",
    "tasks_cancel",
    "tasks_stats",
    "skills_list",
    "a2a_card",
    "plan_cache_get",
    "plan_cache_put",
    "plan_cache_delete",
    "cache_stats",
    "attestation_recent",
    "audit_recent",
    "echo",
    "discover_capabilities",
}


def _tools(server):
    result = server.list_tools()
    if hasattr(result, "__await__"):
        raise RuntimeError("list_tools is async in this SDK — use the async helper")
    return getattr(result, "tools", result)


async def _list_tools(server):
    result = server.list_tools()
    if hasattr(result, "__await__"):
        result = await result
    return getattr(result, "tools", result)


@pytest.fixture
def server():
    init_substrate(console_tracing=False)
    return create_server()


@pytest.mark.asyncio
async def test_all_required_tools_registered(server):
    tools = await _list_tools(server)
    names = {t.name for t in tools}
    missing = REQUIRED - names
    assert not missing, f"missing tools: {missing}"


@pytest.mark.asyncio
async def test_descriptions_are_agent_briefs(server):
    tools = await _list_tools(server)
    short = []
    tautology = []
    for t in tools:
        desc = (getattr(t, "description", None) or "").strip()
        if len(desc) < 80:
            short.append((t.name, len(desc), desc))
        compact = desc.lower().replace("_", " ").replace(".", "")
        if compact == t.name.replace("_", " ") or compact == t.name:
            tautology.append(t.name)
    assert not short, f"descriptions too short: {short}"
    assert not tautology, f"tautological descriptions: {tautology}"


@pytest.mark.asyncio
async def test_annotations_present(server):
    tools = await _list_tools(server)
    missing = []
    for t in tools:
        ann = getattr(t, "annotations", None)
        if ann is None:
            missing.append(t.name)
            continue
        read_only = getattr(ann, "readOnlyHint", None)
        if read_only is None:
            read_only = getattr(ann, "read_only_hint", None)
        if isinstance(ann, dict):
            read_only = ann.get("readOnlyHint", ann.get("read_only_hint"))
        if read_only is None:
            missing.append(t.name)
    assert not missing, f"tools missing readOnlyHint: {missing}"


@pytest.mark.asyncio
async def test_parameter_schema_descriptions(server):
    tools = await _list_tools(server)
    bare = []
    for t in tools:
        schema = getattr(t, "inputSchema", None) or getattr(t, "input_schema", None) or {}
        if hasattr(schema, "model_dump"):
            schema = schema.model_dump()
        props = schema.get("properties") or {}
        for pname, spec in props.items():
            if not isinstance(spec, dict):
                continue
            if not spec.get("description"):
                bare.append(f"{t.name}.{pname}")
    assert not bare, f"parameters missing descriptions: {bare}"


@pytest.mark.asyncio
async def test_memory_delete_and_plan_cache_delete():
    init_substrate(console_tracing=False)
    ctx = get_context()
    nid = await ctx.memory.write("forget me", importance=0.4)
    assert await ctx.memory.delete(nid) is True
    assert await ctx.memory.delete(nid) is False
    leftover = await ctx.memory.read(item_id=nid)
    assert leftover == []
    ctx.cache.put_plan("ship kernel", {"steps": ["build"]})
    assert ctx.cache.delete_plan("ship kernel") is True
    assert ctx.cache.delete_plan("ship kernel") is False


@pytest.mark.asyncio
async def test_tasks_list_and_update():
    init_substrate(console_tracing=False)
    ctx = get_context()
    rec = await ctx.tasks.create(tool_name="tdqs")
    listed = await ctx.tasks.list(limit=10)
    assert any(r.task_id == rec.task_id for r in listed)
    updated = await ctx.tasks.update(rec.task_id, status="running", progress=0.2, message="go")
    assert updated is not None
    assert updated.status.value == "running"
    assert updated.progress == 0.2
