# YodMCP — Ultimate Autonomous MCP Server (v0.3.0)

Production-oriented **Agent Operating System** built on **MCP 2026-07-28**.

## Capabilities

| Capability | Status |
|------------|--------|
| MCP 2026-07-28 core (stateless, Streamable HTTP + stdio) | ✅ |
| Proper DI via lifespan + contextvars | ✅ |
| Multi-graph memory (semantic / temporal / causal / entity) + embeddings | ✅ |
| **Durable SQLite memory** (vector blobs + edge tables, restart-safe) | ✅ |
| Semantic + plan caching layer | ✅ |
| cMCP TRACE attestation — software HMAC | ✅ |
| **Simulated TEE** (ECDSA P-256 + measurement) | ✅ |
| **Nitro / SGX provider stubs** with safe local fallback | ✅ |
| Tasks extension hooks | ✅ |
| Skills-over-MCP (`skills://` resources) | ✅ |
| Native A2A Agent Card + **fuller HTTP A2A server** | ✅ |
| Full OpenTelemetry trajectory spans | ✅ |
| Policy engine + Decision System of Record | ✅ |
| Governance dashboard (FastAPI) | ✅ |
| **GitHub Actions CI** (3.11 / 3.12, memory + sqlite + TEE) | ✅ |
| Unit + E2E verification | ✅ 17 tests |

## Quick start

```bash
pip install -e ".[dev]"

# stdio MCP
python -m yodmcp

# Streamable HTTP MCP
python -m yodmcp --http --port 8000

# Durable memory + simulated TEE
YODMCP_MEMORY_BACKEND=sqlite YODMCP_MEMORY_DB=./data.db \
YODMCP_ATTEST_MODE=simulated_tee python -m yodmcp --http

# A2A HTTP surface
python -m yodmcp.a2a.server --port 9000

# Governance UI
uvicorn yodmcp.frontend.dashboard:app --port 8080
```

## Environment

| Variable | Values | Default |
|----------|--------|---------|
| `YODMCP_MEMORY_BACKEND` | `memory` \| `sqlite` | `memory` |
| `YODMCP_MEMORY_DB` | path | `yodmcp_memory.db` |
| `YODMCP_ATTEST_MODE` | `software` \| `simulated_tee` \| `tee_nitro` \| `tee_sgx` | `software` |
| `YODMCP_ATTEST_SECRET` | HMAC secret (software mode) | dev secret |
| `YODMCP_TEE_KEY_PEM` | PEM private key (simulated TEE) | ephemeral |

## Tools (17)

`memory_write` `memory_read` `memory_consolidate` `memory_stats`  
`tasks_create` `tasks_get` `tasks_cancel` `tasks_stats`  
`skills_list` `a2a_card`  
`plan_cache_get` `plan_cache_put` `cache_stats`  
`attestation_recent` `audit_recent`  
`discover_capabilities` `echo`

## A2A endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/a2a/.well-known/agent.json` | Agent Card |
| GET | `/a2a/card` | Agent Card alias |
| POST | `/a2a/message` | message/send |
| POST | `/a2a/tasks` | create long-running task |
| GET | `/a2a/tasks/{id}` | poll task |
| GET | `/a2a/health` | liveness |

## Verify

```bash
PYTHONPATH=src pytest tests/ -v
PYTHONPATH=src python scripts/verify_e2e.py

YODMCP_MEMORY_BACKEND=sqlite YODMCP_ATTEST_MODE=simulated_tee \
  PYTHONPATH=src python scripts/verify_e2e.py
```

## License

Apache-2.0
