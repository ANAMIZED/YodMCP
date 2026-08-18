# YodMCP — Ultimate Autonomous MCP Server (v0.3.0)

Production-oriented **Agent Operating System** built on **MCP 2026-07-28**.

## Substrate (v0.3)

| Capability | Status |
|------------|--------|
| MCP 2026-07-28 core (stdio + Streamable HTTP) | ✅ |
| Lifespan DI + contextvars | ✅ |
| Multi-graph memory (in-memory **or SQLite durable**) | ✅ |
| Semantic + plan caching | ✅ |
| cMCP TRACE attestation (`software` / `simulated_tee` / Nitro+SGX stubs) | ✅ |
| Tasks extension hooks | ✅ |
| Skills-over-MCP resources | ✅ |
| Full A2A HTTP surface (card, message, tasks) | ✅ |
| OpenTelemetry tool spans | ✅ |
| Policy + Decision System of Record | ✅ |
| Governance dashboard | ✅ |
| GitHub Actions CI | ✅ |

## Quick start

```bash
pip install -e ".[dev]"

# stdio MCP
python -m yodmcp

# Streamable HTTP MCP
python -m yodmcp --http --port 8000

# A2A HTTP surface
python -m yodmcp.a2a.server --port 9000

# Durable memory + simulated TEE
YODMCP_MEMORY_BACKEND=sqlite YODMCP_MEMORY_DB=./yod.db \
YODMCP_ATTEST_MODE=simulated_tee \
  python -m yodmcp --http
```

## Environment

| Variable | Values | Default |
|----------|--------|--------|
| `YODMCP_MEMORY_BACKEND` | `memory` \| `sqlite` | `memory` |
| `YODMCP_MEMORY_DB` | path | `yodmcp_memory.db` |
| `YODMCP_ATTEST_MODE` | `software` \| `simulated_tee` \| `tee_nitro` \| `tee_sgx` | `software` |

## Verify

```bash
PYTHONPATH=src pytest tests/ -v
PYTHONPATH=src python scripts/verify_e2e.py
```

## License

Apache-2.0
