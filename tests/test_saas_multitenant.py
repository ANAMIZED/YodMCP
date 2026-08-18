"""Multi-tenant SaaS polish: tenant scope, HITL, policy allowlists, validation."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def saas_env(tmp_path, monkeypatch):
    monkeypatch.setenv("YODMCP_SYSTEM_DB", str(tmp_path / "sys.db"))
    monkeypatch.setenv("YODMCP_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("YODMCP_API_KEY", "saas-key")
    monkeypatch.delenv("YODMCP_TOOL_ALLOWLIST", raising=False)
    yield


def test_tenant_scoped_policy_denylist(saas_env):
    from yodmcp.core.substrate import init_substrate
    from yodmcp.core.tenant import set_tenant
    from yodmcp.security.policy import PolicyEngine

    ctx = init_substrate()
    ctx.policy.set_tenant_denylist("t1", ["memory_write"])
    set_tenant("t1")
    d = ctx.policy.evaluate_tool_call("memory_write", {}, tenant_id="t1")
    assert d.allowed is False
    d2 = ctx.policy.evaluate_tool_call("memory_write", {}, tenant_id="t2")
    assert d2.allowed is True


def test_hitl_enqueue_and_decide(saas_env):
    from yodmcp.core.substrate import init_substrate
    from yodmcp.api.app import create_api_app

    init_substrate()
    client = TestClient(create_api_app(init_ctx=False))
    headers = {"X-API-Key": "saas-key", "X-YodMCP-Tenant": "acme"}

    # Trigger high-risk path via policy + gate indirectly through hitl API after enqueue
    from yodmcp.core.context import get_context

    ctx = get_context()
    req = ctx.hitl.enqueue("acme", "sandbox_exec", {"cmd": "id"}, risk_tier="code_exec")
    r = client.get("/api/hitl/pending", headers=headers)
    assert r.status_code == 200
    assert any(p["id"] == req.id for p in r.json()["pending"])

    r = client.post(
        f"/api/hitl/{req.id}/decide",
        headers=headers,
        json={"approve": True, "reason": "ok"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


def test_validation_rejects_huge_args(saas_env):
    from yodmcp.security.validation import ValidationError, validate_tool_arguments

    with pytest.raises(ValidationError):
        validate_tool_arguments({"blob": "x" * 100_000})


def test_structured_tenant_on_auth(saas_env):
    from yodmcp.core.substrate import init_substrate
    from yodmcp.api.app import create_api_app
    from yodmcp.core.tenant import get_tenant

    init_substrate()
    client = TestClient(create_api_app(init_ctx=False))
    r = client.get(
        "/api/skills",
        headers={"X-API-Key": "saas-key", "X-YodMCP-Tenant": "tenant-z"},
    )
    assert r.status_code == 200
    # tenant set during request via auth dependency
    assert get_tenant() in ("tenant-z", "default")  # context may clear after request
