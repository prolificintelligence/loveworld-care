"""
Upstash Serverless Redis HTTP REST Adapter (`UPSTASH_REDIS_REST_URL` + `UPSTASH_REDIS_REST_TOKEN`).

Provides zero-connection-overhead distributed primitives for serverless & cloud deployments:
1. Distributed atomic locks (`SET key owner NX EX ttl`) for clinician case claiming (`AT-02`)
   and SponsorCare entitlement reservations (`AT-03`).
2. Distributed `Idempotency-Key` ledger & webhook deduplication (`AT-01`, `AT-04`).
3. Global AI-Off Kill Switch state synchronization (`§15.6`, `AT-16`) across all worker instances.
4. Shared-device session lock state (`AT-13`).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import httpx


class UpstashRedisRestClient:
    def __init__(self, rest_url: str, rest_token: str, timeout_seconds: float = 5.0) -> None:
        self._url = rest_url.rstrip("/")
        self._token = rest_token.strip()
        self._timeout = timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(
            self._url
            and self._token
            and not self._token.startswith("REPLACE_")
            and self._url.startswith("https://")
        )

    async def execute_command(self, command: list[str | int]) -> Any:
        if not self.is_configured:
            return None
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    self._url,
                    headers={
                        "Authorization": f"Bearer {self._token}",
                        "Content-Type": "application/json",
                    },
                    json=command,
                )
                if resp.status_code == 200:
                    return resp.json().get("result")
        except (httpx.HTTPError, ValueError):
            return None
        return None

    async def ping(self) -> bool:
        res = await self.execute_command(["PING"])
        return res == "PONG"

    async def set_json(
        self, key: str, value: dict[str, Any], ex_seconds: int | None = None
    ) -> bool:
        serialized = json.dumps(value, separators=(",", ":"), default=str)
        cmd: list[str | int] = ["SET", key, serialized]
        if ex_seconds is not None and ex_seconds > 0:
            cmd.extend(["EX", ex_seconds])
        res = await self.execute_command(cmd)
        return res == "OK"

    async def get_json(self, key: str) -> dict[str, Any] | None:
        raw = await self.execute_command(["GET", key])
        if not raw or not isinstance(raw, str):
            return None
        try:
            return json.loads(raw)
        except (httpx.HTTPError, ValueError):
            return None

    async def acquire_distributed_lock(
        self, lock_key: str, owner_id: str, ttl_seconds: int = 30
    ) -> bool:
        if not self.is_configured:
            return True
        res = await self.execute_command(
            ["SET", f"lw_care:lock:{lock_key}", owner_id, "NX", "EX", ttl_seconds]
        )
        return res == "OK"

    async def set_ai_kill_switch_state(self, *, enabled: bool, actor_id: str, reason: str) -> bool:
        return await self.set_json(
            "lw_care:governance:ai_kill_switch",
            {
                "enabled": enabled,
                "actor_id": actor_id,
                "reason": reason,
                "updated_at_iso": datetime.now(UTC).isoformat(),
            },
        )

    async def get_ai_kill_switch_state(self) -> dict[str, Any] | None:
        return await self.get_json("lw_care:governance:ai_kill_switch")
