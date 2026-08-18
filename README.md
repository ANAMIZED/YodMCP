# YodMCP — Ultimate Autonomous MCP Server (v0.2.0)

Production-oriented **Agent Operating System** built on **MCP 2026-07-28**.

## Completed substrate (exhaustive)

| Capability | Status |
|------------|--------|
| MCP 2026-07-28 core (stateless, Streamable HTTP + stdio) | ✅ |
| Proper DI via lifespan + contextvars | ✅ |
| Multi-graph memory (semantic / temporal / causal / entity) + embedding retrieval | ✅ |
| Semantic + plan caching layer | ✅ |
| cMCP-style TRACE claim attestation (HMAC software mode) | ✅ |
| Tasks extension hooks (`tasks_*` tools, CreateTaskResult shape) | ✅ |
| Skills-over-MCP (`skills://` resources + `skills_list`) | ✅ |
| Native A2A surface (Agent Card + message handler) | ✅ |
| Full OpenTelemetry trajectory spans on tool calls | ✅ |
| Policy engine + Decision System of Record (audit) | ✅ |
| Governance dashboard (FastAPI) | ✅ |
| Unit + E2E verification | ✅ 8 tests + E2E script green |

## Tools (17)

`memory_write` `memory_read` `memory_consolidate` `memory_stats`  
`tasks_create` `tasks_get` `tasks_cancel` `tasks_stats`  
`skills_list` `a2a_card`  
`plan_cache_get` `plan_cache_put` `cache_stats`  
`attestation_recent` `audit_recent`  
`discover_capabilities` `echo`

## Resources

- `skills://{name}` — Agent Skills (SKILL.md style)
- `yodmcp://agent-card` — A2A Agent Card JSON

## Quick start

```bash
pip install -e .
python -m yodmcp                  # stdio
python -m yodmcp --http --port 8000
python -m yodmcp --trace          # OTEL console spans
uvicorn yodmcp.frontend.dashboard:app --port 8080
```

## Verify

```bash
PYTHONPATH=src pytest tests/ -v
PYTHONPATH=src python scripts/verify_e2e.py
```

## Architecture

```
Transport (stdio | Streamable HTTP)
  → Protocol (mcp SDK v2)
  → Lifespan DI + contextvars
  → Tools / Resources / Skills / A2A
  → MultiGraphMemory | TaskManager | CacheLayer | Attestation | Policy | Audit
  → OpenTelemetry spans
```

## License

Apache-2.0
