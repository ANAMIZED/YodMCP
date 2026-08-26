"""Decision System of Record (DSoR) style audit trail for YodMCP.

Every tool call, memory op, policy decision, and agent interaction is recorded
with provenance. Supports process-local + JSONL and optional SQLite durable index.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import aiosqlite

from yodmcp.storage.aiosqlite_conn import LoopSafeSqlite


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


AUDIT_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    timestamp REAL NOT NULL,
    event_type TEXT NOT NULL,
    actor TEXT,
    session_id TEXT,
    tool_name TEXT,
    arguments_summary TEXT,
    decision TEXT,
    risk_tier TEXT,
    outcome TEXT,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_events(event_type);
"""


class AuditLogger:
    def __init__(self, log_path: str | Path | None = None, db_path: str | Path | None = None) -> None:
        self._events: list[AuditEvent] = []
        self._path = Path(log_path) if log_path else Path(
            os.environ.get("YODMCP_AUDIT_LOG", "/tmp/yodmcp_audit.jsonl")
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._backend = os.environ.get("YODMCP_AUDIT_BACKEND", "jsonl").lower()
        self._db_path = str(
            db_path
            or os.environ.get("YODMCP_SYSTEM_DB")
            or os.environ.get("YODMCP_MEMORY_DB", "./data/yodmcp_system.db")
        )
        self._sqlite = LoopSafeSqlite(self._db_path)

    async def _conn(self) -> aiosqlite.Connection:
        return await self._sqlite.conn(AUDIT_SCHEMA)

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
        try:
            with self._path.open("a") as f:
                f.write(json.dumps(asdict(event)) + "\n")
        except Exception:
            pass

        if self._backend in ("sqlite", "db", "durable"):
            try:
                import asyncio

                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None
                if loop is not None and loop.is_running():
                    loop.create_task(self._persist(event))
                else:
                    asyncio.run(self._persist(event))
            except Exception:
                pass
        return event_id

    async def _persist(self, event: AuditEvent) -> None:
        db = await self._conn()
        await db.execute(
            "INSERT OR IGNORE INTO audit_events "
            "(id, timestamp, event_type, actor, session_id, tool_name, arguments_summary, "
            "decision, risk_tier, outcome, metadata) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                event.id,
                event.timestamp,
                event.event_type,
                event.actor,
                event.session_id,
                event.tool_name,
                event.arguments_summary,
                event.decision,
                event.risk_tier,
                event.outcome,
                json.dumps(event.metadata),
            ),
        )
        await db.commit()

    def recent(self, limit: int = 50) -> list[AuditEvent]:
        return self._events[-limit:]

    def stats(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        for e in self._events:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
        total = len(self._events)
        return {
            "total": total,
            "total_events": total,  # backward compat
            "by_type": by_type,
            "backend": self._backend,
            "log_path": str(self._path),
        }
