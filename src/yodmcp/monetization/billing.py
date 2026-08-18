"""Billing service — plan gates + Stripe-ready checkout hooks."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from yodmcp.monetization.plans import Plan, get_plan
from yodmcp.monetization.metering import UsageMeter


@dataclass
class QuotaDecision:
    allowed: bool
    reason: str
    plan_id: str
    metric: str
    used: int
    limit: int


class BillingService:
    def __init__(
        self,
        plan_id: str | None = None,
        tenant_id: str = "default",
        meter: UsageMeter | None = None,
    ) -> None:
        self.tenant_id = tenant_id or os.environ.get("YODMCP_TENANT_ID", "default")
        self.plan = get_plan(plan_id)
        self.meter = meter or UsageMeter()
        self.stripe_enabled = os.environ.get("YODMCP_STRIPE_ENABLED", "").lower() in ("1", "true", "yes")

    def check_quota(self, metric: str) -> QuotaDecision:
        limit_map = {
            "tool_call": self.plan.tool_calls_per_day,
            "memory_write": self.plan.memory_writes_per_day,
            "task_create": self.plan.tasks_per_day,
        }
        limit = limit_map.get(metric, -1)
        used = self.meter.usage_today(self.tenant_id, metric)
        if limit < 0:
            return QuotaDecision(True, "unlimited", self.plan.id, metric, used, limit)
        if used >= limit:
            return QuotaDecision(
                False,
                f"Plan '{self.plan.id}' daily limit reached for {metric} ({used}/{limit}). Upgrade at /api/billing/plans.",
                self.plan.id,
                metric,
                used,
                limit,
            )
        return QuotaDecision(True, "within quota", self.plan.id, metric, used, limit)

    def record_and_check(self, metric: str, metadata: dict[str, Any] | None = None) -> QuotaDecision:
        decision = self.check_quota(metric)
        if decision.allowed:
            self.meter.record(self.tenant_id, metric, metadata=metadata)
            used = self.meter.usage_today(self.tenant_id, metric)
            return QuotaDecision(True, "within quota", self.plan.id, metric, used, decision.limit)
        return decision

    def feature_allowed(self, feature: str) -> bool:
        mapping = {
            "durable_memory": self.plan.durable_memory,
            "tee_attestation": self.plan.tee_attestation,
            "a2a": self.plan.a2a_enabled,
            "skills_marketplace": self.plan.skills_marketplace,
        }
        return mapping.get(feature, True)

    def plans_catalog(self) -> list[dict[str, Any]]:
        from yodmcp.monetization.plans import PLANS
        return [p.to_dict() for p in PLANS.values()]

    def status(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "plan": self.plan.to_dict(),
            "usage": self.meter.summary(self.tenant_id),
            "stripe_enabled": self.stripe_enabled,
        }

    def create_checkout_stub(self, plan_id: str, success_url: str, cancel_url: str) -> dict[str, Any]:
        plan = get_plan(plan_id)
        if plan.price_usd_month == 0:
            return {"error": "free plan does not require checkout", "plan_id": plan.id}
        payload = {
            "mode": "subscription",
            "line_items": [{"price": plan.stripe_price_id or f"price_stub_{plan.id}", "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {"yodmcp_plan": plan.id, "tenant_id": self.tenant_id},
            "amount_usd": plan.price_usd_month,
        }
        if not self.stripe_enabled:
            return {
                "status": "stub",
                "message": "Stripe not enabled. Set YODMCP_STRIPE_ENABLED=true and STRIPE_SECRET_KEY.",
                "checkout": payload,
            }
        return {
            "status": "ready",
            "message": "Pass this payload to Stripe Checkout Session create",
            "checkout": payload,
        }
