"""Human-in-the-loop approval queue (SaaS control plane foundation).

High-risk tools can enqueue a pending action; operators approve/deny via API.
Fail-closed when YODMCP_HITL_FAIL_CLOSED=true and no approval within TTL.
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HitlStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


@dataclass
class HitlRequest:
    id: str
    tenant_id: str
    tool_name: str
    arguments_summary: str
    risk_tier: str
    status: HitlStatus = HitlStatus.PENDING
    created_at: float = field(default_factory=time.time)
    decided_at: float | None = None
    decided_by: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class HitlQueue:
    def __init__(self, ttl_seconds: int | None = None) -> None:
        self._items: dict[str, HitlRequest] = {}
        self.ttl = ttl_seconds or int(os.environ.get("YODMCP_HITL_TTL_SECONDS", "3600"))
        self.fail_closed = os.environ.get("YODMCP_HITL_FAIL_CLOSED", "").lower() in (
            "1",
            "true",
            "yes",
        )

    def enqueue(
        self,
        tenant_id: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        risk_tier: str = "high",
        metadata: dict[str, Any] | None = None,
    ) -> HitlRequest:
        import json

        rid = str(uuid.uuid4())
        summary = ""
        if arguments:
            try:
                summary = json.dumps(arguments)[:400]
            except Exception:
                summary = str(arguments)[:400]
        req = HitlRequest(
            id=rid,
            tenant_id=tenant_id,
            tool_name=tool_name,
            arguments_summary=summary,
            risk_tier=risk_tier,
            metadata=metadata or {},
        )
        self._items[rid] = req
        return req

    def get(self, request_id: str) -> HitlRequest | None:
        req = self._items.get(request_id)
        if req and req.status == HitlStatus.PENDING and time.time() - req.created_at > self.ttl:
            req.status = HitlStatus.EXPIRED
            req.decided_at = time.time()
        return req

    def decide(
        self,
        request_id: str,
        approve: bool,
        decided_by: str = "operator",
        reason: str | None = None,
    ) -> HitlRequest | None:
        req = self.get(request_id)
        if req is None or req.status != HitlStatus.PENDING:
            return req
        req.status = HitlStatus.APPROVED if approve else HitlStatus.DENIED
        req.decided_at = time.time()
        req.decided_by = decided_by
        req.reason = reason
        return req

    def list_pending(self, tenant_id: str | None = None, limit: int = 50) -> list[HitlRequest]:
        out = []
        for req in sorted(self._items.values(), key=lambda r: r.created_at, reverse=True):
            if req.status == HitlStatus.PENDING:
                if time.time() - req.created_at > self.ttl:
                    req.status = HitlStatus.EXPIRED
                    continue
                if tenant_id and req.tenant_id != tenant_id:
                    continue
                out.append(req)
                if len(out) >= limit:
                    break
        return out

    def stats(self) -> dict[str, Any]:
        by = {}
        for r in self._items.values():
            by[r.status.value] = by.get(r.status.value, 0) + 1
        return {"total": len(self._items), "by_status": by, "fail_closed": self.fail_closed}
