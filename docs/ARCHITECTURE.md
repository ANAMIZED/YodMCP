# YodMCP Architecture

## Layers

1. **Transport** — stdio, Streamable HTTP (MCP), FastAPI (API / A2A)
2. **Protocol** — MCP tools + `skills://` resources, A2A agent card + message/tasks
3. **Domain** — multi-graph memory, tasks, skills, semantic/plan cache, policy, attestation, billing
4. **Infrastructure** — in-memory or SQLite, OpenTelemetry, audit log, usage meter

## Process model

| Process | Command | Default port |
|---------|---------|--------------|
| MCP kernel | `yodmcp` / `yodmcp --http` | stdio or 8000 |
| REST API + billing | `yodmcp-api` | 8080 |
| A2A surface | `yodmcp-a2a` | 9000 |

Shared substrate is initialized per process via `init_substrate()` + contextvars (no shared DB connection across processes unless SQLite path is shared).

## Monetization plane

- Plan catalog: free / pro / enterprise (`YODMCP_PLAN`)
- UsageMeter for `tool_call` / `memory_write` / `task_create`
- Soft quotas enforced in tool gate (`_gated`)
- Checkout: live Stripe Session if `STRIPE_SECRET_KEY` set; else static payment links

## Skills

- Built-ins always registered
- Disk skills loaded from `skills/*/SKILL.md` (or `YODMCP_SKILLS_DIR`)
- Exposed as MCP resources under `skills://{name}`

## Honesty notes

- TEE modes `nitro` / `sgx` are hooks with simulated fallback unless real providers are wired
- Plan cache uses lightweight bag-of-bytes embeddings; threshold defaults to 0.68
- Frontend `src/yodmcp/frontend/dashboard.py` still uses legacy `core.runtime` and is not the primary control plane
