"""Reproduce reporting readiness findings with isolated local synthetic fixtures.

Run with the existing workspace dev environment. No production credentials or
network providers are used. The historical-read 409 is an audit finding, not a
passing regression expectation or a measured production volume benchmark.
Output and disposable SQLite fixture files remain under ignored .toolchain/.
"""

# Imports below follow the explicit repository paths for the existing test fixtures.

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "services/api/src"))
sys.path.insert(0, str(root / "tests/integration"))
from lw_care_api.platform import db
from lw_care_api.platform.clinical import tables as ct
from lw_care_api.platform.reporting import contracts as c
from lw_care_api.platform.reporting import native
from lw_care_api.platform.reporting.store import canonical
from pydantic import ValidationError
from test_platform_native_reporting import declared_values, save, seed_sources, setup_native
from test_platform_reporting import journey, run

(root / ".toolchain").mkdir(exist_ok=True)
results = []


def fixture():
    folder = root / ".toolchain" / ("audit-probe-" + db.uid())
    folder.mkdir()
    generator = journey.__wrapped__(folder)
    return generator, next(generator)


def finish(generator):
    try:
        next(generator)
    except StopIteration:
        pass


generator, j = fixture()
try:
    definition = j.definition(source_selector="EMR_COMPLETED_ENCOUNTERS")
    start = datetime.fromisoformat(j.start)
    end = datetime.fromisoformat(j.end)
    body = {
        "scope_type": "FACILITY",
        "scope_id": j.facilities[0],
        "stream": "FACILITY_ACTIVITY",
        "period_start": start.astimezone(timezone(timedelta(hours=1))).isoformat(),
        "period_end": end.astimezone(timezone(timedelta(hours=1))).isoformat(),
        "due_at": j.due,
        "timezone": "Africa/Lagos",
        "definition_ids": [definition["id"]],
        "adoption_reference": "Synthetic offset qualification",
    }
    obligation = j.create("/obligations", body, "governor")

    async def source():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                ct.records.insert().values(
                    id=db.uid(),
                    facility_id=j.facilities[0],
                    kind="encounter",
                    status="COMPLETED",
                    service="SYNTHETIC",
                    authority_node_id=j.app.state.settings.authority_node_id,
                    authority_epoch="SYNTHETIC",
                    version=1,
                    content_ciphertext=j.app.state.box.encrypt(
                        canonical(
                            {
                                "content": {
                                    "disposition": {
                                        "occurred_at": (start + timedelta(minutes=30)).isoformat()
                                    }
                                }
                            }
                        )
                    ),
                    created_by=j.actors["reporter"][0],
                    created_at=db.now(),
                    updated_at=db.now(),
                )
            )

    run(source())
    extract = j.create(f"/obligations/{obligation['id']}/extract", {})
    actual = extract["data"]["values"][definition["id"]]["value"]
    results.append(
        {
            "control": "UTC_OFFSET_NORMALISATION",
            "expected_qualifying_contacts": 1,
            "actual_qualifying_contacts": int(actual),
            "outcome": "PASSED" if int(actual) == 1 else "FAILED",
            "source": "services/api/src/lw_care_api/platform/contracts.py",
        }
    )
    rejected = False
    try:
        c.Obligation.model_validate(
            body
            | {
                "period_start": "2026-11-01T00:00:00",
                "period_end": "2026-11-02T00:00:00",
                "due_at": "2026-11-03T00:00:00",
            }
        )
    except ValidationError:
        rejected = True
    results.append(
        {
            "control": "NAIVE_REPORTING_TIMESTAMPS",
            "rejected": rejected,
            "outcome": "PASSED" if rejected else "FAILED",
            "source": "services/api/src/lw_care_api/platform/contracts.py",
        }
    )
finally:
    finish(generator)

generator, j = fixture()
try:
    obligation, definitions = setup_native(j)
    run(seed_sources(j.app, j.facilities[0], j.actors["reporter"][0]))
    extract = j.create(f"/obligations/{obligation['id']}/extract", {})
    draft = save(
        j, obligation, [value | {"completeness": "VALUE"} for value in declared_values(extract)]
    )
    submitted = j.create(
        f"/returns/{draft['id']}/submit",
        {
            "expected_version": draft["version"],
            "reason": "Synthetic source attestation",
            "intent_confirmed": True,
        },
    )
    j.create(
        f"/returns/{draft['id']}/review",
        {
            "expected_version": submitted["version"],
            "decision": "VERIFY",
            "reason": "Synthetic independent examination",
            "evidence_examined": "Synthetic signed source cohort",
            "method": "Synthetic actual reconciliation",
            "verification_scope": "Synthetic cohort only",
            "warning_overrides": {},
            "intent_confirmed": True,
        },
        "reviewer",
    )
    policy = j.policy(allowed_metric_ids=[value["metric_id"] for value in definitions])
    cohort = j.cohort([obligation], policy)
    released = j.released(cohort)
    prior = native.MAX_RECORDS
    try:
        native.MAX_RECORDS = 1
        response = j.get(f"/snapshots/{released['snapshot_id']}", "executive")
        exported = j.get(f"/snapshots/{released['snapshot_id']}/export.csv", "executive")
        results.append(
            {
                "finding": "HISTORICAL_SNAPSHOT_BATCH_LIMIT",
                "before_http": 200,
                "after_http": response.status_code,
                "export_after_http": exported.status_code,
                "error_code": response.json().get("error", {}).get("code"),
                "reproduction": "Configured record limit reduced to 1 to exercise the same branch; this is not a claim of observed production load.",
                "source": "services/api/src/lw_care_api/platform/reporting/native.py",
            }
        )
    finally:
        native.MAX_RECORDS = prior
    restored = j.get(f"/snapshots/{released['snapshot_id']}", "executive")
    results[-1]["after_limit_reset_http"] = restored.status_code
    results[-1]["retained_cells_unchanged"] = restored.json().get("cells") == released["cells"]
finally:
    finish(generator)
(root / ".toolchain/comprehensive-audit-behavior-probes.json").write_text(
    json.dumps(results, indent=2), encoding="utf-8"
)
print(json.dumps(results))
