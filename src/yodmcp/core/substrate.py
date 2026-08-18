"""Initialize the full YodMCP substrate and bind it into context."""

from __future__ import annotations

from yodmcp.core.context import YodContext, set_context
from yodmcp.memory.multigraph import MultiGraphMemory
from yodmcp.security.policy import PolicyEngine
from yodmcp.security.attestation import AttestationService
from yodmcp.observability.audit import AuditLogger
from yodmcp.cache.layer import CacheLayer
from yodmcp.tasks.manager import TaskManager
from yodmcp.skills.registry import SkillsRegistry
from yodmcp.observability.otel import init_tracing


def init_substrate(console_tracing: bool = False) -> YodContext:
    init_tracing(console=console_tracing)
    ctx = YodContext(
        memory=MultiGraphMemory(),
        policy=PolicyEngine(),
        audit=AuditLogger(),
        cache=CacheLayer(),
        attestation=AttestationService(),
        tasks=TaskManager(),
        skills=SkillsRegistry(),
    )
    set_context(ctx)
    return ctx
