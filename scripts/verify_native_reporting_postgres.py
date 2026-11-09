"""Real Neon template qualification in an isolated, cleaned schema; no real adoptions."""

import asyncio
import json
import re
import sys
import traceback
from pathlib import Path

import httpx
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api/src"))
sys.path.insert(0, str(ROOT / "tests/integration"))
from lw_care_api.platform import db
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.control.continuity import verify_lineage
from lw_care_api.platform.main import create_platform_app
from lw_care_api.platform.reporting import tables as t
from test_platform_controls import ORIGIN, seed_controls, stamp
from test_platform_native_reporting import seed_sources
from lw_care_api.platform.clinical import store as cs
from lw_care_api.platform.clinical import tables as ct


async def verify():
    cfg = PlatformSettings(_env_file=ROOT / ".env.platform.local")
    database = db.Database(cfg.database_url)
    namespace = "lwh_native_verify_" + db.uid().replace("-", "")
    assert re.fullmatch(r"lwh_native_verify_[0-9a-f]{32}", namespace)
    settings = cfg.model_copy(
        update={
            "environment": "test",
            "web_origin": ORIGIN,
            "dispatch_recovery_after_commit": False,
            "resend_api_key": "synthetic-not-a-sending-key",
            "enforce_activation_dossiers": False,
        }
    )
    app = create_platform_app(settings)
    await app.state.database.engine.dispose()
    mapped = database.engine.execution_options(schema_translate_map={db.SCHEMA: namespace})
    app.state.database.engine = mapped
    app.state.database.session = async_sessionmaker(mapped, expire_on_commit=False)
    result = {"native_postgres": "RUNNING", "schema_version": 8}
    try:
        assert await database.version() == 8
        async with database.transaction() as session:
            before = [
                await session.scalar(select(func.count()).select_from(table))
                for table in (t.definitions, t.obligations, ct.records)
            ]
        print(
            json.dumps(
                {"qualification": "Creating isolated Neon schema and immutable-history protections"}
            ),
            flush=True,
        )
        async with database.engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{namespace}"'))
            translated = await connection.execution_options(
                schema_translate_map={db.SCHEMA: namespace}
            )
            await translated.run_sync(db.metadata.create_all)
            await db.protect_history(translated, namespace, schema_version=8)
        async with app.state.database.transaction() as session:
            await session.execute(
                db.schema_versions.insert().values(version=8, applied_at=db.now())
            )
        actors, facility = await seed_controls(app)
        async with app.state.database.transaction() as session:
            for name, role in [
                ("proposer", "DATA_GOVERNOR"),
                ("successor", "DATA_REVIEWER"),
                ("target", "REPORTING_OFFICER"),
            ]:
                await session.execute(
                    db.grants.insert().values(
                        id=db.uid(),
                        account_id=actors[name][0],
                        role=role,
                        scope_type="GLOBAL",
                        scope_id="GLOBAL",
                        valid_from=stamp(-1),
                        valid_until=stamp(20),
                        revoked=False,
                        grantor="SYNTHETIC_QUALIFICATION",
                    )
                )
        async with app.state.database.transaction() as session:
            await session.execute(ct.sites.delete().where(ct.sites.c.facility_id == facility))
        source_ids = await seed_sources(app, facility, actors["target"][0])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=ORIGIN, timeout=120
        ) as client:

            async def post(path, body, actor="proposer", key=None):
                return await client.post(
                    "/v1/reporting" + path,
                    json=body,
                    headers={
                        "Origin": ORIGIN,
                        "Authorization": "Bearer " + actors[actor][1],
                        "Idempotency-Key": key or db.uid(),
                    },
                )

            async def create(path, body, actor="proposer"):
                response = await post(path, body, actor)
                assert response.status_code == 200, (
                    path,
                    response.status_code,
                    response.json().get("error", {}).get("code"),
                )
                return response.json()["resource"]

            async def get(path, actor="proposer"):
                response = await client.get(
                    "/v1/reporting" + path, headers={"Authorization": "Bearer " + actors[actor][1]}
                )
                assert response.status_code == 200, (path, response.status_code)
                return response.json()

            async def decide(row, action, actor="proposer"):
                return await create(
                    f"/templates/{row['id']}/actions",
                    {
                        "expected_version": row["version"],
                        "action": action,
                        "reason": "Synthetic qualification decision",
                        "evidence": "Synthetic actual source mapping examination",
                        "intent_confirmed": True,
                    },
                    actor,
                )

            body = {
                "edition": "LWH-NATIVE-2026.1",
                "valid_from": stamp(-10),
                "valid_until": stamp(10),
                "authority_reference": "Synthetic native mapping qualification; never Director adoption",
                "intent_confirmed": True,
            }
            template = await create("/source-profiles/prepare", body)
            template = await decide(template, "SUBMIT")
            template = await decide(template, "REVIEW_ACCEPT", "successor")
            template = await decide(template, "ADOPT")
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
                    "definition_ids": template["definition_ids"],
                    "template_id": template["id"],
                    "template_version": template["version"],
                    "adoption_reference": "Synthetic exact reporting calendar",
                },
            )
            key = db.uid()
            path = f"/obligations/{obligation['id']}/extract"
            replies = await asyncio.gather(
                post(path, {}, "target", key), post(path, {}, "target", key)
            )
            assert (
                all(reply.status_code == 200 for reply in replies)
                and replies[0].json() == replies[1].json()
            )
            extract = replies[0].json()["resource"]
            values = {item["metric_id"]: item for item in extract["data"]["values"].values()}
            assert values["LWH-MET-010"]["value"] == "1" and values["LWH-MET-013"]["value"] == "1"
            assert (
                values["LWH-MET-014"]["numerator"] == "1"
                and values["LWH-MET-014"]["denominator"] == "3"
            )
            assert (
                values["LWH-MET-025"]["numerator"] == "2"
                and values["LWH-MET-025"]["denominator"] == "3"
            )
            assert all(item["completeness"] == "PARTIAL" for item in values.values())
            assert "PRIVATE_SYNTHETIC" not in str(extract) and source_ids["patient"] not in str(
                extract
            )
            declared = [
                {
                    "definition_id": identifier,
                    "completeness": item["completeness"],
                    "value": item["value"],
                    "numerator": item["numerator"],
                    "denominator": item["denominator"],
                    "explanation": item["explanation"],
                    "extract_id": extract["id"],
                }
                for identifier, item in extract["data"]["values"].items()
            ]
            draft = await create(
                f"/obligations/{obligation['id']}/draft",
                {
                    "expected_version": 0,
                    "values": declared,
                    "source_method": "Synthetic native clinical source",
                    "reconciliation": "Native subset only; no manual addition",
                    "reason": "Synthetic actual source review",
                },
                "target",
            )
            assert not any(
                item["severity"] == "BLOCKING" for item in draft["validation"]["findings"]
            )
            async with app.state.database.transaction() as session:
                site = (
                    (
                        await session.execute(
                            select(ct.sites).where(ct.sites.c.facility_id == facility)
                        )
                    )
                    .mappings()
                    .one()
                )
                await cs.create(
                    session,
                    settings,
                    app.state.box,
                    {"id": actors["target"][0]},
                    site,
                    "record_error",
                    {"target_id": source_ids["death"]},
                    "SYNTHETIC",
                    patient_id=source_ids["patient"],
                    status="ENTERED_IN_ERROR",
                )
            response = await post(
                f"/returns/{draft['id']}/submit",
                {
                    "expected_version": draft["version"],
                    "reason": "Synthetic stale source cannot be attested",
                    "intent_confirmed": True,
                },
                "target",
            )
            assert response.status_code == 409
            assert (await get(f"/extracts/{extract['id']}", "successor"))[
                "native_source_current"
            ] is False
            fresh = await create(path, {}, "target")
            assert (
                next(
                    item
                    for item in fresh["data"]["values"].values()
                    if item["metric_id"] == "LWH-MET-013"
                )["value"]
                == "0"
            )
            async with app.state.database.transaction() as session:
                assert await session.scalar(select(func.count()).select_from(t.extracts)) == 2
                signatures, hashes = await verify_lineage(
                    session,
                    {"schema_version": 8, "data_key_hex": cfg.data_key_hex},
                    app.state.box,
                    settings,
                )
                assert signatures >= 12 and hashes >= 12
            blocked = False
            try:
                async with app.state.database.transaction() as session:
                    await session.execute(t.extracts.delete())
            except DBAPIError as exc:
                blocked = getattr(exc.orig, "sqlstate", None) == "P0001"
            assert blocked
        async with database.transaction() as session:
            after = [
                await session.scalar(select(func.count()).select_from(table))
                for table in (t.definitions, t.obligations, ct.records)
            ]
        assert before == after
        result.update(
            native_postgres="PASSED",
            native_profiles=4,
            signed_clinical_events_verified=signatures,
            reporting_history_hashes_verified=hashes,
            duplicate_extract="ONE_RECEIPT_AND_ONE_EXTRACT",
            mortality_components="1/3",
            referral_acceptance_components="2/3",
            default_coverage="PARTIAL_NATIVE_SUBSET",
            stale_submission="BLOCKED",
            old_extract="RETAINED_NOT_CURRENT",
            fresh_death_count="0_NATIVE_SUBSET",
            protected_extract_delete="REJECTED",
            production_records_unchanged=True,
            production_records_seeded=0,
        )
    finally:
        assert re.fullmatch(r"lwh_native_verify_[0-9a-f]{32}", namespace) and namespace != db.SCHEMA
        async with database.engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{namespace}" CASCADE'))
        await database.engine.dispose()
        result["disposable_schema_removed"] = True
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except Exception as exc:
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        print(
            json.dumps(
                {
                    "native_postgres": "FAILED",
                    "error_type": type(exc).__name__,
                    "source": Path(frame.filename).name,
                    "line": frame.lineno,
                    "sqlstate": getattr(getattr(exc, "orig", None), "sqlstate", None),
                }
            )
        )
        raise SystemExit(1) from None
