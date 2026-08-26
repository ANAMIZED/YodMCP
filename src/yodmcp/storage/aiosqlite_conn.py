"""Loop-safe aiosqlite connection cache.

pytest-asyncio (mode=auto) creates a new event loop per test. Caching an
aiosqlite connection across loops deadlocks on Python 3.12 (worker thread
posts back to a closed loop). Reconnect when the running loop changes.
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

    async def conn(self, schema: str | None = None) -> aiosqlite.Connection:
        loop = asyncio.get_running_loop()
        if self._db is not None and self._loop is not loop:
            old = self._db
            self._db = None
            self._loop = None
            try:
                await old.close()
            except Exception:
                try:
                    old._stop_running()  # type: ignore[attr-defined]
                except Exception:
                    pass
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
        if self._db is not None:
            try:
                await self._db.close()
            except Exception:
                pass
            self._db = None
            self._loop = None
