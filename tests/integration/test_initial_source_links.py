"""Exact historical inspection lineage remains separate from current corrective proof."""

import asyncio

import httpx
import pytest
from lw_care_api.platform import db
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.main import create_platform_app
from sqlalchemy import select, update
from test_corrective_plans import exercise as fixture
from test_director_affiliation_conformance import ORIGIN, stamp

SCENARIOS = (
    "source_guards_and_resolution",
    "source_withdrawal",
    "source_scope_and_legacy",
    "source_met_refusal",
    "concurrent_source_confirmation",
)


async def exercise(app, client, scenario):
    f = await fixture(
        app,
        client,
        "initial_pending_link_fixture"
        if scenario == "source_withdrawal"
        else "initial_met_link_fixture"
        if scenario == "source_met_refusal"
        else "initial_link_fixture",
    )
    j, create, post, actors, reason = (
        f[key] for key in ("j", "create", "post", "actors", "reason")
    )
    finding, case, original = f["finding"], f["case"], f["initial_attestation"]
    path = f["path"] + "/initial-source-links"

    async def read(actor="reviewer", cursor=0):
        response = await client.get(
            "/v1" + path + "?before_version=" + str(cursor),
            headers={"Authorization": "Bearer " + actors[actor][1]},
        )
        assert response.status_code == 200
        assert "ciphertext" not in response.text and "object_key" not in response.text
        return response.json()

    page = await read()
    if scenario == "source_met_refusal":
        data = reason | {
            "expected_version": finding["version"],
            "expected_case_version": case["version"],
            "application_id": page["application_id"],
            "expected_application_version": page["application_version"],
            "inspection_id": original["inspection_id"],
            "attestation_version": original["version"],
        }
        assert all(not value["eligible"] for value in page["candidates"])
        await f["refused"](path, data, "reviewer", 409, "SOURCE_CORRECTION_REQUIRED")
        return {
            "scenario": scenario,
            "result": "AN_ACTUAL_MET_INITIAL_OBSERVATION_CANNOT_BE_RELABELLED_AS_A_CORRECTION_SOURCE",
        }
    source = next(value for value in page["candidates"] if value["eligible"])
    body = reason | {
        "expected_version": finding["version"],
        "expected_case_version": case["version"],
        "application_id": page["application_id"],
        "expected_application_version": page["application_version"],
        "inspection_id": source["inspection_id"],
        "attestation_version": source["attestation_version"],
    }
    assert (
        source["observation"]["outcome"] == "NOT_MET"
        and source["observation"]["observation"] == "Synthetic initial source noncompliance"
    )
    await f["refused"](path, body, "creator", 403)
    await f["refused"](path, body, "inspector", 403)
    before = await f["effects"]()
    if scenario == "concurrent_source_confirmation":
        assert app.state.database.postgres
        replies = await asyncio.gather(post(path, body, "reviewer"), post(path, body, "reviewer"))
        assert sorted(row.status_code for row in replies) == [200, 409]
        after = await f["effects"]()
        assert (
            after[0][4:] == [value + 1 for value in before[0][4:]]
            and after[0][:4] == before[0][:4]
            and after[1:] == before[1:]
        )
        return {
            "scenario": scenario,
            "result": "ONE_EXACT_SOURCE_ASSOCIATION_FOR_CONCURRENT_DISTINCT_INTENTS_NO_FINDING_TRANSITION",
        }
    if scenario == "source_withdrawal":
        await create(
            j["path"] + "/withdraw",
            {
                "expected_version": page["application_version"],
                "reason": "Synthetic actual terminal source withdrawal",
                "intent_confirmed": True,
            },
        )
        current = await read()
        withdrawn = body | {"expected_application_version": current["application_version"]}
        await f["refused"](path, body, "reviewer", 412)
        await f["refused"](path, withdrawn, "reviewer", 409, "SOURCE_WITHDRAWN")
        assert all(not value["eligible"] for value in current["candidates"])
        return {
            "scenario": scenario,
            "result": "ACTUAL_SOURCE_WITHDRAWAL_RETAINS_HISTORY_AND_REFUSES_NEW_LINKS",
        }
    if scenario == "source_scope_and_legacy":
        await f["new_actor"]("outsider", "CLINICAL_STAFF")
        denied = await client.get(
            "/v1" + path, headers={"Authorization": "Bearer " + actors["outsider"][1]}
        )
        assert denied.status_code == 404
        # Labelled foreign metadata only; not a claimed executed registration.
        async with app.state.database.transaction() as session:
            old_facility = (
                (
                    await session.execute(
                        select(db.facilities).where(db.facilities.c.id == j["facility"]["id"])
                    )
                )
                .mappings()
                .one()
            )
            old_application = (
                (
                    await session.execute(
                        select(db.applications).where(
                            db.applications.c.id == page["application_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            foreign_facility, foreign_application = db.uid(), db.uid()
            await session.execute(
                db.facilities.insert().values(
                    **{
                        **old_facility,
                        "id": foreign_facility,
                        "external_reference": "SYN_SOURCE_FOREIGN_" + foreign_facility,
                    }
                )
            )
            await session.execute(
                db.applications.insert().values(
                    **{
                        **old_application,
                        "id": foreign_application,
                        "facility_id": foreign_facility,
                    }
                )
            )
        await f["refused"](
            path,
            body | {"application_id": foreign_application},
            "reviewer",
            409,
            "SOURCE_SCOPE_MISMATCH",
        )
        await f["refused"](
            path, body | {"attestation_version": source["attestation_version"] - 1}, "reviewer", 409
        )
        # An additive legacy-shaped revision is not a fabricated executed attestation.
        legacy_version = page["application_version"] + 1
        legacy = {**original, "version": legacy_version}
        legacy.pop("extension_contract", None)
        async with app.state.database.transaction() as session:
            await session.execute(
                db.revisions.insert().values(
                    id=db.uid(),
                    resource_type="Application",
                    resource_id=page["application_id"],
                    version=legacy_version,
                    payload=legacy,
                    actor_id=actors["inspector"][0],
                    recorded_at=stamp(),
                )
            )
            await session.execute(
                update(db.applications)
                .where(db.applications.c.id == page["application_id"])
                .values(version=legacy_version)
            )
        await f["refused"](
            path,
            body
            | {
                "expected_application_version": legacy_version,
                "attestation_version": legacy_version,
            },
            "reviewer",
            409,
            "CURRENT_INSPECTION_REQUIRED",
        )
        return {
            "scenario": scenario,
            "result": "SCOPED_CURRENT_AUTHORITY_AND_ACTUAL_BOUND_SCREENING_CHAIN_REQUIRED_NO_LEGACY_BACKFILL",
        }

    for key in ["expected_version", "expected_case_version", "expected_application_version"]:
        await f["refused"](path, body | {key: body[key] + 1}, "reviewer", 412)
    await f["refused"](
        path, body | {"inspection_id": db.uid()}, "reviewer", 409, "SOURCE_ATTESTATION_REQUIRED"
    )
    key = db.uid()
    linked = await create(path, body, "reviewer", key)
    after = await f["effects"]()
    assert after[0][:4] == before[0][:4] and after[1:] == before[1:]
    assert (
        linked["source"]["observation"] == source["observation"]
        and linked["effect"] == "CONTEXT_ONLY_NO_WORKFLOW_TRANSITION"
    )
    assert await create(path, body, "reviewer", key) == linked
    await f["refused"](path, body, "reviewer", 409, "SOURCE_ALREADY_LINKED")
    assert (await f["current"]())["corrective_plan"] is None
    await f["refused"](
        f["cp"] + "/recommend",
        reason | {"expected_version": case["version"], "action": "RENEW"},
        "reviewer",
        409,
    )
    retract_body = reason | {
        "expected_version": finding["version"],
        "expected_case_version": case["version"],
    }
    await f["refused"](path + "/" + linked["id"] + "/retract", retract_body, "creator", 403)
    retracted = await create(path + "/" + linked["id"] + "/retract", retract_body, "reviewer")
    retained = (await read())["items"][0]
    assert (
        retained["status"] == "RETRACTED"
        and retained["source"] == linked["source"]
        and retained["retraction"]["id"] == retracted["id"]
    )
    await f["refused"](
        path + "/" + linked["id"] + "/retract", retract_body, "reviewer", 409, "INVALID_STATE"
    )
    await f["refused"](path, body, "reviewer", 409, "SOURCE_ALREADY_LINKED")
    # Real current work still needs its own agreement/response/independent resolution.
    proposed = await create(f["path"] + "/corrective-plan", f["proposal"](finding["version"]))
    agreed = await create(
        f["path"] + "/corrective-plan-review", f["review_plan"](proposed), "reviewer"
    )
    response = await create(f["path"] + "/respond", f["response_body"](agreed["version"]))
    await create(
        f["path"] + "/review",
        reason
        | {
            "expected_version": response["version"],
            "response_id": response["response_id"],
            "decision": "RESOLVE",
        },
        "reviewer",
    )
    recommended = await create(
        f["cp"] + "/recommend",
        reason | {"expected_version": case["version"], "action": "RENEW"},
        "reviewer",
    )
    await create(
        f["cp"] + "/decide",
        reason
        | {
            "expected_version": recommended["version"],
            "action": "RENEW",
            "scope": "Synthetic lineage proof only",
            "conditions": "",
            "expires_at": stamp(8),
        },
        "decider",
    )
    async with app.state.database.transaction() as session:
        retained_source = await session.scalar(
            select(db.revisions.c.payload).where(
                db.revisions.c.resource_type == "Application",
                db.revisions.c.resource_id == page["application_id"],
                db.revisions.c.version == original["version"],
            )
        )
        assert retained_source == original
    return {
        "scenario": scenario,
        "result": "EXACT_HISTORICAL_NEGATIVE_SOURCE_LINK_AND_RETRACTION_NEVER_SUBSTITUTE_FOR_CURRENT_CORRECTIVE_WORK",
    }


@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_initial_source_link_guards(tmp_path, scenario):
    if scenario == "concurrent_source_confirmation":
        pytest.skip("Real PostgreSQL source-confirmation race runs in isolated Neon")
    cfg = PlatformSettings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'links.db').as_posix()}",
        data_key_hex="09" * 32,
        web_origin=ORIGIN,
        authority_node_id=db.uid(),
        enforce_activation_dossiers=False,
        dispatch_recovery_after_commit=False,
    )
    app = create_platform_app(cfg)
    await app.state.database.migrate()
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=ORIGIN
        ) as client:
            await exercise(app, client, scenario)
    finally:
        await app.state.database.engine.dispose()
