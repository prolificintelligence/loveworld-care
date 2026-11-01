"""
Executes live schema migration, table creation, append-only immutability trigger installation,
and baseline seeding against Neon PostgreSQL, verifies Upstash Redis REST connectivity,
and tests OpenRouter Free-Tier clinical intake extraction.
"""

from __future__ import annotations

import asyncio
import json

from lw_care_api.config import get_settings
from lw_care_api.db.neon_migrator import NeonDatabaseManager
from lw_care_api.integrations.upstash_redis import UpstashRedisRestClient
from lw_model_gateway import (
    AgentRoleId,
    DataTier,
    ModelGatewayConfig,
    ModelGatewayRouter,
    ModelInvocationRequest,
)


async def main() -> None:
    cfg = get_settings()

    print("=== 1. Migrating & Seeding Neon PostgreSQL ===")
    neon = NeonDatabaseManager(cfg.database_url)
    db_summary = await neon.migrate_and_seed()
    print(json.dumps(db_summary, indent=2))
    assert db_summary.get("connected") is True, f"Neon DB failed: {db_summary}"

    print("\n=== 2. Verifying Upstash Serverless Redis ===")
    redis = UpstashRedisRestClient(cfg.upstash_redis_rest_url, cfg.upstash_redis_rest_token)
    pong = await redis.ping()
    await redis.set_ai_kill_switch_state(
        enabled=False, actor_id="system-bootstrap", reason="INITIAL_PRODUCTION_READY_STATE"
    )
    ks_state = await redis.get_ai_kill_switch_state()
    print(json.dumps({"pong": pong, "ai_kill_switch_state": ks_state}, indent=2))
    assert pong is True, "Upstash Redis PING failed"

    print("\n=== 3. Verifying OpenRouter Free-Tier Model Gateway ===")
    router = ModelGatewayRouter(
        ModelGatewayConfig(
            ai_kill_switch_enabled=False,
            openrouter_api_key=cfg.openrouter_api_key,
        )
    )
    res = await router.invoke(
        ModelInvocationRequest(
            agent_id=AgentRoleId.INTAKE_ASSISTANT,
            data_tier=DataTier.T3_SENSITIVE_CLINICAL,
            actor_id="patient-verify-01",
            structured_context={
                "patient_age_years": 34,
                "severe_chest_pain_or_pressure": False,
                "acute_breathing_difficulty": False,
                "symptom_duration_days": 2,
                "primary_symptom_category": "FEVER_OR_MALARIA_LIKE",
            },
            untrusted_user_text="I have had an intermittent fever and mild frontal headache for 2 days.",
        )
    )
    print(
        json.dumps(
            {
                "status": res.status,
                "backend_used": res.backend_used.value,
                "model_id": res.model_id,
                "watermark": res.watermark,
                "draft_summary": res.draft_summary,
                "latency_ms": res.latency_ms,
            },
            indent=2,
        )
    )
    assert res.status == "COMPLETED_DRAFT"


if __name__ == "__main__":
    asyncio.run(main())
