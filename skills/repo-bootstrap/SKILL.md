---
name: repo-bootstrap
description: Automate full ANAMIZED product repo structure (Server OS parity) including USDC, Stripe, badges, CI, skills, AGENTS.md.
version: 1.0.0
tags: [bootstrap, funding, server-os, yodmcp]
---

# Repo Bootstrap (Autonomous)

When creating **any new ANAMIZED product repo**, run this skill end-to-end. Do not invent addresses or Stripe IDs.

## 1. Scaffold (required surface)

```
REPO/
  README.md, AGENTS.md, CHANGELOG.md, CONTRIBUTING.md, LICENSE
  .env.example, Dockerfile, docker-compose.yml, pyproject.toml
  .github/FUNDING.yml, .github/workflows/ci.yml
  funding/addresses.json, funding/USDC.md
  skills/*/SKILL.md, src/, tests/, scripts/, docs/
```

## 2. Canonical USDC (copy verbatim from server-os)

| Network | Address |
|---------|--------|
| Base | `0xD3d0E9eDAe3Ac7bb199a8EAA761BdA423b878438` |
| Ethereum | `0xD3d0E9eDAe3Ac7bb199a8EAA761BdA423b878438` |
| Solana | `ETQwWf19axArsY493UfC6bxe2BmEzmzvCb58PPnC38A` |

## 3. Stripe + FUNDING.yml
Reuse org payment links; never invent wallet addresses.

## 4. Verify
`pytest` / `scripts/verify_e2e.py` / `scripts/verify.sh`

## 5. Automate
`bash scripts/bootstrap_repo_structure.sh /path/to/new-repo`
