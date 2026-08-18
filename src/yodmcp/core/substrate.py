"""Initialize the full YodMCP substrate and bind it into context."""

from __future__ import annotations

import os

from yodmcp.core.context import YodContext, set_context
from yodmcp.memory.durable import create_memory
from yodmcp.security.policy import PolicyEngine
from yodmcp.security.attestation import AttestationService
from yodmcp.observability.audit import AuditLogger
from yodmcp.cache.layer import CacheLayer
from yodmcp.tasks.manager import TaskManager
from yodmcp.skills.registry import SkillsRegistry
from yodmcp.observability.otel import init_tracing


def init_substrate(
    console_tracing: bool = False,
    memory_backend: str | None = None,
    memory_db_path: str | None = None,
    attest_mode: str | None = None,
) -> YodContext:
    """Boot substrate.

    Env overrides
    -------------
    YODMCP_MEMORY_BACKEND  memory | sqlite
    YODMCP_MEMORY_DB       path for sqlite file
    YODMCP_ATTEST_MODE     software | simulated_tee | tee_nitro | tee_sgx
    """
    init_tracing(console=console_tracing)
    backend = memory_backend or os.environ.get("YODMCP_MEMORY_BACKEND", "memory")
    db_path = memory_db_path or os.environ.get("YODMCP_MEMORY_DB", "yodmcp_memory.db")
    mode = attest_mode or os.environ.get("YODMCP_ATTEST_MODE", "software")

    memory = create_memory(backend=backend, db_path=db_path)
    attestation = AttestationService(mode=mode)

    ctx = YodContext(
        memory=memory,
        policy=PolicyEngine(),
        audit=AuditLogger(),
        cache=CacheLayer(),
        attestation=attestation,
        tasks=TaskManager(),
        skills=SkillsRegistry(),
    )
    set_context(ctx)
    return ctx
