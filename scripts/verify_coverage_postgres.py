"""Qualify administrative coverage on actual Neon in two disposable reporting tables."""

import asyncio
import json
import re
import sys
import traceback
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api/src"))
from lw_care_api.platform import db
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.reporting import tables as t
from lw_care_api.platform.reporting.coverage import coverage


async def verify():
    database = db.Database(PlatformSettings(_env_file=ROOT / ".env.platform.local").database_url)
    namespace = "lwh_coverage_verify_" + db.uid().replace("-", "")
    assert re.fullmatch(r"lwh_coverage_verify_[0-9a-f]{32}", namespace)
    created = False
    try:
        assert await database.version() == 8
        async with database.engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{namespace}"'))
            created = True
            target = await connection.execution_options(schema_translate_map={db.SCHEMA: namespace})
            await target.run_sync(
                lambda c: db.metadata.create_all(c, tables=[t.obligations, t.returns])
            )
        mapped = database.engine.execution_options(schema_translate_map={db.SCHEMA: namespace})
        sessions = async_sessionmaker(mapped, expire_on_commit=False)
        facilities = [db.uid(), db.uid()]
        async with sessions() as session, session.begin():
            obligations, returns = [], []
            for facility in facilities:
                for number in range(210):
                    identifier = db.uid()
                    obligations.append(
                        {
                            "id": identifier,
                            "scope_type": "FACILITY",
                            "scope_id": facility,
                            "facility_id": facility,
                            "region_id": None,
                            "zone_id": None,
                            "hierarchy_snapshot": [],
                            "stream": "FACILITY_ACTIVITY",
                            "period_start": f"2025-01-01T00:00:00.{number:06d}+00:00",
                            "period_end": "2025-02-01T00:00:00.000000+00:00",
                            "due_at": "2025-02-02T00:00:00.000000+00:00",
                            "timezone": "UTC",
                            "definition_ids": [],
                            "adoption_reference": "SYNTHETIC_SQL_QUALIFICATION_ONLY",
                            "created_by": "SYNTHETIC",
                            "created_at": db.now(),
                        }
                    )
                    if number % 5 != 4:
                        returns.append(
                            {
                                "id": db.uid(),
                                "obligation_id": identifier,
                                "version": 1,
                                "state": [
                                    "DRAFT",
                                    "SUBMITTED",
                                    "VERIFIED",
                                    "RETURNED_FOR_CORRECTION",
                                ][number % 5],
                                "payload_ciphertext": "SYNTHETIC_NOT_OPENED_BY_AGGREGATE",
                                "source_hash": "0" * 64,
                                "created_by": "SYNTHETIC",
                                "received_at": "2025-02-03T00:00:00.000000+00:00",
                                "updated_at": db.now(),
                            }
                        )
            await session.execute(t.obligations.insert(), obligations)
            await session.execute(t.returns.insert(), returns)
        async with sessions() as session, session.begin():
            actor = {
                "id": db.uid(),
                "grants": [
                    {
                        "role": "REPORTING_OFFICER",
                        "scope_type": "FACILITY",
                        "scope_id": facilities[0],
                    }
                ],
            }
            value = await coverage(session, actor)
            assert value["totals"] == {
                "expected": 210,
                "missing": 42,
                "draft": 42,
                "submitted": 42,
                "returned_for_correction": 42,
                "verified": 42,
                "current_received": 84,
                "on_time_current_receipt": 0,
                "late_current_receipt": 84,
                "overdue_submission": 126,
            }
            actor["grants"].append(
                {"role": "DATA_GOVERNOR", "scope_type": "GLOBAL", "scope_id": "GLOBAL"}
            )
            assert (await coverage(session, actor))["totals"]["expected"] == 420
            actor["grants"] = [
                {"role": "REPORTING_OFFICER", "scope_type": "FACILITY", "scope_id": db.uid()}
            ]
            assert (await coverage(session, actor))["receipt_fraction"] is None
    finally:
        if created:
            async with database.engine.begin() as connection:
                await connection.execute(text(f'DROP SCHEMA "{namespace}" CASCADE'))
        await database.engine.dispose()
    result = {
        "outcome": "PASSED",
        "synthetic_obligations": 420,
        "scoped_expected": 210,
        "duplicate_grants_do_not_duplicate": True,
        "empty_denominator": "NOT_ESTABLISHED",
        "production_reporting_records_seeded": 0,
        "disposable_schema_removed": True,
    }
    (ROOT / ".toolchain/coverage-postgres.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except Exception as exc:  # noqa: BLE001 -- no provider bodies, source data or credentials
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        print(
            json.dumps(
                {
                    "coverage_postgres": "FAILED",
                    "error_type": type(exc).__name__,
                    "source": Path(frame.filename).name,
                    "line": frame.lineno,
                }
            )
        )
        raise SystemExit(1) from None
