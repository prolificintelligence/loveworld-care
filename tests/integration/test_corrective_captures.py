"""Canonical missingness stays explicit; immutable capture cannot advance consequential work."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest
from lw_care_api.platform import db
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.control.service import canonical
from lw_care_api.platform.institutional import tables as t
from lw_care_api.platform.institutional.captures import ACTION
from lw_care_api.platform.main import create_platform_app
from test_corrective_plans import clock_offset
from test_corrective_plans import exercise as finding_fixture
from test_director_affiliation_conformance import ORIGIN, stamp

SCENARIOS = (
    "capture_missingness_and_source",
    "capture_handover_and_scope",
    "capture_reference_and_history",
    "concurrent_capture_replay",
)
SUITE = (
    Path(__file__).resolve().parents[2]
    / "docs/LW_Health_Intelligence_Platform_Complete_Documentation_Suite_v1.0/LW_Health_Intelligence_Platform_Documentation_Suite_v1.0/contracts/forms"
)
REQUIRED = json.loads((SUITE / "LWH-FRM-010.schema.json").read_text(encoding="utf-8"))["allOf"][0][
    "then"
]["properties"]["answers"]["required"]
REASONS = json.loads((SUITE / "common.schema.json").read_text(encoding="utf-8"))["$defs"][
    "absence"
]["properties"]["absent_reason"]["enum"]


async def exercise(app, client, scenario):
    f = await finding_fixture(app, client, "corrective_capture_fixture")
    j, actors, post, reason = (f[key] for key in ("j", "actors", "post", "reason"))

    async def create(path, data, actor="creator", key=None):
        response = await post(path, data, actor, key)
        assert response.status_code == (201 if "/delivery-teams" in path else 200), (
            path,
            response.status_code,
            response.json().get("error", {}).get("code"),
        )
        return response.json()["resource"]

    finding, case = f["finding"], f["case"]
    path = f["path"] + "/corrective-captures"

    def body(answers=None, stage="draft", actor="creator", row=None, current_case=None):
        return reason | {
            "expected_version": (row or finding)["version"],
            "expected_case_version": (current_case or case)["version"],
            "form": {
                "form_id": "LWH-FRM-010",
                "schema_version": "1.0.0",
                "stage": stage,
                "authority_node_id": app.state.settings.authority_node_id,
                "actor_id": actors[actor][0],
                "facility_or_unit_id": j["facility"]["id"],
                "answers": answers or {},
            },
        }

    async def read(actor="creator", before=None):
        response = await client.get(
            "/v1" + path + ("?before_id=" + before if before else ""),
            headers={"Authorization": "Bearer " + actors[actor][1]},
        )
        assert response.status_code == 200
        assert "ciphertext" not in response.text and "object_key" not in response.text
        return response.json()

    async def capture(data, actor="creator", key=None):
        before = await f["effects"]()
        result = await create(path, data, actor, key)
        after = await f["effects"]()
        assert after[0][:4] == before[0][:4] and after[1:] == before[1:]
        assert result["effect"] == "FORM_CAPTURE_ONLY_NO_WORKFLOW_TRANSITION"
        return result

    first_body = body()
    key = db.uid()
    first = await capture(first_body, key=key)
    assert (
        first["form"]["answers"] == {}
        and "source_refs" not in first["form"]
        and "recorded_at" not in first["form"]
    )
    assert first["capture_status"] == "DRAFT_UNVERIFIED"
    before = await f["effects"]()
    assert await create(path, first_body, "creator", key) == first
    assert await f["effects"]() == before

    if scenario == "concurrent_capture_replay":
        assert app.state.database.postgres
        data, key = body({"response": {"absent_reason": "not_assessed"}}), db.uid()
        before = await f["effects"]()
        replies = await asyncio.gather(
            post(path, data, "creator", key), post(path, data, "creator", key)
        )
        assert [response.status_code for response in replies] == [200, 200]
        assert replies[0].json()["resource"] == replies[1].json()["resource"]
        after = await f["effects"]()
        assert (
            after[0][4:] == [count + 1 for count in before[0][4:]]
            and after[0][:4] == before[0][:4]
            and after[1:] == before[1:]
        )
        return {
            "scenario": scenario,
            "result": "ONE_IMMUTABLE_CAPTURE_AND_RECEIPT_FOR_SIMULTANEOUS_REPLAY_NO_FINDING_TRANSITION",
        }

    if scenario == "capture_handover_and_scope":
        await f["new_actor"]("colleague", "FACILITY_ADMIN")
        await f["refused"](path, body(actor="colleague"), "colleague", 403)
        await f["new_actor"]("outsider", "CLINICAL_STAFF")
        denied = await client.get(
            "/v1" + path, headers={"Authorization": "Bearer " + actors["outsider"][1]}
        )
        assert denied.status_code == 404
        await f["new_actor"]("successor", "FACILITY_ADMIN")
        offered = await create(
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
            reason | {"expected_version": offered["version"], "assignment_kind": "RESPONDENT"},
            "successor",
        )
        await f["refused"](path, first_body, "creator", 403)
        replay = await post(path, first_body, "creator", key)
        assert replay.status_code == 403
        finding = await f["current"]()
        result = await capture(
            body({key: {"absent_reason": "unknown"} for key in REQUIRED}, "submitted", "successor"),
            "successor",
        )
        assert result["form"]["actor_id"] == actors["successor"][0]
        assert any(
            item["id"] == first["id"] and item["recorded_by"] == actors["creator"][0]
            for item in (await read("successor"))["items"]
        )
        return {
            "scenario": scenario,
            "result": "CURRENT_PERSONAL_AUTHORITY_AND_HANDOVER_RECHECKED_ORIGINAL_CAPTURE_AUTHOR_RETAINED",
        }

    if scenario == "capture_reference_and_history":
        await f["refused"](
            path, body({"finding_id": db.uid()}), "creator", 409, "CAPTURE_SCOPE_MISMATCH"
        )
        await f["refused"](path, body({"owner_team_id": actors["creator"][0]}), "creator", 404)
        await f["refused"](
            path,
            body({"evidence_refs": [j["proofs"]["SYN-B"]]}),
            "creator",
            409,
            "EVIDENCE_SCOPE_MISMATCH",
        )
        await f["refused"](
            path, body({"evidence_refs": [j["proofs"]["SYN-A"]] * 2}), "creator", 422
        )
        with clock_offset(20):
            await f["refused"](
                path,
                body({"evidence_refs": [j["proofs"]["SYN-A"]]}),
                "creator",
                409,
                "EVIDENCE_NOT_CURRENT",
            )
        result = await capture(
            body(
                {"evidence_refs": [], "response": {"absent_reason": "declined", "explanation": ""}}
            )
        )
        assert result["form"]["answers"] == {
            "evidence_refs": [],
            "response": {"absent_reason": "declined", "explanation": ""},
        }
        at = stamp()
        # Labelled volume rows exercise paging only, not claimed executed form submissions.
        async with app.state.database.transaction() as session:
            for _ in range(53):
                identifier = db.uid()
                data = {
                    **first,
                    "id": identifier,
                    "recorded_at": at,
                    "fixture": "PAGINATION_METADATA_NOT_EXECUTED_CAPTURES",
                }
                await session.execute(
                    t.journal.insert().values(
                        id=identifier,
                        resource_id=finding["id"],
                        facility_id=j["facility"]["id"],
                        action=ACTION,
                        actor_id=actors["creator"][0],
                        version=finding["version"],
                        recorded_at=at,
                        correlation_id=db.uid(),
                        payload_ciphertext=app.state.box.encrypt(canonical(data)),
                    )
                )
        page = await read()
        next_page = await read(before=page["next_before_id"])
        assert len(page["items"]) == 50 and len(next_page["items"]) == 5
        assert not {item["id"] for item in page["items"]} & {
            item["id"] for item in next_page["items"]
        }
        denied = await client.get(
            "/v1" + path + "?before_id=" + db.uid(),
            headers={"Authorization": "Bearer " + actors["creator"][1]},
        )
        assert denied.status_code == 404
        return {
            "scenario": scenario,
            "result": "EXPLICIT_EMPTY_AND_DECLINED_SCOPE_EXPIRY_DUPLICATION_AND_PRIVATE_PAGINATION_RETAINED",
        }

    for absence in REASONS:
        answers = {key: {"absent_reason": absence} for key in REQUIRED}
        result = await capture(body(answers, "submitted"))
        assert result["form"]["answers"] == answers
    await f["refused"](
        f["cp"] + "/recommend",
        reason | {"expected_version": case["version"], "action": "RENEW"},
        "reviewer",
        409,
    )
    assert (await f["current"]())["corrective_plan"] is None
    for slot in REQUIRED:
        answers = {key: {"absent_reason": "unknown"} for key in REQUIRED if key != slot}
        await f["refused"](path, body(answers, "submitted"), "creator", 422)
    for answers in [
        {"response": None},
        {"response": ""},
        {"response": {"absent_reason": "NIL"}},
        {"response": {"absent_reason": "unknown", "value": "claimed"}},
        {"due_at": 0},
        {"due_at": "2026-11-11T10:00:00"},
        {"unknown_field": "value"},
    ]:
        await f["refused"](path, body(answers), "creator", 422)
    for field in ["actor_id", "authority_node_id", "facility_or_unit_id"]:
        data = body()
        data["form"][field] = db.uid()
        await f["refused"](path, data, "creator", 409)
    await f["refused"](path, body() | {"expected_version": finding["version"] + 1}, "creator", 412)
    await f["refused"](
        path, body() | {"expected_case_version": case["version"] + 1}, "creator", 412
    )
    data = body()
    data["form"]["recorded_at"] = stamp(1)
    await f["refused"](path, data, "creator", 422)
    data["form"]["recorded_at"] = None
    await f["refused"](path, data, "creator", 422)
    # Actual consequential source work is separately proposed, accepted and reviewed.
    team = await create(
        "/institutional/delivery-teams",
        reason
        | {
            "facility_id": j["facility"]["id"],
            "name": "Synthetic capture delivery team",
            "purpose": "Isolated source evidence only",
            "authority_reference": "SYNTHETIC_CAPTURE_NOT_ADOPTION",
            "lead_account_id": actors["creator"][0],
        },
    )
    team = await create(
        "/institutional/delivery-teams/" + team["id"] + "/accept",
        reason | {"expected_version": team["version"]},
    )
    plan = await create(
        f["path"] + "/corrective-plan",
        f["proposal"](finding["version"])
        | {"owner_team_id": team["id"], "owner_team_version": team["version"]},
    )
    agreed = await create(f["path"] + "/corrective-plan-review", f["review_plan"](plan), "reviewer")
    finding = await f["current"]()
    invalid = {key: {"absent_reason": "unknown"} for key in REQUIRED} | {
        "required_action": "Not the actual agreed action"
    }
    await f["refused"](path, body(invalid, "submitted"), "creator", 409, "CAPTURE_SOURCE_MISMATCH")
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
    finding = await f["current"]()
    known = (await read("reviewer"))["recorded_source_values"]
    assert set(known) == {
        "finding_id",
        "required_action",
        "owner_team_id",
        "due_at",
        "response",
        "evidence_refs",
        "review_result",
    }
    await f["refused"](
        path, body(known, "submitted"), "creator", 409, "INDEPENDENT_REVIEW_REQUIRED"
    )
    checked = await capture(body(known, "submitted", "reviewer"), "reviewer")
    assert (
        checked["capture_status"] == "SUBMITTED_SOURCE_CHECKED"
        and checked["source_binding"]["review_actor_id"] == actors["reviewer"][0]
    )
    recommended = await create(
        f["cp"] + "/recommend",
        reason | {"expected_version": case["version"], "action": "RENEW"},
        "reviewer",
    )
    case = await create(
        f["cp"] + "/decide",
        reason
        | {
            "expected_version": recommended["version"],
            "action": "RENEW",
            "scope": "Synthetic capture proof only",
            "conditions": "",
            "expires_at": stamp(8),
        },
        "decider",
    )
    case = {"version": (await read())["context"]["case_version"]}
    await f["refused"](path, body(), "creator", 409, "INVALID_STATE")
    assert await create(path, first_body, "creator", key) == first
    return {
        "scenario": scenario,
        "result": "CANONICAL_ABSENCES_OMISSIONS_AND_CHECKED_SOURCE_CAPTURE_NEVER_REPLACE_ACTUAL_TEAM_PLAN_RESPONSE_REVIEW_DECISION",
    }


@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_corrective_capture_guards(tmp_path, scenario):
    if scenario == "concurrent_capture_replay":
        pytest.skip("Real PostgreSQL capture replay race runs in isolated Neon")
    cfg = PlatformSettings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'capture.db').as_posix()}",
        data_key_hex="08" * 32,
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
