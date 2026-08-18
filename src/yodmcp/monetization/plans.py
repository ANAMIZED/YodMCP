"""Subscription plans for YodMCP Server OS."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    price_usd_month: int
    tool_calls_per_day: int
    memory_writes_per_day: int
    tasks_per_day: int
    durable_memory: bool
    tee_attestation: bool
    a2a_enabled: bool
    skills_marketplace: bool
    stripe_price_id: str | None = None
    features: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "price_usd_month": self.price_usd_month,
            "tool_calls_per_day": self.tool_calls_per_day,
            "memory_writes_per_day": self.memory_writes_per_day,
            "tasks_per_day": self.tasks_per_day,
            "durable_memory": self.durable_memory,
            "tee_attestation": self.tee_attestation,
            "a2a_enabled": self.a2a_enabled,
            "skills_marketplace": self.skills_marketplace,
            "stripe_price_id": self.stripe_price_id,
            "features": list(self.features),
        }


PLANS: dict[str, Plan] = {
    "free": Plan(
        id="free",
        name="Free",
        price_usd_month=0,
        tool_calls_per_day=500,
        memory_writes_per_day=100,
        tasks_per_day=20,
        durable_memory=False,
        tee_attestation=False,
        a2a_enabled=True,
        skills_marketplace=False,
        features=("MCP stdio/HTTP", "In-memory graphs", "3 built-in skills", "Community support"),
    ),
    "pro": Plan(
        id="pro",
        name="Pro",
        price_usd_month=49,
        tool_calls_per_day=50_000,
        memory_writes_per_day=10_000,
        tasks_per_day=2_000,
        durable_memory=True,
        tee_attestation=True,
        a2a_enabled=True,
        skills_marketplace=True,
        features=(
            "Everything in Free",
            "Durable SQLite memory",
            "Simulated TEE attestation",
            "Skills marketplace",
            "Priority support",
        ),
    ),
    "enterprise": Plan(
        id="enterprise",
        name="Enterprise",
        price_usd_month=499,
        tool_calls_per_day=-1,
        memory_writes_per_day=-1,
        tasks_per_day=-1,
        durable_memory=True,
        tee_attestation=True,
        a2a_enabled=True,
        skills_marketplace=True,
        features=(
            "Everything in Pro",
            "Unlimited usage",
            "Nitro/SGX TEE hooks",
            "SSO / multi-tenant",
            "SLA + dedicated support",
            "Custom skill packs",
        ),
    ),
}


def get_plan(plan_id: str | None = None) -> Plan:
    import os
    pid = plan_id or os.environ.get("YODMCP_PLAN", "free")
    return PLANS.get(pid, PLANS["free"])
