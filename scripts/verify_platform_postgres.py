"""Verify the installed Neon schema and concurrency in a disposable isolated namespace."""

import asyncio
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api/src"))

from lw_care_api.platform import db
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.main import create_platform_app
from lw_care_api.platform.security import issue_session


async def verify():
    cfg = PlatformSettings(_env_file=ROOT / ".env.platform.local")
    database = db.Database(cfg.database_url)
    namespace = "lwh_verify_" + uuid4().hex
    assert re.fullmatch(r"lwh_verify_[0-9a-f]{32}", namespace)
    try:
        async with database.transaction() as session:
            version = await session.scalar(select(func.max(db.schema_versions.c.version)))
            triggers = await session.scalar(
                text("""select count(*) from information_schema.triggers
                where trigger_schema='health_platform' and trigger_name='immutable_history'""")
            )
            assert (
                (version == 2 and triggers == 20)
                or (version == 3 and triggers == 56)
                or (version == 4 and triggers == 74)
                or (version == 5 and triggers == 76)
                or (version in {6, 7} and triggers == 96)
            )  # UPDATE and DELETE entries for the protected history tables.
        async with database.engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{namespace}"'))
            translated = await connection.execution_options(
                schema_translate_map={db.SCHEMA: namespace}
            )
            await translated.run_sync(db.metadata.create_all)
            await translated.execute(
                text(f'''CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE
                ON "{namespace}".audit FOR EACH ROW EXECUTE FUNCTION health_platform.reject_history_mutation()''')
            )
        test_cfg = cfg.model_copy(update={"environment": "test"})
        app = create_platform_app(test_cfg)
        await app.state.database.engine.dispose()
        app.state.database.engine = database.engine.execution_options(
            schema_translate_map={db.SCHEMA: namespace}
        )
        app.state.database.session = async_sessionmaker(
            app.state.database.engine, expire_on_commit=False
        )
        moment = datetime.now(UTC)
        actor_id = str(uuid4())
        async with app.state.database.transaction() as session:
            await session.execute(
                db.accounts.insert().values(
                    id=actor_id,
                    name="Isolated release verification",
                    email="release-verification@example.invalid",
                    active=True,
                    totp_last_step=-1,
                    created_at=db.now(),
                )
            )
            await session.execute(
                db.grants.insert().values(
                    id=db.uid(),
                    account_id=actor_id,
                    role="PLATFORM_ADMIN",
                    scope_type="GLOBAL",
                    scope_id="GLOBAL",
                    valid_from=(moment - timedelta(minutes=1)).isoformat(),
                    valid_until=(moment + timedelta(minutes=10)).isoformat(),
                    revoked=False,
                    grantor="RELEASE_VERIFICATION",
                )
            )
            bearer = await issue_session(session, actor_id, 10)
        headers = {"Authorization": "Bearer " + bearer, "Idempotency-Key": str(uuid4())}
        body = {
            "name": "Isolated verification region",
            "code": "VERIFY-" + uuid4().hex,
            "kind": "REGION",
            "valid_from": (moment - timedelta(minutes=1)).isoformat(),
        }
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=cfg.web_origin
        ) as client:
            first, second = await asyncio.gather(
                *[
                    client.post("/v1/organisation-units", json=body, headers=headers)
                    for _ in range(2)
                ]
            )
            assert first.status_code == second.status_code == 200
            assert first.json() == second.json()
            conflict = await client.post(
                "/v1/organisation-units", json={**body, "name": "Different body"}, headers=headers
            )
            assert conflict.status_code == 409
        async with app.state.database.transaction() as session:
            assert await session.scalar(select(func.count()).select_from(db.units)) == 1
            assert await session.scalar(select(func.count()).select_from(db.operations)) == 1
            assert await session.scalar(select(func.count()).select_from(db.revisions)) == 1
            assert await session.scalar(select(func.count()).select_from(db.outbox)) == 1
            try:
                async with session.begin_nested():
                    await session.execute(db.audit.update().values(outcome="ERROR"))
            except DBAPIError:
                immutable = True
            else:
                immutable = False
            assert immutable
        print(
            json.dumps(
                {
                    "postgres_verification": "PASSED",
                    "schema_version": version,
                    "protected_tables": triggers // 2,
                    "concurrent_duplicate_effects": 1,
                    "key_reuse_conflict": 409,
                    "append_only_trigger": "ENFORCED",
                    "production_records_seeded": 0,
                }
            )
        )
    finally:
        async with database.engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{namespace}" CASCADE'))
        await database.engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except Exception as exc:  # noqa: BLE001 -- avoid printing exception values containing connection secrets
        print(json.dumps({"postgres_verification": "FAILED", "error_type": type(exc).__name__}))
        raise SystemExit(1) from None
