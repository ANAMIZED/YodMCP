"""Loop-safe aiosqlite connection cache.

pytest-asyncio (mode=auto) creates a new event loop per test. Caching an
aiosqlite connection across loops deadlocks on Python 3.12 (worker thread
posts back to a closed loop). Reconnect when the running loop changes.

Never await Connection.close() on a *different* loop — that is itself a hang.
Call Connection.stop() so the non-daemon worker thread can exit.
Hold a local connection reference across awaits so close() cannot null
self._db mid-schema-init (AuditLogger persist race).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import aiosqlite


def _stop_worker(conn: aiosqlite.Connection) -> None:
    try:
        conn.stop()
    except Exception:
        pass
    thread = getattr(conn, "_thread", None)
    if thread is None:
        return
    try:
        thread.daemon = True
        thread.join(timeout=0.25)
    except Exception:
        pass


class LoopSafeSqlite:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._db: aiosqlite.Connection | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock: asyncio.Lock | None = None
        self._lock_loop: asyncio.AbstractEventLoop | None = None

    def _get_lock(self) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        if self._lock is None or self._lock_loop is not loop:
            self._lock = asyncio.Lock()
            self._lock_loop = loop
        return self._lock

    def _abandon(self) -> None:
        old = self._db
        self._db = None
        self._loop = None
        if old is not None:
            _stop_worker(old)

    async def conn(self, schema: str | None = None) -> aiosqlite.Connection:
        async with self._get_lock():
            loop = asyncio.get_running_loop()
            if self._db is not None and self._loop is not loop:
                self._abandon()
            if self._db is None:
                parent = Path(self.db_path).parent
                if str(parent) not in ("", "."):
                    parent.mkdir(parents=True, exist_ok=True)
                db = await aiosqlite.connect(self.db_path)
                db.row_factory = aiosqlite.Row
                self._db = db
                self._loop = loop
                if schema:
                    await db.executescript(schema)
                    await db.commit()
                return db
            return self._db

    async def close(self) -> None:
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            self._abandon()
            return
        async with self._get_lock():
            db, bound = self._db, self._loop
            if db is None:
                return
            self._db = None
            self._loop = None
            if running is bound:
                try:
                    await db.close()
                except Exception:
                    pass
            _stop_worker(db)
