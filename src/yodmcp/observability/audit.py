"""Decision System of Record (DSoR) style audit trail for YodMCP.

Every tool call, memory op, policy decision, and agent interaction is recorded
with provenance. Production upgrades to immutable Merkle chain + TRACE Claims.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AuditEvent:
    id: str
    timestamp: float
    event_type: str
    actor: str | None
    session_id: str | None
    tool_name: str | None
    arguments_summary: str | None
    decision: str | None
    risk_tier: str | None
    outcome: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


class AuditLogger:
    def __init__(self, log_path: str | Path | None = None) -> None:
        self._events: list[AuditEvent] = []
        self._path = Path(log_path) if log_path else Path("/tmp/yodmcp_audit.jsonl")
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        event_type: str,
        actor: str | None = None,
        session_id: str | None = None,
        tool_name: str | None = None,
        arguments: dict[str, Any] | None = None,
        decision: str | None = None,
        risk_tier: str | None = None,
        outcome: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        event_id = str(uuid.uuid4())
        args_summary = None
        if arguments:
            try:
                args_summary = json.dumps(arguments)[:500]
            except Exception:
                args_summary = str(arguments)[:500]

        event = AuditEvent(
            id=event_id,
            timestamp=time.time(),
            event_type=event_type,
            actor=actor,
            session_id=session_id,
            tool_name=tool_name,
            arguments_summary=args_summary,
            decision=decision,
            risk_tier=risk_tier,
            outcome=outcome,
            metadata=metadata or {},
        )
        self._events.append(event)
        with self._path.open("a") as f:
            f.write(json.dumps(asdict(event)) + "\n")
        return event_id

    def recent(self, limit: int = 50) -> list[AuditEvent]:
        return self._events[-limit:]

    def stats(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        for e in self._events:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
        return {
            "total_events": len(self._events),
            "by_type": by_type,
            "log_path": str(self._path),
        }
