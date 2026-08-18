"""SQLite DDL for durable multi-graph memory."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    level TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL,
    importance REAL NOT NULL DEFAULT 0.5,
    agent_id TEXT,
    session_id TEXT
);
CREATE TABLE IF NOT EXISTS edges (
    graph_kind TEXT NOT NULL,
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    PRIMARY KEY (graph_kind, src, dst)
);
CREATE TABLE IF NOT EXISTS entities (
    entity_key TEXT NOT NULL,
    node_id TEXT NOT NULL,
    PRIMARY KEY (entity_key, node_id)
);
CREATE INDEX IF NOT EXISTS idx_nodes_level ON nodes(level);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS idx_entities_key ON entities(entity_key);
"""
