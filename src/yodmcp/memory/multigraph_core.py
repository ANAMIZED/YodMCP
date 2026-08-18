"""Multi-graph hierarchical memory: semantic / temporal / causal / entity + embeddings.

Extends the original multi-level store with orthogonal graphs and
lightweight embedding retrieval (pure-Python cosine for zero heavy deps).
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable


class MemoryLevel(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class GraphKind(str, Enum):
    SEMANTIC = "semantic"
    TEMPORAL = "temporal"
    CAUSAL = "causal"
    ENTITY = "entity"


@dataclass
class MemoryNode:
    id: str
    level: MemoryLevel
    content: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    importance: float = 0.5
    agent_id: str | None = None
    session_id: str | None = None
    graph_ids: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))


def _simple_embed(text: str, dim: int = 64) -> list[float]:
    """Deterministic bag-of-chars style embedding for prototype retrieval."""
    vec = [0.0] * dim
    data = text.lower().encode("utf-8")
    for i, b in enumerate(data):
        vec[i % dim] += (b / 255.0) * (1.0 + (i % 7) * 0.1)
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
