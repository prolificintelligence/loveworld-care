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


async def verify():
    cfg = PlatformSettings(_env_file=ROOT / ".env.platform.local")
    database = db.Database(cfg.database_url)
    namespace = "lwh_templates_verify_" + db.uid().replace("-", "")
    assert re.fullmatch(r"lwh_templates_verify_[0-9a-f]{32}", namespace)
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
    result = {"template_postgres": "RUNNING", "schema_version": 8}
    try:
        assert await database.version() == 8
        async with database.transaction() as session:
            before = [
                await session.scalar(select(func.count()).select_from(table))
                for table in (t.definitions, t.obligations)
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
                assert response.status_code == 200
                return response.json()

            async def decide(row, action, actor="proposer"):
                return await create(
                    f"/templates/{row['id']}/actions",
                    {
                        "expected_version": row["version"],
                        "action": action,
                        "reason": "Synthetic actual qualification decision",
                        "evidence": "Synthetic independent examination of the packaged proposal and full mapping",
                        "intent_confirmed": True,
                    },
                    actor,
                )

            pack = await get("/template-proposals")
            body = {
                "edition": pack["edition"],
                "form_code": "FACILITY-MONTHLY",
                "valid_from": stamp(-10),
                "valid_until": stamp(10),
                "authority_reference": "Synthetic qualification, never actual Director adoption",
                "intent_confirmed": True,
            }
            key = db.uid()
            replies = await asyncio.gather(
                post("/template-proposals/prepare", body, key=key),
                post("/template-proposals/prepare", body, key=key),
            )
            assert (
                all(reply.status_code == 200 for reply in replies)
                and replies[0].json() == replies[1].json()
            )
            row = replies[0].json()["resource"]
            detail = await get(f"/templates/{row['id']}")
            assert len(detail["definitions"]) == 15 and row["state"] == "DRAFT"
            row = await decide(row, "SUBMIT")
            denied = await post(
                f"/templates/{row['id']}/actions",
                {
                    "expected_version": row["version"],
                    "action": "REVIEW_ACCEPT",
                    "reason": "Synthetic forbidden self review",
                    "evidence": "Must not pass",
                    "intent_confirmed": True,
                },
            )
            assert denied.status_code in {403, 404}
            row = await decide(row, "REVIEW_ACCEPT", "successor")
            row = await decide(row, "ADOPT")
            obligation = await create(
                "/obligations",
                {
                    "scope_type": "FACILITY",
                    "scope_id": facility,
                    "stream": "FACILITY_ACTIVITY",
                    "period_start": stamp(-4),
                    "period_end": stamp(-3),
                    "due_at": stamp(1),
                    "timezone": "Africa/Lagos",
                    "definition_ids": row["definition_ids"],
                    "adoption_reference": "Synthetic exact calendar authority",
                    "template_id": row["id"],
                    "template_version": row["version"],
                },
            )
            frozen = await get(f"/obligations/{obligation['id']}/template", "target")
            draft = await create(
                f"/obligations/{obligation['id']}/draft",
                {
                    "expected_version": 0,
                    "values": [
                        {
                            "definition_id": item["id"],
                            "completeness": "UNKNOWN",
                            "explanation": "Synthetic source unavailable; no fabricated clinical zeros",
                        }
                        for item in detail["definitions"]
                    ],
                    "source_method": "Synthetic source review",
                    "reconciliation": "Explicit missingness for all fields",
                    "reason": "Synthetic draft qualification",
                },
                "target",
            )
            assert draft["state"] == "DRAFT"
            await decide(row, "WITHDRAW")
            assert await get(f"/obligations/{obligation['id']}/template", "target") == frozen
            async with app.state.database.transaction() as session:
                assert await session.scalar(select(func.count()).select_from(t.definitions)) == 15
                history = list(
                    (
                        await session.execute(
                            select(t.history).where(
                                t.history.c.resource_type == "REPORTING_TEMPLATE"
                            )
                        )
                    ).mappings()
                )
                assert len(history) == 5
                signatures, hashes = await verify_lineage(
                    session,
                    {"schema_version": 8, "data_key_hex": cfg.data_key_hex},
                    app.state.box,
                    settings,
                )
                assert hashes >= 22
            for mutation in (
                t.history.update().values(action="SYNTHETIC_FORBIDDEN"),
                t.history.delete(),
            ):
                blocked = False
                try:
                    async with app.state.database.transaction() as session:
                        await session.execute(mutation)
                except DBAPIError as exc:
                    blocked = getattr(exc.orig, "sqlstate", None) == "P0001"
                assert blocked
            async with app.state.database.transaction() as session:
                await session.execute(
                    update(db.grants)
                    .where(
                        db.grants.c.account_id == actors["proposer"][0],
                        db.grants.c.role == "DATA_GOVERNOR",
                    )
                    .values(revoked=True)
                )
            assert (await post("/template-proposals/prepare", body, key=key)).status_code == 404
        async with database.transaction() as session:
            after = [
                await session.scalar(select(func.count()).select_from(table))
                for table in (t.definitions, t.obligations)
            ]
        assert before == after
        result.update(
            template_postgres="PASSED",
            proposed_definitions=15,
            concurrent_prepare="ONE_RECEIPT_AND_ONE_DRAFT",
            independent_review="ENFORCED",
            frozen_binding_after_withdrawal="UNCHANGED",
            history_hashes_verified=hashes,
            clinical_signatures_verified=signatures,
            history_update_and_delete="REJECTED",
            revoked_receipt_replay="DENIED",
            production_reporting_counts_unchanged=True,
            production_reporting_records_seeded=0,
        )
    finally:
        assert (
            re.fullmatch(r"lwh_templates_verify_[0-9a-f]{32}", namespace) and namespace != db.SCHEMA
        )
        async with database.engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{namespace}" CASCADE'))
        await database.engine.dispose()
        result["disposable_schema_removed"] = True
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except Exception as exc:  # noqa: BLE001 -- no DSN, credential or provider response in diagnostics
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        print(
            json.dumps(
                {
                    "template_postgres": "FAILED",
                    "error_type": type(exc).__name__,
                    "source": Path(frame.filename).name,
                    "line": frame.lineno,
                    "sqlstate": getattr(getattr(exc, "orig", None), "sqlstate", None),
                }
            )
        )
        raise SystemExit(1) from None
