"""Isolated corrective-plan facts, actual version binding and historical-source retention."""

import asyncio
import hashlib
import hmac
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from lw_care_api.platform import db
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.control import tables as control
from lw_care_api.platform.control.service import canonical
from lw_care_api.platform.institutional import tables as t
from lw_care_api.platform.main import create_platform_app
from lw_care_api.platform.security import issue_session
from sqlalchemy import func, select, update
from test_director_affiliation_conformance import ORIGIN, stamp
from test_director_affiliation_conformance import exercise as initial_fixture

SCENARIOS = (
    "guards_and_resolution",
    "revision_and_history",
    "deadline_and_expiry",
    "legacy_receipt_scope",
    "legacy_resolved_recovery",
    "handover_pending",
    "handover_resolved",
    "concurrent_agree_revise",
)


@contextmanager
def clock_offset(minutes):
    original = db.now
    at = (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat(timespec="microseconds")
    db.now = lambda: at
    try:
        yield
    finally:
        db.now = original


async def exercise(app, client, scenario):
    j = await initial_fixture(
        app,
        client,
        "corrective_fixture",
        fixture_state="INSPECTION",
        evidence_valid_minutes=60 if app.state.database.postgres else 10,
    )
    actors, create, post = (j[k] for k in ("actors", "create", "post"))
    async with app.state.database.transaction() as session:
        await session.execute(
            db.grants.insert().values(
                id=db.uid(),
                account_id=actors["creator"][0],
                role="FACILITY_ADMIN",
                scope_type="GLOBAL",
                scope_id="GLOBAL",
                valid_from=stamp(-10),
                valid_until=stamp(30),
                revoked=False,
                grantor="ISOLATED_CORRECTIVE_PROOF",
            )
        )
    await create(
        f"/facilities/{j['facility']['id']}/verification",
        {
            "expected_version": 1,
            "identity_status": "VERIFIED",
            "statutory_status": "CHECKED",
            "reason": "Synthetic independently qualified fixture identity",
        },
    )
    inspected = await create(j["path"] + "/inspections", j["finding"], "inspector")
    recommended = await create(
        j["path"] + "/recommendation",
        {
            "expected_version": inspected["version"],
            "decision": "APPROVE",
            "reason": "Synthetic independent baseline review",
        },
        "reviewer",
    )
    await create(
        j["path"] + "/decisions",
        {
            "expected_version": recommended["version"],
            "decision": "APPROVE",
            "reason": "Synthetic baseline initial recognition",
            "scope": "Synthetic only",
            "conditions": "",
            "effective_at": stamp(-1),
            "expires_at": stamp(12),
            "intent_confirmed": True,
        },
        "decider",
    )
    case = await create(
        "/institutional/cases",
        {
            "facility_id": j["facility"]["id"],
            "kind": "RENEWAL",
            "criteria_id": j["criteria"]["id"],
            "respondent_id": actors["creator"][0],
            "due_at": stamp(5),
            "calendar_authority_reference": "SYNTHETIC_ONLY_CALENDAR",
            "evidence": "Synthetic case, not operating adoption",
            "intent_confirmed": True,
        },
    )
    cp = "/institutional/cases/" + case["id"]
    case = await create(
        cp + "/assign",
        {
            "expected_version": case["version"],
            "inspector_id": actors["inspector"][0],
            "reviewer_id": actors["reviewer"][0],
            "competence_reference": "Synthetic assigned independent competence",
            "evidence": "Synthetic actual assignment",
            "intent_confirmed": True,
        },
        "reviewer",
    )
    case = await create(
        cp + "/inspect",
        {
            "expected_version": case["version"],
            "conflict_declared": False,
            "observed_at": stamp(-1),
            "findings": [
                {
                    "criterion": code,
                    "outcome": "NOT_MET" if code == "SYN-A" else "MET",
                    "observation": "Synthetic actual source observation",
                    "evidence_ids": [] if code == "SYN-A" else [identifier],
                    "due_at": stamp(4),
                }
                for code, identifier in j["proofs"].items()
            ],
            "evidence": "Synthetic actual independent findings",
            "intent_confirmed": True,
        },
        "inspector",
    )

    async def dossier(actor="creator"):
        response = await client.get(
            "/v1" + cp, headers={"Authorization": "Bearer " + actors[actor][1]}
        )
        assert response.status_code == 200
        return response.json()

    async def current():
        return next(row for row in (await dossier())["findings"] if row["criterion"] == "SYN-A")

    async def effects():
        async with app.state.database.transaction() as session:
            counts = [
                await session.scalar(select(func.count()).select_from(table))
                for table in (
                    t.cases,
                    t.findings,
                    t.responses,
                    t.decisions,
                    t.journal,
                    control.receipts,
                )
            ]
            findings = (
                (await session.execute(select(t.findings).order_by(t.findings.c.id)))
                .mappings()
                .all()
            )
            facilities = (
                await session.execute(
                    select(
                        db.facilities.c.id,
                        db.facilities.c.version,
                        db.facilities.c.affiliation_status,
                    ).order_by(db.facilities.c.id)
                )
            ).all()
            return counts, [dict(row) for row in findings], facilities

    async def refused(path, body, actor, status, code=None):
        before = await effects()
        response = await post(path, body, actor)
        assert response.status_code == status, (
            path,
            response.status_code,
            response.json().get("error", {}).get("code"),
        )
        if code:
            assert response.json()["error"]["code"] == code
        assert await effects() == before, (
            "Refusal changed consequential finding/case/source/receipt facts"
        )

    async def new_actor(name, role):
        identifier = db.uid()
        async with app.state.database.transaction() as session:
            await session.execute(
                db.accounts.insert().values(
                    id=identifier,
                    email=identifier + "@synthetic.invalid",
                    name="Synthetic corrective " + name,
                    active=True,
                    created_at=stamp(),
                )
            )
            await session.execute(
                db.grants.insert().values(
                    id=db.uid(),
                    account_id=identifier,
                    role=role,
                    scope_type="GLOBAL",
                    scope_id="GLOBAL",
                    valid_from=stamp(-1),
                    valid_until=stamp(20),
                    revoked=False,
                    grantor="ISOLATED_CORRECTIVE_PROOF",
                )
            )
            actors[name] = (identifier, await issue_session(session, identifier, 30))

    finding = await current()
    original = dict(finding)
    path = "/institutional/findings/" + finding["id"]
    reason = {"evidence": "Synthetic actual action under test authority", "intent_confirmed": True}

    def proposal(version, due=None):
        return reason | {
            "expected_version": version,
            "required_action": "Synthetic agreed repair with actual proof",
            "due_at": due or stamp(2),
            "deadline_authority_reference": "SYNTHETIC_ACTUAL_DEADLINE_AUTHORITY",
        }

    def response_body(version, plan_id=None):
        body = reason | {
            "expected_version": version,
            "completion_evidence": "Synthetic actual corrective work and resolution proof",
            "evidence_ids": [j["proofs"]["SYN-A"]],
        }
        return body | {"corrective_plan_id": plan_id} if plan_id else body

    def review_plan(row, decision="AGREE"):
        return reason | {
            "expected_version": row["version"],
            "plan_id": row["corrective_plan"]["plan_id"],
            "decision": decision,
        }

    if scenario == "legacy_resolved_recovery":
        # Retained pre-extension shape, not claimed executed transitions.
        response = {
            "id": db.uid(),
            "finding_id": finding["id"],
            "author_id": actors["creator"][0],
            "created_at": stamp(),
            "details_ciphertext": app.state.box.encrypt(canonical(response_body(1))),
        }
        async with app.state.database.transaction() as session:
            await session.execute(t.responses.insert().values(**response))
            for version, action, details in [
                (2, "standards.response_submitted", {"response": response}),
                (
                    3,
                    "standards.response_reviewed",
                    reason
                    | {
                        "response_id": response["id"],
                        "decision": "RESOLVE",
                        "fixture": "LEGACY_SHAPE_NOT_EXECUTED_TRANSITIONS",
                    },
                ),
            ]:
                await session.execute(
                    t.journal.insert().values(
                        id=db.uid(),
                        resource_id=finding["id"],
                        facility_id=j["facility"]["id"],
                        action=action,
                        actor_id=actors["reviewer"][0],
                        version=version,
                        recorded_at=stamp(),
                        correlation_id=db.uid(),
                        payload_ciphertext=app.state.box.encrypt(canonical({"details": details})),
                    )
                )
            await session.execute(
                update(t.findings)
                .where(t.findings.c.id == finding["id"])
                .values(state="RESOLVED", version=3)
            )
        finding = await current()
        await refused(
            cp + "/recommend",
            reason | {"expected_version": case["version"], "action": "RENEW"},
            "reviewer",
            409,
            "CORRECTIVE_PLAN_REQUIRED",
        )

    if scenario == "legacy_receipt_scope":
        # An explicitly labelled old-shape receipt qualifies hash/replay compatibility,
        # not execution of an old response or a production business transition.
        body, key = response_body(1), db.uid()
        result = {
            "resource": {
                "id": finding["id"],
                "version": 2,
                "state": "RESPONSE_SUBMITTED",
                "response_id": db.uid(),
                "resolved": False,
                "fixture": "LEGACY_RECEIPT_NOT_EXECUTED_TRANSITION",
            },
            "execution_state": "CENTRAL_COMMITTED",
            "authority_node_id": app.state.settings.authority_node_id,
        }
        async with app.state.database.transaction() as session:
            await session.execute(
                control.receipts.insert().values(
                    id=db.uid(),
                    actor_id=actors["creator"][0],
                    operation="/v1" + path + "/respond",
                    key=key,
                    request_hash=hmac.new(
                        bytes.fromhex(app.state.settings.data_key_hex),
                        canonical(body).encode(),
                        hashlib.sha256,
                    ).hexdigest(),
                    response_ciphertext=app.state.box.encrypt(canonical(result)),
                    expires_at=stamp(1),
                )
            )
        before = await effects()
        cached = await post(path + "/respond", body, "creator", key)
        assert cached.status_code == 200 and cached.json() == result and await effects() == before
        await refused(path + "/respond", body, "creator", 409, "CORRECTIVE_PLAN_REQUIRED")
        async with app.state.database.transaction() as session:
            await session.execute(
                update(db.grants)
                .where(
                    db.grants.c.account_id == actors["creator"][0],
                    db.grants.c.role == "FACILITY_ADMIN",
                )
                .values(revoked=True)
            )
        cached = await post(path + "/respond", body, "creator", key)
        assert cached.status_code == 409 and await effects() == before
        return {
            "scenario": scenario,
            "result": "LEGACY_BODY_HASH_REPLAY_RETAINED_CURRENT_AUTHORITY_STILL_REQUIRED_NO_NEW_EFFECT",
        }

    if scenario == "guards_and_resolution":
        await refused(
            path + "/respond", response_body(1), "creator", 409, "CORRECTIVE_PLAN_REQUIRED"
        )
        await refused(path + "/corrective-plan", proposal(1), "reviewer", 403)
        await refused(
            path + "/corrective-plan", proposal(1) | {"intent_confirmed": False}, "creator", 422
        )
        await refused(
            path + "/corrective-plan", proposal(1) | {"required_action": ""}, "creator", 422
        )
        await refused(
            path + "/corrective-plan", proposal(1) | {"due_at": stamp(-1)}, "creator", 422
        )
        await refused(
            path + "/corrective-plan", proposal(1) | {"owner_team_id": db.uid()}, "creator", 422
        )
    due = (
        (datetime.now(UTC) + timedelta(minutes=2)).isoformat()
        if scenario == "deadline_and_expiry"
        else None
    )
    key = db.uid()
    body = proposal(finding["version"], due)
    proposed = await create(path + "/corrective-plan", body, "creator", key)
    assert await create(path + "/corrective-plan", body, "creator", key) == proposed
    if scenario == "concurrent_agree_revise":
        assert app.state.database.postgres
        before = await effects()
        replies = await asyncio.gather(
            post(path + "/corrective-plan-review", review_plan(proposed), "reviewer"),
            post(path + "/corrective-plan", proposal(proposed["version"]), "creator"),
        )
        assert sorted(row.status_code for row in replies) == [200, 412]
        after = await effects()
        assert after[0][4:] == [value + 1 for value in before[0][4:]]
        assert (await current())["version"] == proposed["version"] + 1
        assert (await current())["details"] == original["details"]
        return {
            "scenario": scenario,
            "result": "ONE_PLAN_AGREEMENT_OR_REVISION_ONE_JOURNAL_AND_RECEIPT_NO_DOUBLE_EFFECT",
        }
    if scenario == "guards_and_resolution":
        await refused(
            path + "/respond",
            response_body(proposed["version"]),
            "creator",
            409,
            "CORRECTIVE_PLAN_REQUIRED",
        )
        await refused(path + "/corrective-plan-review", review_plan(proposed), "creator", 403)
        await refused(
            path + "/corrective-plan-review",
            review_plan(proposed) | {"plan_id": db.uid()},
            "reviewer",
            409,
            "STALE_CORRECTIVE_PLAN",
        )
        await refused(
            path + "/corrective-plan-review",
            review_plan(proposed) | {"expected_version": 1},
            "reviewer",
            412,
        )
        await new_actor("unassigned", "STANDARDS_REVIEWER")
        await refused(path + "/corrective-plan-review", review_plan(proposed), "unassigned", 403)
        await refused(
            cp + "/recommend",
            reason | {"expected_version": case["version"], "action": "CONDITIONAL"},
            "reviewer",
            409,
            "CORRECTIVE_PLAN_REQUIRED",
        )
    if scenario == "deadline_and_expiry":
        with clock_offset(3):
            await refused(path + "/corrective-plan-review", review_plan(proposed), "reviewer", 422)
        proposed = await create(path + "/corrective-plan", proposal(proposed["version"], due))
    if scenario == "revision_and_history":
        returned = await create(
            path + "/corrective-plan-review", review_plan(proposed, "RETURN"), "reviewer"
        )
        await refused(
            path + "/respond",
            response_body(returned["version"]),
            "creator",
            409,
            "CORRECTIVE_PLAN_REQUIRED",
        )
        proposed = await create(path + "/corrective-plan", proposal(returned["version"]))
    agreed = await create(path + "/corrective-plan-review", review_plan(proposed), "reviewer")
    owner = "creator"
    if scenario == "deadline_and_expiry":
        with clock_offset(3):
            first_response = await create(
                path + "/respond",
                response_body(agreed["version"], agreed["corrective_plan"]["plan_id"]),
            )
    else:
        first_response = await create(
            path + "/respond",
            response_body(agreed["version"], agreed["corrective_plan"]["plan_id"]),
        )
    assert first_response["resolved"] is False

    async def resolve(response, actor="reviewer"):
        return await create(
            path + "/review",
            reason
            | {
                "expected_version": response["version"],
                "response_id": response["response_id"],
                "decision": "RESOLVE",
            },
            actor,
        )

    if scenario == "revision_and_history":
        returned = await create(
            path + "/review",
            reason
            | {
                "expected_version": first_response["version"],
                "response_id": first_response["response_id"],
                "decision": "RETURN",
            },
            "reviewer",
        )
        proposed2 = await create(
            path + "/corrective-plan",
            proposal(returned["version"])
            | {"required_action": "Synthetic revised corrective action"},
        )
        agreed2 = await create(path + "/corrective-plan-review", review_plan(proposed2), "reviewer")
        await refused(
            path + "/respond",
            response_body(agreed2["version"], agreed["corrective_plan"]["plan_id"]),
            "creator",
            409,
            "STALE_CORRECTIVE_PLAN",
        )
        with clock_offset(-60):
            second = await create(
                path + "/respond",
                response_body(agreed2["version"], agreed2["corrective_plan"]["plan_id"]),
            )
        await refused(
            path + "/review",
            reason
            | {
                "expected_version": second["version"],
                "response_id": first_response["response_id"],
                "decision": "RESOLVE",
            },
            "reviewer",
            409,
            "STALE_RESPONSE",
        )
        await resolve(second)
    elif scenario in {"handover_pending", "handover_resolved"}:
        if scenario == "handover_resolved":
            await resolve(first_response)
        await new_actor("successor", "FACILITY_ADMIN")
        offered = await create(
            cp + "/assignment-offer",
            reason
            | {
                "expected_version": case["version"],
                "assignment_kind": "RESPONDENT",
                "successor_id": actors["successor"][0],
            },
            "reviewer",
        )
        case = await create(
            cp + "/assignment-accept",
            reason | {"expected_version": offered["version"], "assignment_kind": "RESPONDENT"},
            "successor",
        )
        if scenario == "handover_pending":
            finding = await current()
            assert not finding["corrective_plan"]["current_for_response"]
            await refused(
                path + "/review",
                reason
                | {
                    "expected_version": finding["version"],
                    "response_id": first_response["response_id"],
                    "decision": "RESOLVE",
                },
                "reviewer",
                409,
                "STALE_RESPONSE",
            )
            owner = "successor"
            proposed = await create(path + "/corrective-plan", proposal(finding["version"]), owner)
            agreed = await create(
                path + "/corrective-plan-review", review_plan(proposed), "reviewer"
            )
            response = await create(path + "/respond", response_body(agreed["version"]), owner)
            await resolve(response)
        else:
            assert (await current())["owner_id"] == actors["creator"][0]
    else:
        await refused(
            cp + "/recommend",
            reason | {"expected_version": case["version"], "action": "RENEW"},
            "reviewer",
            409,
            "UNRESOLVED_FINDINGS",
        )
        if scenario == "deadline_and_expiry":
            # A deadline is not an evidence expiry or automatic completion rule.
            with clock_offset(3):
                await resolve(first_response)
        else:
            await resolve(first_response)

    if scenario == "deadline_and_expiry":
        with clock_offset(20):
            await refused(
                cp + "/recommend",
                reason | {"expected_version": case["version"], "action": "RENEW"},
                "reviewer",
                409,
                "EVIDENCE_NOT_CURRENT",
            )
    case = await create(
        cp + "/recommend",
        reason | {"expected_version": case["version"], "action": "RENEW"},
        "reviewer",
    )
    await create(
        cp + "/decide",
        reason
        | {
            "expected_version": case["version"],
            "action": "RENEW",
            "scope": "Synthetic qualified scope only",
            "conditions": "",
            "expires_at": stamp(8),
        },
        "decider",
    )
    final = await current()
    assert final["details"] == original["details"] and final["state"] == "RESOLVED"
    history = await client.get(
        "/v1" + path + "/corrective-history",
        headers={"Authorization": "Bearer " + actors[owner][1]},
    )
    assert history.status_code == 200 and "ciphertext" not in history.text
    if scenario == "guards_and_resolution":
        await new_actor("outsider", "CLINICAL_STAFF")
        denied = await client.get(
            "/v1" + path + "/corrective-history",
            headers={"Authorization": "Bearer " + actors["outsider"][1]},
        )
        assert denied.status_code == 404
    assert any(
        item["action"] == "standards.response_reviewed" and item["details"]["decision"] == "RESOLVE"
        for item in history.json()["items"]
    )
    if scenario == "revision_and_history":
        # Explicit pagination volume, never a claim of executed domain transitions.
        async with app.state.database.transaction() as session:
            for version in range(100, 155):
                await session.execute(
                    t.journal.insert().values(
                        id=db.uid(),
                        resource_id=finding["id"],
                        facility_id=j["facility"]["id"],
                        action="standards.response_reviewed",
                        actor_id=actors["reviewer"][0],
                        version=version,
                        recorded_at=stamp(),
                        correlation_id=db.uid(),
                        payload_ciphertext=app.state.box.encrypt(
                            canonical(
                                {"details": {"fixture": "PAGINATION_ONLY_NOT_EXECUTED_TRANSITIONS"}}
                            )
                        ),
                    )
                )
        first = (
            await client.get(
                "/v1" + path + "/corrective-history",
                headers={"Authorization": "Bearer " + actors["creator"][1]},
            )
        ).json()
        second = (
            await client.get(
                "/v1" + path + "/corrective-history",
                params={"before_version": first["next_before_version"]},
                headers={"Authorization": "Bearer " + actors["creator"][1]},
            )
        ).json()
        assert len(first["items"]) == 50 and not {row["version"] for row in first["items"]} & {
            row["version"] for row in second["items"]
        }
        assert (await current())["corrective_plan"]["status"] == "AGREED"
    return {
        "scenario": scenario,
        "result": "EXACT_AGREED_PLAN_RESPONSE_AND_INDEPENDENT_RESOLUTION_ORIGINAL_SOURCE_RETAINED",
    }


@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_corrective_plan_guards_and_history(tmp_path, scenario):
    if scenario == "concurrent_agree_revise":
        pytest.skip("Real PostgreSQL plan-agreement/revision race runs in isolated Neon")
    cfg = PlatformSettings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'plans.db').as_posix()}",
        data_key_hex="06" * 32,
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
