# YodMCP — Agent Operating System

[![CI](https://github.com/ANAMIZED/YodMCP/actions/workflows/ci.yml/badge.svg)](https://github.com/ANAMIZED/YodMCP/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.5.0-blue.svg)](https://github.com/ANAMIZED/YodMCP)
[![YodMCP MCP server](https://glama.ai/mcp/servers/ANAMIZED/YodMCP/badges/score.svg)](https://glama.ai/mcp/servers/ANAMIZED/YodMCP/score)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-2026--07--28-purple.svg)](https://modelcontextprotocol.io/)

**YodMCP** is a production-oriented **Agent Operating System** kernel on MCP: multi-graph memory, Tasks, Skills, A2A, attestation (software / simulated TEE), OpenTelemetry, and plan-based monetization.

This README is written so a senior engineer with **only this file + the source tree** can install, deploy every surface, exercise features, and verify end-to-end.

## FOUNDRY mapping

FOUNDRY (host-owned trust and memory for long-horizon agent swarms) separates untrusted proposal generation from host-owned verification + established-facts registry.

YodMCP is that registry in production: agents call `memory_write`; promotion to semantic memory is gated; the host owns the evaluator. Full note: [`docs/FOUNDRY.md`](docs/FOUNDRY.md).

### First dollar

Meters first. Seat if the loop holds.

| Unit | Stripe | x402 |
|------|--------|------|
| OpenGOS Search $0.40 | [Buy](https://buy.stripe.com/7sY8wQ5EW3iZ5xb5Re43S06) | `GET /v1/search` |
| OpenGOS Draft $2.50 | [Buy](https://buy.stripe.com/9B69AUd7o7zf2kZ2F243S03) | `GET /v1/draft` |
| Agentic OS Cycle $0.75 | [Buy](https://buy.stripe.com/3cI14o8R8dXD3p3frO43S04) | `GET /v1/cycle` |
| **YodMCP Pro $49/mo** | [Subscribe](https://buy.stripe.com/bJe3cw0kCaLrbVz1AY43S09) | USDC |

x402 rail: [x402-cloudflare-starter](https://github.com/ANAMIZED/x402-cloudflare-starter). Desk sync: https://anamized.grok.me

## Package surfaces

| Surface | Command | Default | Purpose |
|---------|---------|---------|
| **MCP** | `yodmcp` | stdio | Local MCP clients (Cursor, Claude Desktop, etc.) |
| **MCP HTTP** | `yodmcp --http --port 8000` | `:8000/mcp` | Remote / Streamable HTTP MCP |
| **API** | `yodmcp-api --port 8080` | `:8080` | REST health, memory, audit, skills, billing |
| **A2A** | `yodmcp-a2a --port 9000` | `:9000` | Agent Card, message, tasks |
| **SDK** | `from yodmcp.sdk import YodClient` | HTTP client | Thin client for the API |
| **Skills** | `skills://` + `skills/*/SKILL.md` | auto-loaded | Agent Skills as MCP resources |
| **Verify** | `pytest` + `scripts/verify_e2e.py` | CI | Substrate + durable + TEE modes |

## Requirements

- Python **3.11 or 3.12** (3.10+ declared; CI covers 3.11/3.12)
- Optional: Docker for multi-service compose

## Install

```bash
git clone https://github.com/ANAMIZED/YodMCP.git
cd YodMCP
python -m venv .venv && source .venv.bin/activate   # recommended
pip install -e ".[dev]"
```

Copy environment defaults:

```bash
cp .env.example .env
```

| Variable | Default | Meaning |
|----------|---------|---------|
| `YODMCP_MEMORY_BACKEND` | `memory` | `memory` \| `sqlite` \| `durable` |
| `YODMCP_MEMORY_DB` | `./data/yodmcp_memory.db` | SQLite path when durable |
| `YODMCP_ATTEST_MODE` | `software` | `software` \| `simulated_tee` \| `nitro` \| `sgx` |
| `YODMCP_PLAN` | `free` | `free` \| `pro` \| `enterprise` |
| `YODMCP_TENANT_ID` | `default` | Soft quota tenant key |
| `YODMCP_SKILLS_DIR` | *(auto)* | Override skills root |
| `STRIPE_SECRET_KEY` | unset | Enables live Checkout Sessions |

> **TEE honesty:** `nitro` / `sgx` are provider hooks; without real TEE libraries they fall back to simulated claims. Prefer `software` or `simulated_tee` for local verify.

## Quick start (local)

```bash
# 1) MCP over stdio (attach from an MCP client)
yodmcp

# 2) REST API
yodmcp-api --port 8080
# curl http://127.0.0.1:8080/health

# 3) A2A
yodmcp-a2a --port 9000
# curl http://127.0.0.1:9000/a2a/card
```

### MCP client configuration (stdio)

**Cursor** — project `.cursor/mcp.json` or global MCP settings:

```json
{
  "mcpServers": {
    "yodmcp": {
      "command": "yodmcp",
      "args": [],
      "env": {
        "YODMCP_MEMORY_BACKEND": "memory",
        "YODMCP_PLAN": "free",
        "YODMCP_ATTEST_MODE": "software"
      }
    }
  }
}
```

If `yodmcp` is not on `PATH`, use the module form:

```json
{
  "mcpServers": {
    "yodmcp": {
      "command": "python",
      "args": ["-m", "yodmcp"],
      "cwd": "/absolute/path/to/YodMCP",
      "env": {
        "PYTHONPATH": "src",
        "YODMCP_MEMORY_BACKEND": "memory"
      }
    }
  }
}
```

**Claude Desktop** — same shape under `mcpServers` in `claude_desktop_config.json`.

**Streamable HTTP MCP** (remote clients that support URL transport):

```bash
yodmcp --http --host 0.0.0.0 --port 8000
# endpoint: http://127.0.0.1:8000/mcp
```

## Docker

```bash
docker compose up --build
# API  :8080  A2A :9000  MCP HTTP :8000
```

Single API container:

```bash
docker build -t yodmcp .
docker run --rm -p 8080:8080 -e YODMCP_PLAN=free yodmcp
```

## Verify end-to-end (no external accounts required)

```bash
# Unit + integration
YODMCP_MEMORY_BACKEND=memory YODMCP_ATTEST_MODE=software \
  PYTHONPATH=src pytest tests/ -v

# Durable SQLite + simulated TEE
YODMCP_MEMORY_BACKEND=sqlite YODMCP_MEMORY_DB=/tmp/yodmcp.db \
  YODMCP_ATTEST_MODE=simulated_tee \
  PYTHONPATH=src pytest tests/ -v

# Exhaustive substrate script
PYTHONPATH=src python scripts/verify_e2e.py
```

Expected: all tests green; script prints `ALL E2E CHECKS PASSED`.

API smoke (with `yodmcp-api` running):

```bash
curl -s http://127.0.0.1:8080/health
curl -s http://127.0.0.1:8080/api/skills
curl -s http://127.0.0.1:8080/api/billing/plans
curl -s http://127.0.0.1:8080/api/billing/status
```

SDK:

```bash
python examples/sdk_quickstart.py   # requires API on :8080
```

## MCP tools (catalog)

| Tool | Description |
|------|-------------|
| `memory_write` | Insert one memory node (facts/decisions). Not for plans (`plan_cache_put`). |
| `memory_read` | Retrieve nodes by similarity or `item_id`. Not for plans (`plan_cache_get`). |
| `memory_delete` | Hard-delete one node + incident edges. Idempotent if missing. |
| `memory_consolidate` | Promote importance ≥ 0.8 into semantic summaries. Does not delete sources. |
| `memory_stats` | Node/edge/entity counts. Not content (`memory_read`). |
| `tasks_create` | Create a durable pending task handle. |
| `tasks_get` | Fetch one handle by id. |
| `tasks_list` | List recent handles, optional status filter. |
| `tasks_update` | Patch status/progress/result. Not cancel (`tasks_cancel`). |
| `tasks_cancel` | Mark a handle cancelled (kernel state only). |
| `tasks_stats` | Counts by status. Not a listing (`tasks_list`). |
| `skills_list` | List Agent Skills + `skills://` URIs (bodies are resources). |
| `a2a_card` | A2A Agent Card JSON. Not the MCP catalog (`discover_capabilities`). |
| `plan_cache_get` / `plan_cache_put` / `plan_cache_delete` | Semantic plan templates. Not memory facts. |
| `cache_stats` | In-process cache entry/hit totals. |
| `attestation_recent` | TRACE-style provenance claims. Not the audit trail (`audit_recent`). |
| `audit_recent` | Policy/tool Decision-System-of-Record events. |
| `discover_capabilities` | List MCP tools + loaded skills. |
| `echo` | Liveness probe (`message` echoed + version). |

Resources:

- `skills://{name}` — skill markdown body
- `yodmcp://agent-card` — agent card JSON

## Skills

Built-in skills are always registered. **Disk skills** under `skills/*/SKILL.md` are loaded automatically (override via `YODMCP_SKILLS_DIR`). Repo ships:

- `memory-hygiene`, `safe-tool-use`, `funding-usdc`, `repo-bootstrap`
- Plus built-in `long-horizon-planning`

## Monetization

| Plan | $/mo | Tool calls/day | Durable | TEE |
|------|------|----------------|---------|-----|
| Free | 0 | 500 | — | — |
| Pro | 49 | 50k | yes | simulated |
| Enterprise | 499 | unlimited | yes | Nitro/SGX hooks |

- Soft quotas via tool gate; upgrade messaging on exhaustion
- Live Stripe Checkout when `STRIPE_SECRET_KEY` is set; otherwise checkout returns `status: payment_link`

| Option | Link |
|------|------|
| **YodMCP Pro** | https://buy.stripe.com/bJe3cw0kCaLrbVz1AY43S09 |
| **YodMCP Enterprise** | https://buy.stripe.com/9B68wQ1oGcTz9NrfrO43S0a |
| **Agentic OS Kernel Support** ($99) | https://buy.stripe.com/bJecN63wObPv6Bf7Zm43S02 |
| **Public Goods Support** ($25) | https://donate.stripe.com/00w5kE3wOg5L8Jn2F243S00 |
| **Agentic Systems Consulting Hour** ($199) | https://buy.stripe.com/dRmaEYgjA9Hnf7LdjG43S0b |

### Non-custodial USDC (preferred for agents)

| Network | Address |
|---------|---------|
| **Base** | `0xD3d0E9eDAe3Ac7bb199a8EAA761BdA423b878438` |
| **Ethereum** | `0xD3d0E9eDAe3Ac7bb199a8EAA761BdA423b878438` |
| **Solana** | `ETQwWf19axArsY493UfC6bxe2BmEzmzvCb58PPnC38A` |

Canonical: [`funding/addresses.json`](funding/addresses.json)

## Project layout

```
src/yodmcp/          # package (src-layout)
  core/              # server, substrate, context
  memory/            # in-memory + durable SQLite multi-graph
  tools/             # MCP tool registration + gate
  tasks/ skills/ cache/ security/ observability/ monetization/
  api/ a2a/ sdk/
skills/*/SKILL.md    # portable Agent Skills (loaded at runtime)
scripts/verify_e2e.py
tests/
docs/ARCHITECTURE.md
docs/FOUNDRY.md
docs/TDQS.md
```

## Known limitations (read before claiming production)

1. **Plan cache** uses lightweight embeddings; default similarity threshold is **0.68** (not production vector search).
2. **TEE** Nitro/SGX are hooks with simulated fallback unless you wire real providers.
3. **Frontend** `src/yodmcp/frontend/dashboard.py` still uses legacy `core.runtime` and is **not** the primary control plane — use `yodmcp-api` + MCP tools.
4. **Quotas** are soft (in-process meter); not a distributed billing ledger.
5. Processes do **not** share in-memory state; use `sqlite` backend + shared volume for multi-process durability.

## License

Apache-2.0 · [CONTRIBUTING](CONTRIBUTING.md) · [CHANGELOG](CHANGELOG.md) · [ARCHITECTURE](docs/ARCHITECTURE.md) · [FOUNDRY](docs/FOUNDRY.md) · [TDQS](docs/TDQS.md) · [AGENTS.md](AGENTS.md)
