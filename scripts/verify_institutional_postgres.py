"""Actual Neon concurrency and institutional/publication proof in one disposable schema.

Pre-existing evidence metadata is explicitly synthetic, not a scan qualification.
No production domain rows, published text, external notices or emails are created.
"""

import asyncio
import json
import re
import sys
import traceback
from pathlib import Path

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api/src"))
sys.path.insert(0, str(ROOT / "tests/integration"))
from lw_care_api.platform import db
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.institutional import tables as t
from lw_care_api.platform.main import create_platform_app
from lw_care_api.platform.reporting.store import scope_for
from test_platform_controls import ORIGIN, seed_controls, stamp
from test_platform_lifecycle import content, seed_lifecycle


async def verify():
    cfg = PlatformSettings(_env_file=ROOT / ".env.platform.local")
    database = db.Database(cfg.database_url)
    namespace = "lwh_institutional_verify_" + db.uid().replace("-", "")
    assert re.fullmatch(r"lwh_institutional_verify_[0-9a-f]{32}", namespace)
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
    try:
        assert await database.version() in {5, 6}
        async with database.engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{namespace}"'))
            target = await connection.execution_options(schema_translate_map={db.SCHEMA: namespace})
            await target.run_sync(db.metadata.create_all)
            await db.protect_history(target, namespace)
        async with app.state.database.transaction() as session:
            await session.execute(
                db.schema_versions.insert().values(version=6, applied_at=db.now())
            )
        actors, facility = await seed_controls(app)
        facts = await seed_lifecycle(app, actors, facility)
        async with app.state.database.transaction() as session:
            old = await scope_for(session, "FACILITY", facility, at=stamp(-1))
            zone = (
                (await session.execute(select(db.units).where(db.units.c.id == old["zone_id"])))
                .mappings()
                .one()
            )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=ORIGIN
        ) as client:

            async def post(path, body, name, key=None):
                return await client.post(
                    "/v1" + path,
                    json=body,
                    headers={
                        "Origin": ORIGIN,
                        "Authorization": "Bearer " + actors[name][1],
                        "Idempotency-Key": key or db.uid(),
                    },
                )

            async def create(path, body, name):
                response = await post(path, body, name)
                assert response.status_code == 200, (path, response.status_code)
                return response.json()["resource"]

            async def get(path, name):
                return await client.get(
                    "/v1" + path, headers={"Authorization": "Bearer " + actors[name][1]}
                )

            intention = {
                "evidence": "SYNTHETIC_ENGINEERING_AUTHORITY_ONLY",
                "intent_confirmed": True,
            }
            body = {
                **intention,
                "kind": "ZONE_REGION",
                "resource_id": zone["id"],
                "target_id": facts["region2"],
                "expected_version": 1,
            }
            key = db.uid()
            proposals = await asyncio.gather(
                *(post("/institutional/changes", body, "admin", key) for _ in range(2))
            )
            assert (
                all(response.status_code == 200 for response in proposals)
                and proposals[0].json() == proposals[1].json()
            )
            proposal = proposals[0].json()["resource"]
            await create(
                f"/institutional/changes/{proposal['id']}/review",
                {**intention, "expected_version": 1, "decision": "APPROVE"},
                "admin2",
            )
            assert (await get("/institutional/changes", "admin")).status_code == 200
            async with app.state.database.transaction() as session:
                new = await scope_for(session, "FACILITY", facility)
                historical = await scope_for(session, "FACILITY", facility, at=stamp(-1))
                assert (
                    new["region_id"] == facts["region2"]
                    and historical["region_id"] == old["region_id"]
                )
                assert await session.scalar(select(func.count()).select_from(t.changes)) == 1
                assert await session.scalar(select(func.count()).select_from(t.relationships)) == 2
            case = await create(
                "/institutional/cases",
                {
                    **intention,
                    "facility_id": facility,
                    "kind": "RENEWAL",
                    "criteria_id": facts["criteria"],
                    "respondent_id": actors["applicant"][0],
                    "due_at": stamp(5),
                    "calendar_authority_reference": "SYNTHETIC_CALENDAR_AUTHORITY",
                },
                "applicant",
            )
            case = await create(
                f"/institutional/cases/{case['id']}/assign",
                {
                    **intention,
                    "expected_version": case["version"],
                    "inspector_id": actors["inspector"][0],
                    "reviewer_id": actors["reviewer"][0],
                    "competence_reference": "SYNTHETIC_COMPETENCE_FIXTURE",
                },
                "reviewer",
            )
            case = await create(
                f"/institutional/cases/{case['id']}/inspect",
                {
                    **intention,
                    "expected_version": case["version"],
                    "conflict_declared": False,
                    "observed_at": stamp(-1),
                    "findings": [
                        {
                            "criterion": "SAFE",
                            "outcome": "MET",
                            "observation": "SYNTHETIC_INSPECTION_FACT_ONLY",
                            "evidence_ids": [facts["file"]],
                            "due_at": stamp(1),
                        }
                    ],
                },
                "inspector",
            )
            case = await create(
                f"/institutional/cases/{case['id']}/recommend",
                {**intention, "expected_version": case["version"], "action": "RENEW"},
                "reviewer",
            )
            body = {
                **intention,
                "expected_version": case["version"],
                "action": "RENEW",
                "scope": "SYNTHETIC_RECOGNITION_SCOPE_ONLY",
                "expires_at": stamp(30),
            }
            key = db.uid()
            results = await asyncio.gather(
                *(
                    post(f"/institutional/cases/{case['id']}/decide", body, "decider", key)
                    for _ in range(2)
                )
            )
            assert (
                all(response.status_code == 200 for response in results)
                and results[0].json() == results[1].json()
            )
            article = await create("/institutional/articles", content(None), "editor")
            assert (await client.get("/v1/knowledge/" + article["id"])).status_code == 404
            article = await create(
                f"/institutional/articles/{article['id']}/submit",
                {**intention, "expected_version": article["version"]},
                "editor",
            )
            article = await create(
                f"/institutional/articles/{article['id']}/review",
                {
                    **intention,
                    "expected_version": article["version"],
                    "decision": "APPROVE",
                    "qualification_reference": "SYNTHETIC_REVIEW_APPOINTMENT",
                },
                "clinical",
            )
            article = await create(
                f"/institutional/articles/{article['id']}/publish",
                {**intention, "expected_version": article["version"]},
                "publisher",
            )
            published = await client.get("/v1/knowledge/" + article["id"])
            assert published.status_code == 200 and published.json()["body_served"]
            article = await create(
                f"/institutional/articles/{article['id']}/withdraw",
                {**intention, "expected_version": article["version"]},
                "publisher",
            )
            assert (await client.get("/v1/knowledge/" + article["id"])).status_code == 410
            assert not (await client.get("/v1/knowledge")).json()["items"]
            assert (await get("/institutional/cases/" + case["id"], "outsider")).status_code in {
                403,
                404,
            }
        async with app.state.database.transaction() as session:
            assert await session.scalar(select(func.count()).select_from(t.decisions)) == 1
            assert await session.scalar(select(func.count()).select_from(db.decisions)) == 1
            for table in (t.journal, t.decisions, t.revisions):
                try:
                    async with session.begin_nested():
                        await session.execute(table.delete())
                except DBAPIError:
                    pass
                else:
                    raise AssertionError("Lifecycle history accepted mutation")
        restarted = create_platform_app(settings)
        await restarted.state.database.engine.dispose()
        restarted.state.database.engine = mapped
        restarted.state.database.session = async_sessionmaker(mapped, expire_on_commit=False)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=restarted), base_url=ORIGIN
        ) as client:
            assert (await client.get("/v1/knowledge/" + article["id"])).status_code == 410
        print(
            json.dumps(
                {
                    "institutional_postgres_verification": "PASSED",
                    "concurrent_hierarchy_proposals": "ONE_EFFECT_IDENTICAL_RECEIPTS",
                    "historical_reporting_scope": "PRESERVED",
                    "concurrent_central_decisions": "ONE_NEW_DECISION_PRIOR_DECISION_PRESERVED",
                    "unreviewed_publication": "DENIED",
                    "withdrawn_text": "NOT_SERVED",
                    "wrong_facility": "DENIED",
                    "history_mutation": "REJECTED",
                    "restart": "PERSISTED",
                    "scanner_qualification": "NOT_EXECUTED_SYNTHETIC_PREEXISTING_EVIDENCE_METADATA",
                    "production_domain_records_seeded": 0,
                }
            )
        )
    finally:
        assert re.fullmatch(r"lwh_institutional_verify_[0-9a-f]{32}", namespace)
        async with database.engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{namespace}" CASCADE'))
        await database.engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except Exception as exc:  # noqa: BLE001 -- never print rows, response bodies or credentials
        frames = [
            {"source": Path(frame.filename).name, "line": frame.lineno}
            for frame in traceback.extract_tb(exc.__traceback__)
            if "site-packages" not in frame.filename
        ]
        print(
            json.dumps(
                {
                    "institutional_verification": "FAILED",
                    "error_type": type(exc).__name__,
                    "sqlstate": getattr(getattr(exc, "orig", None), "sqlstate", None),
                    "frames": frames,
                }
            )
        )
        raise SystemExit(1) from None
