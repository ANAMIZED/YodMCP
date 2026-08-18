# YodMCP — Agent Operating System

[![CI](https://github.com/ANAMIZED/YodMCP/actions/workflows/ci.yml/badge.svg)](https://github.com/ANAMIZED/YodMCP/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.4.0-blue.svg)](https://github.com/ANAMIZED/YodMCP)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-2026--07--28-purple.svg)](https://modelcontextprotocol.io/)
[![A2A](https://img.shields.io/badge/A2A-ready-orange.svg)](https://github.com/ANAMIZED/YodMCP)

**YodMCP** is a production-oriented **Agent Operating System** kernel on **MCP 2026-07-28**: multi-graph memory, Tasks, Skills, A2A, TEE attestation, OpenTelemetry, and **plan-based monetization**.

## Package surfaces

| Surface | Entry | Description |
|---------|-------|-------------|
| **MCP** | `python -m yodmcp` / `yodmcp` | stdio / Streamable HTTP |
| **CLI** | `yodmcp` · `yodmcp-a2a` · `yodmcp-api` | Console scripts |
| **API** | `yodmcp-api --port 8080` | REST + OpenAPI + billing |
| **A2A** | `yodmcp-a2a --port 9000` | Agent Card, message, tasks |
| **SDK** | `from yodmcp.sdk import YodClient` | HTTP client |
| **Skills** | `skills://` + `skills/*/SKILL.md` | Agent Skills |
| **CI** | `.github/workflows/ci.yml` | 3.11 / 3.12 |
| **Monetization** | `/api/billing/*` | Free / Pro / Enterprise + metering |

## Quick start

```bash
pip install -e ".[dev]"
yodmcp                          # MCP stdio
yodmcp --http --port 8000
yodmcp-api --port 8080          # unified API + billing
yodmcp-a2a --port 9000
```

### SDK

```python
from yodmcp.sdk import YodClient
with YodClient("http://localhost:8080") as client:
    print(client.health())
    print(client.billing_plans())
```

## Monetization

| Plan | $/mo | Tool calls/day | Durable | TEE |
|------|------|----------------|---------|-----|
| Free | 0 | 500 | — | — |
| Pro | 49 | 50k | ✅ | simulated |
| Enterprise | 499 | unlimited | ✅ | Nitro/SGX hooks |

```bash
YODMCP_PLAN=pro yodmcp-api
curl -X POST localhost:8080/api/billing/checkout -H 'content-type: application/json' -d '{"plan_id":"pro"}'
```

## License

Apache-2.0 · [CONTRIBUTING](CONTRIBUTING.md) · [CHANGELOG](CHANGELOG.md) · [ARCHITECTURE](docs/ARCHITECTURE.md)
