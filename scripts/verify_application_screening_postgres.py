"""Isolated real-Neon screening/order proofs; never operating or scanner acceptance.

Local ASGI uses a pooled fixture engine, not the Vercel production connection pool.
All outbound providers are excluded. Only a checked disposable schema is removed.
"""

import argparse
import asyncio
import json
import re
import secrets
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
from release_guard import committed_source
from sqlalchemy import func, literal, select, text, union_all
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool
from test_application_screening import exercise

SCENARIOS = ("guards_and_order", "legacy_recovery", "concurrent_screen_withdraw")
OUTPUT = ROOT / ".toolchain/screening-neon-proof.json"
RESULT = {
    "status": "RUNNING",
    "qualification": "LOCAL_ASGI_POOLED_NEON_NOT_CAPACITY_OR_OPERATING_ACCEPTANCE",
    "scenarios": [],
    "schema_version": 9,
    "evidence_fixture": "LABELLED_METADATA_ONLY_NOT_SCANNER_QUALIFICATION",
    "synthetic_evidence_valid_minutes": 60,
    "clock_override": "NONE_IN_SELECTED_NEON_SCENARIOS",
    "legacy_fixture": "LEGACY_SHAPE_NOT_EXECUTED_HISTORICAL_TRANSITIONS",
    "disposable_schema_removed": False,
}


def save():
    OUTPUT.write_text(json.dumps(RESULT, indent=2) + "\n", encoding="utf-8")


async def verify(scenarios):
    cfg = PlatformSettings(_env_file=ROOT / ".env.platform.local").model_copy(
        update={
            "environment": "test",
            "data_key_hex": secrets.token_hex(32),
            "authority_node_id": db.uid(),
            "web_origin": "http://localhost:3004",
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
    namespace = "lwh_screening_verify_" + db.uid().replace("-", "")
    assert re.fullmatch(r"lwh_screening_verify_[0-9a-f]{32}", namespace) and namespace != db.SCHEMA
    RESULT["disposable_schema"] = namespace
    save()
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

    async def counts():
        from lw_care_api.platform.clinical import tables as ct
        from lw_care_api.platform.reporting import tables as rt

        tables = (
            db.accounts,
            db.units,
            db.operators,
            db.facilities,
            db.criteria,
            db.applications,
            db.evidence,
            db.inspections,
            db.decisions,
            ct.sites,
            ct.records,
            ct.events,
            rt.definitions,
            rt.obligations,
            rt.returns,
            rt.snapshots,
        )
        async with production.transaction() as session:
            return {
                row[0]: row[1]
                for row in (
                    await session.execute(
                        union_all(
                            *[
                                select(literal(table.name), func.count()).select_from(table)
                                for table in tables
                            ]
                        )
                    )
                ).all()
            }

    try:
        RESULT["production_before"] = await counts()
        save()
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
            transport=httpx.ASGITransport(app=app), base_url=cfg.web_origin
        ) as client:
            for scenario in scenarios:
                RESULT["running_scenario"] = scenario
                save()
                print(json.dumps({"scenario": scenario, "stage": "RUNNING"}), flush=True)
                RESULT["scenarios"].append(await exercise(app, client, scenario))
                save()
        for name, table in (
            ("application_history", db.revisions),
            ("decision_history", db.decisions),
        ):
            async with app.state.database.transaction() as session:
                nonempty = await session.scalar(select(func.count()).select_from(table))
            if not nonempty:
                RESULT["immutable_" + name + "_delete"] = "NOT_EXERCISED_NO_ROWS_IN_SELECTED_SUBSET"
                continue
            blocked = False
            try:
                async with app.state.database.transaction() as session:
                    await session.execute(table.delete())
            except DBAPIError as exc:
                blocked = getattr(exc.orig, "sqlstate", None) == "P0001"
            assert blocked, "Nonempty retained history deletion was not rejected"
            RESULT["immutable_" + name + "_delete"] = "REJECTED"
        RESULT["production_after"] = await counts()
        assert RESULT["production_before"] == RESULT["production_after"]
        RESULT.update(
            status="PASSED",
            production_domain_counts_unchanged=True,
            production_domain_records_seeded=0,
            provider_dispatch_invoked=False,
        )
    finally:
        for attempt in range(3):
            try:
                async with production.engine.begin() as connection:
                    await connection.execute(text(f'DROP SCHEMA IF EXISTS "{namespace}" CASCADE'))
                    remains = await connection.scalar(
                        text(
                            "SELECT count(*) FROM information_schema.schemata WHERE schema_name=:name"
                        ),
                        {"name": namespace},
                    )
                    assert remains == 0
                RESULT["disposable_schema_removed"] = True
                break
            except Exception as exc:
                RESULT.setdefault("cleanup_retries", []).append(
                    {"attempt": attempt + 1, "error_type": type(exc).__name__}
                )
                save()
                if attempt == 2:
                    raise
                await asyncio.sleep(attempt + 1)
        await harness.dispose()
        await production.engine.dispose()
        save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, action="append")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    OUTPUT = args.output.resolve()
    assert OUTPUT.parent == ROOT / ".toolchain", "Keep receipts in the local evidence directory"
    try:
        RESULT["source_commit"] = committed_source(ROOT)
        asyncio.run(verify(args.scenario or SCENARIOS))
    except Exception as exc:  # noqa: BLE001 -- never print credentials or provider response values
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        RESULT.update(
            status="FAILED",
            failure={
                "type": type(exc).__name__,
                "file": Path(frame.filename).name,
                "line": frame.lineno,
            },
        )
        save()
        print(json.dumps({"screening_neon": "FAILED", "failure": RESULT["failure"]}), flush=True)
        raise SystemExit(1) from None
    print(json.dumps(RESULT), flush=True)
