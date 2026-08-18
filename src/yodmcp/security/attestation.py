"""cMCP-style policy attestation with TEE-ready modes.

Modes: software (HMAC), simulated_tee (ECDSA P-256 + measurement),
tee_nitro / tee_sgx (interface stubs for AWS Nitro / Intel SGX).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


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
    mode: str = "software"
    measurement: str | None = None
    public_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TEEProvider(Protocol):
    @property
    def mode(self) -> str: ...
    @property
    def measurement(self) -> str: ...
    @property
    def public_key_pem(self) -> str | None: ...
    def sign(self, payload: str) -> str: ...
    def verify(self, payload: str, signature: str) -> bool: ...


class SoftwareHMACProvider:
    def __init__(self, secret: bytes | None = None) -> None:
        self._secret = secret or os.environ.get("YODMCP_ATTEST_SECRET", "yodmcp-dev-secret").encode()

    @property
    def mode(self) -> str:
        return "software"

    @property
    def measurement(self) -> str:
        return hashlib.sha256(b"yodmcp-software-v1").hexdigest()[:32]

    @property
    def public_key_pem(self) -> str | None:
        return None

    def sign(self, payload: str) -> str:
        return hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()

    def verify(self, payload: str, signature: str) -> bool:
        return hmac.compare_digest(self.sign(payload), signature)


class SimulatedTEEProvider:
    """Simulated TEE: ECDSA P-256 + code measurement."""

    def __init__(self, measurement_input: str = "yodmcp-simulated-tee-v1") -> None:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric.utils import (
            encode_dss_signature,
            decode_dss_signature,
        )

        self._hashes = hashes
        self._ec = ec
        self._encode = encode_dss_signature
        self._decode = decode_dss_signature

        pem = os.environ.get("YODMCP_TEE_KEY_PEM")
        if pem:
            self._private = serialization.load_pem_private_key(pem.encode(), password=None)
        else:
            self._private = ec.generate_private_key(ec.SECP256R1())
        self._public = self._private.public_key()
        self._measurement = hashlib.sha256(measurement_input.encode()).hexdigest()[:48]
        self._pub_pem = self._public.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

    @property
    def mode(self) -> str:
        return "simulated_tee"

    @property
    def measurement(self) -> str:
        return self._measurement

    @property
    def public_key_pem(self) -> str | None:
        return self._pub_pem

    def sign(self, payload: str) -> str:
        sig = self._private.sign(payload.encode(), self._ec.ECDSA(self._hashes.SHA256()))
        r, s = self._decode(sig)
        return f"{r:064x}{s:064x}"

    def verify(self, payload: str, signature: str) -> bool:
        try:
            r = int(signature[:64], 16)
            s = int(signature[64:], 16)
            der = self._encode(r, s)
            self._public.verify(der, payload.encode(), self._ec.ECDSA(self._hashes.SHA256()))
            return True
        except Exception:
            return False


class NitroTEEStub:
    @property
    def mode(self) -> str:
        return "tee_nitro"

    @property
    def measurement(self) -> str:
        return "nitro-pcr0-pending"

    @property
    def public_key_pem(self) -> str | None:
        return None

    def sign(self, payload: str) -> str:
        raise NotImplementedError("NitroTEEStub: deploy inside Nitro Enclave + NSM")

    def verify(self, payload: str, signature: str) -> bool:
        raise NotImplementedError("NitroTEEStub: verify against AWS root of trust")


class SGXTEEStub:
    @property
    def mode(self) -> str:
        return "tee_sgx"

    @property
    def measurement(self) -> str:
        return "sgx-mrenclave-pending"

    @property
    def public_key_pem(self) -> str | None:
        return None

    def sign(self, payload: str) -> str:
        raise NotImplementedError("SGXTEEStub: use Intel SGX SDK / DCAP")

    def verify(self, payload: str, signature: str) -> bool:
        raise NotImplementedError("SGXTEEStub: verify quote via PCCS/IAS")


def build_tee_provider(mode: str | None = None) -> Any:
    mode = (mode or os.environ.get("YODMCP_ATTEST_MODE", "software")).lower()
    if mode in ("simulated_tee", "tee", "ecdsa"):
        return SimulatedTEEProvider()
    if mode in ("tee_nitro", "nitro"):
        return NitroTEEStub()
    if mode in ("tee_sgx", "sgx"):
        return SGXTEEStub()
    return SoftwareHMACProvider()


class AttestationService:
    def __init__(
        self,
        secret: bytes | None = None,
        policy_bundle: str = "yodmcp-default-v1",
        mode: str | None = None,
        provider: Any | None = None,
    ) -> None:
        self._policy_bundle = policy_bundle
        self._policy_hash = hashlib.sha256(policy_bundle.encode()).hexdigest()[:32]
        self._claims: list[TraceClaim] = []
        if provider is not None:
            self._provider = provider
        elif mode is None and secret is not None:
            self._provider = SoftwareHMACProvider(secret)
        else:
            self._provider = build_tee_provider(mode)

    def _body(self, claim_id, ts, tool_name, policy_decision, risk_tier, args_hash) -> str:
        return (
            f"{claim_id}|{ts}|{tool_name}|{policy_decision}|{risk_tier}|"
            f"{args_hash}|{self._policy_hash}|{self._provider.measurement}"
        )

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
        body = self._body(claim_id, ts, tool_name, policy_decision, risk_tier, args_hash)
        sig = self._provider.sign(body)
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
            mode=self._provider.mode,
            measurement=self._provider.measurement,
            public_key=self._provider.public_key_pem,
            metadata=metadata or {},
        )
        self._claims.append(claim)
        return claim

    def verify(self, claim: TraceClaim | dict[str, Any]) -> bool:
        if isinstance(claim, dict):
            fields = {k: claim[k] for k in TraceClaim.__dataclass_fields__ if k in claim}
            claim = TraceClaim(**fields)
        body = self._body(
            claim.claim_id, claim.timestamp, claim.tool_name,
            claim.policy_decision, claim.risk_tier, claim.arguments_hash,
        )
        return self._provider.verify(body, claim.signature)

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._claims[-limit:]]

    def stats(self) -> dict[str, Any]:
        return {
            "claims_issued": len(self._claims),
            "policy_bundle_hash": self._policy_hash,
            "mode": self._provider.mode,
            "measurement": self._provider.measurement,
            "has_public_key": self._provider.public_key_pem is not None,
        }
