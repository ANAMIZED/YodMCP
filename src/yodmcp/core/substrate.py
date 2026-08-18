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
from yodmcp.monetization.billing import BillingService
from yodmcp.monetization.metering import UsageMeter
from yodmcp.monetization.entitlements import EntitlementStore
from yodmcp.observability.otel import init_tracing


def init_substrate(
    console_tracing: bool = False,
    memory_backend: str | None = None,
    memory_db_path: str | None = None,
    attest_mode: str | None = None,
) -> YodContext:
    init_tracing(console=console_tracing)
    backend = memory_backend or os.environ.get("YODMCP_MEMORY_BACKEND", "memory")
    db_path = memory_db_path or os.environ.get("YODMCP_MEMORY_DB", "yodmcp_memory.db")
    mode = attest_mode or os.environ.get("YODMCP_ATTEST_MODE", "software")
    system_db = os.environ.get("YODMCP_SYSTEM_DB") or db_path

    memory = create_memory(backend=backend, db_path=db_path)
    attestation = AttestationService(mode=mode)

    tasks = TaskManager(
        backend=os.environ.get("YODMCP_TASKS_BACKEND", "memory"),
        db_path=system_db,
    )
    meter = UsageMeter(
        backend=os.environ.get("YODMCP_METER_BACKEND", "memory"),
        db_path=system_db,
    )
    audit = AuditLogger(db_path=system_db)
    entitlements = EntitlementStore(db_path=system_db)

    ctx = YodContext(
        memory=memory,
        policy=PolicyEngine(),
        audit=audit,
        cache=CacheLayer(),
        attestation=attestation,
        tasks=tasks,
        skills=SkillsRegistry(),
        billing=BillingService(meter=meter, entitlements=entitlements),
    )
    # Attach extras for operators / future use
    setattr(ctx, "entitlements", entitlements)
    set_context(ctx)
    return ctx
