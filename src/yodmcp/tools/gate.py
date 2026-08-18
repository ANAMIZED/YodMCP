"""Policy/attestation/audit/tracing gate for tool calls."""

from __future__ import annotations

from typing import Any

from yodmcp.core.context import get_context
from yodmcp.observability.otel import start_tool_span, end_span


def _gated(tool_name: str, arguments: dict[str, Any] | None = None):
    ctx = get_context()
    span = start_tool_span(tool_name, {"args_preview": str(arguments)[:120] if arguments else ""})
    decision = ctx.policy.evaluate_tool_call(tool_name, arguments or {})
    claim = None
    if decision.requires_hitl or decision.risk_tier.value in ("code_exec", "high_privilege", "destructive"):
        claim = ctx.attestation.issue(
            tool_name=tool_name,
            policy_decision=decision.reason,
            risk_tier=decision.risk_tier.value,
            arguments=arguments,
        )
    ctx.audit.record(
        "tool_call",
        tool_name=tool_name,
        arguments=arguments,
        decision=decision.reason,
        risk_tier=decision.risk_tier.value,
        outcome="allowed" if decision.allowed else "denied",
        metadata={"claim_id": claim.claim_id if claim else None},
    )
    if not decision.allowed:
        end_span(span, ok=False, error=decision.reason)
    else:
        end_span(span, ok=True)
    return ctx, decision
