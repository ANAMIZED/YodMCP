"""Loop-safe aiosqlite connection cache.

pytest-asyncio (mode=auto) creates a new event loop per test. Caching an
aiosqlite connection across loops deadlocks on Python 3.12 (worker thread
posts back to a closed loop). Reconnect when the running loop changes.

Never await Connection.close() on a *different* loop — that is itself a hang.
Call Connection.stop() so the non-daemon worker thread can exit.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

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
            old.stop()
        except Exception:
            pass
        try:
            thread = getattr(old, "_thread", None)
            if thread is not None:
                thread.daemon = True
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
        db, bound = self._db, self._loop
        if db is None:
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is not None and running is bound:
            self._db = None
            self._loop = None
            try:
                await db.close()
                return
            except Exception:
                self._db = db
                self._loop = bound
        self._abandon()
