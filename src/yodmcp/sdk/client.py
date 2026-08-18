"""HTTP client for YodMCP API / A2A / health / billing endpoints."""

from __future__ import annotations

from typing import Any

import httpx


class YodClient:
    def __init__(self, base_url: str = "http://localhost:8080", timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "YodClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def health(self) -> dict[str, Any]:
        r = self._client.get("/health")
        if r.status_code == 404:
            r = self._client.get("/a2a/health")
        r.raise_for_status()
        return r.json()

    def agent_card(self) -> dict[str, Any]:
        r = self._client.get("/a2a/card")
        r.raise_for_status()
        return r.json()

    def send_message(self, text: str, role: str = "user") -> dict[str, Any]:
        r = self._client.post(
            "/a2a/message",
            json={"role": role, "parts": [{"type": "text", "text": text}]},
        )
        r.raise_for_status()
        return r.json()

    def create_task(self, description: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        r = self._client.post(
            "/a2a/tasks",
            json={"description": description, "metadata": metadata or {}},
        )
        r.raise_for_status()
        return r.json()

    def get_task(self, task_id: str) -> dict[str, Any]:
        r = self._client.get(f"/a2a/tasks/{task_id}")
        r.raise_for_status()
        return r.json()

    def billing_status(self) -> dict[str, Any]:
        r = self._client.get("/api/billing/status")
        r.raise_for_status()
        return r.json()

    def billing_plans(self) -> dict[str, Any]:
        r = self._client.get("/api/billing/plans")
        r.raise_for_status()
        return r.json()

    def create_checkout(self, plan_id: str = "pro", success_url: str = "", cancel_url: str = "") -> dict[str, Any]:
        r = self._client.post(
            "/api/billing/checkout",
            json={
                "plan_id": plan_id,
                "success_url": success_url or f"{self.base_url}/ok",
                "cancel_url": cancel_url or f"{self.base_url}/cancel",
            },
        )
        r.raise_for_status()
        return r.json()

    def usage(self) -> dict[str, Any]:
        r = self._client.get("/api/usage")
        r.raise_for_status()
        return r.json()
