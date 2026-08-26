"""Durable plan entitlements per tenant (SQLite).

Activated by Stripe webhooks or manual admin. Overrides env YODMCP_PLAN.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import aiosqlite

from yodmcp.storage.aiosqlite_conn import LoopSafeSqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS entitlements (
    tenant_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'env',
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    activated_at REAL NOT NULL,
    expires_at REAL,
    metadata TEXT NOT NULL DEFAULT '{}'
);
"""


class EntitlementStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = str(
            db_path
            or os.environ.get("YODMCP_SYSTEM_DB")
            or os.environ.get("YODMCP_MEMORY_DB", "./data/yodmcp_system.db")
        )
        self._sqlite = LoopSafeSqlite(self.db_path)

    async def _conn(self) -> aiosqlite.Connection:
        return await self._sqlite.conn(SCHEMA)

    async def get_plan(self, tenant_id: str) -> str | None:
        db = await self._conn()
        cur = await db.execute(
            "SELECT plan_id, expires_at FROM entitlements WHERE tenant_id = ?",
            (tenant_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        plan_id, expires = row[0], row[1]
        if expires is not None and expires < time.time():
            return None
        return plan_id

    async def activate(
        self,
        tenant_id: str,
        plan_id: str,
        source: str = "stripe",
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
        expires_at: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        db = await self._conn()
        await db.execute(
            "INSERT INTO entitlements (tenant_id, plan_id, source, stripe_customer_id, "
            "stripe_subscription_id, activated_at, expires_at, metadata) VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(tenant_id) DO UPDATE SET plan_id=excluded.plan_id, source=excluded.source, "
            "stripe_customer_id=excluded.stripe_customer_id, stripe_subscription_id=excluded.stripe_subscription_id, "
            "activated_at=excluded.activated_at, expires_at=excluded.expires_at, metadata=excluded.metadata",
            (
                tenant_id,
                plan_id,
                source,
                stripe_customer_id,
                stripe_subscription_id,
                time.time(),
                expires_at,
                json.dumps(metadata or {}),
            ),
        )
        await db.commit()

    async def deactivate(self, tenant_id: str) -> None:
        db = await self._conn()
        await db.execute("DELETE FROM entitlements WHERE tenant_id = ?", (tenant_id,))
        await db.commit()

    async def close(self) -> None:
        await self._sqlite.close()
