"""Durable multi-graph memory backed by SQLite (vector blobs + edge tables)."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

import aiosqlite

from yodmcp.memory.multigraph_core import GraphKind, MemoryLevel, _cosine, _simple_embed

SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY, level TEXT NOT NULL, content TEXT NOT NULL,
    embedding TEXT NOT NULL, metadata TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL, importance REAL NOT NULL DEFAULT 0.5,
    agent_id TEXT, session_id TEXT
);
CREATE TABLE IF NOT EXISTS edges (
    graph_kind TEXT NOT NULL, src TEXT NOT NULL, dst TEXT NOT NULL,
    PRIMARY KEY (graph_kind, src, dst)
);
CREATE TABLE IF NOT EXISTS entities (
    entity_key TEXT NOT NULL, node_id TEXT NOT NULL,
    PRIMARY KEY (entity_key, node_id)
);
CREATE INDEX IF NOT EXISTS idx_nodes_level ON nodes(level);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS idx_entities_key ON entities(entity_key);
"""


class DurableMultiGraphMemory:
    def __init__(self, db_path: str | Path = "yodmcp_memory.db", embed_dim: int = 64) -> None:
        self.db_path = str(db_path)
        self.embed_dim = embed_dim
        self._db: aiosqlite.Connection | None = None

    async def _conn(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            self._db.row_factory = aiosqlite.Row
            await self._db.executescript(SCHEMA)
            await self._db.commit()
        return self._db

    async def write(
        self, content: str, level: MemoryLevel | str = MemoryLevel.EPISODIC,
        importance: float = 0.5, agent_id: str | None = None,
        session_id: str | None = None, metadata: dict[str, Any] | None = None,
        link_to: list[str] | None = None, causal_parent: str | None = None,
        entities: list[str] | None = None,
    ) -> str:
        if isinstance(level, str):
            try:
                level = MemoryLevel(level)
            except ValueError:
                level = MemoryLevel.EPISODIC
        node_id = str(uuid.uuid4())
        emb = _simple_embed(content, self.embed_dim)
        db = await self._conn()
        await db.execute(
            "INSERT INTO nodes (id, level, content, embedding, metadata, created_at, importance, agent_id, session_id) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (node_id, level.value, content, json.dumps(emb), json.dumps(metadata or {}),
             time.time(), importance, agent_id, session_id),
        )
        cur = await db.execute(
            "SELECT id FROM nodes WHERE level=? AND id!=? ORDER BY created_at DESC LIMIT 1",
            (level.value, node_id),
        )
        row = await cur.fetchone()
        if row:
            for a, b in ((node_id, row["id"]), (row["id"], node_id)):
                await db.execute(
                    "INSERT OR IGNORE INTO edges (graph_kind, src, dst) VALUES (?,?,?)",
                    (GraphKind.TEMPORAL.value, a, b),
                )
        if causal_parent:
            for a, b in ((node_id, causal_parent), (causal_parent, node_id)):
                await db.execute(
                    "INSERT OR IGNORE INTO edges (graph_kind, src, dst) VALUES (?,?,?)",
                    (GraphKind.CAUSAL.value, a, b),
                )
        if link_to:
            for other in link_to:
                for a, b in ((node_id, other), (other, node_id)):
                    await db.execute(
                        "INSERT OR IGNORE INTO edges (graph_kind, src, dst) VALUES (?,?,?)",
                        (GraphKind.SEMANTIC.value, a, b),
                    )
        ents = entities or [t for t in content.split() if t[:1].isupper() and len(t) > 2]
        for e in ents:
            key = e.lower()
            await db.execute(
                "INSERT OR IGNORE INTO entities (entity_key, node_id) VALUES (?,?)", (key, node_id)
            )
            cur = await db.execute(
                "SELECT node_id FROM entities WHERE entity_key=? AND node_id!=? LIMIT 20",
                (key, node_id),
            )
            for r in await cur.fetchall():
                for a, b in ((node_id, r["node_id"]), (r["node_id"], node_id)):
                    await db.execute(
                        "INSERT OR IGNORE INTO edges (graph_kind, src, dst) VALUES (?,?,?)",
                        (GraphKind.ENTITY.value, a, b),
                    )
        await db.commit()
        return node_id

    async def read(
        self, query: str | None = None, level: MemoryLevel | str | None = None,
        limit: int = 10, agent_id: str | None = None, session_id: str | None = None,
        item_id: str | None = None, graph: GraphKind | str | None = None,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        db = await self._conn()
        sql, params = "SELECT * FROM nodes WHERE 1=1", []
        if item_id:
            sql += " AND id=?"; params.append(item_id)
        if level:
            lv = level.value if isinstance(level, MemoryLevel) else level
            sql += " AND level=?"; params.append(lv)
        if agent_id:
            sql += " AND (agent_id IS NULL OR agent_id=?)"; params.append(agent_id)
        if session_id:
            sql += " AND (session_id IS NULL OR session_id=?)"; params.append(session_id)
        cur = await db.execute(sql, params)
        rows = await cur.fetchall()
        q_emb = _simple_embed(query, self.embed_dim) if query else None
        scored = []
        for row in rows:
            emb = json.loads(row["embedding"])
            score = row["importance"]
            if q_emb is not None:
                score = 0.6 * _cosine(q_emb, emb) + 0.4 * row["importance"]
            if score >= min_score:
                scored.append((score, row))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, row in scored[:limit]:
            neighbors = {}
            kinds = [GraphKind(graph) if isinstance(graph, str) else graph] if graph else list(GraphKind)
            lim = 10 if graph else 5
            for gk in kinds:
                key = gk.value if isinstance(gk, GraphKind) else gk
                cur = await db.execute(
                    "SELECT dst FROM edges WHERE graph_kind=? AND src=? LIMIT ?",
                    (key, row["id"], lim),
                )
                ns = [r["dst"] for r in await cur.fetchall()]
                if ns:
                    neighbors[key] = ns
            results.append({
                "id": row["id"], "level": row["level"], "content": row["content"],
                "importance": row["importance"], "score": round(score, 4),
                "created_at": row["created_at"], "metadata": json.loads(row["metadata"]),
                "neighbors": neighbors,
            })
        return results

    async def consolidate(self, from_level: MemoryLevel | str = MemoryLevel.EPISODIC) -> int:
        if isinstance(from_level, str):
            try:
                from_level = MemoryLevel(from_level)
            except ValueError:
                from_level = MemoryLevel.EPISODIC
        db = await self._conn()
        cur = await db.execute(
            "SELECT * FROM nodes WHERE level=? AND importance>=0.8", (from_level.value,)
        )
        rows = await cur.fetchall()
        promoted = 0
        for row in rows:
            summary = f"[CONSOLIDATED] {row['content'][:240]}"
            emb = _simple_embed(summary, self.embed_dim)
            sid = str(uuid.uuid4())
            meta = json.loads(row["metadata"])
            meta["source_ids"] = [row["id"]]
            await db.execute(
                "INSERT INTO nodes (id, level, content, embedding, metadata, created_at, importance, agent_id, session_id) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (sid, MemoryLevel.SEMANTIC.value, summary, json.dumps(emb), json.dumps(meta),
                 time.time(), row["importance"], row["agent_id"], None),
            )
            await db.execute(
                "INSERT OR IGNORE INTO edges (graph_kind, src, dst) VALUES (?,?,?)",
                (GraphKind.SEMANTIC.value, sid, row["id"]),
            )
            await db.execute(
                "INSERT OR IGNORE INTO edges (graph_kind, src, dst) VALUES (?,?,?)",
                (GraphKind.CAUSAL.value, sid, row["id"]),
            )
            promoted += 1
        await db.commit()
        return promoted

    async def stats(self) -> dict[str, Any]:
        db = await self._conn()
        by_level = {l.value: 0 for l in MemoryLevel}
        cur = await db.execute("SELECT level, COUNT(*) AS c FROM nodes GROUP BY level")
        for row in await cur.fetchall():
            by_level[row["level"]] = row["c"]
        edge_counts = {}
        for gk in GraphKind:
            cur = await db.execute(
                "SELECT COUNT(*) AS c FROM edges WHERE graph_kind=?", (gk.value,)
            )
            edge_counts[gk.value] = (await cur.fetchone())["c"]
        cur = await db.execute("SELECT COUNT(*) AS c FROM nodes")
        total = (await cur.fetchone())["c"]
        cur = await db.execute("SELECT COUNT(DISTINCT entity_key) AS c FROM entities")
        ents = (await cur.fetchone())["c"]
        return {
            "backend": "sqlite", "db_path": self.db_path, "nodes": total,
            "by_level": by_level, "edges": edge_counts, "entities_indexed": ents,
        }

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None


def create_memory(backend: str = "memory", db_path: str | Path = "yodmcp_memory.db", embed_dim: int = 64) -> Any:
    if backend in ("sqlite", "durable"):
        return DurableMultiGraphMemory(db_path=db_path, embed_dim=embed_dim)
    from yodmcp.memory.multigraph import MultiGraphMemory
    return MultiGraphMemory(embed_dim=embed_dim)
