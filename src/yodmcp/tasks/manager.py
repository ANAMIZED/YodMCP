"""MCP Tasks extension hooks (io.modelcontextprotocol/tasks).

Supports in-memory (default) and SQLite durable backend so tasks survive
process restart when YODMCP_TASKS_BACKEND=sqlite (or shared system DB).
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable

import aiosqlite

from yodmcp.storage.aiosqlite_conn import LoopSafeSqlite


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    INPUT_REQUIRED = "input_required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskRecord:
    task_id: str
    status: TaskStatus
    created_at: float
    updated_at: float
    tool_name: str | None = None
    progress: float = 0.0
    message: str | None = None
    result: Any = None
    error: str | None = None
    ttl_ms: int = 3_600_000
    poll_interval_ms: int = 1000
    metadata: dict[str, Any] = field(default_factory=dict)


TASK_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    tool_name TEXT,
    progress REAL NOT NULL DEFAULT 0,
    message TEXT,
    result TEXT,
    error TEXT,
    ttl_ms INTEGER NOT NULL DEFAULT 3600000,
    poll_interval_ms INTEGER NOT NULL DEFAULT 1000,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_updated ON tasks(updated_at);
"""


class TaskManager:
    def __init__(self, backend: str | None = None, db_path: str | Path | None = None) -> None:
        self._backend = (backend or os.environ.get("YODMCP_TASKS_BACKEND", "memory")).lower()
        self._db_path = str(
            db_path
            or os.environ.get("YODMCP_SYSTEM_DB")
            or os.environ.get("YODMCP_MEMORY_DB", "./data/yodmcp_system.db")
        )
        self._tasks: dict[str, TaskRecord] = {}
        self._lock: asyncio.Lock | None = None
        self._lock_loop: asyncio.AbstractEventLoop | None = None
        self._sqlite = LoopSafeSqlite(self._db_path)

    def _mem_lock(self) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        if self._lock is None or self._lock_loop is not loop:
            self._lock = asyncio.Lock()
            self._lock_loop = loop
        return self._lock

    async def _conn(self) -> aiosqlite.Connection:
        return await self._sqlite.conn(TASK_SCHEMA)

    def _row_to_rec(self, row: aiosqlite.Row) -> TaskRecord:
        return TaskRecord(
            task_id=row["task_id"],
            status=TaskStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            tool_name=row["tool_name"],
            progress=row["progress"] or 0.0,
            message=row["message"],
            result=json.loads(row["result"]) if row["result"] else None,
            error=row["error"],
            ttl_ms=row["ttl_ms"] or 3_600_000,
            poll_interval_ms=row["poll_interval_ms"] or 1000,
            metadata=json.loads(row["metadata"] or "{}"),
        )

    async def create(
        self,
        tool_name: str | None = None,
        ttl_ms: int = 3_600_000,
        poll_interval_ms: int = 1000,
        metadata: dict[str, Any] | None = None,
    ) -> TaskRecord:
        tid = str(uuid.uuid4())
        now = time.time()
        rec = TaskRecord(
            task_id=tid,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            tool_name=tool_name,
            ttl_ms=ttl_ms,
            poll_interval_ms=poll_interval_ms,
            metadata=metadata or {},
        )
        if self._backend == "sqlite":
            db = await self._conn()
            await db.execute(
                "INSERT INTO tasks (task_id, status, created_at, updated_at, tool_name, progress, "
                "message, result, error, ttl_ms, poll_interval_ms, metadata) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    rec.task_id,
                    rec.status.value,
                    rec.created_at,
                    rec.updated_at,
                    rec.tool_name,
                    rec.progress,
                    rec.message,
                    None,
                    None,
                    rec.ttl_ms,
                    rec.poll_interval_ms,
                    json.dumps(rec.metadata),
                ),
            )
            await db.commit()
        else:
            async with self._mem_lock():
                self._tasks[tid] = rec
        return rec

    async def update(
        self,
        task_id: str,
        status: TaskStatus | str | None = None,
        progress: float | None = None,
        message: str | None = None,
        result: Any = None,
        error: str | None = None,
    ) -> TaskRecord | None:
        if self._backend == "sqlite":
            db = await self._conn()
            cur = await db.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = await cur.fetchone()
            if not row:
                return None
            rec = self._row_to_rec(row)
            if status is not None:
                rec.status = TaskStatus(status) if isinstance(status, str) else status
            if progress is not None:
                rec.progress = progress
            if message is not None:
                rec.message = message
            if result is not None:
                rec.result = result
            if error is not None:
                rec.error = error
            rec.updated_at = time.time()
            await db.execute(
                "UPDATE tasks SET status=?, updated_at=?, progress=?, message=?, result=?, error=? WHERE task_id=?",
                (
                    rec.status.value,
                    rec.updated_at,
                    rec.progress,
                    rec.message,
                    json.dumps(rec.result) if rec.result is not None else None,
                    rec.error,
                    task_id,
                ),
            )
            await db.commit()
            return rec

        async with self._mem_lock():
            rec = self._tasks.get(task_id)
            if not rec:
                return None
            if status is not None:
                rec.status = TaskStatus(status) if isinstance(status, str) else status
            if progress is not None:
                rec.progress = progress
            if message is not None:
                rec.message = message
            if result is not None:
                rec.result = result
            if error is not None:
                rec.error = error
            rec.updated_at = time.time()
            return rec

    async def get(self, task_id: str) -> TaskRecord | None:
        if self._backend == "sqlite":
            db = await self._conn()
            cur = await db.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = await cur.fetchone()
            return self._row_to_rec(row) if row else None
        async with self._mem_lock():
            return self._tasks.get(task_id)

    async def cancel(self, task_id: str) -> bool:
        rec = await self.update(task_id, status=TaskStatus.CANCELLED)
        return rec is not None

    def to_handle(self, rec: TaskRecord) -> dict[str, Any]:
        return {
            "resultType": "task",
            "taskId": rec.task_id,
            "status": rec.status.value,
            "progress": rec.progress,
            "message": rec.message,
            "ttlMs": rec.ttl_ms,
            "pollIntervalMs": rec.poll_interval_ms,
            "createdAt": rec.created_at,
            "updatedAt": rec.updated_at,
            "result": rec.result,
            "error": rec.error,
            "toolName": rec.tool_name,
        }

    async def run_background(
        self,
        coro_factory: Callable[[TaskRecord], Awaitable[Any]],
        tool_name: str | None = None,
    ) -> dict[str, Any]:
        rec = await self.create(tool_name=tool_name)
        await self.update(rec.task_id, status=TaskStatus.RUNNING, progress=0.05, message="started")

        async def _runner() -> None:
            try:
                result = await coro_factory(rec)
                await self.update(
                    rec.task_id,
                    status=TaskStatus.COMPLETED,
                    progress=1.0,
                    message="done",
                    result=result,
                )
            except Exception as exc:
                await self.update(
                    rec.task_id,
                    status=TaskStatus.FAILED,
                    progress=1.0,
                    error=str(exc),
                    message="failed",
                )

        asyncio.create_task(_runner())
        return self.to_handle(rec)

    async def stats(self) -> dict[str, Any]:
        if self._backend == "sqlite":
            db = await self._conn()
            cur = await db.execute("SELECT status, COUNT(*) as c FROM tasks GROUP BY status")
            rows = await cur.fetchall()
            by_status = {r["status"]: r["c"] for r in rows}
            total = sum(by_status.values())
            return {"total": total, "by_status": by_status, "backend": "sqlite"}
        async with self._mem_lock():
            by_status: dict[str, int] = {}
            for t in self._tasks.values():
                by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
            return {"total": len(self._tasks), "by_status": by_status, "backend": "memory"}
