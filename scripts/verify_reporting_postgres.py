"""Real Neon reporting concurrency proofs in a disposable schema; no production fixtures."""

import asyncio
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api/src"))
from lw_care_api.platform import db
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.main import create_platform_app
from lw_care_api.platform.reporting import tables as t
from lw_care_api.platform.security import issue_session


def stamp(days=0):
    return (datetime.now(UTC) + timedelta(days=days)).isoformat(timespec="microseconds")


async def verify():
    cfg = PlatformSettings(_env_file=ROOT / ".env.platform.local")
    database = db.Database(cfg.database_url)
    namespace = "lwh_report_verify_" + db.uid().replace("-", "")
    assert re.fullmatch(r"lwh_report_verify_[0-9a-f]{32}", namespace)
    engine = database.engine.execution_options(schema_translate_map={db.SCHEMA: namespace})
    app = create_platform_app(
        cfg.model_copy(update={"environment": "test", "reporting_enabled": True})
    )
    await app.state.database.engine.dispose()
    app.state.database.engine = engine
    app.state.database.session = async_sessionmaker(engine, expire_on_commit=False)
    facility, region, zone, operator = (db.uid() for _ in range(4))
    actors = {}
    try:
        assert await database.version() in {2, 3, 4, 5, 6}
        async with database.engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{namespace}"'))
            mapped = await connection.execution_options(schema_translate_map={db.SCHEMA: namespace})
            await mapped.run_sync(db.metadata.create_all)
            for table in t.IMMUTABLE:
                await mapped.execute(
                    text(
                        f'CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE ON "{namespace}"."{table.name}" FOR EACH ROW EXECUTE FUNCTION health_platform.reject_history_mutation()'
                    )
                )
        async with app.state.database.transaction() as session:
            await session.execute(
                db.schema_versions.insert().values(version=3, applied_at=db.now())
            )
            for name, role in {
                "governor": "DATA_GOVERNOR",
                "reporter": "REPORTING_OFFICER",
                "reviewer": "DATA_REVIEWER",
                "reviewer2": "DATA_REVIEWER",
                "analyst": "DATA_ANALYST",
                "executive": "EXECUTIVE_VIEWER",
            }.items():
                identifier = db.uid()
                await session.execute(
                    db.accounts.insert().values(
                        id=identifier,
                        email=name + "@isolated.invalid",
                        name="Isolated reporting proof " + name,
                        active=True,
                        totp_last_step=-1,
                        created_at=db.now(),
                    )
                )
                await session.execute(
                    db.grants.insert().values(
                        id=db.uid(),
                        account_id=identifier,
                        role=role,
                        scope_type="GLOBAL",
                        scope_id="GLOBAL",
                        valid_from=stamp(-1),
                        valid_until=stamp(1),
                        revoked=False,
                        grantor="ISOLATED_VERIFICATION",
                    )
                )
                actors[name] = (identifier, await issue_session(session, identifier, 30))
            await session.execute(
                db.units.insert().values(
                    id=region, name="Isolated region", kind="REGION", code=region, version=1
                )
            )
            await session.execute(
                db.units.insert().values(
                    id=zone,
                    name="Isolated zone",
                    kind="ZONE",
                    code=zone,
                    parent_id=region,
                    version=1,
                )
            )
            await session.execute(
                db.operators.insert().values(
                    id=operator, name="Isolated operator", external_reference=operator
                )
            )
            await session.execute(
                db.facilities.insert().values(
                    id=facility,
                    operator_id=operator,
                    zone_id=zone,
                    name="Isolated reporting facility",
                    site_type="COMMUNITY_PRIMARY",
                    ownership="MEMBER_OWNED",
                    jurisdiction="ISOLATED_ONLY",
                    external_reference=facility,
                    address="Isolated",
                    public_contact="isolated@invalid.example",
                    private_contact="isolated@invalid.example",
                    services=["TEST"],
                    identity_status="VERIFIED",
                    statutory_status="CHECKED",
                    created_by=actors["governor"][0],
                    created_at=db.now(),
                    updated_at=db.now(),
                    version=1,
                )
            )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=cfg.web_origin, timeout=90
        ) as client:

            async def post(path, body, actor="reporter", key=None):
                return await client.post(
                    "/v1/reporting" + path,
                    json=body,
                    headers={
                        "Authorization": "Bearer " + actors[actor][1],
                        "Origin": cfg.web_origin,
                        "Idempotency-Key": key or db.uid(),
                    },
                )

            async def create(path, body, actor="reporter"):
                response = await post(path, body, actor)
                assert response.status_code == 200, (path, response.status_code)
                return response.json()["resource"]

            definition_body = {
                "metric_id": "LWH-MET-010",
                "definition_version": "ISOLATED-1",
                "name": "Isolated reporting proof",
                "stream": "FACILITY_ACTIVITY",
                "formula": "COUNT",
                "unit": "contacts",
                "aggregation": "SUM",
                "source_selector": "MANUAL",
                "numerator_definition": "Isolated count",
                "denominator_definition": "Not applicable",
                "population_definition": "Isolated unit-period",
                "inclusion_exclusion": "Isolated source only",
                "dimensions": ["facility"],
                "adoption_reference": "ISOLATED TEST AUTHORITY ONLY",
                "template_reconciliation": "Isolated mapping",
                "valid_from": stamp(-30),
                "valid_until": stamp(30),
                "intent_confirmed": True,
            }
            key = db.uid()
            first, second = await asyncio.gather(
                *(post("/definitions", definition_body, "governor", key) for _ in range(2))
            )
            assert first.status_code == second.status_code == 200 and first.json() == second.json()
            definition = first.json()["resource"]
            conflict = await post(
                "/definitions", {**definition_body, "name": "Changed body"}, "governor", key
            )
            assert conflict.status_code == 409
            obligation = await create(
                "/obligations",
                {
                    "scope_type": "FACILITY",
                    "scope_id": facility,
                    "stream": "FACILITY_ACTIVITY",
                    "period_start": stamp(-3),
                    "period_end": stamp(-2),
                    "due_at": stamp(1),
                    "timezone": "Africa/Lagos",
                    "definition_ids": [definition["id"]],
                    "adoption_reference": "Isolated calendar",
                },
                "governor",
            )
            draft_body = {
                "expected_version": 0,
                "values": [
                    {
                        "definition_id": definition["id"],
                        "completeness": "VALUE",
                        "value": "10",
                        "source_reference": "Isolated source",
                    }
                ],
                "source_method": "Isolated actual preparation",
                "reconciliation": "Single isolated authority",
                "reason": "Isolated initial draft",
            }
            draft_key = db.uid()
            path = f"/obligations/{obligation['id']}/draft"
            first, second = await asyncio.gather(
                *(post(path, draft_body, key=draft_key) for _ in range(2))
            )
            assert first.status_code == second.status_code == 200 and first.json() == second.json()
            row = first.json()["resource"]
            row = await create(
                f"/returns/{row['id']}/submit",
                {
                    "expected_version": row["version"],
                    "reason": "Isolated actual attestation",
                    "intent_confirmed": True,
                },
            )
            review = {
                "expected_version": row["version"],
                "reason": "Isolated independent review",
                "intent_confirmed": True,
                "decision": "VERIFY",
                "evidence_examined": "Isolated source",
                "method": "Isolated reconciliation",
                "verification_scope": "Exact isolated scope",
                "warning_overrides": {},
            }
            reviews = await asyncio.gather(
                *(
                    post(f"/returns/{row['id']}/review", review, who)
                    for who in ("reviewer", "reviewer2")
                )
            )
            assert sorted(response.status_code for response in reviews) == [200, 409]
            row = next(
                response.json()["resource"] for response in reviews if response.status_code == 200
            )
            policy = await create(
                "/policies",
                {
                    "name": "Isolated policy",
                    "policy_version": "ISOLATED-1",
                    "purpose": "STRATEGIC_LEADERSHIP",
                    "allowed_metric_ids": ["LWH-MET-010"],
                    "minimum_units": 2,
                    "minimum_cell": 5,
                    "minimum_change": 5,
                    "allow_partial": False,
                    "adoption_reference": "ISOLATED TEST AUTHORITY ONLY",
                    "risk_assessment": "Isolated reviewed controls; no anonymity certification",
                    "valid_from": stamp(-1),
                    "valid_until": stamp(1),
                    "intent_confirmed": True,
                },
                "governor",
            )
            cohort = await create(
                "/cohorts",
                {
                    "scope_type": "GLOBAL",
                    "name": "Isolated frozen cohort",
                    "obligation_ids": [obligation["id"]],
                    "policy_id": policy["id"],
                },
                "analyst",
            )
            snapshot = await create("/snapshots", {"cohort_id": cohort["id"]}, "analyst")
            release, correction = await asyncio.gather(
                post(
                    f"/snapshots/{snapshot['id']}/review",
                    {
                        "decision": "RELEASE",
                        "reason": "Isolated independent disclosure review",
                        "intent_confirmed": True,
                    },
                    "reviewer",
                ),
                post(
                    f"/returns/{row['id']}/correction",
                    {"expected_version": row["version"], "reason": "Isolated changed source"},
                ),
            )
            assert correction.status_code == 200 and release.status_code in {200, 409}
            if release.status_code == 200:
                public = await client.get(
                    f"/v1/reporting/snapshots/{snapshot['id']}",
                    headers={"Authorization": "Bearer " + actors["executive"][1]},
                )
                assert (
                    public.status_code == 200
                    and public.json()["current_eligible"] is False
                    and public.json()["cells"][0]["value"] is None
                )
            async with app.state.database.transaction() as session:
                assert await session.scalar(select(func.count()).select_from(t.definitions)) == 1
                assert await session.scalar(select(func.count()).select_from(t.returns)) == 1
                assert await session.scalar(select(func.count()).select_from(t.versions)) == 4
                assert await session.scalar(select(func.count()).select_from(t.invalidations)) == 1
                for table in (t.versions, t.audit, t.definitions):
                    try:
                        async with session.begin_nested():
                            await session.execute(table.update().values(id=db.uid()))
                    except DBAPIError:
                        pass
                    else:
                        raise AssertionError("Append-only reporting history mutation accepted")
                await session.execute(
                    update(db.grants)
                    .where(db.grants.c.account_id == actors["reporter"][0])
                    .values(revoked=True)
                )
            revoked = await post(path, draft_body, key=draft_key)
            assert revoked.status_code == 404
        restarted = create_platform_app(cfg.model_copy(update={"environment": "test"}))
        await restarted.state.database.engine.dispose()
        restarted.state.database.engine = engine
        restarted.state.database.session = async_sessionmaker(engine, expire_on_commit=False)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=restarted), base_url=cfg.web_origin
        ) as client:
            result = await client.get(
                f"/v1/reporting/returns/{row['id']}",
                headers={"Authorization": "Bearer " + actors["reviewer"][1]},
            )
            assert result.status_code == 200 and result.json()["version"] == 4
        print(
            json.dumps(
                {
                    "reporting_postgres_verification": "PASSED",
                    "concurrent_duplicate_effects": 1,
                    "independent_review_race": "ONE_REVIEW",
                    "release_correction_race": "SERIAL_AND_INVALIDATED",
                    "append_only_triggers": "ENFORCED",
                    "revoked_cached_receipt": "DENIED",
                    "restart_persistence": "PASSED",
                    "production_records_seeded": 0,
                }
            )
        )
    finally:
        # The only removal target is the random, validated namespace created above.
        assert re.fullmatch(r"lwh_report_verify_[0-9a-f]{32}", namespace)
        async with database.engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{namespace}" CASCADE'))
        await database.engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except Exception as exc:  # noqa: BLE001 -- secret-safe release boundary
        print(
            json.dumps(
                {"reporting_postgres_verification": "FAILED", "error_type": type(exc).__name__}
            )
        )
        raise SystemExit(1) from None
