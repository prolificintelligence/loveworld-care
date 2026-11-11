"""Screening/order proofs with labelled isolated metadata, never scanner/adoption evidence."""

import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from lw_care_api.platform import db
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.main import create_platform_app
from lw_care_api.platform.security import issue_session
from sqlalchemy import update
from test_director_affiliation_conformance import ORIGIN, advance_review, evidence_expired, stamp
from test_director_affiliation_conformance import exercise as fixture

SCENARIOS = (
    "guards_and_order",
    "expiry",
    "policy_and_scope",
    "scope_and_replay",
    "unreviewed_evidence",
    "legacy_recovery",
    "concurrent_screen_withdraw",
)


async def exercise(app, client, scenario):
    legacy = scenario == "legacy_recovery"
    j = await fixture(
        app,
        client,
        "screening_fixture",
        fixture_state="SUBMITTED" if legacy else "SCREENING",
        evidence_valid_minutes=60 if app.state.database.postgres else 10,
        criteria_valid_until=(datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        if scenario == "policy_and_scope"
        else None,
    )
    create, refused, post, path, actors = (
        j[k] for k in ("create", "refused", "post", "path", "actors")
    )

    async def dossier():
        response = await client.get(
            "/v1" + path, headers={"Authorization": "Bearer " + actors["creator"][1]}
        )
        assert response.status_code == 200
        return response.json()

    async def row():
        return (await dossier())["application"]

    async def mismatched_scope(suffix, body, actor):
        # Mutable synthetic profile change, not an institutional operating decision.
        async with app.state.database.transaction() as session:
            await session.execute(
                update(db.facilities)
                .where(db.facilities.c.id == j["facility"]["id"])
                .values(jurisdiction="SYNTHETIC-OTHER-SCOPE")
            )
        try:
            await refused(path + suffix, body, actor, 409, "POLICY_NOT_ACTIVE")
        finally:
            async with app.state.database.transaction() as session:
                await session.execute(
                    update(db.facilities)
                    .where(db.facilities.c.id == j["facility"]["id"])
                    .values(jurisdiction=j["facility"]["jurisdiction"])
                )

    def screen_body(version):
        return {
            "expected_version": version,
            "reason": "Synthetic actual dossier screening",
            "intent_confirmed": True,
        }

    def review_body(version):
        return screen_body(version) | {
            "reason": "Synthetic actual evidence review",
            "assessments": [
                {
                    "criterion": code,
                    "assessment": "Synthetic examined proof, not recognition",
                    "evidence_ids": [identifier],
                }
                for code, identifier in j["proofs"].items()
            ],
        }

    async def proof(application_id, *, status="CLEAN"):
        identifier = db.uid()
        async with app.state.database.transaction() as session:
            await session.execute(
                db.evidence.insert().values(
                    id=identifier,
                    application_id=application_id,
                    criterion="SYN-A",
                    object_key="SYNTHETIC_NO_OBJECT",
                    sha256="0" * 64,
                    filename="synthetic.txt",
                    media_type="text/plain",
                    size=1,
                    source="ISOLATED_METADATA_NOT_SCANNER_QUALIFICATION",
                    expires_at=stamp(1),
                    scan_status=status,
                    uploaded_by=actors["creator"][0],
                    created_at=stamp(),
                )
            )
        return identifier

    before = await dossier()
    if legacy:
        # Explicit legacy-shaped fixture, not executed transitions or rewritten old history.
        application = dict(before["application"])
        inspection_id = db.uid()
        async with app.state.database.transaction() as session:
            application.update(
                inspector_id=actors["inspector"][0], reviewer_id=actors["reviewer"][0]
            )
            await session.execute(
                db.inspections.insert().values(
                    id=inspection_id,
                    application_id=application["id"],
                    inspector_id=actors["inspector"][0],
                    findings=[
                        {
                            "criterion": code,
                            "observation": "Synthetic legacy finding",
                            "outcome": "MET",
                            "evidence_ids": [identifier],
                        }
                        for code, identifier in j["proofs"].items()
                    ],
                    conflict_declared=False,
                    observed_at=stamp(-1),
                    recorded_at=stamp(),
                )
            )
            for version, state in [(3, "INSPECTION"), (4, "EVIDENCE_REVIEW"), (5, "RECOMMENDED")]:
                application.update(
                    version=version,
                    state=state,
                    recommendation={
                        "decision": "APPROVE",
                        "reason": "Synthetic legacy recommendation",
                    }
                    if version == 5
                    else None,
                )
                payload = application | {"fixture": "LEGACY_SHAPE_NOT_EXECUTED_TRANSITIONS"}
                if version == 4:
                    payload.update(
                        inspection_id=inspection_id, extension_contract="LWH-EXT-APPLICATION-001"
                    )
                await session.execute(
                    db.revisions.insert().values(
                        id=db.uid(),
                        resource_id=application["id"],
                        resource_type="Application",
                        version=version,
                        payload=payload,
                        actor_id=actors["creator"][0],
                        recorded_at=stamp(),
                    )
                )
            await session.execute(
                update(db.applications)
                .where(db.applications.c.id == application["id"])
                .values(
                    **{
                        k: application[k]
                        for k in (
                            "state",
                            "version",
                            "inspector_id",
                            "reviewer_id",
                            "recommendation",
                        )
                    }
                )
            )
        before = await dossier()
        await refused(
            path + "/decisions",
            {
                "expected_version": 5,
                "decision": "APPROVE",
                "reason": "Synthetic cannot infer old screening",
                "scope": "Synthetic only",
                "conditions": "",
                "effective_at": stamp(-1),
                "expires_at": stamp(1),
                "intent_confirmed": True,
            },
            "decider",
            409,
            "CURRENT_INSPECTION_REQUIRED",
        )
        await create(
            path + "/correction-request",
            screen_body(5) | {"criterion_codes": ["SYN-A", "SYN-B"]},
            "reviewer",
        )
        corrected = await row()
        submitted = await create(
            path + "/resubmit",
            screen_body(corrected["version"])
            | {
                "responses": [
                    {
                        "criterion": code,
                        "response": "Synthetic actual legacy resubmission",
                        "evidence_ids": [identifier],
                    }
                    for code, identifier in j["proofs"].items()
                ]
            },
        )
        assigned = await create(
            path + "/assignment",
            {
                "expected_version": submitted["version"],
                "inspector_id": actors["inspector"][0],
                "reviewer_id": actors["reviewer"][0],
            },
        )
        ready = await advance_review(j, assigned)
    else:
        current = await row()
        body = screen_body(current["version"])
        if scenario == "concurrent_screen_withdraw":
            assert app.state.database.postgres
            effects = await j["effects"]()
            responses = await asyncio.gather(
                post(path + "/screening", body, "reviewer"), post(path + "/withdraw", body)
            )
            assert sorted(r.status_code for r in responses) == [200, 412]
            assert (await row())["version"] == current["version"] + 1
            after = await j["effects"]()
            assert after[0][4:] == [count + 1 for count in effects[0][4:]]
            return {
                "scenario": scenario,
                "result": "ONE_CONCURRENT_SCREEN_OR_WITHDRAW_NO_DOUBLE_EFFECT",
            }
        if scenario == "guards_and_order":
            await refused(path + "/screening", body, "creator", 403)
            await refused(path + "/screening", body | {"expected_version": 2}, "reviewer", 412)
            await refused(path + "/screening", body | {"intent_confirmed": False}, "reviewer", 422)
            await refused(path + "/screening", body | {"reason": ""}, "reviewer", 422)
            await refused(path + "/inspections", j["finding"], "inspector", 409)
            await refused(path + "/evidence-review", review_body(3), "reviewer", 409)
            signed_out = await client.post(
                "/v1" + path + "/screening", json=body, headers={"Origin": ORIGIN}
            )
            assert signed_out.status_code == 401
        if scenario == "expiry":
            with evidence_expired():
                await refused(path + "/screening", body, "reviewer", 422)
        if scenario == "policy_and_scope":
            await mismatched_scope("/screening", body, "reviewer")
            with evidence_expired():
                await refused(path + "/screening", body, "reviewer", 409, "POLICY_NOT_ACTIVE")
        if scenario == "scope_and_replay":
            identifier = db.uid()
            async with app.state.database.transaction() as session:
                await session.execute(
                    db.accounts.insert().values(
                        id=identifier,
                        email=identifier + "@synthetic.invalid",
                        name="Synthetic unassigned reviewer",
                        active=True,
                        created_at=stamp(),
                    )
                )
                await session.execute(
                    db.grants.insert().values(
                        id=db.uid(),
                        account_id=identifier,
                        role="STANDARDS_REVIEWER",
                        scope_type="GLOBAL",
                        scope_id="GLOBAL",
                        valid_from=stamp(-1),
                        valid_until=stamp(1),
                        revoked=False,
                        grantor="ISOLATED_SCREENING_PROOF",
                    )
                )
                actors["unassigned"] = (identifier, await issue_session(session, identifier, 30))
            await refused(path + "/screening", body, "unassigned", 403)
        key = db.uid()
        screened = await create(path + "/screening", body, "reviewer", key)
        assert await create(path + "/screening", body, "reviewer", key) == screened
        assert screened["state"] == "EVIDENCE_REVIEW"
        if scenario == "scope_and_replay":
            async with app.state.database.transaction() as session:
                await session.execute(
                    update(db.grants)
                    .where(db.grants.c.account_id == actors["reviewer"][0])
                    .values(scope_type="FACILITY", scope_id=db.uid())
                )
            effects = await j["effects"]()
            response = await post(path + "/screening", body, "reviewer", key)
            assert response.status_code == 404 and await j["effects"]() == effects
            async with app.state.database.transaction() as session:
                await session.execute(
                    update(db.grants)
                    .where(db.grants.c.account_id == actors["reviewer"][0])
                    .values(scope_type="GLOBAL", scope_id="GLOBAL", revoked=True)
                )
            response = await post(path + "/screening", body, "reviewer", key)
            assert response.status_code == 404 and await j["effects"]() == effects
            return {
                "scenario": scenario,
                "result": "PERSONAL_ASSIGNMENT_AND_CURRENT_SCOPE_REQUIRED_FOR_REPLAY",
            }
        review = review_body(screened["version"])
        if scenario == "policy_and_scope":
            await mismatched_scope("/evidence-review", review, "reviewer")
        if scenario == "guards_and_order":
            await refused(path + "/evidence-review", review, "inspector", 403)
            for values in ([], review["assessments"][:1], [review["assessments"][0]] * 2):
                await refused(
                    path + "/evidence-review",
                    review | {"assessments": values},
                    "reviewer",
                    409,
                    "INCOMPLETE_EVIDENCE_REVIEW",
                )
            wrong = [{**item} for item in review["assessments"]]
            wrong[0]["evidence_ids"] = [j["proofs"]["SYN-B"]]
            await refused(
                path + "/evidence-review",
                review | {"assessments": wrong},
                "reviewer",
                409,
                "EVIDENCE_NOT_CURRENT",
            )
            other_facility = await create(
                "/facilities",
                j["registration"]
                | {"site_name": "Synthetic other facility", "external_reference": db.uid()},
            )
            other = await create(
                "/applications",
                {"facility_id": other_facility["id"], "criteria_id": j["criteria"]["id"]},
            )
            for identifier in (
                await proof(other["id"]),
                await proof(current["id"], status="UNVERIFIED"),
            ):
                wrong[0]["evidence_ids"] = [identifier]
                await refused(
                    path + "/evidence-review",
                    review | {"assessments": wrong},
                    "reviewer",
                    409,
                    "EVIDENCE_NOT_CURRENT",
                )
        if scenario == "expiry":
            with evidence_expired():
                await refused(
                    path + "/evidence-review", review, "reviewer", 409, "EVIDENCE_NOT_CURRENT"
                )
        key = db.uid()
        ready = await create(path + "/evidence-review", review, "reviewer", key)
        assert await create(path + "/evidence-review", review, "reviewer", key) == ready
    assert ready["state"] == "INSPECTION"
    recommendation = {
        "expected_version": ready["version"],
        "decision": "APPROVE",
        "reason": "Synthetic independent recommendation",
    }
    await refused(
        path + "/recommendation", recommendation, "reviewer", 409, "CURRENT_INSPECTION_REQUIRED"
    )
    finding = {
        "expected_version": ready["version"],
        "conflict_declared": False,
        "observed_at": stamp(-1),
        "findings": [
            {
                "criterion": code,
                "observation": "Synthetic actual observation",
                "outcome": "MET",
                "evidence_ids": [identifier],
            }
            for code, identifier in j["proofs"].items()
        ],
    }
    if scenario == "unreviewed_evidence":
        extra = await proof(ready["id"])
        unreviewed = finding | {"findings": [{**item} for item in finding["findings"]]}
        unreviewed["findings"][0]["evidence_ids"] = [extra]
        await refused(path + "/inspections", unreviewed, "inspector", 409, "UNREVIEWED_EVIDENCE")
    if scenario == "expiry":
        with evidence_expired():
            await refused(path + "/inspections", finding, "inspector", 409, "EVIDENCE_NOT_CURRENT")
    if scenario == "policy_and_scope":
        await mismatched_scope("/inspections", finding, "inspector")
    inspected = await create(path + "/inspections", finding, "inspector")
    assert inspected["state"] == "INSPECTION" and inspected["version"] == ready["version"] + 1
    await refused(
        path + "/inspections",
        finding | {"expected_version": inspected["version"]},
        "inspector",
        409,
        "EVIDENCE_REVIEW_REQUIRED",
    )
    if scenario == "policy_and_scope":
        await mismatched_scope(
            "/recommendation",
            recommendation | {"expected_version": inspected["version"]},
            "reviewer",
        )
    recommended = await create(
        path + "/recommendation",
        recommendation | {"expected_version": inspected["version"]},
        "reviewer",
    )
    decision = {
        "expected_version": recommended["version"],
        "decision": "APPROVE",
        "reason": "Synthetic independent central decision",
        "scope": "Synthetic only",
        "conditions": "",
        "effective_at": stamp(-1),
        "expires_at": stamp(1),
        "intent_confirmed": True,
    }
    if scenario == "policy_and_scope":
        await mismatched_scope("/decisions", decision, "decider")
    await create(path + "/decisions", decision, "decider")
    after = await dossier()
    if legacy:
        retained = {item["version"]: item["payload"] for item in after["history"]}
        assert all(retained[item["version"]] == item["payload"] for item in before["history"])
        assert all(item in after["inspections"] for item in before["inspections"])
    else:
        assert [item["payload"]["state"] for item in reversed(after["history"])] == [
            "DRAFT",
            "SUBMITTED",
            "SCREENING",
            "EVIDENCE_REVIEW",
            "INSPECTION",
            "INSPECTION",
            "RECOMMENDED",
            "DECIDED",
        ]
    if scenario not in {"unreviewed_evidence", "guards_and_order"}:
        assert before["evidence"] == after["evidence"]
    return {
        "scenario": scenario,
        "result": "SCREENING_EVIDENCE_REVIEW_INSPECTION_RECOMMENDATION_BOUND_BY_VERSION_HISTORY_RETAINED",
    }


@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_application_screening_order_and_guards(tmp_path, scenario):
    if scenario == "concurrent_screen_withdraw":
        pytest.skip("Concurrent row-lock proof runs in isolated Neon")
    cfg = PlatformSettings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'screening.db').as_posix()}",
        data_key_hex="05" * 32,
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
