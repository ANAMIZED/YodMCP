"""Policy / attestation / audit / OTEL / billing gate for tool calls."""

from __future__ import annotations

from typing import Any

from yodmcp.core.context import get_context
from yodmcp.core.tenant import get_tenant
from yodmcp.observability.otel import start_tool_span, end_span
from yodmcp.security.validation import ValidationError, validate_tool_arguments


def _gated(tool_name: str, arguments: dict[str, Any] | None = None):
    ctx = get_context()
    tenant = get_tenant()
    span = start_tool_span(
        tool_name,
        {
            "args_preview": str(arguments)[:120] if arguments else "",
            "tenant_id": tenant,
        },
    )
    try:
        args = validate_tool_arguments(arguments)
    except ValidationError as e:
        from yodmcp.security.policy import PolicyDecision, RiskTier

        decision = PolicyDecision(
            allowed=False, reason=str(e), risk_tier=RiskTier.WRITE, requires_hitl=False
        )
        ctx.audit.record(
            "tool_call",
            tool_name=tool_name,
            arguments=arguments,
            decision=str(e),
            risk_tier="write",
            outcome="denied",
            metadata={"tenant_id": tenant, "validation": True},
        )
        end_span(span, ok=False, error=str(e))
        return ctx, decision

    decision = ctx.policy.evaluate_tool_call(tool_name, args, tenant_id=tenant)
    claim = None
    if decision.requires_hitl or decision.risk_tier.value in (
        "code_exec",
        "high_privilege",
        "destructive",
    ):
        claim = ctx.attestation.issue(
            tool_name=tool_name,
            policy_decision=decision.reason,
            risk_tier=decision.risk_tier.value,
            arguments=args,
        )
        # Enqueue HITL when high-risk and fail-closed mode may apply
        hitl = getattr(ctx, "hitl", None)
        if hitl is not None and decision.requires_hitl:
            req = hitl.enqueue(
                tenant_id=tenant,
                tool_name=tool_name,
                arguments=args,
                risk_tier=decision.risk_tier.value,
            )
            if hitl.fail_closed and decision.risk_tier.value in (
                "code_exec",
                "destructive",
                "high_privilege",
            ):
                # Soft fail-closed for prototype: still allow under audit unless env forces deny
                # Real production would park the call until approved
                decision = type(decision)(
                    allowed=decision.allowed,
                    reason=f"{decision.reason}; hitl_id={req.id}",
                    risk_tier=decision.risk_tier,
                    requires_hitl=True,
                )

    ctx.audit.record(
        "tool_call",
        tool_name=tool_name,
        arguments=args,
        decision=decision.reason,
        risk_tier=decision.risk_tier.value,
        outcome="allowed" if decision.allowed else "denied",
        metadata={
            "claim_id": claim.claim_id if claim else None,
            "tenant_id": tenant,
        },
    )
    if not decision.allowed:
        end_span(span, ok=False, error=decision.reason)
        return ctx, decision

    # Bind billing to request tenant
    ctx.billing.tenant_id = tenant
    quota = ctx.billing.record_and_check("tool_call", metadata={"tool": tool_name})
    if not quota.allowed:
        decision.allowed = False
        decision.reason = quota.reason
        end_span(span, ok=False, error=quota.reason)
        return ctx, decision

    end_span(span, ok=True)
    return ctx, decision
