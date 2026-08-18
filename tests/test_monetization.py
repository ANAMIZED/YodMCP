"""Monetization: plans, metering, quotas, billing stubs."""

from __future__ import annotations

from yodmcp.core.substrate import init_substrate
from yodmcp.monetization.plans import get_plan, PLANS
from yodmcp.monetization.metering import UsageMeter
from yodmcp.monetization.billing import BillingService


def test_plans_catalog():
    assert set(PLANS) == {"free", "pro", "enterprise"}
    assert get_plan("free").price_usd_month == 0
    assert get_plan("pro").durable_memory is True
    assert get_plan("enterprise").tool_calls_per_day == -1


def test_meter_and_quota():
    meter = UsageMeter()
    bill = BillingService(plan_id="free", tenant_id="t1", meter=meter)
    for _ in range(5):
        d = bill.record_and_check("tool_call")
        assert d.allowed
    assert bill.meter.usage_today("t1", "tool_call") == 5


def test_quota_exhausted():
    meter = UsageMeter()
    bill = BillingService(plan_id="free", tenant_id="t2", meter=meter)
    meter._counts["t2"]["tool_call"][meter._day_key()] = 500
    d = bill.check_quota("tool_call")
    assert d.allowed is False


def test_checkout_stub():
    bill = BillingService(plan_id="free")
    out = bill.create_checkout_stub("pro", "http://ok", "http://cancel")
    assert out["status"] in ("stub", "ready")
    assert out["checkout"]["amount_usd"] == 49


def test_substrate_billing_attached():
    ctx = init_substrate(console_tracing=False)
    assert ctx.billing.plan.id in PLANS
    assert "usage" in ctx.billing.status()
