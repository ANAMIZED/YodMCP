# Changelog

## 0.5.0-dev (production-prep)

### Added
- **Auth foundation (P0.1)**: `YODMCP_API_KEY` / `YODMCP_API_KEYS` protect API routes via Bearer or `X-API-Key`. Health remains open. See `src/yodmcp/security/auth.py`.
- **Durable tasks & metering (P0.2)**: `YODMCP_TASKS_BACKEND=sqlite` and `YODMCP_METER_BACKEND=sqlite` (or shared `YODMCP_SYSTEM_DB`).
- **Docker harden**: non-root user (uid 10001), `HEALTHCHECK` on `/health`, system DB env defaults.
- **Billing webhook stub**: `POST /api/billing/webhook` (signature + entitlement activation still TODO).
- **docs/PRODUCTION.md**: full P0–P3 roadmap and production definition.

### Notes
Still **not production-ready** for public traffic or paid tenants until full Stripe entitlement store, request-scoped tenants, OTLP, and MCP protocol CI land. Position as self-hosted beta.

## 0.4.0

- Initial public prototype: MCP surfaces, multi-graph memory (memory/sqlite), soft quotas, A2A card + message, skills, attestation (software/simulated_tee), OTEL console, verify_e2e.
