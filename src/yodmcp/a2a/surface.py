"""Native A2A surface for YodMCP.

Exposes an Agent Card and minimal message handling so YodMCP can
participate in Agent2Agent collaboration. Uses the official a2a-sdk
types when available; falls back to pure dict card otherwise.
"""

from __future__ import annotations

from typing import Any


def build_agent_card(
    name: str = "YodMCP",
    url: str = "http://localhost:8000/a2a",
    description: str | None = None,
    version: str = "0.4.0",
) -> dict[str, Any]:
    """A2A Agent Card (v1.0 shape)."""
    return {
        "name": name,
        "description": description
        or (
            "YodMCP — Ultimate Autonomous MCP Server / Agent Operating System. "
            "Provides hierarchical multi-graph memory, policy-attested tools, "
            "Tasks, Skills, and multi-agent coordination."
        ),
        "url": url,
        "version": version,
        "protocolVersion": "1.0",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": True,
        },
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text", "application/json"],
        "skills": [
            {
                "id": "memory-ops",
                "name": "Memory Operations",
                "description": "Read/write/consolidate hierarchical multi-graph memory",
                "tags": ["memory", "cognitive"],
            },
            {
                "id": "task-orchestration",
                "name": "Long-running Tasks",
                "description": "Create and manage durable async tasks (MCP Tasks extension)",
                "tags": ["tasks", "async"],
            },
            {
                "id": "policy-attested-tools",
                "name": "Policy-Attested Tool Execution",
                "description": "Execute tools under cMCP-style TRACE claims",
                "tags": ["security", "governance"],
            },
        ],
        "authentication": {
            "schemes": ["bearer"],
        },
        "provider": {
            "organization": "YodMCP",
            "url": "https://github.com/ANAMIZED/YodMCP",
        },
    }


class A2ASurface:
    """Lightweight A2A adapter bound to YodMCP context."""

    def __init__(self, card: dict[str, Any] | None = None) -> None:
        self.card = card or build_agent_card()

    def get_card(self) -> dict[str, Any]:
        return self.card

    async def handle_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """Minimal message/send handler — routes simple intents to tools later."""
        text = ""
        parts = message.get("parts") or message.get("content") or []
        if isinstance(parts, str):
            text = parts
        elif isinstance(parts, list):
            for p in parts:
                if isinstance(p, dict) and p.get("text"):
                    text += p["text"]
                elif isinstance(p, str):
                    text += p

        return {
            "role": "agent",
            "parts": [
                {
                    "type": "text",
                    "text": (
                        f"YodMCP A2A received: {text[:200] or '(empty)'}. "
                        "Use MCP tools (memory_*, tasks_*, discover_capabilities) "
                        "or Skills resources for full capability."
                    ),
                }
            ],
            "metadata": {"agent": self.card["name"], "protocol": "A2A/1.0"},
        }
