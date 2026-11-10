"""Initial affiliation guard proofs in a disposable Neon schema, never real adoption.

Local ASGI with a pooled fixture engine is not cloud capacity or human UAT.
Evidence is labelled metadata-only; no malware scan or file upload is performed.
"""

import asyncio
import json
import re
import secrets
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "services/api/src"), str(ROOT / "tests/integration")]

import httpx
from lw_care_api.db.connection import normalize_async_database_url
from lw_care_api.platform import db
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.main import create_platform_app
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool
from test_director_affiliation_conformance import ORIGIN, SCENARIOS, exercise

OUTPUT = ROOT / ".toolchain/director-neon-proof.json"
RESULT = {
    "status": "RUNNING",
    "qualification": "LOCAL_ASGI_POOLED_NEON_ENGINEERING_NOT_CAPACITY_OR_OPERATING_ADOPTION",
    "schema_version": 9,
    "scenarios": [],
    "evidence_fixture": "METADATA_ONLY_NOT_SCANNER_QUALIFICATION",
    "controlled_expiry_clock": "ADVANCED_20_MINUTES_WITHOUT_EDITING_IMMUTABLE_EVIDENCE",
}


async def verify():
    cfg = PlatformSettings(_env_file=ROOT / ".env.platform.local").model_copy(
        update={
            "environment": "test",
            "data_key_hex": secrets.token_hex(32),
            "authority_node_id": db.uid(),
            "web_origin": ORIGIN,
            "resend_api_key": "",
            "email_from": "",
            "s3_endpoint": "",
            "s3_access_key": "",
            "s3_secret_key": "",
            "s3_bucket": "",
            "clamav_host": "",
            "jobs_secret": "",
            "upstash_rest_url": "",
            "upstash_rest_token": "",
            "openrouter_api_key": "",
            "openrouter_model": "",
            "enforce_activation_dossiers": False,
            "dispatch_recovery_after_commit": False,
        }
    )
    production = db.Database(cfg.database_url)
    namespace = "lwh_director_verify_" + db.uid().replace("-", "")
    assert re.fullmatch(r"lwh_director_verify_[0-9a-f]{32}", namespace) and namespace != db.SCHEMA
    app = create_platform_app(cfg)
    await app.state.database.engine.dispose()
    url, arguments = normalize_async_database_url(cfg.database_url)
    harness = create_async_engine(
        url,
        connect_args=arguments,
        poolclass=AsyncAdaptedQueuePool,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )
    mapped = harness.execution_options(schema_translate_map={db.SCHEMA: namespace})
    app.state.database.engine = mapped
    app.state.database.session = async_sessionmaker(mapped, expire_on_commit=False)

    async def counts(database):
        async with database.transaction() as session:
            return {
                t.name: await session.scalar(select(func.count()).select_from(t))
                for t in (
                    db.accounts,
                    db.units,
                    db.operators,
                    db.facilities,
                    db.criteria,
                    db.applications,
                    db.evidence,
                    db.inspections,
                    db.decisions,
                )
            }

    try:
        before = await counts(production)
        print(json.dumps({"stage": "INSTALLING_DISPOSABLE_SCHEMA"}), flush=True)
        async with production.engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{namespace}"'))
            translated = await connection.execution_options(
                schema_translate_map={db.SCHEMA: namespace}
            )
            await translated.run_sync(db.metadata.create_all)
            await db.protect_history(translated, namespace, schema_version=9)
        async with app.state.database.transaction() as session:
            await session.execute(
                db.schema_versions.insert().values(version=9, applied_at=db.now())
            )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=ORIGIN
        ) as client:
            for scenario in SCENARIOS:
                print(json.dumps({"scenario": scenario, "stage": "RUNNING"}), flush=True)
                RESULT["scenarios"].append(await exercise(app, client, scenario))
                OUTPUT.write_text(json.dumps(RESULT, indent=2), encoding="utf-8")
        blocked = False
        try:
            async with app.state.database.transaction() as session:
                await session.execute(db.decisions.delete())
        except DBAPIError as exc:
            blocked = getattr(exc.orig, "sqlstate", None) == "P0001"
        assert blocked, "Immutable decision history was not protected"
        after = await counts(production)
        assert before == after
        RESULT.update(
            status="PASSED",
            production_before=before,
            production_after=after,
            production_domain_counts_unchanged=True,
            production_domain_records_seeded=0,
            immutable_decision_delete="REJECTED",
            provider_dispatch_invoked=False,
        )
    finally:
        async with production.engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{namespace}" CASCADE'))
        await harness.dispose()
        await production.engine.dispose()
        RESULT["disposable_schema_removed"] = True
        OUTPUT.write_text(json.dumps(RESULT, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        RESULT["source_commit"] = subprocess.check_output(
            ["git", "-c", "safe.directory=" + ROOT.as_posix(), "rev-parse", "HEAD"], text=True
        ).strip()
        asyncio.run(verify())
    except Exception as exc:  # noqa: BLE001 -- credentials/provider responses must not enter logs
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        RESULT.update(
            status="FAILED",
            failure={
                "type": type(exc).__name__,
                "file": Path(frame.filename).name,
                "line": frame.lineno,
            },
        )
        OUTPUT.write_text(json.dumps(RESULT, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"director_neon": "FAILED", "failure": RESULT["failure"]}), flush=True)
        raise SystemExit(1) from None
    print(json.dumps(RESULT), flush=True)
