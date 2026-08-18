"""Non-custodial USDC funding addresses (canonical ANAMIZED set)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_EMBEDDED: dict[str, Any] = {
    "asset": "USDC",
    "version": 1,
    "recipient": "ANAMIZED",
    "networks": {
        "base": {
            "chain_id": 8453,
            "caip2": "eip155:8453",
            "address": "0xD3d0E9eDAe3Ac7bb199a8EAA761BdA423b878438",
            "explorer": "https://basescan.org/address/0xD3d0E9eDAe3Ac7bb199a8EAA761BdA423b878438",
            "preferred": True,
        },
        "ethereum": {
            "chain_id": 1,
            "caip2": "eip155:1",
            "address": "0xD3d0E9eDAe3Ac7bb199a8EAA761BdA423b878438",
            "explorer": "https://etherscan.io/address/0xD3d0E9eDAe3Ac7bb199a8EAA761BdA423b878438",
        },
        "solana": {
            "chain_id": None,
            "caip2": "solana:mainnet",
            "address": "ETQwWf19axArsY493UfC6bxe2BmEzmzvCb58PPnC38A",
            "explorer": "https://solscan.io/account/ETQwWf19axArsY493UfC6bxe2BmEzmzvCb58PPnC38A",
        },
    },
    "notes": "Non-custodial USDC only. Wrong asset or network may result in permanent loss.",
}


@lru_cache(maxsize=1)
def load_usdc_addresses() -> dict[str, Any]:
    candidates = [
        Path.cwd() / "funding" / "addresses.json",
        Path(__file__).resolve().parents[3] / "funding" / "addresses.json",
    ]
    for p in candidates:
        if p.is_file():
            return json.loads(p.read_text())
    return dict(_EMBEDDED)


def usdc_table_markdown() -> str:
    data = load_usdc_addresses()
    lines = [
        "| Network | Address | Explorer |",
        "|---------|---------|----------|",
    ]
    for name, net in data.get("networks", {}).items():
        addr = net["address"]
        exp = net.get("explorer", "")
        lines.append(f"| **{name.title()}** | `{addr}` | [link]({exp}) |")
    return "\n".join(lines)
