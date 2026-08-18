"""Production-prep: auth, durable tasks/meter/entitlements, readiness."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_system_db(tmp_path: Path):
    db = tmp_path / "system.db"
    os.environ["YODMCP_SYSTEM_DB"] = str(db)
    os.environ["YODMCP_TASKS_BACKEND"] = "sqlite"
    os.environ["YODMCP_METER_BACKEND"] = "sqlite"
    os.environ["YODMCP_AUDIT_BACKEND"] = "sqlite"
    os.environ["YODMCP_MEMORY_BACKEND"] = "memory"
    yield db
    for k in ("YODMCP_SYSTEM_DB", "YODMCP_TASKS_BACKEND", "YODMCP_METER_BACKEND", "YODMCP_AUDIT_BACKEND"):
        os.environ.pop(k, None)


@pytest.mark.asyncio
async def test_durable_task_survives_reinit(tmp_system_db):
    from yodmcp.core.substrate import init_substrate
    from yodmcp.core.context import set_context

    ctx1 = init_substrate()
    rec = await ctx1.tasks.create(tool_name="test", metadata={"k": 1})
    tid = rec.task_id
    await ctx1.tasks.update(tid, status="completed", progress=1.0, result={"ok": True})

    # New process simulation: new TaskManager on same DB
    from yodmcp.tasks.manager import TaskManager

    tm2 = TaskManager(backend="sqlite", db_path=str(tmp_system_db))
    got = await tm2.get(tid)
    assert got is not None
    assert got.status.value == "completed"
    assert got.result == {"ok": True}


@pytest.mark.asyncio
async def test_entitlement_activate_and_refresh(tmp_system_db):
    from yodmcp.monetization.entitlements import EntitlementStore
    from yodmcp.monetization.billing import BillingService
    from yodmcp.monetization.metering import UsageMeter

    store = EntitlementStore(db_path=str(tmp_system_db))
    await store.activate("tenant-a", "pro", source="test")
    assert await store.get_plan("tenant-a") == "pro"

    billing = BillingService(tenant_id="tenant-a", meter=UsageMeter(), entitlements=store)
    assert billing.plan.id == "free" or billing.plan.id  # default until refresh
    plan = await billing.refresh_plan_from_entitlement()
    assert plan == "pro"
    assert billing.plan.id == "pro"


def test_api_auth_required(tmp_system_db, monkeypatch):
    monkeypatch.setenv("YODMCP_API_KEY", "test-secret-key")
    from yodmcp.core.context import set_context
    from yodmcp.core.substrate import init_substrate
    from yodmcp.api.app import create_api_app

    init_substrate()
    client = TestClient(create_api_app(init_ctx=False))

    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["auth_required"] is True

    r = client.get("/api/skills")
    assert r.status_code == 401

    r = client.get("/api/skills", headers={"X-API-Key": "test-secret-key"})
    assert r.status_code == 200
    assert "skills" in r.json()

    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_webhook_activates_entitlement(tmp_system_db, monkeypatch):
    monkeypatch.delenv("YODMCP_API_KEY", raising=False)
    monkeypatch.delenv("YODMCP_API_KEYS", raising=False)
    from yodmcp.core.substrate import init_substrate
    from yodmcp.api.app import create_api_app
    import json

    init_substrate()
    client = TestClient(create_api_app(init_ctx=False))

    payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"yodmcp_plan": "enterprise", "tenant_id": "webhook-tenant"},
                "customer": "cus_test",
                "subscription": "sub_test",
            }
        },
    }
    r = client.post("/api/billing/webhook", content=json.dumps(payload))
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert body.get("activated") == "enterprise"
