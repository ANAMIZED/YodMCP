"""Loop-safe aiosqlite connection cache.

pytest-asyncio (mode=auto) creates a new event loop per test. Caching an
aiosqlite connection across loops deadlocks on Python 3.12 (worker thread
posts back to a closed loop). Reconnect when the running loop changes.

Never await Connection.close() on a *different* loop — that is itself a hang.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import aiosqlite


class LoopSafeSqlite:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._db: aiosqlite.Connection | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def _abandon(self) -> None:
        old = self._db
        self._db = None
        self._loop = None
        if old is None:
            return
        try:
            stopper = getattr(old, "_stop_running", None)
            if callable(stopper):
                stopper()
        except Exception:
            pass

    async def conn(self, schema: str | None = None) -> aiosqlite.Connection:
        loop = asyncio.get_running_loop()
        if self._db is not None and self._loop is not loop:
            self._abandon()
        if self._db is None:
            parent = Path(self.db_path).parent
            if str(parent) not in ("", "."):
                parent.mkdir(parents=True, exist_ok=True)
            self._db = await aiosqlite.connect(self.db_path)
            self._db.row_factory = aiosqlite.Row
            self._loop = loop
            if schema:
                await self._db.executescript(schema)
                await self._db.commit()
        return self._db

    async def close(self) -> None:
        db, loop = self._db, self._loop
        self._db = None
        self._loop = None
        if db is None:
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is not None and running is loop:
            try:
                await db.close()
                return
            except Exception:
                pass
        self._db = db
        self._abandon()
