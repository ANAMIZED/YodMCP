"""Hierarchical multi-level memory substrate for YodMCP.

Implements working / episodic / semantic / procedural stores with
basic consolidation. Designed for progressive upgrade to multi-graph
(MAGMA-style) and agentic control-flow memory ops.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MemoryLevel(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


@dataclass
class MemoryItem:
    id: str
    level: MemoryLevel
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
    created_at: float = field(default_factory=time.time)
    importance: float = 0.5
    agent_id: str | None = None
    session_id: str | None = None


class MemoryStore:
    """In-memory prototype of the multi-level cognitive substrate."""

    def __init__(self) -> None:
        self._stores: dict[MemoryLevel, dict[str, MemoryItem]] = {
            level: {} for level in MemoryLevel
        }
        self._lock = asyncio.Lock()
        self._entity_index: dict[str, set[str]] = defaultdict(set)

    async def write(
        self,
        content: str,
        level: MemoryLevel = MemoryLevel.EPISODIC,
        metadata: dict[str, Any] | None = None,
        importance: float = 0.5,
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> str:
        item_id = str(uuid.uuid4())
        item = MemoryItem(
            id=item_id,
            level=level,
            content=content,
            metadata=metadata or {},
            importance=importance,
            agent_id=agent_id,
            session_id=session_id,
        )
        async with self._lock:
            self._stores[level][item_id] = item
            for token in content.split():
                if token[0].isupper() and len(token) > 2:
                    self._entity_index[token.lower()].add(item_id)
        return item_id

    async def read(
        self,
        item_id: str | None = None,
        level: MemoryLevel | None = None,
        query: str | None = None,
        limit: int = 10,
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> list[MemoryItem]:
        async with self._lock:
            candidates: list[MemoryItem] = []
            levels = [level] if level else list(MemoryLevel)
            for lvl in levels:
                for item in self._stores[lvl].values():
                    if agent_id and item.agent_id and item.agent_id != agent_id:
                        continue
                    if session_id and item.session_id and item.session_id != session_id:
                        continue
                    if item_id and item.id != item_id:
                        continue
                    candidates.append(item)

            if query:
                q = query.lower()
                candidates = [c for c in candidates if q in c.content.lower()]

            candidates.sort(key=lambda x: (x.importance, x.created_at), reverse=True)
            return candidates[:limit]

    async def consolidate(self, from_level: MemoryLevel = MemoryLevel.EPISODIC) -> int:
        async with self._lock:
            promoted = 0
            for item in list(self._stores[from_level].values()):
                if item.importance >= 0.8:
                    summary_id = str(uuid.uuid4())
                    summary = MemoryItem(
                        id=summary_id,
                        level=MemoryLevel.SEMANTIC,
                        content=f"[CONSOLIDATED] {item.content[:200]}...",
                        metadata={"source_ids": [item.id], **item.metadata},
                        importance=item.importance,
                        agent_id=item.agent_id,
                    )
                    self._stores[MemoryLevel.SEMANTIC][summary_id] = summary
                    promoted += 1
            return promoted

    async def stats(self) -> dict[str, int]:
        async with self._lock:
            return {level.value: len(store) for level, store in self._stores.items()}

    async def close(self) -> None:
        pass
