"""Semantic + plan caching layer for YodMCP.

Exact-match + embedding similarity cache for tool results and
structured plan templates (Agentic Plan Caching pattern).
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from typing import Any


def _embed(text: str, dim: int = 48) -> list[float]:
    vec = [0.0] * dim
    data = text.lower().encode()
    for i, b in enumerate(data):
        vec[i % dim] += b / 255.0
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


@dataclass
class CacheEntry:
    key: str
    value: Any
    embedding: list[float]
    created_at: float = field(default_factory=time.time)
    hits: int = 0
    kind: str = "result"  # result | plan


class CacheLayer:
    def __init__(self, similarity_threshold: float = 0.68, max_entries: int = 2048) -> None:
        self.threshold = similarity_threshold
        self.max_entries = max_entries
        self._exact: dict[str, CacheEntry] = {}
        self._entries: list[CacheEntry] = []

    def _key(self, namespace: str, payload: str) -> str:
        h = hashlib.sha256(f"{namespace}:{payload}".encode()).hexdigest()[:24]
        return f"{namespace}:{h}"

    def get_exact(self, namespace: str, payload: str) -> Any | None:
        k = self._key(namespace, payload)
        entry = self._exact.get(k)
        if entry:
            entry.hits += 1
            return entry.value
        return None

    def get_semantic(self, namespace: str, query: str) -> tuple[Any | None, float]:
        q_emb = _embed(query)
        best: CacheEntry | None = None
        best_score = 0.0
        for e in self._entries:
            if not e.key.startswith(namespace):
                continue
            score = _cosine(q_emb, e.embedding)
            if score > best_score:
                best_score = score
                best = e
        if best and best_score >= self.threshold:
            best.hits += 1
            return best.value, best_score
        return None, best_score

    def put(self, namespace: str, payload: str, value: Any, kind: str = "result") -> str:
        k = self._key(namespace, payload)
        emb = _embed(payload)
        entry = CacheEntry(key=k, value=value, embedding=emb, kind=kind)
        self._exact[k] = entry
        self._entries.append(entry)
        if len(self._entries) > self.max_entries:
            self._entries.sort(key=lambda e: (e.hits, e.created_at))
            drop = self._entries[: len(self._entries) // 4]
            for d in drop:
                self._exact.pop(d.key, None)
            self._entries = self._entries[len(self._entries) // 4 :]
        return k

    def put_plan(self, task_desc: str, plan: dict[str, Any]) -> str:
        return self.put("plan", task_desc, plan, kind="plan")

    def get_plan(self, task_desc: str) -> tuple[dict[str, Any] | None, float]:
        val, score = self.get_semantic("plan", task_desc)
        return (val if isinstance(val, dict) else None), score

    def delete_plan(self, task_desc: str) -> bool:
        k = self._key("plan", task_desc)
        existed = k in self._exact
        self._exact.pop(k, None)
        self._entries = [e for e in self._entries if e.key != k]
        return existed

    def stats(self) -> dict[str, Any]:
        hits = sum(e.hits for e in self._entries)
        return {
            "entries": len(self._entries),
            "exact_keys": len(self._exact),
            "total_hits": hits,
            "threshold": self.threshold,
        }
