"""Correction-cycle and withdrawal proofs; isolated synthetic metadata, never adoption."""

import asyncio
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from lw_care_api.platform import db
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.main import create_platform_app
from lw_care_api.platform.security import issue_session
from sqlalchemy import update
from test_director_affiliation_conformance import ORIGIN, advance_review, stamp
from test_director_affiliation_conformance import exercise as initial_fixture

SCENARIOS = (
    "round_trip",
    "cycle_binding",
    "historical_independence",
    "response_validation",
    "withdraw_DRAFT",
    "withdraw_SUBMITTED",
    "withdraw_SCREENING",
    "withdraw_INSPECTION",
    "withdraw_EVIDENCE_REVIEW",
    "withdraw_RECOMMENDED",
    "withdraw_CORRECTION_REQUIRED",
    "decided_terminal",
    "history_scope_and_paging",
    "concurrent_withdraw_resubmit",
)


@contextmanager
def older_recording_time():
    original = db.now
    at = (datetime.now(UTC) - timedelta(hours=1)).isoformat(timespec="microseconds")
    db.now = lambda: at
    try:
        yield
    finally:
        db.now = original


async def exercise(app, client, scenario):
    target = (
        scenario.removeprefix("withdraw_") if scenario.startswith("withdraw_") else "RECOMMENDED"
    )
    phase = target if target in {"DRAFT", "SUBMITTED", "SCREENING", "EVIDENCE_REVIEW"} else "INSPECTION"
    j = await initial_fixture(app, client, "workflow_fixture", fixture_state=phase)
    post, create, refused, actors, path = (
        j[k] for k in ("post", "create", "refused", "actors", "path")
    )

    async def get(actor="creator", cursor=0):
        r = await client.get(
            "/v1" + path + (f"?history_before={cursor}" if cursor else ""),
            headers={"Authorization": "Bearer " + actors[actor][1]},
        )
        assert r.status_code == 200
        return r.json()

    async def state():
        return (await get())["application"]

    async def grant(name, role):
        async with app.state.database.transaction() as s:
            await s.execute(
                db.grants.insert().values(
                    id=db.uid(),
                    account_id=actors[name][0],
                    role=role,
                    scope_type="GLOBAL",
                    scope_id="GLOBAL",
                    valid_from=stamp(-10),
                    valid_until=stamp(30),
                    revoked=False,
                    grantor="ISOLATED_WORKFLOW_PROOF",
                )
            )

    async def new_actor(name, role):
        identifier = db.uid()
        async with app.state.database.transaction() as s:
            await s.execute(
                db.accounts.insert().values(
                    id=identifier,
                    email=identifier + "@synthetic.invalid",
                    name="Synthetic workflow " + name,
                    active=True,
                    created_at=stamp(),
                )
            )
            actors[name] = (identifier, await issue_session(s, identifier, 30))
        await grant(name, role)

    async def request():
        row = await state()
        body = {
            "expected_version": row["version"],
            "reason": "Synthetic actual response required",
            "criterion_codes": ["SYN-A", "SYN-B"],
            "intent_confirmed": True,
        }
        key = db.uid()
        value = await create(path + "/correction-request", body, "reviewer", key)
        j["request_receipt"] = (body, key)
        assert await create(path + "/correction-request", body, "reviewer", key) == value
        return value

    async def response_body():
        return {
            "expected_version": (await state())["version"],
            "reason": "Synthetic actual correction response",
            "responses": [
                {
                    "criterion": c,
                    "response": "Synthetic actual response for " + c,
                    "evidence_ids": [identifier],
                }
                for c, identifier in j["proofs"].items()
            ],
            "intent_confirmed": True,
        }

    if phase == "INSPECTION" and target not in {"INSPECTION"}:
        await create(path + "/inspections", j["finding"], "inspector")
        if target != "EVIDENCE_REVIEW":
            await create(
                path + "/recommendation",
                {
                    "expected_version": 6,
                    "decision": "APPROVE",
                    "reason": "Synthetic independent recommendation",
                },
                "reviewer",
            )
    if target == "CORRECTION_REQUIRED":
        await request()

    if scenario.startswith("withdraw_"):
        before = await get()
        row = before["application"]
        body = {
            "expected_version": row["version"],
            "reason": "Synthetic actual withdrawal request",
            "intent_confirmed": True,
        }
        await refused(path + "/withdraw", body, "reviewer", 403)
        await refused(path + "/withdraw", body | {"expected_version": 0}, "creator", 422)
        key = db.uid()
        withdrawn = await create(path + "/withdraw", body, "creator", key)
        assert await create(path + "/withdraw", body, "creator", key) == withdrawn
        after = await get()
        assert after["application"]["state"] == "WITHDRAWN"
        assert before["facility"] == after["facility"] and before["evidence"] == after["evidence"]
        assert (
            before["inspections"] == after["inspections"]
            and before["decisions"] == after["decisions"]
        )
        assert after["history"][0]["payload"]["withdrawal"]["reason"] == body["reason"]
        await refused(path + "/submit", {"expected_version": withdrawn["version"]}, "creator", 409)
        await refused(
            path + "/withdraw", body | {"expected_version": withdrawn["version"]}, "creator", 409
        )
        decision = {
            "expected_version": withdrawn["version"],
            "decision": "APPROVE",
            "reason": "Synthetic forbidden completion",
            "scope": "Synthetic only",
            "conditions": "",
            "effective_at": stamp(-1),
            "expires_at": stamp(1),
            "intent_confirmed": True,
        }
        await refused(path + "/decisions", decision, "decider", 409)
        return {
            "scenario": scenario,
            "result": "WITHDRAWAL_RETAINS_HISTORY_AND_AFFILIATION_NO_RECOGNITION",
        }

    if scenario == "decided_terminal":
        await create(
            path + "/decisions",
            {
                "expected_version": 7,
                "decision": "APPROVE",
                "reason": "Synthetic final decision",
                "scope": "Synthetic only",
                "conditions": "",
                "effective_at": stamp(-1),
                "expires_at": stamp(1),
                "intent_confirmed": True,
            },
            "decider",
        )
        await refused(
            path + "/withdraw",
            {
                "expected_version": 8,
                "reason": "Synthetic cannot erase decision",
                "intent_confirmed": True,
            },
            "creator",
            409,
        )
        return {"scenario": scenario, "result": "DECIDED_APPLICATION_CANNOT_BE_WITHDRAWN"}

    original = await get()
    row = original["application"]
    request_body = {
        "expected_version": row["version"],
        "reason": "Synthetic reviewer correction request",
        "criterion_codes": ["SYN-A", "SYN-B"],
        "intent_confirmed": True,
    }
    if scenario == "response_validation":
        await refused(path + "/correction-request", request_body, "creator", 403)
        await refused(
            path + "/correction-request",
            request_body | {"criterion_codes": ["SYN-A", "SYN-A"]},
            "reviewer",
            422,
        )
        await refused(
            path + "/correction-request",
            request_body | {"criterion_codes": ["UNADOPTED"]},
            "reviewer",
            422,
        )
        await refused(
            path + "/correction-request",
            request_body | {"expected_version": row["version"] - 1},
            "reviewer",
            412,
        )
    await request()
    correction = await get()
    assert correction["application"]["recommendation"] is None
    assert (
        original["evidence"] == correction["evidence"]
        and original["inspections"] == correction["inspections"]
    )
    assert correction["correction_request"]["criterion_codes"] == ["SYN-A", "SYN-B"]
    response = await response_body()
    await refused(
        path + "/submit", {"expected_version": response["expected_version"]}, "creator", 409
    )
    if scenario == "response_validation":
        effects_before = await j["effects"]()
        upload = await client.post(
            "/v1" + path + "/evidence",
            params={
                "criterion": "SYN-A",
                "filename": "synthetic.pdf",
                "source": "ISOLATED SCANNER EXCLUSION PROBE",
                "expires_at": stamp(1),
            },
            content=b"%PDF-1.4\nSYNTHETIC\n",
            headers={
                "Origin": ORIGIN,
                "Authorization": "Bearer " + actors["creator"][1],
                "Content-Type": "application/pdf",
                "Idempotency-Key": db.uid(),
            },
        )
        assert upload.status_code == 503 and await j["effects"]() == effects_before
        await refused(path + "/resubmit", response, "reviewer", 403)
        await refused(
            path + "/resubmit", response | {"responses": response["responses"][:1]}, "creator", 409
        )
        await refused(
            path + "/resubmit",
            response | {"responses": [response["responses"][0]] * 2},
            "creator",
            409,
        )
        wrong = [dict(r) for r in response["responses"]]
        wrong[0]["evidence_ids"] = [j["proofs"]["SYN-B"]]
        await refused(path + "/resubmit", response | {"responses": wrong}, "creator", 409)

    if scenario == "concurrent_withdraw_resubmit":
        assert app.state.database.postgres
        replies = await asyncio.gather(
            post(path + "/resubmit", response),
            post(
                path + "/withdraw",
                {
                    "expected_version": response["expected_version"],
                    "reason": "Synthetic concurrent withdrawal",
                    "intent_confirmed": True,
                },
            ),
        )
        assert sorted(r.status_code for r in replies) == [200, 412]
        assert (await state())["version"] == response["expected_version"] + 1
        return {"scenario": scenario, "result": "ONE_CONCURRENT_TRANSITION_NO_DOUBLE_EFFECT"}

    key = db.uid()
    submitted = await create(path + "/resubmit", response, "creator", key)
    assert await create(path + "/resubmit", response, "creator", key) == submitted
    assert (
        submitted["state"] == "SUBMITTED"
        and submitted["inspector_id"] is None
        and submitted["reviewer_id"] is None
    )
    assert (await get())["facility"] == original["facility"]

    if scenario == "history_scope_and_paging":
        async with app.state.database.transaction() as s:
            for version in range(submitted["version"] + 1, 65):
                await s.execute(
                    db.revisions.insert().values(
                        id=db.uid(),
                        resource_id=j["application"]["id"],
                        resource_type="Application",
                        version=version,
                        payload={
                            "state": "SUBMITTED",
                            "fixture": "SYNTHETIC_PAGINATION_ONLY_NOT_EXECUTED_TRANSITIONS",
                        },
                        actor_id=actors["creator"][0],
                        recorded_at=stamp(),
                    )
                )
            await s.execute(
                update(db.applications)
                .where(db.applications.c.id == j["application"]["id"])
                .values(version=64)
            )
        first = await get()
        second = await get(cursor=first["history_next_before"])
        assert len(first["history"]) == 50 and second["history"]
        assert not {r["version"] for r in first["history"]} & {
            r["version"] for r in second["history"]
        }
        assert first["history"][0]["version"] == 64 and second["history"][-1]["version"] == 1
        await new_actor("outsider", "CLINICAL_STAFF")
        r = await client.get(
            "/v1" + path, headers={"Authorization": "Bearer " + actors["outsider"][1]}
        )
        assert r.status_code == 404
        return {
            "scenario": scenario,
            "result": "BOUNDED_PRIVATE_HISTORY_PAGES_SYNTHETIC_PAGINATION_FIXTURE",
        }

    assignment = {
        "expected_version": submitted["version"],
        "inspector_id": actors["inspector"][0],
        "reviewer_id": actors["reviewer"][0],
    }
    if scenario == "historical_independence":
        await new_actor("new_inspector", "INSPECTOR")
        await new_actor("new_reviewer", "STANDARDS_REVIEWER")
        assignment.update(
            inspector_id=actors["new_inspector"][0], reviewer_id=actors["new_reviewer"][0]
        )
    assigned = await create(path + "/assignment", assignment)
    reviewer = "new_reviewer" if scenario == "historical_independence" else "reviewer"
    ready = await advance_review(j, assigned, reviewer)
    findings = {**j["finding"], "expected_version": ready["version"]}
    if scenario == "cycle_binding":
        findings["findings"][0]["outcome"] = "NOT_MET"
        with older_recording_time():
            inspected = await create(path + "/inspections", findings, "inspector")
        await refused(
            path + "/recommendation",
            {
                "expected_version": inspected["version"],
                "decision": "APPROVE",
                "reason": "Synthetic cannot reuse old met inspection",
            },
            "reviewer",
            409,
            "UNRESOLVED_FINDINGS",
        )
        return {
            "scenario": scenario,
            "result": "CURRENT_REVISION_BINDS_INSPECTION_DESPITE_REVERSED_TIMESTAMPS",
        }
    inspector = "new_inspector" if scenario == "historical_independence" else "inspector"
    reviewer = "new_reviewer" if scenario == "historical_independence" else "reviewer"
    inspected = await create(path + "/inspections", findings, inspector)
    recommended = await create(
        path + "/recommendation",
        {
            "expected_version": inspected["version"],
            "decision": "APPROVE",
            "reason": "Synthetic fresh independent review",
        },
        reviewer,
    )
    decision = {
        "expected_version": recommended["version"],
        "decision": "APPROVE",
        "reason": "Synthetic central outcome",
        "scope": "Synthetic only",
        "conditions": "",
        "effective_at": stamp(-1),
        "expires_at": stamp(1),
        "intent_confirmed": True,
    }
    if scenario == "historical_independence":
        for former in ("inspector", "reviewer"):
            await grant(former, "STANDARDS_DECIDER")
            await refused(path + "/decisions", decision, former, 403)
    await create(path + "/decisions", decision, "decider")
    final = await get()
    assert len(final["inspections"]) == 2 and len(final["decisions"]) == 1
    assert original["evidence"] == final["evidence"]
    if scenario == "response_validation":
        async with app.state.database.transaction() as s:
            await s.execute(
                update(db.grants)
                .where(db.grants.c.account_id == actors["reviewer"][0])
                .values(revoked=True)
            )
        body, key = j["request_receipt"]
        cached = await post(path + "/correction-request", body, "reviewer", key)
        assert cached.status_code == 404
    return {
        "scenario": scenario,
        "result": "CORRECTION_RESPONSE_FRESH_INSPECTION_AND_INDEPENDENT_DECISION_HISTORY_RETAINED",
    }


@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_application_correction_and_withdrawal(tmp_path, scenario):
    if scenario == "concurrent_withdraw_resubmit":
        pytest.skip("PostgreSQL row-lock proof runs against isolated Neon")
    cfg = PlatformSettings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'workflow.db').as_posix()}",
        data_key_hex="04" * 32,
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
