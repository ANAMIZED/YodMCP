"""Usage metering for billable events."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MeterEvent:
    tenant_id: str
    metric: str
    quantity: int = 1
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class UsageMeter:
    def __init__(self) -> None:
        self._counts: dict[str, dict[str, dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(int))
        )
        self._events: list[MeterEvent] = []

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
        ev = MeterEvent(tenant_id=tenant_id, metric=metric, quantity=quantity, metadata=metadata or {})
        self._events.append(ev)
        self._counts[tenant_id][metric][self._day_key(ev.timestamp)] += quantity
        return ev

    def usage_today(self, tenant_id: str, metric: str) -> int:
        return self._counts[tenant_id][metric].get(self._day_key(), 0)

    def summary(self, tenant_id: str) -> dict[str, Any]:
        day = self._day_key()
        metrics = self._counts.get(tenant_id, {})
        return {
            "tenant_id": tenant_id,
            "day": day,
            "usage": {m: metrics[m].get(day, 0) for m in metrics},
            "events_retained": len([e for e in self._events if e.tenant_id == tenant_id]),
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
