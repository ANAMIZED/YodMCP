# YodMCP Architecture

## Layers

1. **Transport** — stdio, Streamable HTTP (MCP), FastAPI (API/A2A)
2. **Protocol** — MCP tools/resources, A2A card + message/tasks
3. **Domain** — memory, tasks, skills, cache, policy, attestation, billing
4. **Infrastructure** — SQLite, OTEL, audit log, usage meter

## Monetization plane

- Plan catalog (free/pro/enterprise)
- UsageMeter for tool_call / memory_write / task_create
- BillingService soft quotas in tool gate
- Stripe Checkout stub at `/api/billing/checkout`
