# Changelog

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
