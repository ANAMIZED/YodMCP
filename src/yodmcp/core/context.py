"""Request-scoped and process-scoped context for YodMCP.

Uses contextvars so tools, middleware, and extensions can access the
substrate without a global singleton. Lifespan initializes the process
defaults; individual requests can override when the SDK supplies a
request context.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from yodmcp.memory.multigraph import MultiGraphMemory
    from yodmcp.security.policy import PolicyEngine
    from yodmcp.security.attestation import AttestationService
    from yodmcp.observability.audit import AuditLogger
    from yodmcp.cache.layer import CacheLayer
    from yodmcp.tasks.manager import TaskManager
    from yodmcp.skills.registry import SkillsRegistry


@dataclass
class YodContext:
    memory: "MultiGraphMemory"
    policy: "PolicyEngine"
    audit: "AuditLogger"
    cache: "CacheLayer"
    attestation: "AttestationService"
    tasks: "TaskManager"
    skills: "SkillsRegistry"
    tracer_name: str = "yodmcp"


_ctx: ContextVar[Optional[YodContext]] = ContextVar("yodmcp_ctx", default=None)


def set_context(ctx: YodContext) -> None:
    _ctx.set(ctx)


def get_context() -> YodContext:
    ctx = _ctx.get()
    if ctx is None:
        raise RuntimeError("YodMCP context not initialized — call init_substrate() first")
    return ctx


def try_get_context() -> Optional[YodContext]:
    return _ctx.get()
