"""Actual accepted team identity, exact plan binding and preserved individual/history semantics."""

import asyncio

import httpx
import pytest
from lw_care_api.platform import db
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.main import create_platform_app
from sqlalchemy import update
from test_corrective_plans import exercise as corrective_fixture
from test_director_affiliation_conformance import ORIGIN, stamp

SCENARIOS = (
    "team_guards_and_completion",
    "team_revision_and_retirement",
    "team_handover",
    "concurrent_accept_revise",
)


async def exercise(app, client, scenario):
    f = await corrective_fixture(app, client, "delivery_team_fixture")
    j, actors, post, reason = (f[key] for key in ("j", "actors", "post", "reason"))

    async def create(path, body, actor="creator", key=None):
        response = await post(path, body, actor, key)
        assert response.status_code == (201 if "/delivery-teams" in path else 200), (
            path,
            response.status_code,
            response.json().get("error", {}).get("code"),
        )
        return response.json()["resource"]

    path, finding, case = f["path"], f["finding"], f["case"]
    team_body = reason | {
        "facility_id": j["facility"]["id"],
        "name": "Synthetic delivery team",
        "purpose": "Synthetic documented corrective delivery only",
        "authority_reference": "ISOLATED_ENGINEERING_TEAM_REFERENCE_NOT_ADOPTION",
        "lead_account_id": actors["creator"][0],
    }
    base = "/institutional/delivery-teams"
    team_key = db.uid()
    team = await create(base, team_body, "creator", team_key)
    assert team == await create(base, team_body, "creator", team_key)
    assert team["id"] != actors["creator"][0] and team["state"] == "PROPOSED"
    tp = base + "/" + team["id"]

    def versioned(row):
        return reason | {"expected_version": row["version"]}

    def proposal(row, selected=None):
        selected = selected or team
        return f["proposal"](row["version"]) | {
            "owner_team_id": selected["id"],
            "owner_team_version": selected["version"],
        }

    await f["refused"](
        path + "/corrective-plan", proposal(finding), "creator", 409, "TEAM_ACCEPTANCE_REQUIRED"
    )
    await f["refused"](tp + "/accept", versioned(team), "reviewer", 403)
    if scenario == "concurrent_accept_revise":
        assert app.state.database.postgres
        before = await f["effects"]()
        replies = await asyncio.gather(
            post(tp + "/accept", versioned(team), "creator"),
            post(tp + "/revise", team_body | versioned(team), "creator"),
        )
        assert sorted(row.status_code for row in replies) == [201, 412]
        after = await f["effects"]()
        assert after[0][4:] == [value + 1 for value in before[0][4:]]
        assert after[0][:4] == before[0][:4] and after[1:] == before[1:]
        return {
            "scenario": scenario,
            "result": "ONE_TEAM_ACCEPTANCE_OR_REVISION_ONE_JOURNAL_AND_RECEIPT",
        }

    team = await create(tp + "/accept", versioned(team), "creator")
    assert team["state"] == "ACCEPTED" and team["accepted_by"] == actors["creator"][0]
    if scenario == "team_guards_and_completion":
        # Labelled foreign-facility fixture metadata, not a production registration.
        async with app.state.database.transaction() as session:
            original = (
                (
                    await session.execute(
                        db.facilities.select().where(db.facilities.c.id == j["facility"]["id"])
                    )
                )
                .mappings()
                .one()
            )
            foreign_id = db.uid()
            await session.execute(
                db.facilities.insert().values(
                    **{
                        **original,
                        "id": foreign_id,
                        "name": "Synthetic foreign team facility",
                        "external_reference": "SYNTHETIC_FOREIGN_TEAM_" + foreign_id,
                    }
                )
            )
        foreign = await create(base, team_body | {"facility_id": foreign_id}, "creator")
        foreign = await create(
            base + "/" + foreign["id"] + "/accept", versioned(foreign), "creator"
        )
        await f["refused"](path + "/corrective-plan", proposal(finding, foreign), "creator", 404)
    await f["refused"](
        tp + "/retire", reason | {"expected_version": team["version"] - 1}, "creator", 412
    )
    await f["new_actor"]("outsider", "FACILITY_ADMIN")
    async with app.state.database.transaction() as session:
        await session.execute(
            update(db.grants)
            .where(db.grants.c.account_id == actors["outsider"][0])
            .values(scope_type="FACILITY", scope_id=db.uid())
        )
    await f["refused"](tp + "/retire", versioned(team), "outsider", 403)
    response = await client.get(
        "/v1" + base + "?facility_id=" + j["facility"]["id"],
        headers={"Authorization": "Bearer " + actors["outsider"][1]},
    )
    assert response.status_code == 403
    response = await client.get(
        "/v1" + tp + "/history", headers={"Authorization": "Bearer " + actors["creator"][1]}
    )
    assert response.status_code == 200 and "ciphertext" not in response.text
    assert [row["version"] for row in response.json()["items"]] == [2, 1]
    proposed = await create(path + "/corrective-plan", proposal(finding), "creator")
    assert proposed["corrective_plan"]["owner_team"] == team
    if scenario == "team_revision_and_retirement":
        team = await create(tp + "/revise", team_body | versioned(team), "creator")
        await f["refused"](
            path + "/corrective-plan-review",
            f["review_plan"](proposed),
            "reviewer",
            409,
            "STALE_DELIVERY_TEAM",
        )
        assert not (await f["current"]())["corrective_plan"]["current_for_review"]
        team = await create(tp + "/accept", versioned(team), "creator")
        proposed = await create(path + "/corrective-plan", proposal(proposed, team), "creator")
    agreed = await create(path + "/corrective-plan-review", f["review_plan"](proposed), "reviewer")
    response = await create(path + "/respond", f["response_body"](agreed["version"]), "creator")
    if scenario == "team_handover":
        await f["new_actor"]("successor", "FACILITY_ADMIN")
        offer = await create(
            f["cp"] + "/assignment-offer",
            reason
            | {
                "expected_version": case["version"],
                "assignment_kind": "RESPONDENT",
                "successor_id": actors["successor"][0],
            },
            "reviewer",
        )
        case = await create(
            f["cp"] + "/assignment-accept",
            reason | {"expected_version": offer["version"], "assignment_kind": "RESPONDENT"},
            "successor",
        )
        current = await f["current"]()
        await f["refused"](
            path + "/corrective-plan",
            proposal(current),
            "successor",
            409,
            "TEAM_ACCEPTANCE_REQUIRED",
        )
        await f["refused"](
            path + "/review",
            reason
            | {
                "expected_version": current["version"],
                "response_id": response["response_id"],
                "decision": "RESOLVE",
            },
            "reviewer",
            409,
            "STALE_RESPONSE",
        )
        team = await create(
            tp + "/revise",
            team_body | versioned(team) | {"lead_account_id": actors["successor"][0]},
            "creator",
        )
        await f["refused"](tp + "/accept", versioned(team), "creator", 403)
        team = await create(tp + "/accept", versioned(team), "successor")
        proposed = await create(path + "/corrective-plan", proposal(current, team), "successor")
        agreed = await create(
            path + "/corrective-plan-review", f["review_plan"](proposed), "reviewer"
        )
        response = await create(
            path + "/respond", f["response_body"](agreed["version"]), "successor"
        )
    if scenario == "team_revision_and_retirement":
        retired = await create(tp + "/retire", versioned(team), "creator")
        await f["refused"](
            path + "/review",
            reason
            | {
                "expected_version": response["version"],
                "response_id": response["response_id"],
                "decision": "RESOLVE",
            },
            "reviewer",
            409,
            "STALE_DELIVERY_TEAM",
        )
        # Explicitly opt back into actual individual accountability; no automatic conversion.
        proposed = await create(
            path + "/corrective-plan", f["proposal"](response["version"]), "creator"
        )
        assert "owner_team" not in proposed["corrective_plan"] and retired["state"] == "RETIRED"
        agreed = await create(
            path + "/corrective-plan-review", f["review_plan"](proposed), "reviewer"
        )
        response = await create(path + "/respond", f["response_body"](agreed["version"]), "creator")
    resolved = await create(
        path + "/review",
        reason
        | {
            "expected_version": response["version"],
            "response_id": response["response_id"],
            "decision": "RESOLVE",
        },
        "reviewer",
    )
    if scenario == "team_guards_and_completion":
        await create(tp + "/retire", versioned(team), "creator")
    # Completed accepted ownership facts survive retirement; no pending work inherits them.
    recommendation = await create(
        f["cp"] + "/recommend",
        reason | {"expected_version": case["version"], "action": "RENEW"},
        "reviewer",
    )
    await create(
        f["cp"] + "/decide",
        reason
        | {
            "expected_version": recommendation["version"],
            "action": "RENEW",
            "scope": "Synthetic team proof only",
            "conditions": "",
            "expires_at": stamp(8),
        },
        "decider",
    )
    assert (
        resolved["state"] == "RESOLVED" and (await f["current"]())["details"] == finding["details"]
    )
    return {
        "scenario": scenario,
        "result": "EXACT_ACCEPTED_TEAM_BINDING_CURRENT_PENDING_AUTHORITY_AND_COMPLETED_SOURCE_PRESERVED",
    }


@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_delivery_team_accountability(tmp_path, scenario):
    if scenario == "concurrent_accept_revise":
        pytest.skip("Real PostgreSQL acceptance/revision race runs in isolated Neon")
    cfg = PlatformSettings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'teams.db').as_posix()}",
        data_key_hex="07" * 32,
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
