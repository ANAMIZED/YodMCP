"""Policy engine with tenant-scoped allowlists and HITL flags.

Prototype ruleset; production path is policy-as-code (OPA/Cedar) bundles.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskTier(str, Enum):
    READ = "read"
    WRITE = "write"
    NETWORK = "network"
    CODE_EXEC = "code_exec"
    DESTRUCTIVE = "destructive"
    HIGH_PRIVILEGE = "high_privilege"


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    risk_tier: RiskTier
    requires_hitl: bool = False


class PolicyEngine:
    """Rule-based policy with optional per-tenant allow/deny lists.

    Env:
      YODMCP_TENANT_ALLOWLIST — comma tool names allowed for *all* tenants when set
      Per-tenant: set via set_tenant_allowlist / block_tool at runtime
    """

    def __init__(self) -> None:
        self._tool_risk: dict[str, RiskTier] = {
            "memory_write": RiskTier.WRITE,
            "memory_read": RiskTier.READ,
            "memory_delete": RiskTier.DESTRUCTIVE,
            "memory_consolidate": RiskTier.WRITE,
            "memory_stats": RiskTier.READ,
            "discover_capabilities": RiskTier.READ,
            "echo": RiskTier.READ,
            "audit_recent": RiskTier.READ,
            "cache_stats": RiskTier.READ,
            "tasks_create": RiskTier.WRITE,
            "tasks_get": RiskTier.READ,
            "tasks_list": RiskTier.READ,
            "tasks_update": RiskTier.WRITE,
            "tasks_cancel": RiskTier.DESTRUCTIVE,
            "tasks_stats": RiskTier.READ,
            "skills_list": RiskTier.READ,
            "a2a_card": RiskTier.READ,
            "plan_cache_get": RiskTier.READ,
            "plan_cache_put": RiskTier.WRITE,
            "plan_cache_delete": RiskTier.DESTRUCTIVE,
            "attestation_recent": RiskTier.READ,
            "sandbox_exec": RiskTier.CODE_EXEC,
            "web_search": RiskTier.NETWORK,
            "delegate_task": RiskTier.HIGH_PRIVILEGE,
        }
        self._blocked: set[str] = set()
        # tenant_id -> allowed tool names (empty = use default rules)
        self._tenant_allow: dict[str, set[str]] = {}
        self._tenant_deny: dict[str, set[str]] = {}
        global_allow = os.environ.get("YODMCP_TOOL_ALLOWLIST", "")
        if global_allow.strip():
            self._global_allow = {t.strip() for t in global_allow.split(",") if t.strip()}
        else:
            self._global_allow = set()

    def set_tenant_allowlist(self, tenant_id: str, tools: list[str]) -> None:
        self._tenant_allow[tenant_id] = set(tools)

    def set_tenant_denylist(self, tenant_id: str, tools: list[str]) -> None:
        self._tenant_deny[tenant_id] = set(tools)

    def evaluate_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        agent_id: str | None = None,
        session_id: str | None = None,
        tenant_id: str | None = None,
    ) -> PolicyDecision:
        from yodmcp.core.tenant import get_tenant

        tid = tenant_id or get_tenant()

        if tool_name in self._blocked:
            return PolicyDecision(
                allowed=False,
                reason=f"Tool {tool_name} is blocked by policy",
                risk_tier=RiskTier.HIGH_PRIVILEGE,
                requires_hitl=True,
            )

        deny = self._tenant_deny.get(tid) or set()
        if tool_name in deny:
            return PolicyDecision(
                allowed=False,
                reason=f"Tool {tool_name} denied for tenant {tid}",
                risk_tier=RiskTier.HIGH_PRIVILEGE,
                requires_hitl=False,
            )

        allow = self._tenant_allow.get(tid)
        if allow is not None and tool_name not in allow:
            return PolicyDecision(
                allowed=False,
                reason=f"Tool {tool_name} not on allowlist for tenant {tid}",
                risk_tier=RiskTier.HIGH_PRIVILEGE,
                requires_hitl=False,
            )

        if self._global_allow and tool_name not in self._global_allow:
            return PolicyDecision(
                allowed=False,
                reason=f"Tool {tool_name} not on global allowlist",
                risk_tier=RiskTier.HIGH_PRIVILEGE,
                requires_hitl=False,
            )

        risk = self._tool_risk.get(tool_name, RiskTier.HIGH_PRIVILEGE)

        if risk in (RiskTier.DESTRUCTIVE, RiskTier.HIGH_PRIVILEGE, RiskTier.CODE_EXEC):
            return PolicyDecision(
                allowed=True,
                reason=f"High-risk tool {tool_name} permitted under audit",
                risk_tier=risk,
                requires_hitl=True,
            )

        return PolicyDecision(
            allowed=True,
            reason="Policy allow",
            risk_tier=risk,
            requires_hitl=False,
        )

    def block_tool(self, tool_name: str) -> None:
        self._blocked.add(tool_name)

    def unblock_tool(self, tool_name: str) -> None:
        self._blocked.discard(tool_name)
