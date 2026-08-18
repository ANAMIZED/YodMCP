"""Skills-over-MCP: expose Agent Skills as MCP Resources.

Skills follow the SKILL.md portable format (name + description + body +
optional scripts/references). They are discovered via resources/list and
read via resources/read under the skills:// URI scheme.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Skill:
    name: str
    description: str
    body: str
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def uri(self) -> str:
        return f"skills://{self.name}"

    def to_resource(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": "text/markdown",
            "annotations": {
                "skill": True,
                "version": self.version,
                "tags": self.tags,
            },
        }

    def render(self) -> str:
        header = f"---\nname: {self.name}\ndescription: {self.description}\nversion: {self.version}\n---\n\n"
        return header + self.body


_BUILTIN: list[Skill] = [
    Skill(
        name="memory-hygiene",
        description="Guidelines for writing and consolidating memories effectively in YodMCP.",
        body=(
            "# Memory Hygiene\n\n"
            "- Prefer episodic for events, semantic for durable facts, procedural for reusable steps.\n"
            "- Set importance >= 0.8 for knowledge that should be consolidated.\n"
            "- Always tag agent_id / session_id when available.\n"
            "- After major milestones call memory_consolidate.\n"
        ),
        tags=["memory", "best-practice"],
    ),
    Skill(
        name="long-horizon-planning",
        description="How to break long-horizon goals into tasks and use plan caching.",
        body=(
            "# Long-Horizon Planning\n\n"
            "1. Describe the goal clearly.\n"
            "2. Check plan cache (semantic) for similar past plans.\n"
            "3. Decompose into subtasks; prefer Tasks extension for long work.\n"
            "4. Persist intermediate decisions via memory_write.\n"
            "5. On success, store the plan template for reuse.\n"
        ),
        tags=["planning", "tasks"],
    ),
    Skill(
        name="safe-tool-use",
        description="Policy-aware tool usage and when to expect HITL / attestation.",
        body=(
            "# Safe Tool Use\n\n"
            "- High-risk tools (code_exec, network, destructive) emit TRACE claims and may require HITL.\n"
            "- Prefer read-only discovery tools first.\n"
            "- Never ignore requires_hitl flags.\n"
        ),
        tags=["security", "policy"],
    ),
]


class SkillsRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {s.name: s for s in _BUILTIN}

    def list_skills(self) -> list[Skill]:
        return list(self._skills.values())

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def as_resources(self) -> list[dict[str, Any]]:
        return [s.to_resource() for s in self._skills.values()]

    def read_uri(self, uri: str) -> str | None:
        if not uri.startswith("skills://"):
            return None
        name = uri.removeprefix("skills://")
        skill = self._skills.get(name)
        return skill.render() if skill else None
