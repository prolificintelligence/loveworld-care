"""Synthetic Phase A qualification in a disposable Neon schema, never production data.

ASGI request timings include real Neon I/O and local Python execution. They are
not Vercel function memory/duration or institutional latency acceptance.
"""

import asyncio
import base64
import json
import sys
import traceback
from pathlib import Path
from time import perf_counter

from sqlalchemy import select, text
from verify_native_reporting_postgres import ROOT, verify

sys.path.insert(0, str(ROOT / "services/api/src"))
from lw_care_api.platform import db
from lw_care_api.platform.clinical import store as cs
from lw_care_api.platform.clinical import tables as ct
from lw_care_api.platform.reporting import native, source_index
from lw_care_api.platform.reporting import tables as rt
from lw_care_api.platform.reporting.store import canonical, digest
from test_platform_controls import stamp
from test_platform_native_reporting import seed_sources


async def bulk_contacts(app, facility, actor, patient, amount, at, namespace):
    """Bulk signed synthetic volume fixture, confined to the translated schema."""
    assert namespace.startswith("lwh_native_verify_") and namespace != db.SCHEMA
    assert (
        app.state.database.engine.get_execution_options()["schema_translate_map"][db.SCHEMA]
        == namespace
    )
    box, cfg = app.state.box, app.state.settings
    key = cs.signing_key(cfg)
    for offset in range(0, amount, 200):
        records, events, indexes = [], [], []
        for _ in range(min(200, amount - offset)):
            identifier, event_id, now = db.uid(), db.uid(), db.now()
            content = {"disposition": {"occurred_at": at}, "synthetic_volume_fixture": True}
            row = {
                "id": identifier,
                "facility_id": facility,
                "patient_id": patient,
                "encounter_id": None,
                "kind": "encounter",
                "status": "COMPLETED",
                "service": "SYNTHETIC",
                "confidentiality": "STANDARD",
                "authority_node_id": cfg.authority_node_id,
                "authority_epoch": "SYNTHETIC-1",
                "version": 1,
                "content_ciphertext": cs.seal(box, identifier, content),
                "created_by": actor,
                "created_at": now,
                "updated_at": now,
            }
            event = {
                "id": event_id,
                "record_id": identifier,
                "facility_id": facility,
                "patient_id": patient,
                "version": 1,
                "event_contract_id": "LWH-EXT-CLINICAL-001",
                "action": "clinical.synthetic_volume_fixture",
                "actor_id": actor,
                "occurred_at": at,
                "recorded_at": now,
                "authority_node_id": cfg.authority_node_id,
                "authority_epoch": "SYNTHETIC-1",
                "previous_hash": "0" * 64,
            }
            payload = event | {
                "schema_version": "2.0.0",
                "kind": "encounter",
                "status": "COMPLETED",
                "content": content,
            }
            hashed = digest(payload)
            events.append(
                event
                | {
                    "payload_hash": hashed,
                    "signature": base64.b64encode(key.sign(bytes.fromhex(hashed))).decode(),
                    "payload_ciphertext": box.encrypt(canonical(payload)),
                }
            )
            records.append(row)
            indexes.append(source_index.projection(row, content))
        async with app.state.database.transaction() as session:
            await session.execute(ct.records.insert(), records)
            await session.execute(ct.events.insert(), events)
            await session.execute(source_index.index.insert(), indexes)


async def qualify(
    app, actors, facility, client, post, create, get, obligation, fresh, source, namespace, result
):
    print(json.dumps({"phase_a_stage": "historical_access"}), flush=True)
    actor = actors["target"][0]
    async with app.state.database.transaction() as session:
        await session.execute(
            db.grants.insert().values(
                id=db.uid(),
                account_id=actors["proposer"][0],
                role="DATA_ANALYST",
                scope_type="GLOBAL",
                scope_id="GLOBAL",
                valid_from=stamp(-1),
                valid_until=stamp(10),
                revoked=False,
                grantor="SYNTHETIC_PHASE_A_ONLY",
            )
        )
    values = [
        {
            "definition_id": identifier,
            "completeness": "VALUE",
            "value": item["value"],
            "numerator": item["numerator"],
            "denominator": item["denominator"],
            "explanation": item["explanation"],
            "extract_id": fresh["id"],
        }
        for identifier, item in fresh["data"]["values"].items()
    ]
    async with app.state.database.transaction() as session:
        current = (
            (
                await session.execute(
                    select(rt.returns).where(rt.returns.c.obligation_id == obligation["id"])
                )
            )
            .mappings()
            .one()
        )
    draft = await create(
        f"/obligations/{obligation['id']}/draft",
        {
            "expected_version": current["version"],
            "values": values,
            "source_method": "Synthetic qualified cohort",
            "reconciliation": "Isolated engineering fixture only",
            "reason": "Synthetic current source reconciliation",
        },
        "target",
    )
    submitted = await create(
        f"/returns/{draft['id']}/submit",
        {
            "expected_version": draft["version"],
            "reason": "Synthetic actual attestation",
            "intent_confirmed": True,
        },
        "target",
    )
    await create(
        f"/returns/{draft['id']}/review",
        {
            "expected_version": submitted["version"],
            "decision": "VERIFY",
            "reason": "Synthetic independent verification",
            "evidence_examined": "Synthetic signed fixture",
            "method": "Synthetic reconciliation",
            "verification_scope": "Disposable schema only",
            "warning_overrides": {},
            "intent_confirmed": True,
        },
        "successor",
    )
    policy = await create(
        "/policies",
        {
            "name": "Synthetic Phase A disclosure",
            "policy_version": db.uid(),
            "purpose": "STRATEGIC_LEADERSHIP",
            "allowed_metric_ids": [
                value["metric_id"] for value in fresh["data"]["values"].values()
            ],
            "minimum_units": 2,
            "minimum_cell": 5,
            "minimum_change": 5,
            "allow_partial": False,
            "adoption_reference": "Synthetic only",
            "risk_assessment": "Synthetic independently examined disclosure controls",
            "valid_from": stamp(-1),
            "valid_until": stamp(10),
            "intent_confirmed": True,
        },
    )
    cohort = await create(
        "/cohorts",
        {
            "scope_type": "GLOBAL",
            "name": "Synthetic Phase A cohort",
            "obligation_ids": [obligation["id"]],
            "policy_id": policy["id"],
        },
    )
    released = await create("/snapshots", {"cohort_id": cohort["id"]})
    await create(
        f"/snapshots/{released['id']}/review",
        {
            "decision": "RELEASE",
            "reason": "Synthetic independent disclosure review",
            "intent_confirmed": True,
        },
        "successor",
    )
    retained = await get(f"/snapshots/{released['id']}")
    pending = await create("/snapshots", {"cohort_id": cohort["id"]})
    cap = native.MAX_RECORDS
    try:
        native.MAX_RECORDS = 1
        historical = await get(f"/snapshots/{released['id']}")
        assert historical["cells"] == retained["cells"] and historical["current_eligible"] is False
        assert historical["native_source_health"] == {
            "status": "UNAVAILABLE",
            "reason": "SOURCE_BATCH_REQUIRED",
        }
        assert (await get("/snapshots"))["items"][0]["current_eligible"] is False
        exported = await client.get(
            f"/v1/reporting/snapshots/{released['id']}/export.csv",
            headers={"Authorization": "Bearer " + actors["proposer"][1]},
        )
        assert exported.status_code == 200 and "CURRENT_SOURCE_CHECK_UNAVAILABLE" in exported.text
        blocked = await post(
            f"/snapshots/{pending['id']}/review",
            {
                "decision": "RELEASE",
                "reason": "Synthetic unavailable source must block",
                "intent_confirmed": True,
            },
            "successor",
        )
        assert blocked.status_code == 409
    finally:
        native.MAX_RECORDS = cap
    print(json.dumps({"phase_a_stage": "facility_lock_concurrency"}), flush=True)
    # Prove extraction does not take the governance lock, and a busy facility
    # does not stall extraction for another facility. Events make the ordering
    # deterministic; timeouts detect blocking without an arbitrary sleep.
    async with app.state.database.transaction() as session:
        other = (
            (
                await session.execute(
                    select(db.facilities.c.id).where(db.facilities.c.id != facility)
                )
            )
            .scalars()
            .first()
        )
    await seed_sources(app, other, actor)
    second = await create(
        "/obligations",
        {
            key: value
            for key, value in obligation.items()
            if key
            in {
                "scope_type",
                "scope_id",
                "stream",
                "period_start",
                "period_end",
                "due_at",
                "timezone",
                "definition_ids",
                "adoption_reference",
            }
        }
        | {"scope_id": other},
    )
    path, second_path = (
        f"/obligations/{obligation['id']}/extract",
        f"/obligations/{second['id']}/extract",
    )
    async with app.state.database.transaction() as held:
        await held.execute(text("SELECT pg_advisory_xact_lock(782025011)"))
        await asyncio.wait_for(create(second_path, {}, "target"), timeout=30)
    async with app.state.database.transaction() as held:
        await held.execute(
            select(ct.sites).where(ct.sites.c.facility_id == facility).with_for_update()
        )
        waiting = asyncio.create_task(post(path, {}, "target"))
        await asyncio.wait_for(create(second_path, {}, "target"), timeout=30)
        assert not waiting.done()
    assert (await asyncio.wait_for(waiting, timeout=30)).status_code == 200
    replay_key = db.uid()
    responses = await asyncio.gather(
        post(path, {}, "target", replay_key), post(path, {}, "target", replay_key)
    )
    assert (
        responses[0].status_code == responses[1].status_code == 200
        and responses[0].json() == responses[1].json()
    )
    print(json.dumps({"phase_a_stage": "later_period_volume"}), flush=True)
    # Growth beyond the original facility-wide record cap must leave the old
    # period hash unchanged. These contacts belong to a later period.
    await bulk_contacts(app, facility, actor, source["patient"], 5001, stamp(-1), namespace)
    started = perf_counter()
    after_growth = await create(path, {}, "target")
    growth_seconds = round(perf_counter() - started, 3)
    assert after_growth["source_hash"] == fresh["source_hash"]
    assert (await get(f"/snapshots/{released['id']}"))["current_eligible"] is True
    print(json.dumps({"phase_a_stage": "actual_selected_record_boundary"}), flush=True)
    # Determine the exact dependency-inclusive selected size, then exercise the
    # real 5,000-record boundary rather than only reducing configuration.
    from lw_care_api.platform.reporting.operations import DirectorateService

    async with app.state.database.transaction() as session:
        service = DirectorateService(
            session, app.state.settings, app.state.box, {"id": actor}, "SYNTHETIC"
        )
        selected = len((await native.inventory(service, facility, obligation))[0])
    await bulk_contacts(
        app, facility, actor, source["patient"], cap - selected, stamp(-2.5), namespace
    )
    started = perf_counter()
    boundary = await create(path, {}, "target")
    boundary_seconds = round(perf_counter() - started, 3)
    contacts = next(
        item for item in boundary["data"]["values"].values() if item["metric_id"] == "LWH-MET-010"
    )
    assert (
        contacts["completeness"] == "UNKNOWN"
        and contacts["incomplete_source_records"] == cap - selected
    )
    await bulk_contacts(app, facility, actor, source["patient"], 1, stamp(-2.5), namespace)
    overflow = await post(path, {}, "target")
    assert (
        overflow.status_code == 409 and overflow.json()["error"]["code"] == "SOURCE_BATCH_REQUIRED"
    )
    assert (await get(f"/snapshots/{released['id']}"))["current_eligible"] is False
    result["phase_a"] = {
        "historical_view_list_csv": "PASSED_UNCHANGED_CELLS_UNAVAILABLE_CURRENT_USE",
        "uncheckable_release": "BLOCKED",
        "global_lock_extraction_independent": True,
        "simultaneous_facilities": "UNBLOCKED_OTHER_FACILITY_WHILE_FIRST_WAITS",
        "duplicate_extract": "IDENTICAL_RECEIPT",
        "later_period_added_records": 5001,
        "later_period_source_hash_unchanged": True,
        "later_period_extract_seconds": growth_seconds,
        "period_selected_records_at_bound": cap,
        "period_bound_extract_seconds": boundary_seconds,
        "missing_summaries_accounted_as_unknown": cap - selected,
        "period_selected_records_over_bound": cap + 1,
        "overflow": "BLOCKED_NO_TRUNCATED_TOTAL",
        "measurement_boundary": "LOCAL_ASGI_WITH_REAL_NEON_NOT_VERCEL_FUNCTION_CAPACITY_ACCEPTANCE",
    }


if __name__ == "__main__":
    try:
        asyncio.run(verify(qualify))
    except Exception as exc:  # noqa: BLE001 -- keep credentials and provider payloads out of errors
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        print(
            json.dumps(
                {
                    "phase_a_postgres": "FAILED",
                    "error_type": type(exc).__name__,
                    "source": Path(frame.filename).name,
                    "line": frame.lineno,
                "errno": getattr(exc, "errno", None),
                "winerror": getattr(exc, "winerror", None),
                "stack": [{"file": Path(item.filename).name, "line": item.lineno, "function": item.name}
                          for item in traceback.extract_tb(exc.__traceback__)],
                }
            )
        )
        raise SystemExit(1) from None
