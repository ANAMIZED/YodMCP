"""Skills-over-MCP: expose Agent Skills as MCP Resources.

Skills follow the SKILL.md portable format (name + description + body +
optional scripts/references). They are discovered via resources/list and
read via resources/read under the skills:// URI scheme.

Discovery order:
1. Built-in skills (always present)
2. skills/*/SKILL.md relative to CWD, package root, or YODMCP_SKILLS_DIR
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("yodmcp.skills")


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
        header = (
            f"---\nname: {self.name}\ndescription: {self.description}\n"
            f"version: {self.version}\n---\n\n"
        )
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


def _parse_skill_md(text: str, fallback_name: str) -> Skill | None:
    """Parse optional YAML frontmatter + body from SKILL.md."""
    name = fallback_name
    description = fallback_name
    version = "1.0.0"
    tags: list[str] = []
    body = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm, body = parts[1], parts[2].lstrip("\n")
            for line in fm.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" not in line:
                    continue
                key, val = line.split(":", 1)
                key, val = key.strip().lower(), val.strip().strip("\"'")
                if key == "name":
                    name = val
                elif key == "description":
                    description = val
                elif key == "version":
                    version = val
                elif key == "tags":
                    raw = val.strip("[]")
                    tags = [t.strip().strip("\"'") for t in re.split(r"[, ]+", raw) if t.strip()]
    if not body.strip():
        body = f"# {name}\n\n{description}\n"
    return Skill(name=name, description=description, body=body, version=version, tags=tags)


def _candidate_skill_roots() -> list[Path]:
    roots: list[Path] = []
    env = os.environ.get("YODMCP_SKILLS_DIR")
    if env:
        roots.append(Path(env))
    roots.append(Path.cwd() / "skills")
    pkg = Path(__file__).resolve()
    roots.append(pkg.parents[3] / "skills")
    roots.append(pkg.parents[2] / "skills")
    seen: set[str] = set()
    out: list[Path] = []
    for r in roots:
        key = str(r.resolve()) if r.exists() else str(r)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def load_disk_skills() -> list[Skill]:
    found: list[Skill] = []
    for root in _candidate_skill_roots():
        if not root.is_dir():
            continue
        for skill_md in sorted(root.glob("*/SKILL.md")):
            try:
                text = skill_md.read_text(encoding="utf-8")
                skill = _parse_skill_md(text, fallback_name=skill_md.parent.name)
                if skill:
                    found.append(skill)
            except OSError as e:
                logger.warning("Failed to read skill %s: %s", skill_md, e)
        if found:
            break
    return found


class SkillsRegistry:
    def __init__(self, load_disk: bool = True) -> None:
        self._skills: dict[str, Skill] = {s.name: s for s in _BUILTIN}
        if load_disk:
            for s in load_disk_skills():
                self._skills[s.name] = s

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
