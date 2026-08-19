"""Usage metering for billable events.

Supports in-memory and SQLite durable counters so daily quotas survive restarts.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiosqlite


@dataclass
class MeterEvent:
    tenant_id: str
    metric: str
    quantity: int = 1
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


METER_SCHEMA = """
CREATE TABLE IF NOT EXISTS usage_daily (
    tenant_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    day TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, metric, day)
);
CREATE TABLE IF NOT EXISTS usage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    ts REAL NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_usage_events_tenant ON usage_events(tenant_id, ts);
"""


class UsageMeter:
    def __init__(self, backend: str | None = None, db_path: str | Path | None = None) -> None:
        self._backend = (backend or os.environ.get("YODMCP_METER_BACKEND", "memory")).lower()
        self._db_path = str(
            db_path
            or os.environ.get("YODMCP_SYSTEM_DB")
            or os.environ.get("YODMCP_MEMORY_DB", "./data/yodmcp_system.db")
        )
        self._counts: dict[str, dict[str, dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(int))
        )
        self._events: list[MeterEvent] = []
        self._db: aiosqlite.Connection | None = None

    async def _conn(self) -> aiosqlite.Connection:
        if self._db is None:
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            self._db = await aiosqlite.connect(self._db_path)
            await self._db.executescript(METER_SCHEMA)
            await self._db.commit()
        return self._db

    @staticmethod
    def _day_key(ts: float | None = None) -> str:
        t = time.gmtime(ts or time.time())
        return f"{t.tm_year:04d}-{t.tm_mon:02d}-{t.tm_mday:02d}"

    def record(
        self,
        tenant_id: str,
        metric: str,
        quantity: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> MeterEvent:
        # Sync path kept for existing call sites; durable write is best-effort fire-and-forget
        ev = MeterEvent(tenant_id=tenant_id, metric=metric, quantity=quantity, metadata=metadata or {})
        self._events.append(ev)
        self._counts[tenant_id][metric][self._day_key(ev.timestamp)] += quantity
        if self._backend == "sqlite":
            try:
                asyncio_get = __import__("asyncio").get_event_loop
                loop = asyncio_get()
                if loop.is_running():
                    loop.create_task(self._record_async(ev))
                else:
                    loop.run_until_complete(self._record_async(ev))
            except Exception:
                pass  # never break request path on meter write
        return ev

    async def _record_async(self, ev: MeterEvent) -> None:
        db = await self._conn()
        day = self._day_key(ev.timestamp)
        await db.execute(
            "INSERT INTO usage_daily (tenant_id, metric, day, quantity) VALUES (?,?,?,?) "
            "ON CONFLICT(tenant_id, metric, day) DO UPDATE SET quantity = quantity + excluded.quantity",
            (ev.tenant_id, ev.metric, day, ev.quantity),
        )
        await db.execute(
            "INSERT INTO usage_events (tenant_id, metric, quantity, ts, metadata) VALUES (?,?,?,?,?)",
            (ev.tenant_id, ev.metric, ev.quantity, ev.timestamp, __import__("json").dumps(ev.metadata)),
        )
        await db.commit()

    def usage_today(self, tenant_id: str, metric: str) -> int:
        # Prefer in-memory for speed; durable is eventual consistency for cross-process
        return self._counts[tenant_id][metric].get(self._day_key(), 0)

    async def usage_today_async(self, tenant_id: str, metric: str) -> int:
        if self._backend != "sqlite":
            return self.usage_today(tenant_id, metric)
        db = await self._conn()
        day = self._day_key()
        cur = await db.execute(
            "SELECT quantity FROM usage_daily WHERE tenant_id=? AND metric=? AND day=?",
            (tenant_id, metric, day),
        )
        row = await cur.fetchone()
        return int(row[0]) if row else 0

    def summary(self, tenant_id: str) -> dict[str, Any]:
        day = self._day_key()
        metrics = self._counts.get(tenant_id, {})
        return {
            "tenant_id": tenant_id,
            "day": day,
            "usage": {m: metrics[m].get(day, 0) for m in metrics},
            "events_retained": len([e for e in self._events if e.tenant_id == tenant_id]),
            "backend": self._backend,
        }

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return [
            {
                "tenant_id": e.tenant_id,
                "metric": e.metric,
                "quantity": e.quantity,
                "ts": e.timestamp,
                "metadata": e.metadata,
            }
            for e in self._events[-limit:]
        ]
