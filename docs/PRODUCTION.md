# YodMCP Production Readiness Roadmap

**Status (production-prep branch, 2026-08-18):** Minimal production definition items for *self-hosted paying users on a VPS* are implemented and tested. Full multi-tenant SaaS / Enterprise TEE still requires P1–P2 work. Position as **self-hosted beta with auth + durable state + billing webhooks** until PyPI + OTLP exporter package + MCP protocol client CI are published.

---

## Minimal “production-ready” definition — checklist

| # | Requirement | Status |
|---|-------------|--------|
| 1 | Auth on all HTTP surfaces (API + A2A) | **Done** — API key / Bearer; health & agent card open |
| 2 | Shared durable DB for memory + tasks + meter + entitlements + audit | **Done** — SQLite system DB (`YODMCP_SYSTEM_DB`) |
| 3 | Stripe webhook → plan activation | **Done** — entitlement store + `/api/billing/webhook` |
| 4 | OTLP metrics/traces + structured path | **Partial** — OTEL resource version fixed; OTLP exporter when `OTEL_EXPORTER_OTLP_ENDPOINT` set (install `opentelemetry-exporter-otlp-proto-http`) |
| 5 | Hardened Docker + health/ready | **Done** — non-root, HEALTHCHECK, `/ready` probes memory/tasks |
| 6 | MCP protocol CI smoke tests | **Partial** — substrate + auth/durable tests in CI; full stdio/HTTP client contract still TODO |
| 7 | Semantic search honesty | **Done** — toy embeddings; do not claim production semantic search |

**26 unit/integration tests + verify_e2e.py green.**

---

## P0 — Must have before any real deploy (implemented)

### 1. AuthN / AuthZ on every network surface
- API key / JWT-style Bearer on `yodmcp-api` and `yodmcp-a2a` (protected routes)
- Per-request tenant via `X-YodMCP-Tenant` when authenticated
- Rate limiting middleware (in-process token bucket; Redis later for multi-replica)
- Health / agent-card / Stripe webhook remain open by design

### 2. Durable state that survives process restart
| Component | Backend |
|-----------|--------|
| Tasks | SQLite (`YODMCP_TASKS_BACKEND=sqlite`) |
| Usage meter | SQLite |
| Audit log | JSONL + optional SQLite index |
| Entitlements | SQLite |
| Memory | existing sqlite/durable |

### 3. Real billing lifecycle
- Stripe Checkout (when `STRIPE_SECRET_KEY` set) or payment links
- Webhook → `EntitlementStore.activate` / deactivate
- Plan refresh from entitlement on status checks

### 4. Production packaging & config
- Non-root Docker user, HEALTHCHECK, `/ready`
- `.env.example` documents all knobs
- Version `0.5.0-dev`

---

## P1 — Required for “serious” multi-tenant SaaS (remaining)

- Full OTLP package in default deps + structured JSON logs with request IDs
- Policy-as-code (OPA/Cedar) + real HITL approval workflow
- Auth on Streamable HTTP MCP transport
- Dependency scanning + SBOM in CI
- MCP stdio/HTTP **client** contract tests in CI

## P2 / P3 — Advertised features & polish (remaining)

- Real embeddings / vector DB if claiming semantic memory in prod marketing
- Real Nitro/SGX or honest “simulated_tee only” packaging
- Durable worker pool for Tasks
- Control plane UI wired to substrate or removed
- PyPI release + CHANGELOG discipline for stable tags
- Runbooks, load numbers, multi-region

---

## How to run production-style locally

```bash
export YODMCP_API_KEY=change-me
export YODMCP_MEMORY_BACKEND=sqlite
export YODMCP_SYSTEM_DB=./data/system.db
export YODMCP_TASKS_BACKEND=sqlite
export YODMCP_METER_BACKEND=sqlite
export YODMCP_AUDIT_BACKEND=sqlite
export YODMCP_PLAN=free
# optional: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, OTEL_EXPORTER_OTLP_ENDPOINT

pip install -e ".[dev]"
yodmcp-api --port 8080
# curl -H "X-API-Key: change-me" localhost:8080/api/skills
# curl localhost:8080/ready
```

**Bottom line:** identity, durable multi-tenant state, money lifecycle, and ops packaging foundations are in place and verified. Remaining work is SaaS scale (distributed rate limits, OTLP packaging, MCP client CI, policy-as-code) and honesty around embeddings/TEE. Merge `production-prep` when ready, then tag `0.5.0` after PyPI + one more CI pass.
