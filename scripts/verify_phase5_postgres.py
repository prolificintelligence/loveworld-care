"""Actual Phase 5 Neon proof in a disposable schema; no production seeding or messages."""

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
from lw_care_api.platform.clinical import tables as t
from lw_care_api.platform.clinical.flow_index import index
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.main import create_platform_app
from test_platform_controls import ORIGIN, seed_controls, stamp


async def verify():
    cfg = PlatformSettings(_env_file=ROOT / ".env.platform.local")
    database = db.Database(cfg.database_url)
    namespace = "lwh_phase5_verify_" + db.uid().replace("-", "")
    assert re.fullmatch(r"lwh_phase5_verify_[0-9a-f]{32}", namespace)
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
        assert await database.version() in {6, 7}
        async with database.engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{namespace}"'))
            translated = await connection.execution_options(
                schema_translate_map={db.SCHEMA: namespace}
            )
            await translated.run_sync(db.metadata.create_all)
            await db.protect_history(translated, namespace, schema_version=7)
        async with app.state.database.transaction() as session:
            await session.execute(
                db.schema_versions.insert().values(version=7, applied_at=db.now())
            )
        actors, facility = await seed_controls(app)
        async with app.state.database.transaction() as session:
            await session.execute(
                update(t.privileges)
                .where(t.privileges.c.account_id.in_([actors["target"][0], actors["successor"][0]]))
                .values(
                    capabilities=[
                        "REGISTER",
                        "CARE",
                        "NURSING",
                        "PHARMACY",
                        "PRESCRIBE",
                        "DIAGNOSTICS",
                        "PROCEDURE",
                    ]
                )
            )
        prefix = f"/v1/clinical/{facility}"
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=ORIGIN
        ) as client:

            async def post(path, body, actor="target", key=None):
                return await client.post(
                    prefix + path,
                    json=body,
                    headers={
                        "Origin": ORIGIN,
                        "Authorization": "Bearer " + actors[actor][1],
                        "Idempotency-Key": key or db.uid(),
                    },
                )

            async def create(path, body, actor="target", key=None):
                response = await post(path, body, actor, key)
                assert response.status_code == 200, (
                    path,
                    response.status_code,
                    response.json().get("error", {}).get("code"),
                )
                return response.json()["resource"]

            async def get(path, actor="target"):
                return await client.get(
                    prefix + path, headers={"Authorization": "Bearer " + actors[actor][1]}
                )

            patient = await create(
                "/patients",
                {
                    "display_name": "Synthetic Phase 5 proof only",
                    "provisional": True,
                    "sex": "UNKNOWN",
                },
            )
            encounter = await create(
                "/encounters",
                {
                    "patient_id": patient["id"],
                    "service": "GENERAL",
                    "encounter_type": "AMBULATORY",
                    "arrival": "WALK_IN",
                    "complaint": "Synthetic engineering proof only",
                    "occurred_at": stamp(-1),
                },
            )
            context = {
                "patient_id": patient["id"],
                "encounter_id": encounter["id"],
                "occurred_at": stamp(-1),
            }
            nursing_body = {
                **context,
                "assessment": "Synthetic actual observation",
                "plan": "Synthetic actual plan",
                "escalation": "Synthetic uncertainty retained",
                "source": "Synthetic engineering proof",
                "intent_confirmed": True,
            }
            key = db.uid()
            duplicate = await asyncio.gather(
                post("/workflows/nursing-assessments", nursing_body, key=key),
                post("/workflows/nursing-assessments", nursing_body, key=key),
            )
            assert all(response.status_code == 200 for response in duplicate)
            assert duplicate[0].json() == duplicate[1].json()
            fact = duplicate[0].json()["resource"]
            product = await create(
                "/products",
                {
                    "code": {
                        "system": "urn:lwh:synthetic-only",
                        "code": db.uid(),
                        "display": "NON_CLINICAL_TEST_PRODUCT",
                        "version": "TEST-1",
                    },
                    "ingredient": "SYNTHETIC",
                    "form": "TEST",
                    "strength": "TEST",
                    "strength_unit": "TEST",
                    "permitted_routes": ["TEST"],
                    "formulary_reference": "SYNTHETIC_NOT_REAL_ADOPTION",
                    "valid_until": stamp(3),
                },
            )
            medicine = await create(
                "/medications",
                {
                    **context,
                    "product_id": product["id"],
                    "indication": "SYNTHETIC_ONLY",
                    "dose": "1",
                    "dose_unit": "TEST",
                    "route": "TEST",
                    "timing": "TEST_ONLY",
                    "starts_at": stamp(-2),
                    "stops_at": stamp(2),
                    "substitution": "NOT_PERMITTED",
                    "manual_safety_review": "SYNTHETIC_ONLY",
                    "reconciliation": "SYNTHETIC_ONLY",
                },
            )
            for version, action in [(1, "SIGN"), (2, "VERIFY")]:
                medicine = await create(
                    f"/medications/{medicine['id']}/actions",
                    {
                        "patient_id": patient["id"],
                        "expected_version": version,
                        "action": action,
                        "safety_review": "SYNTHETIC_ONLY",
                        "reason": "Synthetic actual author intent",
                        "intent_confirmed": True,
                    },
                )
            lot = await create(
                "/stock",
                {
                    "product_id": product["id"],
                    "batch": "SYNTHETIC_CONCURRENT_RESERVATION",
                    "expires_at": stamp(4),
                    "quantity": "10",
                    "unit": "TEST",
                    "evidence": "Synthetic actual physical receipt",
                },
            )
            hold = {
                **context,
                "medication_id": medicine["id"],
                "expected_medication_version": 3,
                "lot_id": lot["id"],
                "expected_lot_version": 1,
                "quantity": "8",
                "unit": "TEST",
                "expires_at": stamp(1),
                "reason": "Synthetic physical reservation",
                "intent_confirmed": True,
            }
            raced = await asyncio.gather(
                post("/workflows/stock-holds", hold), post("/workflows/stock-holds", hold)
            )
            assert sorted(response.status_code for response in raced) == [200, 409]
            task = await create(
                "/tasks",
                {
                    **context,
                    "title": "Synthetic unresolved clinical work",
                    "instructions": "Preserve actual responsible clinician",
                    "owner_id": actors["target"][0],
                    "due_at": stamp(1),
                },
            )
            current = (await get(f"/records/{encounter['id']}")).json()
            offered = await create(
                "/workflows/handovers",
                {
                    **context,
                    "expected_encounter_version": current["version"],
                    "recipient_id": actors["successor"][0],
                    "capability": "CARE",
                    "summary": "Synthetic actual current work summary",
                    "due_at": stamp(1),
                    "reason": "Synthetic actual handover",
                    "intent_confirmed": True,
                },
            )
            assert (await get(f"/records/{task['id']}", "successor")).status_code == 403
            accepted = {
                "patient_id": patient["id"],
                "expected_version": 1,
                "action": "ACCEPT",
                "occurred_at": stamp(-1),
                "reason": "Synthetic personal current acceptance",
                "intent_confirmed": True,
            }
            key = db.uid()
            responses = await asyncio.gather(
                post(f"/workflows/handovers/{offered['id']}/actions", accepted, "successor", key),
                post(f"/workflows/handovers/{offered['id']}/actions", accepted, "successor", key),
            )
            assert (
                all(response.status_code == 200 for response in responses)
                and responses[0].json() == responses[1].json()
            )
            transferred = (await get(f"/records/{task['id']}", "successor")).json()
            assert transferred["data"]["owner_id"] == actors["successor"][0]
            work = (await get("/worklist?kind=task", "successor")).json()
            assert work["ordering"] == "ACTUAL_DUE_TIME" and any(
                row["id"] == task["id"] for row in work["items"]
            )
        try:
            async with app.state.database.transaction() as session:
                await session.execute(
                    update(t.records).where(t.records.c.id == fact["id"]).values(status="TAMPER")
                )
        except DBAPIError as exc:
            assert getattr(exc.orig, "sqlstate", None) == "P0001"
        else:
            raise AssertionError("Actual clinical fact accepted an overwrite")
        async with app.state.database.transaction() as session:
            rows = await session.scalar(select(func.count()).select_from(t.records))
            projected = await session.scalar(select(func.count()).select_from(index))
            assert rows == projected
        restarted = create_platform_app(settings)
        await restarted.state.database.engine.dispose()
        restarted.state.database.engine = mapped
        restarted.state.database.session = async_sessionmaker(mapped, expire_on_commit=False)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=restarted), base_url=ORIGIN
        ) as client:
            response = await client.get(
                prefix + f"/records/{task['id']}",
                headers={"Authorization": "Bearer " + actors["successor"][1]},
            )
            assert (
                response.status_code == 200
                and response.json()["data"]["owner_id"] == actors["successor"][0]
            )
        print(
            json.dumps(
                {
                    "phase5_postgres_verification": "PASSED",
                    "concurrent_actual_fact_retries": "ONE_EFFECT_IDENTICAL_RECEIPTS",
                    "concurrent_stock_reservations": "ONE_ACCEPTED_NO_OVER_RESERVATION",
                    "concurrent_personal_handover_acceptance": "ONE_EFFECT_IDENTICAL_RECEIPTS",
                    "unaccepted_successor_chart_access": "DENIED",
                    "actual_fact_overwrite": "REJECTED",
                    "work_projection": "ALL_SOURCE_RECORDS_INDEXED",
                    "restart": "OWNERSHIP_PERSISTED",
                    "production_domain_records_seeded": 0,
                }
            ),
            flush=True,
        )
    finally:
        assert re.fullmatch(r"lwh_phase5_verify_[0-9a-f]{32}", namespace) and namespace != db.SCHEMA
        async with database.engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{namespace}" CASCADE'))
        await database.engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except Exception as exc:  # noqa: BLE001 -- never render secrets, source records or provider bodies
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        print(
            json.dumps(
                {
                    "phase5_postgres_verification": "FAILED",
                    "error_type": type(exc).__name__,
                    "source": Path(frame.filename).name,
                    "line": frame.lineno,
                    "sqlstate": getattr(getattr(exc, "orig", None), "sqlstate", None),
                }
            )
        )
        raise SystemExit(1) from None
