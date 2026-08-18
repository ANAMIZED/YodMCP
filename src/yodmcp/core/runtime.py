"""Global runtime holder for YodMCP substrate components.

In production this is replaced by proper dependency injection via the
MCPServer lifespan and request context. Prototype uses a simple singleton
so tools can reach memory / policy / audit without complex wiring.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from yodmcp.memory.store import MemoryStore
from yodmcp.security.policy import PolicyEngine
from yodmcp.observability.audit import AuditLogger


@dataclass
class Runtime:
    memory: MemoryStore
    policy: PolicyEngine
    audit: AuditLogger


_runtime: Optional[Runtime] = None


def init_runtime() -> Runtime:
    global _runtime
    if _runtime is None:
        _runtime = Runtime(
            memory=MemoryStore(),
            policy=PolicyEngine(),
            audit=AuditLogger(),
        )
    return _runtime


def get_runtime() -> Runtime:
    if _runtime is None:
        return init_runtime()
    return _runtime
