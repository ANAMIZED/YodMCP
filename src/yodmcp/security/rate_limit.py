"""Simple in-process rate limiter for HTTP surfaces (P0 abuse control foundation).

Token-bucket per client key (API key id or IP). Not distributed; for multi-replica
replace with Redis later.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class _Bucket:
    tokens: float
    last: float


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        requests_per_minute: int | None = None,
        exempt_paths: set[str] | None = None,
    ):
        super().__init__(app)
        self.rpm = requests_per_minute or int(os.environ.get("YODMCP_RATE_LIMIT_RPM", "120"))
        self.exempt = exempt_paths or {"/health", "/ready", "/a2a/health", "/a2a/.well-known/agent.json", "/a2a/card"}
        self._buckets: dict[str, _Bucket] = defaultdict(lambda: _Bucket(tokens=float(self.rpm), last=time.time()))

    def _key(self, request: Request) -> str:
        # Prefer authenticated key id if middleware order places auth first; fall back to IP
        auth = request.headers.get("authorization") or request.headers.get("x-api-key") or ""
        if auth:
            return f"key:{auth[-12:]}"
        client = request.client.host if request.client else "unknown"
        return f"ip:{client}"

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        if path in self.exempt or self.rpm <= 0:
            return await call_next(request)

        key = self._key(request)
        now = time.time()
        bucket = self._buckets[key]
        # Refill
        elapsed = now - bucket.last
        bucket.tokens = min(float(self.rpm), bucket.tokens + elapsed * (self.rpm / 60.0))
        bucket.last = now

        if bucket.tokens < 1.0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Retry later.",
                headers={"Retry-After": "30"},
            )
        bucket.tokens -= 1.0
        return await call_next(request)
