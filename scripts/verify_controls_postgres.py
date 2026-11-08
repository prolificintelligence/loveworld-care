"""Actual Neon control concurrency and recovery proof in a disposable namespace."""

import asyncio
import json
import re
import sys
from pathlib import Path

import httpx
import pyotp
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api/src"))
sys.path.insert(0, str(ROOT / "tests/integration"))
from lw_care_api.platform import db
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.control import tables as t
from lw_care_api.platform.control.jobs import claim, finish
from lw_care_api.platform.main import create_platform_app
from lw_care_api.platform.security import resolve_session
from test_platform_controls import ORIGIN, PASSWORD, seed_controls


async def verify():
    cfg = PlatformSettings(_env_file=ROOT / ".env.platform.local")
    database = db.Database(cfg.database_url)
    namespace = "lwh_controls_verify_" + db.uid().replace("-", "")
    assert re.fullmatch(r"lwh_controls_verify_[0-9a-f]{32}", namespace)
    mapped = database.engine.execution_options(schema_translate_map={db.SCHEMA: namespace})
    settings = cfg.model_copy(
        update={
            "environment": "test",
            "web_origin": ORIGIN,
            "dispatch_recovery_after_commit": False,
            "resend_api_key": "synthetic-not-a-sending-key",
            "email_from": "Synthetic <sender@synthetic.invalid>",
        }
    )
    app = create_platform_app(settings)
    await app.state.database.engine.dispose()
    app.state.database.engine = mapped
    app.state.database.session = async_sessionmaker(mapped, expire_on_commit=False)
    try:
        assert await database.version() in {3, 4, 5}
        async with database.engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{namespace}"'))
            translated = await connection.execution_options(
                schema_translate_map={db.SCHEMA: namespace}
            )
            await translated.run_sync(db.metadata.create_all)
            for table in t.IMMUTABLE:
                await translated.execute(
                    text(
                        f'CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE ON "{namespace}"."{table.name}" FOR EACH ROW EXECUTE FUNCTION health_platform.reject_history_mutation()'
                    )
                )
        async with app.state.database.transaction() as session:
            await session.execute(
                db.schema_versions.insert().values(version=4, applied_at=db.now())
            )
        actors, _facility = await seed_controls(app)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=ORIGIN
        ) as client:

            def headers(name, key=None):
                return {
                    "Authorization": "Bearer " + actors[name][1],
                    "Origin": ORIGIN,
                    "Idempotency-Key": key or db.uid(),
                }

            body = {"password": PASSWORD, "otp": pyotp.TOTP(actors["target"][2]).now()}
            key = db.uid()
            codes = await asyncio.gather(
                *(
                    client.post(
                        "/v1/auth/recovery-codes", json=body, headers=headers("target", key)
                    )
                    for _ in range(2)
                )
            )
            assert (
                all(response.status_code == 200 for response in codes)
                and codes[0].json() == codes[1].json()
            )
            values = codes[0].json()["resource"]["codes"]
            requests = await asyncio.gather(
                *(
                    client.post(
                        "/v1/auth/recovery/request",
                        json={"email": "target@synthetic.invalid"},
                        headers={"Origin": ORIGIN},
                    )
                    for _ in range(2)
                )
            )
            assert all(response.status_code == 202 for response in requests), [
                response.status_code for response in requests
            ]
            async with app.state.database.transaction() as session:
                assert await session.scalar(select(func.count()).select_from(t.backup_codes)) == 10
                assert await session.scalar(select(func.count()).select_from(t.recoveries)) == 1
                assert await session.scalar(select(func.count()).select_from(t.jobs)) == 1
                job = (await session.execute(select(t.jobs))).mappings().one()
                payload = json.loads(app.state.box.decrypt(job["payload_ciphertext"]))
            claims = await asyncio.gather(claim(app.state.database), claim(app.state.database))
            assert sum(value is not None for value in claims) == 1
            claimed = next(value for value in claims if value)
            assert await finish(app.state.database, claimed, "RETRY_DEPENDENCY_UNAVAILABLE", None)
            proof = {"token": payload["token"], "method": "BACKUP_CODE", "proof": values[0]}
            proofs = await asyncio.gather(
                *(
                    client.post("/v1/auth/recovery/prove", json=proof, headers={"Origin": ORIGIN})
                    for _ in range(2)
                )
            )
            assert all(
                response.status_code == 200 and response.json()["status"] == "AUTHORIZED"
                for response in proofs
            )
            async with app.state.database.transaction() as session:
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(t.backup_codes)
                        .where(t.backup_codes.c.used_at.is_not(None))
                    )
                    == 1
                )
            setup = await client.post(
                "/v1/auth/recovery/setup",
                json={"token": payload["token"], "password": "A-new-synthetic-password-2026"},
                headers={"Origin": ORIGIN},
            )
            assert setup.status_code == 200
            completed = await client.post(
                "/v1/auth/recovery/complete",
                json={
                    "token": payload["token"],
                    "otp": pyotp.TOTP(setup.json()["setup_key"]).now(),
                },
                headers={"Origin": ORIGIN},
            )
            assert completed.status_code == 200
            async with app.state.database.transaction() as session:
                assert await resolve_session(session, actors["target"][1]) is None
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(db.grants)
                        .where(
                            db.grants.c.account_id == actors["target"][0],
                            db.grants.c.revoked.is_(False),
                        )
                    )
                    == 1
                )
                for table in (t.audit, t.job_attempts):
                    try:
                        async with session.begin_nested():
                            await session.execute(table.update().values(id=db.uid()))
                    except DBAPIError:
                        pass
                    else:
                        raise AssertionError("Protected operating history accepted mutation")
        restarted = create_platform_app(settings)
        await restarted.state.database.engine.dispose()
        restarted.state.database.engine = mapped
        restarted.state.database.session = async_sessionmaker(mapped, expire_on_commit=False)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=restarted), base_url=ORIGIN
        ) as client:
            response = await client.get("/v1/operations/jobs", headers=headers("admin"))
            assert response.status_code == 200 and response.json()["items"][0]["state"] == "RETRY"
        print(
            json.dumps(
                {
                    "controls_postgres_verification": "PASSED",
                    "concurrent_backup_generation": "ONE_SET_AND_IDENTICAL_RECEIPTS",
                    "concurrent_recovery_requests": "ONE_CHALLENGE_AND_JOB",
                    "worker_claims": "ONE_LEASE",
                    "backup_code_use": "ONE_CONSUMPTION",
                    "old_sessions": "REVOKED",
                    "identity_and_grants": "PRESERVED",
                    "history_mutation": "REJECTED",
                    "restart": "PERSISTED",
                    "production_test_records_seeded": 0,
                }
            )
        )
    finally:
        assert re.fullmatch(r"lwh_controls_verify_[0-9a-f]{32}", namespace)
        async with database.engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{namespace}" CASCADE'))
        await database.engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except Exception as exc:  # noqa: BLE001 -- no secrets, response bodies or DSNs
        import traceback

        last = traceback.extract_tb(exc.__traceback__)[-1]
        print(
            json.dumps(
                {
                    "controls_postgres_verification": "FAILED",
                    "error_type": type(exc).__name__,
                    "source": Path(last.filename).name,
                    "line": last.lineno,
                    "errno": getattr(exc, "errno", None),
                    "frames": [
                        {"source": Path(frame.filename).name, "line": frame.lineno}
                        for frame in traceback.extract_tb(exc.__traceback__)
                    ],
                }
            )
        )
        raise SystemExit(1) from None
