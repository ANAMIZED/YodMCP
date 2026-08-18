"""cMCP-style policy attestation stubs.

Produces signed TRACE-style claims for every high-risk tool call.
In production these would be hardware-attested (TEE) and verifiable
offline against a root of trust. Here we use HMAC + structured claims.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TraceClaim:
    claim_id: str
    timestamp: float
    tool_name: str
    policy_decision: str
    risk_tier: str
    actor: str | None
    session_id: str | None
    arguments_hash: str
    policy_bundle_hash: str
    signature: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AttestationService:
    """Software-mode TRACE claim issuer (cMCP pattern)."""

    def __init__(self, secret: bytes | None = None, policy_bundle: str = "yodmcp-default-v1") -> None:
        self._secret = secret or os.environ.get("YODMCP_ATTEST_SECRET", "yodmcp-dev-secret").encode()
        self._policy_bundle = policy_bundle
        self._policy_hash = hashlib.sha256(policy_bundle.encode()).hexdigest()[:32]
        self._claims: list[TraceClaim] = []

    def _sign(self, payload: str) -> str:
        return hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()

    def issue(
        self,
        tool_name: str,
        policy_decision: str,
        risk_tier: str,
        arguments: dict[str, Any] | None = None,
        actor: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TraceClaim:
        args_raw = json.dumps(arguments or {}, sort_keys=True, default=str)
        args_hash = hashlib.sha256(args_raw.encode()).hexdigest()[:32]
        claim_id = str(uuid.uuid4())
        ts = time.time()
        body = f"{claim_id}|{ts}|{tool_name}|{policy_decision}|{risk_tier}|{args_hash}|{self._policy_hash}"
        sig = self._sign(body)
        claim = TraceClaim(
            claim_id=claim_id,
            timestamp=ts,
            tool_name=tool_name,
            policy_decision=policy_decision,
            risk_tier=risk_tier,
            actor=actor,
            session_id=session_id,
            arguments_hash=args_hash,
            policy_bundle_hash=self._policy_hash,
            signature=sig,
            metadata=metadata or {},
        )
        self._claims.append(claim)
        return claim

    def verify(self, claim: TraceClaim | dict[str, Any]) -> bool:
        if isinstance(claim, dict):
            claim = TraceClaim(**{k: claim[k] for k in TraceClaim.__dataclass_fields__ if k in claim})
        body = (
            f"{claim.claim_id}|{claim.timestamp}|{claim.tool_name}|"
            f"{claim.policy_decision}|{claim.risk_tier}|{claim.arguments_hash}|"
            f"{claim.policy_bundle_hash}"
        )
        expected = self._sign(body)
        return hmac.compare_digest(expected, claim.signature)

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._claims[-limit:]]

    def stats(self) -> dict[str, Any]:
        return {
            "claims_issued": len(self._claims),
            "policy_bundle_hash": self._policy_hash,
            "mode": "software-hmac",
        }
