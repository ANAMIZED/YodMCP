"""Policy engine for YodMCP — least-privilege, risk-tiered gates.

Prototype. Production uses Cedar/OPA-style policy-as-code inside TEE
(cMCP pattern) with signed TRACE Claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RiskTier(str, Enum):
    READ = "read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"
    NETWORK = "network"
    CODE_EXEC = "code_exec"
    HIGH_PRIVILEGE = "high_privilege"


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    risk_tier: RiskTier
    requires_hitl: bool = False


class PolicyEngine:
    """Simple rule-based policy for prototype.

    Production: replace with verified policy bundle + hardware attestation.
    """

    def __init__(self) -> None:
        self._tool_risk: dict[str, RiskTier] = {
            "memory_write": RiskTier.WRITE,
            "memory_read": RiskTier.READ,
            "memory_consolidate": RiskTier.WRITE,
            "memory_stats": RiskTier.READ,
            "discover_capabilities": RiskTier.READ,
            "echo": RiskTier.READ,
            "audit_recent": RiskTier.READ,
            "cache_stats": RiskTier.READ,
            "tasks_create": RiskTier.WRITE,
            "tasks_get": RiskTier.READ,
            "tasks_cancel": RiskTier.WRITE,
            "tasks_stats": RiskTier.READ,
            "skills_list": RiskTier.READ,
            "a2a_card": RiskTier.READ,
            "plan_cache_get": RiskTier.READ,
            "plan_cache_put": RiskTier.WRITE,
            "attestation_recent": RiskTier.READ,
            "sandbox_exec": RiskTier.CODE_EXEC,
            "web_search": RiskTier.NETWORK,
            "delegate_task": RiskTier.HIGH_PRIVILEGE,
        }
        self._blocked: set[str] = set()

    def evaluate_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> PolicyDecision:
        if tool_name in self._blocked:
            return PolicyDecision(
                allowed=False,
                reason=f"Tool {tool_name} is blocked by policy",
                risk_tier=RiskTier.HIGH_PRIVILEGE,
                requires_hitl=True,
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
