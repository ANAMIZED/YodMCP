"""MultiGraphMemory class — see multigraph_core for types/helpers."""
from __future__ import annotations

from collections import defaultdict
from typing import Any
import asyncio
import time
import uuid

from yodmcp.memory.multigraph_core import (
    MemoryLevel,
    GraphKind,
    MemoryNode,
    _simple_embed,
    _cosine,
)

class MultiGraphMemory:
    """Hierarchical multi-graph memory substrate."""

    def __init__(self, embed_dim: int = 64) -> None:
        self.embed_dim = embed_dim
        self._nodes: dict[str, MemoryNode] = {}
        self._edges: dict[GraphKind, dict[str, set[str]]] = {
            k: defaultdict(set) for k in GraphKind
        }
        self._entity_index: dict[str, set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def write(
        self,
        content: str,
        level: MemoryLevel | str = MemoryLevel.EPISODIC,
        importance: float = 0.5,
        agent_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        link_to: list[str] | None = None,
        causal_parent: str | None = None,
        entities: list[str] | None = None,
    ) -> str:
        if isinstance(level, str):
            try:
                level = MemoryLevel(level)
            except ValueError:
                level = MemoryLevel.EPISODIC

        node_id = str(uuid.uuid4())
        emb = _simple_embed(content, self.embed_dim)
        node = MemoryNode(
            id=node_id,
            level=level,
            content=content,
            embedding=emb,
            metadata=metadata or {},
            importance=importance,
            agent_id=agent_id,
            session_id=session_id,
        )

        async with self._lock:
            self._nodes[node_id] = node

            recent = [
                n for n in self._nodes.values()
                if n.level == level and n.id != node_id
            ]
            if recent:
                recent.sort(key=lambda n: n.created_at, reverse=True)
                prev = recent[0].id
                self._edges[GraphKind.TEMPORAL][node_id].add(prev)
                self._edges[GraphKind.TEMPORAL][prev].add(node_id)

            if causal_parent and causal_parent in self._nodes:
                self._edges[GraphKind.CAUSAL][node_id].add(causal_parent)
                self._edges[GraphKind.CAUSAL][causal_parent].add(node_id)

            if link_to:
                for other in link_to:
                    if other in self._nodes:
                        self._edges[GraphKind.SEMANTIC][node_id].add(other)
                        self._edges[GraphKind.SEMANTIC][other].add(node_id)

            ents = entities or []
            if not ents:
                ents = [t for t in content.split() if t[:1].isupper() and len(t) > 2]
            for e in ents:
                key = e.lower()
                self._entity_index[key].add(node_id)
                for other_id in list(self._entity_index[key])[:20]:
                    if other_id != node_id:
                        self._edges[GraphKind.ENTITY][node_id].add(other_id)
                        self._edges[GraphKind.ENTITY][other_id].add(node_id)

        return node_id

    async def read(
        self,
        query: str | None = None,
        level: MemoryLevel | str | None = None,
        limit: int = 10,
        agent_id: str | None = None,
        session_id: str | None = None,
        item_id: str | None = None,
        graph: GraphKind | str | None = None,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        async with self._lock:
            candidates = list(self._nodes.values())
            if item_id:
                candidates = [n for n in candidates if n.id == item_id]
            if level:
                if isinstance(level, str):
                    try:
                        level = MemoryLevel(level)
                    except ValueError:
                        level = None
                if level:
                    candidates = [n for n in candidates if n.level == level]
            if agent_id:
                candidates = [n for n in candidates if not n.agent_id or n.agent_id == agent_id]
            if session_id:
                candidates = [
                    n for n in candidates if not n.session_id or n.session_id == session_id
                ]

            scored: list[tuple[float, MemoryNode]] = []
            q_emb = _simple_embed(query, self.embed_dim) if query else None
            for n in candidates:
                score = n.importance
                if q_emb is not None:
                    score = 0.6 * _cosine(q_emb, n.embedding) + 0.4 * n.importance
                if score >= min_score:
                    scored.append((score, n))

            scored.sort(key=lambda x: x[0], reverse=True)
            results = []
            for score, n in scored[:limit]:
                neighbors = {}
                if graph:
                    gk = GraphKind(graph) if isinstance(graph, str) else graph
                    neighbors[gk.value] = list(self._edges[gk].get(n.id, set()))[:10]
                else:
                    for gk in GraphKind:
                        ns = list(self._edges[gk].get(n.id, set()))[:5]
                        if ns:
                            neighbors[gk.value] = ns
                results.append(
                    {
                        "id": n.id,
                        "level": n.level.value,
                        "content": n.content,
                        "importance": n.importance,
                        "score": round(score, 4),
                        "created_at": n.created_at,
                        "metadata": n.metadata,
                        "neighbors": neighbors,
                    }
                )
            return results

    async def consolidate(self, from_level: MemoryLevel | str = MemoryLevel.EPISODIC) -> int:
        if isinstance(from_level, str):
            try:
                from_level = MemoryLevel(from_level)
            except ValueError:
                from_level = MemoryLevel.EPISODIC
        async with self._lock:
            promoted = 0
            for node in list(self._nodes.values()):
                if node.level == from_level and node.importance >= 0.8:
                    summary = f"[CONSOLIDATED] {node.content[:240]}"
                    emb = _simple_embed(summary, self.embed_dim)
                    sid = str(uuid.uuid4())
                    snode = MemoryNode(
                        id=sid,
                        level=MemoryLevel.SEMANTIC,
                        content=summary,
                        embedding=emb,
                        metadata={"source_ids": [node.id], **node.metadata},
                        importance=node.importance,
                        agent_id=node.agent_id,
                    )
                    self._nodes[sid] = snode
                    self._edges[GraphKind.SEMANTIC][sid].add(node.id)
                    self._edges[GraphKind.SEMANTIC][node.id].add(sid)
                    self._edges[GraphKind.CAUSAL][sid].add(node.id)
                    promoted += 1
            return promoted

    async def stats(self) -> dict[str, Any]:
        async with self._lock:
            by_level = {l.value: 0 for l in MemoryLevel}
            for n in self._nodes.values():
                by_level[n.level.value] += 1
            edge_counts = {k.value: sum(len(v) for v in g.values()) for k, g in self._edges.items()}
            return {
                "nodes": len(self._nodes),
                "by_level": by_level,
                "edges": edge_counts,
                "entities_indexed": len(self._entity_index),
            }

    async def delete(self, item_id: str) -> bool:
        async with self._lock:
            if item_id not in self._nodes:
                return False
            self._nodes.pop(item_id, None)
            for graph in self._edges.values():
                graph.pop(item_id, None)
                for peers in graph.values():
                    peers.discard(item_id)
            for key, ids in list(self._entity_index.items()):
                ids.discard(item_id)
                if not ids:
                    self._entity_index.pop(key, None)
            return True

    async def close(self) -> None:
        pass
