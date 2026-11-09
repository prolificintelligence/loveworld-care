"""Synthetic scale/isolation regressions for the November readiness closure."""

import base64
import json

import pytest
from lw_care_api.platform import db
from lw_care_api.platform.clinical import flow_index as fi
from lw_care_api.platform.clinical import tables as ct
from lw_care_api.platform.reporting import tables as rt
from sqlalchemy import select, update
from test_platform_clinical import Journey
from test_platform_clinical import journey as clinical_fixture
from test_platform_reporting import action, category, duty, run, safety, stamp
from test_platform_reporting import journey as reporting_fixture


@pytest.fixture
def reporting(tmp_path):
    yield from reporting_fixture.__wrapped__(tmp_path)


@pytest.fixture
def care(tmp_path):
    yield from clinical_fixture.__wrapped__(tmp_path)


def collect(journey, path, actor):
    ids, pages = [], 0
    response = journey.get(path, actor)
    while True:
        assert response.status_code == 200, response.text
        data = response.json()
        ids.extend(row["id"] for row in data["items"])
        pages += 1
        assert pages < 20
        if not data["next_cursor"]:
            return ids
        response = journey.get(path + "?after=" + data["next_cursor"], actor)


def test_case_and_action_pages_filter_before_limits_and_recheck_revocation(reporting):
    j = reporting
    duty(j)
    sample = safety(j, category(j))
    improvement = action(j)
    case_ids, action_ids = [], []

    async def seed():
        async with j.app.state.database.transaction() as session:
            case = dict(
                (await session.execute(select(rt.cases).where(rt.cases.c.id == sample["id"])))
                .mappings()
                .one()
            )
            act = dict(
                (
                    await session.execute(
                        select(rt.actions).where(rt.actions.c.id == improvement["id"])
                    )
                )
                .mappings()
                .one()
            )
            cases, actions = [], []
            for number in range(430):
                # Ineligible earlier work previously exhausted the entire SQL limit.
                eligible = number >= 215
                case_id, action_id = db.uid(), db.uid()
                cases.append(
                    case
                    | {
                        "id": case_id,
                        "created_by": j.actors["safety_reporter" if eligible else "safety_backup"][
                            0
                        ],
                        "acknowledge_by": stamp(-1) if not eligible else sample["acknowledge_by"],
                    }
                )
                actions.append(
                    act
                    | {
                        "id": action_id,
                        "protected": not eligible,
                        "due_at": stamp(-1) if not eligible else improvement["due_at"],
                    }
                )
                if eligible:
                    case_ids.append(case_id)
                    action_ids.append(action_id)
            await session.execute(rt.cases.insert(), cases)
            await session.execute(rt.actions.insert(), actions)

    run(seed())
    cases = collect(j, "/safety-cases", "safety_reporter")
    actions = collect(j, "/actions", "owner")
    assert len(cases) == len(set(cases)) == 216
    assert set(cases) == set(case_ids + [sample["id"]])
    assert len(actions) == len(set(actions)) == 216
    assert set(actions) == set(action_ids + [improvement["id"]])
    cursor = j.get("/safety-cases", "safety_reporter").json()["next_cursor"]

    async def revoke():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                update(db.grants)
                .where(db.grants.c.account_id == j.actors["safety_reporter"][0])
                .values(revoked=True)
            )

    run(revoke())
    assert j.get("/safety-cases?after=" + cursor, "safety_reporter").json()["items"] == []
    assert j.get("/safety-cases?after=not-a-cursor", "safety_backup").status_code == 422
    bad = base64.urlsafe_b64encode(json.dumps([[], "x"]).encode()).decode()
    assert j.get("/actions?after=" + bad, "owner").status_code == 422


def test_recipient_pages_deduplicate_and_search_beyond_thousand_grants(reporting):
    j = reporting
    expected = []

    async def seed():
        async with j.app.state.database.transaction() as session:
            accounts, grants = [], []
            for number in range(240):
                identifier = db.uid()
                expected.append(identifier)
                accounts.append(
                    {
                        "id": identifier,
                        "name": f"Scale recipient {number:04}",
                        "email": f"scale{number}@synthetic.invalid",
                        "active": True,
                        "totp_last_step": -1,
                        "created_at": db.now(),
                    }
                )
                for _ in range(5):
                    grants.append(
                        {
                            "id": db.uid(),
                            "account_id": identifier,
                            "role": "FACILITY_ADMIN",
                            "scope_type": "FACILITY",
                            "scope_id": j.facilities[0],
                            "valid_from": stamp(-1),
                            "valid_until": stamp(2),
                            "revoked": False,
                            "grantor": "SYNTHETIC_FIXTURE",
                        }
                    )
            await session.execute(db.accounts.insert(), accounts)
            await session.execute(db.grants.insert(), grants)

    run(seed())
    people = collect(j, "/people", "owner")
    assert set(expected).issubset(people)
    assert len(people) == len(set(people))
    assert j.actors["outsider"][0] not in people
    response = j.get("/people?query=Scale%20recipient%200239", "owner").json()
    assert [r["id"] for r in response["items"]] == [expected[-1]]
    assert response["items"][0]["roles"] == ["FACILITY_ADMIN"]
    assert j.get("/people?query=%25", "owner").json()["items"] == []


def test_projection_corruption_is_contained_but_global_assurance_stays_red(care):
    j = care
    patient, _ = j.encounter()
    other_id = db.uid()

    async def second_facility():
        async with j.app.state.database.transaction() as session:
            for table, column, replacements in [
                (
                    db.facilities,
                    db.facilities.c.id,
                    {"id": other_id, "external_reference": other_id},
                ),
                (ct.sites, ct.sites.c.facility_id, {"id": db.uid(), "facility_id": other_id}),
            ]:
                row = dict(
                    (await session.execute(select(table).where(column == j.facility)))
                    .mappings()
                    .one()
                )
                await session.execute(table.insert().values(row | replacements))
            for table, column in [
                (db.grants, db.grants.c.scope_id),
                (ct.privileges, ct.privileges.c.facility_id),
            ]:
                rows = list(
                    (await session.execute(select(table).where(column == j.facility))).mappings()
                )
                for row in rows:
                    await session.execute(
                        table.insert().values(dict(row) | {"id": db.uid(), column.name: other_id})
                    )

    run(second_facility())
    other = Journey(j.app, j.client, other_id, j.actors)
    other_patient, _ = other.encounter()

    async def exercise():
        async with j.app.state.database.transaction() as session:
            source = (
                (await session.execute(select(ct.records).where(ct.records.c.id == patient["id"])))
                .mappings()
                .one()
            )
            local = source["facility_id"]
            unrelated = db.uid()
            await session.execute(
                update(fi.index)
                .where(fi.index.c.record_id == patient["id"])
                .values(indexed_version=0)
            )
            assert not await fi.ready(session)
            assert not await fi.ready(session, local)
            assert await fi.ready(session, unrelated)
            assert await fi.ready(session, other_id)
            # A wrongly assigned projection must block BOTH affected facilities.
            await session.execute(
                update(fi.index)
                .where(fi.index.c.record_id == patient["id"])
                .values(facility_id=unrelated, indexed_version=source["version"])
            )
            assert not await fi.ready(session, unrelated)
            assert not await fi.ready(session, local)

    run(exercise())
    assert j.get("/worklist?kind=encounter").status_code == 503
    assert other.get("/worklist?kind=encounter").status_code == 200
    # Unrelated facility reads remain available while global assurance stays red.
    assert other.get(f"/patients/{other_patient['id']}/chart").status_code == 200
    run(fi.rebuild(j.app.state.database, j.app.state.box, j.app.state.settings))
    assert j.get("/worklist?kind=encounter").status_code == 200


def test_staff_search_and_pages_include_late_recipients_without_duplicates(care):
    j = care
    expected = []

    async def seed():
        async with j.app.state.database.transaction() as session:
            template = dict(
                (
                    await session.execute(
                        select(ct.privileges).where(
                            ct.privileges.c.account_id == j.actors["clinician"][0]
                        )
                    )
                )
                .mappings()
                .first()
            )
            accounts, privileges = [], []
            for number in range(220):
                identifier = db.uid()
                expected.append(identifier)
                accounts.append(
                    {
                        "id": identifier,
                        "name": f"Scale staff {number:04}",
                        "email": f"staff{number}@synthetic.invalid",
                        "active": True,
                        "totp_last_step": -1,
                        "created_at": db.now(),
                    }
                )
                for _ in range(2):
                    privileges.append(template | {"id": db.uid(), "account_id": identifier})
            await session.execute(db.accounts.insert(), accounts)
            await session.execute(ct.privileges.insert(), privileges)

    run(seed())
    people = collect(j, "/staff", "clinician")
    assert set(expected).issubset(people)
    assert len(people) == len(set(people))
    assert j.get("/staff?query=Scale%20staff%200219").json()["items"][0]["id"] == expected[-1]


def test_auth_observations_exclude_identity_secrets_and_query_strings(reporting, capsys):
    response = reporting.client.get("/v1/auth/me?password=DO_NOT_LOG_PRIVATE")
    assert response.status_code == 401
    lines = capsys.readouterr().out.splitlines()
    observations = [
        json.loads(line) for line in lines if '"event": "authentication_request"' in line
    ]
    assert observations
    observation = observations[-1]
    assert set(observation) == {"event", "route", "status", "elapsed_ms", "correlation_id"}
    assert observation["route"] == "/v1/auth/me"
    assert observation["status"] == 401
    assert observation["elapsed_ms"] >= 0
    assert observation["correlation_id"] == response.headers["x-request-id"]
    assert "DO_NOT_LOG_PRIVATE" not in json.dumps(observations)


def test_quality_exceptions_and_retained_history_have_complete_continuation(reporting):
    j = reporting
    definition = j.definition()
    obligation = j.obligation([definition])
    draft = j.draft(obligation, definition)

    async def seed():
        async with j.app.state.database.transaction() as session:
            original = dict(
                (await session.execute(select(rt.returns).where(rt.returns.c.id == draft["id"])))
                .mappings()
                .one()
            )
            version = dict(
                (
                    await session.execute(
                        select(rt.versions).where(rt.versions.c.return_id == draft["id"])
                    )
                )
                .mappings()
                .one()
            )
            # Separate synthetic obligations preserve unique return/obligation keys.
            source = dict(
                (
                    await session.execute(
                        select(rt.obligations).where(rt.obligations.c.id == obligation["id"])
                    )
                )
                .mappings()
                .one()
            )
            obligations, returns, versions, exceptions = [], [], [], []
            for number in range(205):
                oid, rid = db.uid(), db.uid()
                obligations.append(
                    source
                    | {
                        "id": oid,
                        "period_start": stamp(-400 - number),
                        "period_end": stamp(-399 - number),
                    }
                )
                returns.append(original | {"id": rid, "obligation_id": oid})
                # Encryption is retained with its original content; this test exercises
                # version-page traversal, not source correction or fabricated sign-off.
                versions.append(version | {"id": db.uid(), "version": number + 2})
                exceptions.append(
                    {
                        "id": db.uid(),
                        "scope_type": "FACILITY",
                        "scope_id": j.facilities[0],
                        "facility_id": j.facilities[0],
                        "region_id": source["region_id"],
                        "zone_id": source["zone_id"],
                        "hierarchy_snapshot": source["hierarchy_snapshot"],
                        "resource_type": "RETURN",
                        "resource_id": rid,
                        "exception_type": "OVERDUE",
                        "owner_id": j.actors["reporter"][0],
                        "due_at": original["updated_at"],
                        "created_at": db.now(),
                    }
                )
            await session.execute(rt.obligations.insert(), obligations)
            await session.execute(rt.returns.insert(), returns)
            await session.execute(rt.versions.insert(), versions)
            await session.execute(rt.escalations.insert(), exceptions)

    run(seed())
    for path, count in [
        ("/quality", 206),
        ("/exceptions", 205),
        (f"/returns/{draft['id']}/history", 206),
    ]:
        identifiers = collect(j, path, "reporter")
        assert len(identifiers) == len(set(identifiers)) == count
