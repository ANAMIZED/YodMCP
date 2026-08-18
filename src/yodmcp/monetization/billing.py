"""Billing service — plan gates + live Stripe Checkout / Payment Links + entitlements."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from yodmcp.monetization.plans import get_plan
from yodmcp.monetization.metering import UsageMeter

if TYPE_CHECKING:
    from yodmcp.monetization.entitlements import EntitlementStore

# Live Stripe catalog (acct_1TO54GK7tbqokSzb — ANAMIZED)
STRIPE_CATALOG = {
    "pro": {
        "product_id": "prod_V62rWdSIkPN3wT",
        "price_id": "price_1U5qlsK7tbqokSzbzeaDQGof",
        "payment_link": "https://buy.stripe.com/bJe3cw0kCaLrbVz1AY43S09",
        "amount_usd": 49,
    },
    "enterprise": {
        "product_id": "prod_V62rRqLSH82qmd",
        "price_id": "price_1U5qluK7tbqokSzbtKbf923T",
        "payment_link": "https://buy.stripe.com/9B68wQ1oGcTz9NrfrO43S0a",
        "amount_usd": 499,
    },
}


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
        entitlements: "EntitlementStore | None" = None,
    ) -> None:
        self.tenant_id = tenant_id or os.environ.get("YODMCP_TENANT_ID", "default")
        self.plan = get_plan(plan_id)
        self.meter = meter or UsageMeter()
        self.entitlements = entitlements
        self.stripe_enabled = os.environ.get("YODMCP_STRIPE_ENABLED", "").lower() in ("1", "true", "yes")
        self.stripe_secret = os.environ.get("STRIPE_SECRET_KEY", "")

    async def refresh_plan_from_entitlement(self) -> str:
        """Load durable entitlement for tenant if present; falls back to env plan."""
        if self.entitlements is None:
            return self.plan.id
        plan_id = await self.entitlements.get_plan(self.tenant_id)
        if plan_id:
            self.plan = get_plan(plan_id)
        return self.plan.id

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
                f"Plan '{self.plan.id}' daily limit reached for {metric} ({used}/{limit}). "
                f"Upgrade: see /api/billing/plans",
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

        out = []
        for p in PLANS.values():
            d = p.to_dict()
            cat = STRIPE_CATALOG.get(p.id)
            if cat:
                d["stripe_price_id"] = cat["price_id"]
                d["stripe_product_id"] = cat["product_id"]
                d["payment_link"] = cat["payment_link"]
            out.append(d)
        return out

    def status(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "plan": self.plan.to_dict(),
            "usage": self.meter.summary(self.tenant_id),
            "stripe_enabled": self.stripe_enabled or bool(self.stripe_secret),
            "catalog": STRIPE_CATALOG,
            "entitlements_enabled": self.entitlements is not None,
        }

    def create_checkout_stub(
        self,
        plan_id: str,
        success_url: str,
        cancel_url: str,
    ) -> dict[str, Any]:
        """Live Checkout Session when STRIPE_SECRET_KEY is set; else Payment Link."""
        plan = get_plan(plan_id)
        if plan.price_usd_month == 0:
            return {"error": "free plan does not require checkout", "plan_id": plan.id}

        cat = STRIPE_CATALOG.get(plan.id)
        if not cat:
            return {"error": f"no Stripe catalog entry for plan {plan.id}"}

        secret = self.stripe_secret or os.environ.get("STRIPE_SECRET_KEY", "")
        if secret:
            try:
                import stripe

                stripe.api_key = secret
                session = stripe.checkout.Session.create(
                    mode="subscription",
                    line_items=[{"price": cat["price_id"], "quantity": 1}],
                    success_url=success_url
                    if "{CHECKOUT_SESSION_ID}" in success_url
                    else success_url.rstrip("/") + "?session_id={CHECKOUT_SESSION_ID}",
                    cancel_url=cancel_url,
                    metadata={
                        "yodmcp_plan": plan.id,
                        "tenant_id": self.tenant_id,
                        "github_repo": "YodMCP",
                    },
                    subscription_data={
                        "metadata": {
                            "yodmcp_plan": plan.id,
                            "tenant_id": self.tenant_id,
                        }
                    },
                    allow_promotion_codes=True,
                )
                return {
                    "status": "live",
                    "checkout_session_id": session.id,
                    "url": session.url,
                    "plan_id": plan.id,
                    "price_id": cat["price_id"],
                    "amount_usd": cat["amount_usd"],
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "fallback_payment_link": cat["payment_link"],
                    "plan_id": plan.id,
                }

        return {
            "status": "payment_link",
            "url": cat["payment_link"],
            "plan_id": plan.id,
            "price_id": cat["price_id"],
            "product_id": cat["product_id"],
            "amount_usd": cat["amount_usd"],
            "message": "Open url to subscribe. For dynamic Checkout Sessions, set STRIPE_SECRET_KEY.",
        }

    async def handle_stripe_webhook(self, payload: bytes, sig_header: str | None) -> dict[str, Any]:
        """Verify (if secret present) and activate entitlement on checkout.session.completed."""
        secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
        event: dict[str, Any]

        if secret and sig_header:
            try:
                import stripe

                event = stripe.Webhook.construct_event(payload, sig_header, secret)
            except Exception as e:
                return {"ok": False, "error": f"signature verification failed: {e}"}
        else:
            # Dev / unsigned mode — parse JSON only
            import json

            try:
                event = json.loads(payload)
            except Exception as e:
                return {"ok": False, "error": f"invalid json: {e}"}

        etype = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)
        data = event.get("data", {}).get("object", {}) if isinstance(event, dict) else {}

        if etype in ("checkout.session.completed", "customer.subscription.created", "customer.subscription.updated"):
            meta = data.get("metadata") or {}
            plan_id = meta.get("yodmcp_plan") or "pro"
            tenant_id = meta.get("tenant_id") or self.tenant_id
            cust = data.get("customer")
            sub = data.get("subscription") or data.get("id")
            if self.entitlements is not None:
                await self.entitlements.activate(
                    tenant_id=tenant_id,
                    plan_id=plan_id,
                    source="stripe",
                    stripe_customer_id=str(cust) if cust else None,
                    stripe_subscription_id=str(sub) if sub else None,
                )
                if tenant_id == self.tenant_id:
                    self.plan = get_plan(plan_id)
                return {"ok": True, "activated": plan_id, "tenant_id": tenant_id}
            return {"ok": True, "note": "no entitlement store; plan not persisted", "plan_id": plan_id}

        if etype in ("customer.subscription.deleted", "checkout.session.expired"):
            meta = data.get("metadata") or {}
            tenant_id = meta.get("tenant_id") or self.tenant_id
            if self.entitlements is not None:
                await self.entitlements.deactivate(tenant_id)
            return {"ok": True, "deactivated": tenant_id}

        return {"ok": True, "ignored": etype}
