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
| **Monetization** | `/api/billing/*` | Free / Pro / Enterprise + USDC |

## Quick start

```bash
pip install -e ".[dev]"
yodmcp
yodmcp-api --port 8080
yodmcp-a2a --port 9000
```

## Monetization

| Plan | $/mo | Tool calls/day | Durable | TEE |
|------|------|----------------|---------|-----|
| Free | 0 | 500 | — | — |
| Pro | 49 | 50k | ✅ | simulated |
| Enterprise | 499 | unlimited | ✅ | Nitro/SGX hooks |

- **Pro:** https://buy.stripe.com/bJe3cw0kCaLrbVz1AY43S09
- **Enterprise:** https://buy.stripe.com/9B68wQ1oGcTz9NrfrO43S0a

### Non-custodial USDC (preferred for agents)

| Network | Address | Explorer |
|---------|---------|----------|
| **Base** | `0xD3d0E9eDAe3Ac7bb199a8EAA761BdA423b878438` | [basescan](https://basescan.org/address/0xD3d0E9eDAe3Ac7bb199a8EAA761BdA423b878438) |
| **Ethereum** | `0xD3d0E9eDAe3Ac7bb199a8EAA761BdA423b878438` | [etherscan](https://etherscan.io/address/0xD3d0E9eDAe3Ac7bb199a8EAA761BdA423b878438) |
| **Solana** | `ETQwWf19axArsY493UfC6bxe2BmEzmzvCb58PPnC38A` | [solscan](https://solscan.io/account/ETQwWf19axArsY493UfC6bxe2BmEzmzvCb58PPnC38A) |

Canonical: [`funding/addresses.json`](funding/addresses.json) (same as [server-os](https://github.com/ANAMIZED/server-os))

## License

Apache-2.0 · [CONTRIBUTING](CONTRIBUTING.md) · [CHANGELOG](CHANGELOG.md) · [ARCHITECTURE](docs/ARCHITECTURE.md)
