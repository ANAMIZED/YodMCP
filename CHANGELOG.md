# Changelog

## 0.5.0-dev (TDQS + CRUD completeness)

### Added
- MCP tool annotations (`readOnlyHint` / `destructiveHint` / `idempotentHint` / `openWorldHint`) on every core tool
- Per-parameter `Field(description=...)` coverage (100% of input schema properties)
- Agent-facing tool descriptions: verb + resource, when/when-not, named sibling tools, auth/quota/HITL side effects
- CRUD completeness: `memory_delete`, `plan_cache_delete`, `tasks_list`, `tasks_update`
- `tests/test_tdqs_tools.py` + E2E checks that descriptions stay ≥80 chars and annotated

### Notes
- Glama Tool Definition Quality is scored from a **GitHub Release** snapshot. Tag `v0.5.0` and click **Sync Server** on Glama after CI is green.
- Existing tool **names** are unchanged (`echo`, `discover_capabilities` included) so clients do not break.

## 0.5.0-dev (production-prep / multi-tenant SaaS polish)

### Added
- **Request-scoped tenant** (`X-YodMCP-Tenant` + ContextVar) wired into auth, gate, billing
- **HITL queue** + `/api/hitl/pending` and `/api/hitl/{id}/decide`
- **Tenant policy allow/deny lists** + `/api/policy/allowlist|denylist`
- **Input validation** size limits on tool args / memory content
- **Structured JSON logging** (`YODMCP_LOG_FORMAT=json`) with tenant + request_id
- **MCP Streamable HTTP API-key auth** when keys configured
- **Rate limiting** middleware on API/A2A
- Durable tasks, meter, entitlements, audit index (SQLite)
- Stripe webhook → entitlement activation
- Hardened Docker (non-root, HEALTHCHECK), `/ready` probe
- CI: pip-audit + freeze SBOM artifact; SaaS test module

### Notes
- Embeddings remain toy cosine; do not market as production semantic search
- TEE nitro/sgx remain simulated unless real providers are wired
- `frontend/dashboard.py` is **legacy** (uses `core.runtime`); prefer API/HITL endpoints
- Full OPA/Cedar policy-as-code and distributed rate limits are still roadmap

## 0.4.0

- Initial public prototype: MCP surfaces, multi-graph memory, soft quotas, A2A, skills, attestation stubs, OTEL console, verify_e2e
