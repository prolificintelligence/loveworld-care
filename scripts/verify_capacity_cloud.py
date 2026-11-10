"""Bounded synthetic Vercel/Neon measurement; no production alias or business writes.

Uses an existing project, a disposable preview URL/schema and a separate encryption
key. Setup may use a local pool; measured cloud requests retain production NullPool.
No adopted latency target, sustained-load or institutional acceptance is inferred.
"""

import asyncio
import base64
import hashlib
import json
import secrets
import sys
import traceback
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "services/api/src"), str(ROOT / "tests/integration")]

import httpx
from lw_care_api.platform import db
from lw_care_api.platform.clinical import store as cs
from lw_care_api.platform.clinical import tables as ct
from lw_care_api.platform.reporting import native, source_index
from lw_care_api.platform.reporting import tables as rt
from lw_care_api.platform.reporting.operations import DirectorateService
from lw_care_api.platform.reporting.store import canonical, digest
from platform_cloud_release import (
    API,
    active_deployment,
    candidate_probe_access,
    checked,
    http_client,
    source_files,
    vercel_credential,
)
from release_guard import committed_source, manifest, successful_ci, verify_source_tree
from sqlalchemy import func, select, update
from test_platform_controls import stamp
from verify_native_reporting_postgres import ROOT, verify
from verify_phase_a_postgres import bulk_contacts

OUTPUT = ROOT / ".toolchain/capacity-cloud.json"
RESULT = {
    "status": "STARTING",
    "measurement": "SYNTHETIC_DISPOSABLE_VERCEL_PREVIEW_NEON",
    "operating_acceptance": "NOT_ESTABLISHED",
    "requests": [],
}


def record():
    OUTPUT.write_text(json.dumps(RESULT, indent=2) + "\n", encoding="utf-8")


async def grow_selected_history(app, facility, actor, obligation, namespace, target):
    """Append valid signed revisions to one labelled synthetic contact, never production."""
    assert namespace.startswith("lwh_native_verify_") and namespace != db.SCHEMA
    assert (
        app.state.database.engine.get_execution_options()["schema_translate_map"][db.SCHEMA]
        == namespace
    )
    async with app.state.database.transaction() as session:
        service = DirectorateService(
            session, app.state.settings, app.state.box, {"id": actor}, "SYNTHETIC"
        )
        rows = (await native.inventory(service, facility, obligation))[0]
        current = await session.scalar(
            select(func.count())
            .select_from(ct.events)
            .where(ct.events.c.record_id.in_([r["id"] for r in rows]))
        )
        row = next(
            dict(r)
            for r in rows
            if cs.opened(app.state.box, r)["data"].get("synthetic_volume_fixture")
        )
        head = (
            (
                await session.execute(
                    select(ct.events)
                    .where(ct.events.c.record_id == row["id"])
                    .order_by(ct.events.c.version.desc())
                    .limit(1)
                )
            )
            .mappings()
            .one()
        )
        previous, version = head["payload_hash"], row["version"]
        content = cs.opened(app.state.box, row)["data"]
        key = cs.signing_key(app.state.settings)
        events = []
        assert target > current
        for _ in range(target - current):
            version += 1
            event = {
                "id": db.uid(),
                "record_id": row["id"],
                "facility_id": facility,
                "patient_id": row["patient_id"],
                "version": version,
                "event_contract_id": "LWH-EXT-CLINICAL-001",
                "action": "clinical.synthetic_history_revision",
                "actor_id": actor,
                "occurred_at": head["occurred_at"],
                "recorded_at": db.now(),
                "authority_node_id": row["authority_node_id"],
                "authority_epoch": row["authority_epoch"],
                "previous_hash": previous,
            }
            payload = event | {
                "schema_version": "2.0.0",
                "kind": row["kind"],
                "status": row["status"],
                "content": content,
            }
            previous = digest(payload)
            events.append(
                event
                | {
                    "payload_hash": previous,
                    "signature": base64.b64encode(key.sign(bytes.fromhex(previous))).decode(),
                    "payload_ciphertext": app.state.box.encrypt(canonical(payload)),
                }
            )
            if len(events) == 200:
                await session.execute(ct.events.insert(), events)
                events = []
        if events:
            await session.execute(ct.events.insert(), events)
        await session.execute(
            update(ct.records).where(ct.records.c.id == row["id"]).values(version=version)
        )
        session.info["platform_schema_version"] = 9
        await source_index.project(session, row | {"version": version}, content)
    return target


async def qualify(
    app, actors, facility, client, post, create, get, obligation, fresh, source, namespace, result
):
    del client, post, get, result
    cfg = app.state.settings
    identifier = None
    with http_client(vercel_credential()) as provider:
        previous = active_deployment(provider, API)
        web_before = active_deployment(provider, "lw-health-intelligence")
        project = checked(provider.get(f"https://api.vercel.com/v9/projects/{API}"), "project")
        files = source_files("api")
        wrapper = (ROOT / "scripts/capacity_candidate.py").read_bytes()
        config = json.loads((ROOT / "vercel.platform.json").read_text())
        config.pop("crons", None)
        for item in files:
            if item["file"] == "api/index.py":
                item["data"] = base64.b64encode(wrapper).decode()
            if item["file"] == "vercel.json":
                item["data"] = base64.b64encode(json.dumps(config).encode()).decode()
        RESULT["source_manifest"] = [
            {
                "file": item["file"],
                "sha256": hashlib.sha256(base64.b64decode(item["data"])).hexdigest(),
            }
            for item in files
        ]
        try:
            deployed = checked(
                provider.post(
                    "https://api.vercel.com/v13/deployments",
                    json={
                        "name": API,
                        "project": API,
                        "autoAssignCustomDomains": False,
                        "meta": {
                            "lwhQualificationCommit": RESULT["commit"],
                            "lwhPurpose": "DISPOSABLE_CAPACITY_ONLY",
                        },
                        "files": files,
                        "env": {
                            "LWH_DATABASE_URL": cfg.database_url,
                            "LWH_DATA_KEY_HEX": cfg.data_key_hex,
                            "LWH_WEB_ORIGIN": cfg.web_origin,
                            "LWH_AUTHORITY_NODE_ID": cfg.authority_node_id,
                            "LWH_CAPACITY_SCHEMA": namespace,
                            "LWH_ENVIRONMENT": "test",
                        },
                    },
                ),
                "create_capacity_preview",
            )
            identifier = deployed["id"]
            RESULT.update(
                deployment_id=identifier,
                url="https://" + deployed["url"],
                previous_api=previous,
                previous_web=web_before,
                cron_removed=True,
            )
            record()
            print(json.dumps({"capacity_preview": identifier, "stage": "BUILDING"}), flush=True)
            for _ in range(120):
                state = checked(
                    provider.get(f"https://api.vercel.com/v13/deployments/{identifier}"),
                    "preview_state",
                )
                if state.get("readyState") in ("READY", "ERROR", "CANCELED"):
                    break
                await asyncio.sleep(5)
            assert state.get("readyState") == "READY", "Preview build did not become READY"
            assert state.get("target") != "production"
            tree = checked(
                provider.get(f"https://api.vercel.com/v6/deployments/{identifier}/files"),
                "preview_sources",
            )
            RESULT["verified_source_files"] = verify_source_tree(manifest(files), tree)
            RESULT["function_configuration"] = config["functions"]
            with candidate_probe_access(provider, project, identifier) as probe_headers:
                async with httpx.AsyncClient(
                    base_url=RESULT["url"],
                    headers=probe_headers,
                    timeout=90,
                    follow_redirects=False,
                ) as cloud:

                    async def request(
                        label, path, actor="target", key=None, expected=200, method="POST"
                    ):
                        started = perf_counter()
                        headers = {
                            "Authorization": "Bearer " + actors[actor][1],
                            "Origin": cfg.web_origin,
                            "Idempotency-Key": key or db.uid(),
                        }
                        response = await cloud.request(
                            method,
                            path,
                            headers=headers,
                            **({"json": {}} if method == "POST" else {}),
                        )
                        metrics = {
                            "label": label,
                            "http": response.status_code,
                            "client_elapsed_seconds": round(perf_counter() - started, 3),
                            "server_elapsed_ms": response.headers.get("X-Qualification-Elapsed-Ms"),
                            "process_lifetime_maxrss_kib": response.headers.get(
                                "X-Qualification-Process-Maxrss-Kib"
                            ),
                            "pool": response.headers.get("X-Qualification-Pool"),
                        }
                        RESULT["requests"].append(metrics)
                        record()
                        assert response.status_code == expected, (label, response.status_code)
                        assert metrics["pool"] == "NullPool"
                        if expected != 200:
                            metrics["code"] = response.json()["error"]["code"]
                        return response

                    await request("cold_readiness", "/v1/ready", method="GET")
                    excluded = await cloud.post("/v1/internal/jobs")
                    assert excluded.status_code == 403
                    path = f"/v1/reporting/obligations/{obligation['id']}/extract"
                    initial = (await request("baseline_extract", path)).json()["resource"]
                    actor = actors["target"][0]
                    await bulk_contacts(
                        app, facility, actor, source["patient"], 5001, stamp(-1), namespace
                    )
                    later = (await request("5001_later_period_extract", path)).json()["resource"]
                    assert later["source_hash"] == initial["source_hash"]
                    key = db.uid()
                    replies = await asyncio.gather(
                        request("duplicate_a", path, key=key), request("duplicate_b", path, key=key)
                    )
                    assert replies[0].json() == replies[1].json()
                    async with app.state.database.transaction() as session:
                        service = DirectorateService(
                            session, cfg, app.state.box, {"id": actor}, "SYNTHETIC"
                        )
                        selected = len((await native.inventory(service, facility, obligation))[0])
                        other = await session.scalar(
                            select(db.facilities.c.id).where(db.facilities.c.id != facility)
                        )
                    copied = await create(
                        "/obligations",
                        {
                            "scope_type": "FACILITY",
                            "scope_id": other,
                            **{
                                k: obligation[k]
                                for k in (
                                    "stream",
                                    "period_start",
                                    "period_end",
                                    "due_at",
                                    "timezone",
                                    "definition_ids",
                                    "adoption_reference",
                                )
                            },
                        },
                    )
                    await bulk_contacts(
                        app,
                        facility,
                        actor,
                        source["patient"],
                        native.MAX_RECORDS - selected,
                        stamp(-2.5),
                        namespace,
                    )
                    bound = (await request("5000_selected_extract", path)).json()["resource"]
                    contacts = next(
                        v
                        for v in bound["data"]["values"].values()
                        if v["metric_id"] == "LWH-MET-010"
                    )
                    assert contacts["completeness"] == "UNKNOWN"
                    assert contacts["incomplete_source_records"] == native.MAX_RECORDS - selected
                    await asyncio.gather(
                        request("simultaneous_facility_a", path),
                        request(
                            "simultaneous_facility_b",
                            f"/v1/reporting/obligations/{copied['id']}/extract",
                        ),
                    )
                    for i in range(3):
                        await request(f"repeated_bound_{i + 1}", path)
                    await grow_selected_history(
                        app, facility, actor, obligation, namespace, native.MAX_EVENTS
                    )
                    history_bound = await request("5000_records_20000_events", path)
                    assert (
                        next(
                            v
                            for v in history_bound.json()["resource"]["data"]["values"].values()
                            if v["metric_id"] == "LWH-MET-010"
                        )["completeness"]
                        == "UNKNOWN"
                    )
                    await grow_selected_history(
                        app, facility, actor, obligation, namespace, native.MAX_EVENTS + 1
                    )
                    event_overflow = await request("20001_events_overflow", path, expected=409)
                    assert event_overflow.json()["error"]["code"] == "SOURCE_BATCH_REQUIRED"
                    await bulk_contacts(
                        app, facility, actor, source["patient"], 1, stamp(-2.5), namespace
                    )
                    overflow = await request("5001_selected_overflow", path, expected=409)
                    assert overflow.json()["error"]["code"] == "SOURCE_BATCH_REQUIRED"
                    await request(
                        "retained_extract_history_after_overflow",
                        f"/v1/reporting/extracts/{fresh['id']}",
                        actor="successor",
                        method="GET",
                    )
                    async with app.state.database.transaction() as session:
                        RESULT["synthetic_counts"] = {
                            table.name: await session.scalar(
                                select(func.count()).select_from(table)
                            )
                            for table in (ct.records, ct.events, rt.extracts)
                        }
                    RESULT.update(
                        duplicate_receipt_identical=True,
                        later_period_hash_unchanged=True,
                        selected_boundary=5000,
                        selected_overflow=5001,
                        selected_events_boundary=20000,
                        selected_events_overflow=20001,
                        missing_summaries_accounted_as_unknown=native.MAX_RECORDS - selected,
                        jobs_excluded=True,
                        synthetic_fixture_key_separate=True,
                    )
            RESULT["temporary_probe_access"] = "REVOKED"
            RESULT["status"] = "BOUNDED_MEASUREMENTS_PASSED"
        finally:
            if identifier:
                deleted = provider.delete(f"https://api.vercel.com/v13/deployments/{identifier}")
                RESULT["preview_removed"] = deleted.status_code in (200, 204)
                if not RESULT["preview_removed"]:
                    RESULT["cleanup_http"] = deleted.status_code
                removed = provider.get(f"https://api.vercel.com/v13/deployments/{identifier}")
                RESULT["preview_absent_http"] = removed.status_code
                assert removed.status_code in (404, 410)
            final_project = checked(
                provider.get(f"https://api.vercel.com/v9/projects/{API}"), "final_project"
            )
            RESULT["sso_protection_unchanged"] = final_project.get("ssoProtection") == project.get(
                "ssoProtection"
            )
            RESULT["remaining_automation_tokens"] = len(final_project.get("protectionBypass") or {})
            RESULT["production_aliases_unchanged"] = (
                active_deployment(provider, API) == previous
                and active_deployment(provider, "lw-health-intelligence") == web_before
            )
            record()
            assert RESULT.get("preview_removed") and RESULT["production_aliases_unchanged"]


if __name__ == "__main__":
    try:
        RESULT["commit"] = committed_source(ROOT)
        RESULT["ci"] = successful_ci(RESULT["commit"])
        # The existing fixture installer is configured with this one-use key.
        # No production encryption material is used by the preview.
        import verify_native_reporting_postgres as fixture

        original_settings = fixture.PlatformSettings
        fixture.PlatformSettings = lambda **kwargs: original_settings(**kwargs).model_copy(
            update={"data_key_hex": secrets.token_hex(32)}
        )
        asyncio.run(verify(qualify, pooled_harness=True))
        RESULT["disposable_schema_removed"] = True
    except Exception as exc:  # noqa: BLE001 -- provider payloads/credentials must not enter logs
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        RESULT.update(
            status="FAILED",
            failure={
                "type": type(exc).__name__,
                "file": Path(frame.filename).name,
                "line": frame.lineno,
            },
        )
        record()
        print(json.dumps({"capacity_cloud": "FAILED", "failure": RESULT["failure"]}), flush=True)
        raise SystemExit(1) from None
    record()
    print(json.dumps({k: v for k, v in RESULT.items() if k not in {"source_manifest", "requests"}}))
