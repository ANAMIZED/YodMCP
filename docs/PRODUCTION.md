# YodMCP Production & Multi-Tenant SaaS Roadmap

**Status (2026-08-18, `production-prep`):** Minimal production definition **and** core multi-tenant SaaS polish are implemented and under test. Remaining items are distributed scale, policy-as-code bundles, and PyPI stable release.

---

## Multi-tenant SaaS polish — checklist

| Capability | Status |
|------------|--------|
| Auth on API + A2A + MCP HTTP | **Done** |
| Request-scoped tenant (`X-YodMCP-Tenant`) | **Done** |
| Durable shared system DB (tasks, meter, entitlements, audit) | **Done** |
| Stripe webhook → plan entitlement | **Done** |
| Rate limiting (in-process) | **Done** (Redis for multi-replica still open) |
| HITL queue + approve/deny API | **Done** (fail-closed soft; park-until-approve optional next) |
| Tenant tool allow/deny lists | **Done** |
| Input size validation | **Done** |
| Structured JSON logs + request/tenant IDs | **Done** |
| OTEL version + optional OTLP endpoint | **Done** (exporter package optional) |
| `/health` + `/ready` | **Done** |
| Hardened Docker non-root | **Done** |
| CI dependency audit / freeze SBOM | **Done** (best-effort) |
| MCP stdio/HTTP **client** contract tests | **Partial** — substrate + SaaS tests; dedicated client harness still open |
| Policy-as-code (OPA/Cedar) signed bundles | **Open** |
| Distributed rate limits / multi-region | **Open** |
| PyPI `0.5.0` stable publish | **Open** |
| Real embeddings / TEE | **Open** (honest stubs today) |

---

## Operator quick start (SaaS-style)

```bash
export YODMCP_API_KEY=change-me
export YODMCP_LOG_FORMAT=json
export YODMCP_MEMORY_BACKEND=sqlite
export YODMCP_SYSTEM_DB=./data/system.db
export YODMCP_TASKS_BACKEND=sqlite
export YODMCP_METER_BACKEND=sqlite
export YODMCP_AUDIT_BACKEND=sqlite
# optional: STRIPE_*, OTEL_EXPORTER_OTLP_ENDPOINT, YODMCP_HITL_FAIL_CLOSED=true

pip install -e ".[dev]"
yodmcp-api --port 8080

curl -s -H "X-API-Key: change-me" -H "X-YodMCP-Tenant: acme" localhost:8080/api/skills
curl -s -H "X-API-Key: change-me" localhost:8080/api/hitl/pending
curl -s localhost:8080/ready
```

MCP HTTP with auth:

```bash
YODMCP_API_KEY=change-me yodmcp --http --port 8000
# clients must send Authorization: Bearer change-me
```

---

## What “full multi-tenant SaaS” still means after this branch

1. **Horizontal scale** — Redis rate limits, Postgres instead of SQLite, sticky or shared session state  
2. **Policy-as-code** — OPA/Cedar bundles with signatures, not only in-process allowlists  
3. **HITL park** — block high-risk tools until approved (true fail-closed execution path)  
4. **MCP client CI** — automated initialize → list_tools → call_tool over stdio and HTTP  
5. **PyPI + versioned releases** — `pip install yodmcp` without cloning  
6. **Control plane UI** — replace or delete legacy `frontend/dashboard.py`  

Until (1)–(5) ship, market as **self-hosted multi-tenant beta**, not hyperscale SaaS.

See also architecture notes in `docs/ARCHITECTURE.md`.
