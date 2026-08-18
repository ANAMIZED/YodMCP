"""v0.3 tests: durable SQLite memory, simulated TEE, fuller A2A HTTP."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from yodmcp.core.substrate import init_substrate
from yodmcp.security.attestation import AttestationService, build_tee_provider
from yodmcp.memory.durable import DurableMultiGraphMemory, create_memory
from yodmcp.a2a.server import create_a2a_app


@pytest.fixture
def tmp_db(tmp_path: Path) -> str:
    return str(tmp_path / "test_memory.db")


@pytest.mark.asyncio
async def test_durable_write_read_persist(tmp_db: str):
    mem = DurableMultiGraphMemory(db_path=tmp_db)
    id1 = await mem.write("durable fact about YodMCP", importance=0.9, entities=["YodMCP"])
    id2 = await mem.write("follow-up", importance=0.6, causal_parent=id1)
    items = await mem.read(query="YodMCP", limit=5)
    assert len(items) >= 1
    assert items[0]["score"] > 0
    stats = await mem.stats()
    assert stats["backend"] == "sqlite"
    assert stats["nodes"] >= 2
    await mem.close()

    mem2 = DurableMultiGraphMemory(db_path=tmp_db)
    items2 = await mem2.read(query="durable", limit=5)
    assert len(items2) >= 1
    stats2 = await mem2.stats()
    assert stats2["nodes"] >= 2
    await mem2.close()


@pytest.mark.asyncio
async def test_durable_consolidate(tmp_db: str):
    mem = DurableMultiGraphMemory(db_path=tmp_db)
    await mem.write("critical knowledge", importance=0.95)
    promoted = await mem.consolidate()
    assert promoted >= 1
    stats = await mem.stats()
    assert stats["by_level"]["semantic"] >= 1
    await mem.close()


@pytest.mark.asyncio
async def test_create_memory_factory(tmp_db: str):
    m = create_memory("memory")
    assert m.__class__.__name__ == "MultiGraphMemory"
    d = create_memory("sqlite", db_path=tmp_db)
    assert isinstance(d, DurableMultiGraphMemory)
    await d.close()


def test_software_attestation():
    svc = AttestationService(mode="software")
    claim = svc.issue("sandbox_exec", "allowed", "code_exec", {"cmd": "ls"})
    assert claim.mode == "software"
    assert svc.verify(claim) is True
    claim.tool_name = "tampered"
    assert svc.verify(claim) is False


def test_simulated_tee_attestation():
    svc = AttestationService(mode="simulated_tee")
    claim = svc.issue("sandbox_exec", "allowed under audit", "code_exec", {"x": 1})
    assert claim.mode == "simulated_tee"
    assert claim.measurement
    assert claim.public_key and "BEGIN PUBLIC KEY" in claim.public_key
    assert svc.verify(claim) is True
    claim.tool_name = "hacked"
    assert svc.verify(claim) is False
    stats = svc.stats()
    assert stats["mode"] == "simulated_tee"
    assert stats["has_public_key"] is True


def test_build_tee_provider_modes():
    assert build_tee_provider("software").mode == "software"
    assert build_tee_provider("simulated_tee").mode == "simulated_tee"
    assert build_tee_provider("nitro").mode == "tee_nitro"
    assert build_tee_provider("sgx").mode == "tee_sgx"


def test_a2a_http_card_and_message():
    init_substrate(console_tracing=False, memory_backend="memory", attest_mode="software")
    app = create_a2a_app(init_ctx=False)
    client = TestClient(app)

    r = client.get("/a2a/card")
    assert r.status_code == 200
    assert r.json()["name"] == "YodMCP"

    r2 = client.get("/a2a/.well-known/agent.json")
    assert r2.status_code == 200

    r3 = client.get("/a2a/health")
    assert r3.status_code == 200
    assert r3.json()["status"] == "ok"

    r4 = client.post("/a2a/message", json={"parts": [{"type": "text", "text": "hello A2A"}]})
    assert r4.status_code == 200
    assert r4.json()["role"] == "agent"

    r5 = client.post("/a2a/message", json={"parts": [{"type": "text", "text": "remember The cake is a lie"}]})
    assert r5.status_code == 200
    assert r5.json()["metadata"]["routed"] == "memory_write"

    r6 = client.post("/a2a/tasks", json={"description": "long job"})
    assert r6.status_code == 200
    tid = r6.json()["taskId"]
    r7 = client.get(f"/a2a/tasks/{tid}")
    assert r7.status_code == 200
    assert r7.json()["taskId"] == tid


@pytest.mark.asyncio
async def test_substrate_sqlite_and_tee(tmp_db: str):
    ctx = init_substrate(
        console_tracing=False,
        memory_backend="sqlite",
        memory_db_path=tmp_db,
        attest_mode="simulated_tee",
    )
    assert ctx.attestation.stats()["mode"] == "simulated_tee"
    await ctx.memory.write("substrate durable", importance=0.9)
    items = await ctx.memory.read(query="durable")
    assert len(items) >= 1
    claim = ctx.attestation.issue("memory_write", "ok", "write", {})
    assert ctx.attestation.verify(claim)
    await ctx.memory.close()
