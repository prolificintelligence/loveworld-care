"""Exercise readiness queries on Neon in a disposable schema; never seed live care."""

import asyncio
import json
import re
import sys
import traceback
from pathlib import Path
from time import perf_counter

import httpx
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api/src"))
sys.path.insert(0, str(ROOT / "tests/integration"))
from lw_care_api.platform import db
from lw_care_api.platform.clinical import flow_index as fi
from lw_care_api.platform.clinical import store as cs
from lw_care_api.platform.clinical import tables as ct
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.main import create_platform_app
from lw_care_api.platform.reporting import tables as rt
from test_platform_controls import ORIGIN, seed_controls, stamp


async def verify():
    cfg = PlatformSettings(_env_file=ROOT / ".env.platform.local")
    database = db.Database(cfg.database_url)
    namespace = "lwh_readiness_verify_" + db.uid().replace("-", "")
    assert re.fullmatch(r"lwh_readiness_verify_[0-9a-f]{32}", namespace)
    settings = cfg.model_copy(
        update={
            "environment": "test",
            "web_origin": ORIGIN,
            "dispatch_recovery_after_commit": False,
            "enforce_activation_dossiers": False,
            "resend_api_key": "synthetic-not-a-sending-key",
        }
    )
    app = create_platform_app(settings)
    await app.state.database.engine.dispose()
    mapped = database.engine.execution_options(schema_translate_map={db.SCHEMA: namespace})
    app.state.database.engine = mapped
    app.state.database.session = async_sessionmaker(mapped, expire_on_commit=False)
    created = False
    observations = {}
    try:
        assert await database.version() == 7
        async with database.engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{namespace}"'))
            translated = await connection.execution_options(
                schema_translate_map={db.SCHEMA: namespace}
            )
            await translated.run_sync(db.metadata.create_all)
            await db.protect_history(translated, namespace, schema_version=7)
        created = True
        print(json.dumps({"readiness_postgres_stage": "isolated_schema_created"}), flush=True)
        async with app.state.database.transaction() as session:
            await session.execute(
                db.schema_versions.insert().values(version=7, applied_at=db.now())
            )
        actors, facility = await seed_controls(app)
        print(json.dumps({"readiness_postgres_stage": "synthetic_controls_seeded"}), flush=True)
        actor = actors["target"][0]
        async with app.state.database.transaction() as session:
            await session.execute(
                db.grants.insert().values(
                    id=db.uid(),
                    account_id=actor,
                    role="SAFETY_REPORTER",
                    scope_type="FACILITY",
                    scope_id=facility,
                    valid_from=stamp(-1),
                    valid_until=stamp(1),
                    revoked=False,
                    grantor="SYNTHETIC",
                )
            )
            category = db.uid()
            await session.execute(
                rt.event_categories.insert().values(
                    id=category,
                    name="Synthetic pagination only",
                    category_version="SYNTHETIC",
                    payload={},
                    created_by=actor,
                    created_at=db.now(),
                )
            )
            cases, accounts, grants = [], [], []
            expected = set()
            due = stamp(1)
            for number in range(450):
                identifier = db.uid()
                eligible = number >= 220
                if eligible:
                    expected.add(identifier)
                cases.append(
                    {
                        "id": identifier,
                        "scope_type": "FACILITY",
                        "scope_id": facility,
                        "facility_id": facility,
                        "hierarchy_snapshot": [],
                        "category_id": category,
                        "version": 1,
                        "state": "REPORTED",
                        "urgent": False,
                        "created_by": actor if eligible else actors["successor"][0],
                        "occurred_at": stamp(-1),
                        "created_at": db.now(),
                        "acknowledge_by": due if eligible else stamp(-1),
                        "payload_ciphertext": app.state.box.encrypt("{}"),
                    }
                )
            for number in range(220):
                identifier = db.uid()
                accounts.append(
                    {
                        "id": identifier,
                        "name": f"Scale recipient {number:04}",
                        "email": f"scale{number}@synthetic.invalid",
                        "active": True,
                        "totp_last_step": -1,
                        "created_at": db.now(),
                    }
                )
                for _ in range(5):
                    grants.append(
                        {
                            "id": db.uid(),
                            "account_id": identifier,
                            "role": "SAFETY_REVIEWER",
                            "scope_type": "FACILITY",
                            "scope_id": facility,
                            "valid_from": stamp(-1),
                            "valid_until": stamp(1),
                            "revoked": False,
                            "grantor": "SYNTHETIC",
                        }
                    )
            await session.execute(rt.cases.insert(), cases)
            await session.execute(db.accounts.insert(), accounts)
            await session.execute(db.grants.insert(), grants)
        headers = {"Authorization": "Bearer " + actors["target"][1]}
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=ORIGIN, headers=headers
        ) as client:
            found, cursor = [], ""
            for _ in range(5):
                response = await client.get("/v1/reporting/safety-cases", params={"after": cursor})
                assert response.status_code == 200
                payload = response.json()
                found.extend(row["id"] for row in payload["items"])
                cursor = payload["next_cursor"]
                if not cursor:
                    break
            assert len(found) == len(set(found)) == len(expected) and set(found) == expected
            people = await client.get(
                "/v1/reporting/people", params={"query": "Scale recipient 0219"}
            )
            assert people.status_code == 200 and len(people.json()["items"]) == 1
            observations.update(
                eligible_cases=len(found),
                candidate_cases=450,
                recipient_grants=1100,
                late_recipient_found=True,
            )
            print(
                json.dumps({"readiness_postgres_stage": "queues_and_recipients_passed"}), flush=True
            )
        async with app.state.database.transaction() as session:
            records, projections = [], []
            for _ in range(2500):
                identifier = db.uid()
                records.append(
                    {
                        "id": identifier,
                        "facility_id": facility,
                        "kind": "patient",
                        "patient_id": None,
                        "encounter_id": None,
                        "service": "GENERAL",
                        "status": "ACTIVE",
                        "version": 1,
                        "created_by": actor,
                        "authority_node_id": cfg.authority_node_id,
                        "authority_epoch": "1",
                        "created_at": db.now(),
                        "updated_at": db.now(),
                        "content_ciphertext": cs.seal(
                            app.state.box, identifier, {"display_name": "Synthetic scale"}
                        ),
                        "search_tokens": [],
                        "identifier_hash": None,
                    }
                )
                projections.append(
                    {
                        "record_id": identifier,
                        "facility_id": facility,
                        "kind": "patient",
                        "service": "GENERAL",
                        "status": "ACTIVE",
                        "indexed_version": 1,
                    }
                )
            await session.execute(ct.records.insert(), records)
            await session.execute(fi.index.insert(), projections)
        async with app.state.database.transaction() as session:
            started = perf_counter()
            assert await fi.ready(session, facility)
            observations["facility_readiness_ms_2500_records"] = round(
                (perf_counter() - started) * 1000, 2
            )
            await session.execute(
                update(fi.index)
                .where(fi.index.c.record_id == records[-1]["id"])
                .values(indexed_version=0)
            )
            assert not await fi.ready(session, facility)
            assert not await fi.ready(session)
            assert await fi.ready(session, db.uid())
            observations["stale_projection_isolated_global_assurance_red"] = True
        observations.update(outcome="PASSED", schema_version=7, production_care_records_written=0)
    finally:
        if created:
            async with database.engine.begin() as connection:
                await connection.execute(text(f'DROP SCHEMA "{namespace}" CASCADE'))
            observations["disposable_schema_removed"] = True
        await database.engine.dispose()
    folder = ROOT / ".release-evidence"
    folder.mkdir(exist_ok=True)
    (folder / "readiness-postgres.json").write_text(
        json.dumps(observations, indent=2), encoding="utf-8"
    )
    print(json.dumps(observations))


if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except Exception as exc:  # noqa: BLE001 -- never expose database/provider credentials
        frame = next(
            frame
            for frame in reversed(traceback.extract_tb(exc.__traceback__))
            if frame.filename == __file__
        )
        print(
            json.dumps(
                {
                    "readiness_postgres": "FAILED",
                    "error_type": type(exc).__name__,
                    "source": Path(frame.filename).name,
                    "line": frame.lineno,
                }
            )
        )
        raise SystemExit(1) from None
