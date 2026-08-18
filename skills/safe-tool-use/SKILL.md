---
name: safe-tool-use
description: Policy-aware tool usage, HITL, attestation, and plan quotas.
version: 1.0.0
tags: [security, policy, billing]
---

# Safe Tool Use

- High-risk tools emit TRACE claims.
- Respect plan quotas (tool_call / memory_write / task_create).
- Never ignore requires_hitl flags.
