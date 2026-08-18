# AGENTS.md — working on YodMCP

- Package layout is `src/yodmcp/` (src-layout).
- Tool calls go through `_gated` (policy + quota + audit + OTEL).
- Use lifespan + contextvars — no global singleton runtime.
- Run `pytest tests/ -v` and `scripts/verify_e2e.py` before claiming done.
- Monetization quotas are soft; Stripe is optional via env flags.
- **USDC addresses are canonical** — copy from `funding/addresses.json` / server-os; never invent wallets.

## New repos

Run `skills/repo-bootstrap` + `scripts/bootstrap_repo_structure.sh` so USDC, FUNDING.yml, and package surfaces match server-os automatically.
