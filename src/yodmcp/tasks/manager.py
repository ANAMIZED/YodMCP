"""MCP Tasks extension hooks (io.modelcontextprotocol/tasks).

Implements a durable-ish in-memory task store that can return
CreateTaskResult-shaped handles. Full wire protocol integration
depends on SDK extension runtime; this provides the substrate and
tools that clients can poll.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable


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


class TaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = asyncio.Lock()

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
        async with self._lock:
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
        async with self._lock:
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
        async with self._lock:
            return self._tasks.get(task_id)

    async def cancel(self, task_id: str) -> bool:
        async with self._lock:
            rec = self._tasks.get(task_id)
            if not rec:
                return False
            rec.status = TaskStatus.CANCELLED
            rec.updated_at = time.time()
            return True

    def to_handle(self, rec: TaskRecord) -> dict[str, Any]:
        """Shape compatible with CreateTaskResult / tasks/get responses."""
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
        """Create a task and schedule work; return handle immediately."""
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
        async with self._lock:
            by_status: dict[str, int] = {}
            for t in self._tasks.values():
                by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
            return {"total": len(self._tasks), "by_status": by_status}
