# YodMCP Production Readiness Roadmap

**YodMCP is a working prototype / early beta kernel**, not production deployment-ready yet. Cold-start install and substrate verify work; the remaining work is what turns “runs on a laptop” into “you can put customer traffic and money on it.”

Below is the concrete build list, ordered by what actually blocks production. This document tracks the path from v0.4 prototype to production-capable releases.

---

## P0 — Must have before any real deploy

### 1. AuthN / AuthZ on every network surface
Today API and A2A are open (`CORS *`, no API keys, no tenants on requests).

**Build:**
- API key / JWT (or mTLS) on `yodmcp-api` and `yodmcp-a2a`
- Per-request tenant binding (`YODMCP_TENANT_ID` is env-global, not request-scoped)
- Auth on Streamable HTTP MCP (`yodmcp --http`)
- Rate limiting + abuse controls

Without this, exposing `:8080` / `:9000` / `:8000` is unsafe.

**Status (production-prep branch):** Basic API-key auth middleware added; tenant binding and rate limits still required.

### 2. Durable state that survives process restart
| Component | Current | Needed |
|-----------|---------|--------|
| Tasks | **in-memory** dict | SQLite/Postgres task store |
| Usage meter | **in-memory** | Persistent daily counters (DB) |
| Audit log | process-local + JSONL | Append-only durable log + DB index |
| Attestation claims | in-memory list | Durable claim store |
| Plan/exact cache | in-memory | Optional Redis / DB |

Only memory (with `sqlite` backend) is actually durable. Multi-replica or restart = lost tasks, quotas, audit.

**Status:** Durable TaskManager and UsageMeter backends added (SQLite); shared system DB recommended next.

### 3. Real billing lifecycle (not soft quotas + payment links)
**Build:**
- Stripe webhooks: checkout completed → activate plan for tenant
- Persist plan entitlement in DB (not just `YODMCP_PLAN` env)
- Enforce feature gates (`durable_memory`, `tee_attestation`) for real, not only soft tool-call limits
- Idempotent metering + invoice reconciliation
- Optional: USDC payment verification (on-chain or facilitator), not just static addresses in README

Until webhooks + entitlement store exist, Pro/Enterprise is marketing + a checkout URL.

**Status:** Webhook endpoint stub + entitlement table design; full activation flow pending.

### 4. Production packaging & config
**Build:**
- Publish to PyPI (`pip install yodmcp`) with locked deps (`uv.lock` / `requirements.txt`)
- Single process or proper multi-service deployment story (shared DB, not three disconnected substrates)
- Structured config (pydantic-settings from env + file), secrets via env/secret manager
- Non-root Docker user, healthchecks, resource limits
- `HEALTH`/`READY` probes that check DB connectivity

**Status:** Dockerfile hardened (non-root + HEALTHCHECK); compose still multi-process without shared identity.

---

## P1 — Required for “serious” multi-tenant SaaS

### 5. Observability that ops can use
OTEL today: console exporter only, service version still `0.1.0` in tracer resource.

**Build:**
- OTLP export (Grafana/Tempo/Datadog/Honeycomb)
- Metrics: tool latency, quota denials, error rates, memory size
- Structured JSON logs + request/tenant IDs
- Alerting baselines

### 6. Policy that is real policy
`PolicyEngine` is a hardcoded risk map; HITL is a flag with no approval workflow.

**Build:**
- Policy-as-code (OPA/Cedar) with versioned signed bundles
- Actual HITL path (queue + approve/deny API) or fail-closed for high-risk tools
- Tenant-scoped allowlists

### 7. Security hardening
**Build:**
- Rotate `YODMCP_ATTEST_SECRET` (default is `yodmcp-dev-secret`)
- Input validation / size limits on memory writes and tool args
- Secure SQLite (path permissions, optional encryption) or move to Postgres
- Dependency scanning + SBOM in CI
- No secrets in images; strip debug surfaces in prod

### 8. Protocol-level MCP E2E tests
Substrate tests pass; there is still no automated **stdio/HTTP MCP client** test (initialize → list_tools → call_tool).

**Build:**
- CI job that speaks MCP over stdio and Streamable HTTP
- Contract tests for tool schemas

---

## P2 — Make advertised features real (not simulated)

### 9. Memory / embeddings
Current: bag-of-bytes / toy cosine, dim ~64.

**Build (if you claim “semantic memory” in prod):**
- Real embedding model or external vector DB (pgvector, Qdrant, etc.)
- Migrations, backup/restore, retention/TTL policies
- Multi-tenant isolation at storage layer

### 10. TEE
Nitro/SGX are stubs that fall back to simulated ECDSA.

**Build only if Enterprise marketing depends on it:**
- Real Nitro NSM / SGX attestation integration
- Or drop “Nitro/SGX” from the plan table and sell simulated_tee honestly

### 11. Tasks as a real async runtime
TaskManager creates handles but does not own a durable worker pool or MCP Tasks wire protocol end-to-end.

**Build:**
- Durable queue + workers
- TTL expiry / cleanup
- Optional full MCP Tasks extension compliance

### 12. Control plane UI
`frontend/dashboard.py` is on legacy `core.runtime` and is not the real substrate.

**Build or delete:**
- Wire dashboard to substrate/API, or remove it so it cannot confuse operators

---

## P3 — Product / ops polish

| Item | Why |
|------|-----|
| PyPI + versioned releases + CHANGELOG discipline | Install without cloning |
| Runbooks: backup, restore, rotate keys, incident | Ops readiness |
| Load test / capacity numbers | Know when SQLite stops scaling |
| Multi-region / HA story | Only if you sell that |
| A2A full protocol compliance beyond card + message stub | If interop is a product claim |
| Skills marketplace (Pro feature flag) | Currently just local SKILL.md files |

---

## What you already have (do not rebuild)

- Installable package + console scripts  
- MCP tool surface + skills resources + disk skill loading  
- In-memory + SQLite multi-graph memory  
- Soft tool gate (policy + audit + quota + OTEL spans)  
- API / A2A / MCP HTTP entrypoints + compose  
- Unit/substrate tests + `verify_e2e.py`  
- Operational README for cold-start engineers  

That is a solid **v0.4 prototype foundation**, not a production control plane.

---

## Minimal “production-ready” definition for *this* project

If “production” means **you can run it for paying users on a VPS/K8s**:

1. Auth on all HTTP surfaces  
2. Shared durable DB for memory + tasks + meter + entitlements + audit  
3. Stripe webhook → plan activation  
4. OTLP metrics/traces + structured logs  
5. PyPI release + hardened Docker  
6. MCP protocol CI smoke tests  
7. Either real embeddings **or** stop implying production semantic search  

If “production” means **Enterprise TEE + multi-tenant Agent OS**, add P2 items 9–11 and real policy-as-code.

---

## Suggested build order (practical)

```text
Week 1–2  Auth + Postgres/SQLite durability for tasks/meter/audit/entitlements
Week 2–3  Stripe webhooks + plan enforcement
Week 3    OTLP + logging + Docker harden + health/ready
Week 4    MCP protocol CI + PyPI 0.5.0
Later     Embeddings, HITL workflow, real TEE (only if sold)
```

**Bottom line:** nothing major is “missing as a demo kernel.” What’s left is **identity, durable multi-tenant state, real money lifecycle, and ops-grade observability/packaging**. Until those exist, keep the product positioned as **prototype / self-hosted beta**, which the README’s honesty section already points toward.

See also the `production-prep` branch for initial Auth + durable task/meter foundations.
