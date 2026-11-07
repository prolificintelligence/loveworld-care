"""Actual persistent reporting journeys; no provider success mocks or production fixtures."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from lw_care_api.platform import db
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.main import create_platform_app
from lw_care_api.platform.reporting import tables as t
from lw_care_api.platform.security import issue_session
from sqlalchemy import select, update

ORIGIN = "http://localhost:3004"


def run(value):
    return asyncio.run(value)


def stamp(days=0):
    return (datetime.now(UTC) + timedelta(days=days)).isoformat(timespec="microseconds")


class ReportingJourney:
    def __init__(self, app, client, actors, facilities):
        self.app, self.client, self.actors, self.facilities = app, client, actors, facilities
        self.start, self.end, self.due = stamp(-3), stamp(-2), stamp(1)

    def post(self, path, body, actor="reporter", key=None):
        return self.client.post(
            "/v1/reporting" + path,
            json=body,
            headers={
                "Authorization": "Bearer " + self.actors[actor][1],
                "Origin": ORIGIN,
                "Idempotency-Key": key or db.uid(),
            },
        )

    def create(self, path, body, actor="reporter", key=None):
        response = self.post(path, body, actor, key)
        assert response.status_code == 200, (path, response.text)
        return response.json()["resource"]

    def get(self, path, actor="reporter"):
        return self.client.get(
            "/v1/reporting" + path, headers={"Authorization": "Bearer " + self.actors[actor][1]}
        )

    def definition(self, **changes):
        return self.create(
            "/definitions",
            {
                "metric_id": "LWH-MET-010",
                "definition_version": db.uid(),
                "name": "Synthetic service contacts",
                "stream": "FACILITY_ACTIVITY",
                "formula": "COUNT",
                "unit": "contacts",
                "aggregation": "SUM",
                "scale": "1",
                "source_selector": "MANUAL",
                "numerator_definition": "Synthetic completed encounter count",
                "denominator_definition": "Not applicable to this synthetic count",
                "population_definition": "Synthetic facility-period",
                "inclusion_exclusion": "Synthetic adopted inclusion rules",
                "dimensions": ["facility"],
                "adoption_reference": "SYNTHETIC TEST AUTHORITY ONLY",
                "template_reconciliation": "Synthetic complete source mapping",
                "valid_from": stamp(-30),
                "valid_until": stamp(30),
                "intent_confirmed": True,
                **changes,
            },
            "governor",
        )

    def obligation(self, definitions, facility=0):
        return self.create(
            "/obligations",
            {
                "scope_type": "FACILITY",
                "scope_id": self.facilities[facility],
                "stream": "FACILITY_ACTIVITY",
                "period_start": self.start,
                "period_end": self.end,
                "due_at": self.due,
                "timezone": "Africa/Lagos",
                "definition_ids": [row["id"] for row in definitions],
                "adoption_reference": "Synthetic calendar and expected-unit authority",
            },
            "governor",
        )

    def draft(self, obligation, definition, count="10", **changes):
        return self.create(
            f"/obligations/{obligation['id']}/draft",
            {
                "expected_version": 0,
                "values": [
                    {
                        "definition_id": definition["id"],
                        "completeness": "NIL" if count == "0" else "VALUE",
                        "value": count,
                        "source_reference": "Synthetic actual source evidence",
                    }
                ],
                "source_method": "Synthetic actual preparation",
                "reconciliation": "Single declared source; no feed addition",
                "reason": "Synthetic initial preparation",
                **changes,
            },
        )

    def verified(self, obligation, definition, count="10"):
        row = self.draft(obligation, definition, count)
        row = self.create(
            f"/returns/{row['id']}/submit",
            {
                "expected_version": row["version"],
                "reason": "Synthetic actual attestation",
                "intent_confirmed": True,
            },
        )
        return self.create(
            f"/returns/{row['id']}/review",
            {
                "expected_version": row["version"],
                "reason": "Synthetic independent verification",
                "intent_confirmed": True,
                "decision": "VERIFY",
                "evidence_examined": "Synthetic source examined",
                "method": "Synthetic source reconciliation",
                "verification_scope": "Exact synthetic declared counts",
                "warning_overrides": {},
            },
            "reviewer",
        )

    def policy(self, **changes):
        return self.create(
            "/policies",
            {
                "name": "Synthetic disclosure policy " + db.uid(),
                "policy_version": "TEST-1",
                "purpose": "STRATEGIC_LEADERSHIP",
                "allowed_metric_ids": ["LWH-MET-010"],
                "minimum_units": 2,
                "minimum_cell": 5,
                "minimum_change": 5,
                "allow_partial": False,
                "adoption_reference": "Synthetic policy authority",
                "risk_assessment": "Synthetic reviewed cell, cohort and differencing controls; no anonymity certification",
                "valid_from": stamp(-1),
                "valid_until": stamp(10),
                "intent_confirmed": True,
                **changes,
            },
            "governor",
        )

    def cohort(self, obligations, policy):
        return self.create(
            "/cohorts",
            {
                "scope_type": "GLOBAL",
                "name": "Synthetic aligned cohort",
                "obligation_ids": [row["id"] for row in obligations],
                "policy_id": policy["id"],
            },
            "analyst",
        )

    def released(self, cohort):
        row = self.create("/snapshots", {"cohort_id": cohort["id"]}, "analyst")
        self.create(
            f"/snapshots/{row['id']}/review",
            {
                "decision": "RELEASE",
                "reason": "Synthetic independent disclosure and source review",
                "intent_confirmed": True,
            },
            "reviewer",
        )
        response = self.get(f"/snapshots/{row['id']}", "executive")
        assert response.status_code == 200, response.text
        return response.json()


@pytest.fixture
def journey(tmp_path):
    cfg = PlatformSettings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'reporting.db').as_posix()}",
        data_key_hex="c3" * 32,
        web_origin=ORIGIN,
        authority_node_id=db.uid(),
    )
    app = create_platform_app(cfg)
    run(app.state.database.migrate())
    region, zone, operator = db.uid(), db.uid(), db.uid()
    facilities = [db.uid() for _ in range(3)]
    roles = {
        "admin": "PLATFORM_ADMIN",
        "governor": "DATA_GOVERNOR",
        "reporter": "REPORTING_OFFICER",
        "reviewer": "DATA_REVIEWER",
        "analyst": "DATA_ANALYST",
        "executive": "EXECUTIVE_VIEWER",
        "programme": "PROGRAMME_OWNER",
        "owner": "FACILITY_ADMIN",
        "fallback": "FACILITY_ADMIN",
        "action_reviewer": "PROGRAMME_OWNER",
        "safety_reporter": "SAFETY_REPORTER",
        "safety_reviewer": "SAFETY_REVIEWER",
        "safety_backup": "SAFETY_REVIEWER",
        "outsider": "REPORTING_OFFICER",
    }
    actors = {}

    async def seed():
        async with app.state.database.transaction() as session:
            for name, role in roles.items():
                identifier = db.uid()
                await session.execute(
                    db.accounts.insert().values(
                        id=identifier,
                        email=f"{name}@synthetic.invalid",
                        name="Synthetic " + name,
                        active=True,
                        totp_last_step=-1,
                        created_at=db.now(),
                    )
                )
                local = name in {"owner", "fallback", "outsider"}
                await session.execute(
                    db.grants.insert().values(
                        id=db.uid(),
                        account_id=identifier,
                        role=role,
                        scope_type="FACILITY" if local else "GLOBAL",
                        scope_id=facilities[2]
                        if name == "outsider"
                        else facilities[0]
                        if local
                        else "GLOBAL",
                        valid_from=stamp(-10),
                        valid_until=stamp(20),
                        revoked=False,
                        grantor="SYNTHETIC_FIXTURE",
                    )
                )
                actors[name] = (identifier, await issue_session(session, identifier, 30))
            await session.execute(
                db.units.insert().values(
                    id=region, name="Synthetic region", kind="REGION", code=region, version=1
                )
            )
            await session.execute(
                db.units.insert().values(
                    id=zone,
                    name="Synthetic zone",
                    kind="ZONE",
                    code=zone,
                    parent_id=region,
                    version=1,
                )
            )
            await session.execute(
                db.operators.insert().values(
                    id=operator, name="Synthetic operator", external_reference=operator
                )
            )
            for number, identifier in enumerate(facilities):
                await session.execute(
                    db.facilities.insert().values(
                        id=identifier,
                        operator_id=operator,
                        zone_id=zone,
                        name=f"Synthetic facility {number}",
                        site_type="COMMUNITY_PRIMARY",
                        ownership="MEMBER_OWNED",
                        jurisdiction="TEST-ONLY",
                        external_reference=identifier,
                        address="Synthetic",
                        public_contact="public@synthetic.invalid",
                        private_contact="private@synthetic.invalid",
                        services=["TEST"],
                        identity_status="VERIFIED",
                        statutory_status="CHECKED",
                        created_by=actors["admin"][0],
                        created_at=db.now(),
                        updated_at=db.now(),
                        version=1,
                    )
                )

    run(seed())
    with TestClient(app) as client:
        yield ReportingJourney(app, client, actors, facilities)


def test_admin_seniority_is_not_reporting_or_case_authority(journey):
    j = journey
    assert j.get("/context", "admin").json()["roles"] == []
    assert j.get("/audit", "admin").status_code == 404
    assert j.get("/definitions", "admin").status_code == 403
    assert j.client.get("/v1/reporting/context").status_code == 401


def test_nil_missing_unverified_and_released_totals_stay_distinct(journey):
    j = journey
    definition = j.definition()
    first, second = j.obligation([definition]), j.obligation([definition], 1)
    nil = j.verified(first, definition, "0")
    assert nil["state"] == "VERIFIED"
    obligations = j.get("/obligations").json()["items"]
    assert (
        next(row for row in obligations if row["id"] == second["id"])["receipt_state"] == "MISSING"
    )
    policy = j.policy(allow_partial=True)
    cohort = j.cohort([first, second], policy)
    released = j.released(cohort)
    assert released["coverage"]["verified"] == 1 and released["coverage"]["missing"] == 1
    assert released["cells"][0]["value"] is None and released["cells"][0][
        "disclosure_status"
    ].startswith("SUPPRESSED")


def test_verified_snapshot_reconciles_and_correction_invalidates_history(journey):
    j = journey
    definition = j.definition()
    obligations = [j.obligation([definition], number) for number in (0, 1)]
    sources = [
        j.verified(obligation, definition, count)
        for obligation, count in zip(obligations, ("10", "20"), strict=True)
    ]
    cohort = j.cohort(obligations, j.policy())
    released = j.released(cohort)
    assert released["cells"][0]["value"] == "30" and released["current_eligible"] is True
    old_hash = released["source_hash"]
    correction = j.create(
        f"/returns/{sources[0]['id']}/correction",
        {"expected_version": sources[0]["version"], "reason": "Synthetic late source correction"},
    )
    assert released["snapshot_id"] in correction["invalidated_snapshot_ids"]
    historical = j.get(f"/snapshots/{released['snapshot_id']}", "executive").json()
    assert (
        historical["current_eligible"] is False
        and historical["source_hash"] == old_hash
        and historical["cells"][0]["value"] == "30"
    )
    assert len(j.get(f"/returns/{sources[0]['id']}/history").json()["items"]) == 4


def test_wrong_scope_and_cached_receipt_after_revocation_are_denied(journey):
    j = journey
    definition = j.definition()
    obligation = j.obligation([definition])
    key = db.uid()
    body = {
        "expected_version": 0,
        "values": [
            {
                "definition_id": definition["id"],
                "completeness": "NIL",
                "value": "0",
                "source_reference": "Actual synthetic source",
            }
        ],
        "source_method": "Synthetic",
        "reconciliation": "Synthetic",
        "reason": "Synthetic",
    }
    response = j.post(f"/obligations/{obligation['id']}/draft", body, key=key)
    assert response.status_code == 200
    assert j.post(f"/obligations/{obligation['id']}/draft", body, "outsider").status_code == 404
    assert j.get(f"/returns/{response.json()['resource']['id']}", "outsider").status_code == 404

    async def revoke():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                update(db.grants)
                .where(db.grants.c.account_id == j.actors["reporter"][0])
                .values(revoked=True)
            )

    run(revoke())
    assert j.post(f"/obligations/{obligation['id']}/draft", body, key=key).status_code == 404


def test_count_validation_blocks_fractional_values_and_self_verification(journey):
    j = journey
    definition = j.definition()
    obligation = j.obligation([definition])
    row = j.draft(obligation, definition, "1.5")
    assert any(finding["code"] == "COUNT_NOT_INTEGER" for finding in row["validation"]["findings"])
    assert (
        j.post(
            f"/returns/{row['id']}/submit",
            {
                "expected_version": row["version"],
                "reason": "Synthetic invalid attestation",
                "intent_confirmed": True,
            },
        ).status_code
        == 409
    )


def grant(j, name, role, scope_type="GLOBAL", scope_id="GLOBAL"):
    async def apply():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                db.grants.insert().values(
                    id=db.uid(),
                    account_id=j.actors[name][0],
                    role=role,
                    scope_type=scope_type,
                    scope_id=scope_id,
                    valid_from=stamp(-1),
                    valid_until=stamp(10),
                    revoked=False,
                    grantor="SYNTHETIC_FIXTURE",
                )
            )

    run(apply())


def category(j, **changes):
    return j.create(
        "/categories",
        {
            "name": "Synthetic safety classification",
            "category_version": "TEST-1",
            "definition": "Synthetic event scope and exclusions",
            "acknowledgement_minutes": 60,
            "escalation_owner_id": j.actors["safety_backup"][0],
            "external_reporting_obligations": "Synthetic review only; no local law asserted",
            "external_receipt_required": False,
            "adoption_reference": "Synthetic category authority",
            "valid_from": stamp(-1),
            "valid_until": stamp(10),
            "intent_confirmed": True,
            **changes,
        },
        "governor",
    )


def duty(j, name="safety_reviewer"):
    row = j.create(
        "/duty-windows",
        {
            "scope_type": "GLOBAL",
            "account_id": j.actors[name][0],
            "valid_from": stamp(-1),
            "valid_until": stamp(1),
            "evidence": "Synthetic roster authority",
        },
        "governor",
    )
    j.create(
        f"/duty-windows/{row['id']}/accept",
        {"evidence": "Synthetic personally accepted duty"},
        name,
    )
    return row


def safety(j, cat):
    return j.create(
        "/safety-cases",
        {
            "scope_type": "FACILITY",
            "scope_id": j.facilities[0],
            "category_id": cat["id"],
            "occurred_at": stamp(-0.1),
            "source": "Synthetic reporter observation",
            "location_precision": "Synthetic local service",
            "description": "SYNTHETIC_PRIVATE_CASE_TEXT",
            "urgent": True,
            "immediate_local_action": "Synthetic established local emergency route used",
        },
        "safety_reporter",
    )


def case_event(j, row, event, actor="safety_reviewer", **changes):
    return j.create(
        f"/safety-cases/{row['id']}/actions",
        {
            "expected_version": row["version"],
            "action": event,
            "reason": "Synthetic attributed review",
            "evidence": "Synthetic evidence examined",
            "occurred_at": stamp(),
            **changes,
        },
        actor,
    )


def action(j, **changes):
    return j.create(
        "/actions",
        {
            "scope_type": "FACILITY",
            "scope_id": j.facilities[0],
            "title": "Synthetic accountable improvement",
            "intended_result": "Synthetic intended observable change",
            "source_type": "JUSTIFIED_REQUEST",
            "justification": "Synthetic actual service request",
            "owner_id": j.actors["owner"][0],
            "fallback_id": j.actors["fallback"][0],
            "reviewer_id": j.actors["action_reviewer"][0],
            "due_at": stamp(2),
            "review_at": stamp(3),
            "resources": "Synthetic actual requirements",
            "resource_state": "NOT_REQUIRED",
            "budget_authority": "Not applicable to this synthetic action",
            "dependencies": "Synthetic declared dependencies",
            **changes,
        },
        "programme",
    )


def progress(j, row, event, actor="owner", **changes):
    return j.create(
        f"/actions/{row['id']}/progress",
        {
            "expected_version": row["version"],
            "action": event,
            "reason": "Synthetic actual action event",
            "evidence": "Synthetic observed evidence",
            **changes,
        },
        actor,
    )


def test_independent_review_is_required_even_with_both_roles(journey):
    j = journey
    definition = j.definition()
    obligation = j.obligation([definition])
    row = j.draft(obligation, definition)
    row = j.create(
        f"/returns/{row['id']}/submit",
        {
            "expected_version": row["version"],
            "reason": "Actual synthetic attestation",
            "intent_confirmed": True,
        },
    )
    grant(j, "reporter", "DATA_REVIEWER")
    body = {
        "expected_version": row["version"],
        "reason": "Synthetic own review",
        "intent_confirmed": True,
        "decision": "VERIFY",
        "evidence_examined": "Synthetic source",
        "method": "Synthetic method",
        "verification_scope": "Synthetic exact scope",
        "warning_overrides": {},
    }
    assert j.post(f"/returns/{row['id']}/review", body).status_code == 403
    assert j.get(f"/returns/{row['id']}").json()["state"] == "SUBMITTED"


def test_controlled_import_conserves_all_rows_and_blocks_extra_columns(journey):
    import csv
    import io

    j = journey
    definition = j.definition()
    obligation = j.obligation([definition])
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "metric_id",
            "definition_version",
            "completeness",
            "value",
            "numerator",
            "denominator",
            "source_reference",
            "explanation",
        ]
    )
    valid = [
        "LWH-MET-010",
        definition["definition_version"],
        "VALUE",
        "10",
        "",
        "",
        "Synthetic source",
        "",
    ]
    writer.writerow(valid + ["unexpected"])
    writer.writerow(valid)
    writer.writerow(valid)
    writer.writerow(["UNKNOWN", "x", "VALUE", "1", "", "", "source", ""])
    batch = j.create(
        f"/obligations/{obligation['id']}/imports",
        {
            "expected_version": 0,
            "csv_text": output.getvalue(),
            "source_method": "Actual synthetic source",
            "reconciliation": "Single synthetic authority",
        },
    )
    assert batch["counts"] == {"input": 4, "accepted": 1, "blocked": 2, "duplicate": 1}
    assert batch["outcomes"][0]["code"] == "ROW_COLUMN_COUNT_MISMATCH"
    assert (
        batch["return"]["state"] == "DRAFT"
        and batch["return"]["data"]["values"][0]["value"] == "10"
    )
    assert j.get(f"/imports/{batch['id']}", "executive").status_code == 404


def test_new_receipt_invalidates_snapshot_that_previously_counted_missing(journey):
    j = journey
    definition = j.definition()
    obligations = [j.obligation([definition], i) for i in (0, 1)]
    j.verified(obligations[0], definition)
    snapshot = j.released(j.cohort(obligations, j.policy(allow_partial=True)))
    j.draft(obligations[1], definition)
    assert (
        j.get(f"/snapshots/{snapshot['snapshot_id']}", "executive").json()["current_eligible"]
        is False
    )


def test_snapshot_release_rechecks_sources_and_denies_creator(journey):
    j = journey
    definition = j.definition()
    obligations = [j.obligation([definition], i) for i in (0, 1)]
    sources = [j.verified(item, definition) for item in obligations]
    cohort = j.cohort(obligations, j.policy())
    row = j.create("/snapshots", {"cohort_id": cohort["id"]}, "analyst")
    grant(j, "analyst", "DATA_REVIEWER")
    body = {"decision": "RELEASE", "reason": "Synthetic actual review", "intent_confirmed": True}
    assert j.post(f"/snapshots/{row['id']}/review", body, "analyst").status_code == 403
    j.create(
        f"/returns/{sources[0]['id']}/correction",
        {"expected_version": 3, "reason": "Synthetic revised source"},
    )
    assert j.post(f"/snapshots/{row['id']}/review", body, "reviewer").status_code == 409
    assert j.get(f"/snapshots/{row['id']}", "executive").status_code == 404


def test_small_cells_and_exports_share_policy_and_revocation(journey):
    j = journey
    definition = j.definition(unit="=SYNTHETIC_FORMULA")
    obligations = [j.obligation([definition], i) for i in (0, 1)]
    for item in obligations:
        j.verified(item, definition, "1")
    policy = j.policy()
    snapshot = j.released(j.cohort(obligations, policy))
    identifier = snapshot["snapshot_id"]
    assert (
        snapshot["cells"][0]["value"] is None
        and snapshot["cells"][0]["disclosure_status"] == "SUPPRESSED_SMALL_CELL"
    )
    export = j.get(f"/snapshots/{identifier}/export.csv", "executive")
    assert (
        export.status_code == 200
        and "'=SYNTHETIC_FORMULA" in export.text
        and "SUPPRESSED_SMALL_CELL" in export.text
    )
    j.create(
        f"/policies/{policy['id']}/revoke",
        {"evidence": "Synthetic adoption authority withdrawn"},
        "governor",
    )
    assert j.get(f"/snapshots/{identifier}", "executive").status_code == 403
    assert j.get(f"/snapshots/{identifier}/export.csv", "executive").status_code == 403


def test_correction_small_difference_is_withheld_in_successor_release(journey):
    j = journey
    definition = j.definition()
    obligations = [j.obligation([definition], i) for i in (0, 1)]
    first = j.verified(obligations[0], definition, "10")
    j.verified(obligations[1], definition, "20")
    cohort = j.cohort(obligations, j.policy())
    assert j.released(cohort)["cells"][0]["value"] == "30"
    row = j.create(
        f"/returns/{first['id']}/correction",
        {"expected_version": 3, "reason": "Synthetic corrected event"},
    )
    row = j.draft(obligations[0], definition, "11", expected_version=row["version"])
    row = j.create(
        f"/returns/{row['id']}/submit",
        {
            "expected_version": row["version"],
            "reason": "Synthetic reattestation",
            "intent_confirmed": True,
        },
    )
    j.create(
        f"/returns/{row['id']}/review",
        {
            "expected_version": row["version"],
            "reason": "Synthetic independent corrected review",
            "intent_confirmed": True,
            "decision": "VERIFY",
            "evidence_examined": "Synthetic corrected source",
            "method": "Reconciliation",
            "verification_scope": "Synthetic exact period",
            "warning_overrides": {},
        },
        "reviewer",
    )
    successor = j.released(cohort)
    assert (
        successor["cells"][0]["value"] is None
        and successor["cells"][0]["disclosure_status"] == "SUPPRESSED_DIFFERENCING"
    )


def test_case_without_accepted_coverage_stays_unassigned_and_private(journey):
    j = journey
    cat = category(j)
    row = safety(j, cat)
    assert (
        row["state"] == "SIGNAL"
        and row["reviewer_id"] is None
        and row["ownership_exception"] == "UNASSIGNED"
    )
    assert j.get(f"/safety-cases/{row['id']}", "safety_reviewer").status_code == 404
    for actor in ("admin", "executive", "governor", "outsider"):
        assert j.get(f"/safety-cases/{row['id']}", actor).status_code == 404
        assert "SYNTHETIC_PRIVATE_CASE_TEXT" not in j.get("/safety-cases", actor).text
    exception = j.get("/exceptions", "safety_backup").json()["items"][0]
    assert (
        j.post(
            f"/exceptions/{exception['id']}/acknowledge",
            {"evidence": "Synthetic received escalation"},
            "safety_reviewer",
        ).status_code
        == 403
    )
    receipt = j.create(
        f"/exceptions/{exception['id']}/acknowledge",
        {"evidence": "Synthetic received escalation"},
        "safety_backup",
    )
    assert receipt["responsibility_transferred"] is False


def test_case_accepted_handover_preserves_current_reviewer_until_acceptance(journey):
    j = journey
    cat = category(j)
    duty(j)
    row = safety(j, cat)
    assert row["reviewer_id"] == j.actors["safety_reviewer"][0]
    row = case_event(j, row, "ACKNOWLEDGE")
    row = case_event(j, row, "START_REVIEW")
    row = case_event(j, row, "OFFER_HANDOVER", reviewer_id=j.actors["safety_backup"][0])
    assert row["reviewer_id"] == j.actors["safety_reviewer"][0]
    assert (
        j.post(
            f"/safety-cases/{row['id']}/actions",
            {
                "expected_version": row["version"],
                "action": "ACCEPT_HANDOVER",
                "reason": "Synthetic",
                "evidence": "Synthetic",
                "occurred_at": stamp(),
            },
            "safety_backup",
        ).status_code
        == 409
    )
    duty(j, "safety_backup")
    row = case_event(j, row, "ACCEPT_HANDOVER", "safety_backup")
    assert row["reviewer_id"] == j.actors["safety_backup"][0]
    assert j.get(f"/safety-cases/{row['id']}", "safety_reviewer").status_code == 404
    row = case_event(
        j,
        row,
        "VERIFY",
        "safety_backup",
        contributing_factors="Synthetic review, no certified cause",
    )
    reporter = j.get(f"/safety-cases/{row['id']}", "safety_reporter").json()
    assert reporter["data"]["review_details"] == "RESTRICTED_TO_ASSIGNED_REVIEWER"
    row = case_event(
        j,
        row,
        "RECORD_EXTERNAL_RECEIPT",
        "safety_backup",
        external_agency="Synthetic recipient",
        external_receipt="Synthetic actual external receipt",
    )
    assert (
        row["data"]["external_receipts"][0]["verification"]
        == "MANUAL_ATTESTATION_NOT_PROVIDER_INTEGRATION"
    )


def test_inactive_covered_reviewer_does_not_block_signal_capture(journey):
    j = journey
    cat = category(j)
    duty(j)

    async def deactivate():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                update(db.accounts)
                .where(db.accounts.c.id == j.actors["safety_reviewer"][0])
                .values(active=False)
            )

    run(deactivate())
    row = safety(j, cat)
    assert row["reviewer_id"] is None and row["state"] == "SIGNAL"


def test_action_acceptance_resources_evidence_and_completion_are_distinct(journey):
    j = journey
    row = action(j, resource_state="AWAITING_APPROVAL")
    assert row["state"] == "ASSIGNED" and row["data"]["accepted_at"] is None
    row = progress(j, row, "ACCEPT")
    assert (
        j.post(
            f"/actions/{row['id']}/progress",
            {
                "expected_version": row["version"],
                "action": "START",
                "evidence": "Synthetic",
                "reason": "Synthetic",
            },
            "owner",
        ).status_code
        == 409
    )
    row = progress(j, row, "RESOURCE_APPROVAL", "action_reviewer")
    row = progress(j, row, "START")
    row = progress(j, row, "SUBMIT_EVIDENCE")
    assert row["state"] == "EVIDENCE_SUBMITTED"
    assert (
        j.post(
            f"/actions/{row['id']}/progress",
            {
                "expected_version": row["version"],
                "action": "ACCEPT_COMPLETION",
                "evidence": "Synthetic",
                "reason": "Synthetic",
            },
            "owner",
        ).status_code
        == 403
    )
    row = progress(j, row, "ACCEPT_COMPLETION", "action_reviewer")
    assert row["state"] == "REVIEWED_COMPLETE"
    row = progress(
        j,
        row,
        "OUTCOME_REVIEW",
        "action_reviewer",
        outcome="Synthetic observed improvement",
        limitations="Synthetic small observation; no causal inference",
    )
    assert row["data"]["outcome_review"]["limitations"].endswith("no causal inference")


def test_action_handover_requires_successor_acceptance_and_versions(journey):
    j = journey
    row = progress(j, action(j), "ACCEPT")
    old = row["version"]
    row = progress(j, row, "OFFER_HANDOVER", successor_id=j.actors["fallback"][0])
    assert row["owner_id"] == j.actors["owner"][0]
    assert (
        j.post(
            f"/actions/{row['id']}/progress",
            {
                "expected_version": old,
                "action": "START",
                "evidence": "Synthetic",
                "reason": "Synthetic",
            },
            "owner",
        ).status_code
        == 412
    )
    row = progress(j, row, "ACCEPT_HANDOVER", "fallback")
    assert row["owner_id"] == j.actors["fallback"][0] and row["state"] == "ACCEPTED"
    assert j.get(f"/actions/{row['id']}", "executive").status_code == 404


def test_manual_reconciliation_has_one_exception_and_does_not_complete_action(journey):
    from sqlalchemy import func

    j = journey
    row = action(j, due_at=stamp(-1), review_at=stamp(1))
    j.create("/reconcile", {}, "governor")
    j.create("/reconcile", {}, "governor")

    async def counts():
        async with j.app.state.database.transaction() as session:
            return await session.scalar(select(func.count()).select_from(t.escalations))

    assert (
        run(counts()) == 1 and j.get(f"/actions/{row['id']}", "owner").json()["state"] == "ASSIGNED"
    )


def test_paused_reporting_preserves_existing_api_health(journey):
    j = journey
    j.app.state.settings.reporting_enabled = False
    assert j.client.get("/v1/ready").status_code == 200
    assert j.get("/context").status_code == 503


def attest_review(j, row):
    row = j.create(
        f"/returns/{row['id']}/submit",
        {
            "expected_version": row["version"],
            "reason": "Synthetic attestation",
            "intent_confirmed": True,
        },
    )
    return j.create(
        f"/returns/{row['id']}/review",
        {
            "expected_version": row["version"],
            "reason": "Synthetic independent review",
            "intent_confirmed": True,
            "decision": "VERIFY",
            "evidence_examined": "Actual synthetic source",
            "method": "Reconciliation",
            "verification_scope": "Exact period and measure",
            "warning_overrides": {},
        },
        "reviewer",
    )


def test_ratio_aggregates_numerators_and_denominators_instead_of_unit_rates(journey):
    from decimal import Decimal

    j = journey
    definition = j.definition(
        metric_id="LWH-MET-015",
        formula="RATIO",
        aggregation="RATIO_OF_SUMS",
        scale="100",
        unit="percent",
        numerator_is_subset=True,
    )
    obligations = [j.obligation([definition], i) for i in (0, 1)]
    for item, numerator, denominator in zip(obligations, ("10", "10"), ("20", "100"), strict=True):
        row = j.draft(
            item,
            definition,
            values=[
                {
                    "definition_id": definition["id"],
                    "completeness": "VALUE",
                    "numerator": numerator,
                    "denominator": denominator,
                    "source_reference": "Synthetic actual numerator and denominator",
                }
            ],
        )
        attest_review(j, row)
    snapshot = j.released(j.cohort(obligations, j.policy(allowed_metric_ids=["LWH-MET-015"])))
    cell = snapshot["cells"][0]
    assert (
        Decimal(cell["value"]) == Decimal("16.66666667")
        and cell["numerator"] == "20"
        and cell["denominator"] == "120"
    )


def test_related_total_is_complementarily_withheld_and_arithmetic_blocked(journey):
    j = journey
    total = j.definition()
    child = j.definition(metric_id="LWH-MET-012", less_or_equal_metric=total["metric_id"])
    obligations = [j.obligation([total, child], i) for i in (0, 1)]
    for item in obligations:
        row = j.draft(
            item,
            total,
            values=[
                {
                    "definition_id": total["id"],
                    "completeness": "VALUE",
                    "value": "10",
                    "source_reference": "Synthetic total",
                },
                {
                    "definition_id": child["id"],
                    "completeness": "VALUE",
                    "value": "1",
                    "source_reference": "Synthetic subset",
                },
            ],
        )
        attest_review(j, row)
    snapshot = j.released(
        j.cohort(obligations, j.policy(allowed_metric_ids=[total["metric_id"], child["metric_id"]]))
    )
    cells = {cell["metric_id"]: cell for cell in snapshot["cells"]}
    assert cells[total["metric_id"]]["disclosure_status"] == "SUPPRESSED_COMPLEMENTARY" and all(
        cell["value"] is None for cell in cells.values()
    )


def test_historical_obligation_retains_original_region_after_reorganisation(journey):
    j = journey
    definition = j.definition()
    obligation = j.obligation([definition])
    old_region = obligation["region_id"]

    async def reparent():
        async with j.app.state.database.transaction() as session:
            new_region = db.uid()
            await session.execute(
                db.units.insert().values(
                    id=new_region,
                    name="Synthetic new region",
                    kind="REGION",
                    code=new_region,
                    version=1,
                )
            )
            await session.execute(
                update(db.units)
                .where(db.units.c.id == obligation["zone_id"])
                .values(parent_id=new_region, version=2)
            )

    run(reparent())
    grant(j, "outsider", "DATA_REVIEWER", "REGION", old_region)
    rows = j.get("/obligations", "outsider").json()["items"]
    assert (
        rows[0]["region_id"] == old_region
        and rows[0]["hierarchy_snapshot"] == obligation["hierarchy_snapshot"]
    )


def test_real_emr_extract_excludes_error_and_ongoing_encounters_without_patient_data(journey):
    from lw_care_api.platform.clinical import tables as clinical
    from lw_care_api.platform.reporting.store import canonical

    j = journey
    definition = j.definition(source_selector="EMR_COMPLETED_ENCOUNTERS")
    obligation = j.obligation([definition])
    identifiers = [db.uid() for _ in range(4)]
    patient = db.uid()

    async def seed():
        async with j.app.state.database.transaction() as session:
            for number, identifier in enumerate(identifiers):
                content = (
                    {"target_id": identifiers[1]}
                    if number == 3
                    else {
                        "disposition": {"occurred_at": stamp(-2.5)},
                        "private_patient": "SYNTHETIC_CHART_SECRET",
                    }
                )
                await session.execute(
                    clinical.records.insert().values(
                        id=identifier,
                        facility_id=j.facilities[0],
                        patient_id=patient,
                        kind="record_error" if number == 3 else "encounter",
                        status="RECORDED"
                        if number == 3
                        else "ONGOING"
                        if number == 2
                        else "COMPLETED",
                        service="SYNTHETIC",
                        authority_node_id=j.app.state.settings.authority_node_id,
                        authority_epoch="TEST-1",
                        version=1,
                        content_ciphertext=j.app.state.box.encrypt(canonical({"content": content})),
                        created_by=j.actors["reporter"][0],
                        created_at=db.now(),
                        updated_at=db.now(),
                    )
                )

    run(seed())
    extract = j.create(f"/obligations/{obligation['id']}/extract", {})
    assert (
        extract["data"]["source_count"] == 1 and extract["data"]["excluded_entered_in_error"] == 1
    )
    assert patient not in str(extract) and "SYNTHETIC_CHART_SECRET" not in str(extract)
    row = j.draft(
        obligation,
        definition,
        "2",
        values=[
            {
                "definition_id": definition["id"],
                "completeness": "VALUE",
                "value": "2",
                "source_reference": "Synthetic declared discrepancy",
                "extract_id": extract["id"],
            }
        ],
    )
    assert any(item["code"] == "EXTRACT_DISCREPANCY" for item in row["validation"]["findings"])
    assert row["data"]["values"][0]["value"] == "2"


def test_version_two_database_keeps_clinical_ready_while_reporting_awaits_migration(journey):
    j = journey

    async def compatibility():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                db.schema_versions.delete().where(db.schema_versions.c.version == 3)
            )

    run(compatibility())
    assert (
        j.client.get("/v1/ready").status_code == 200
        and j.client.get("/v1/ready").json()["schema_version"] == 2
    )
    assert j.get("/context").status_code == 503
    assert j.client.get("/v1/clinical/sites").status_code == 401


def test_adopted_receipt_requirement_blocks_case_closure_until_actual_evidence(journey):
    j = journey
    cat = category(j, external_receipt_required=True)
    duty(j)
    row = safety(j, cat)
    for event in ("ACKNOWLEDGE", "START_REVIEW", "VERIFY"):
        row = case_event(j, row, event)
    body = {
        "expected_version": row["version"],
        "action": "CLOSE",
        "reason": "Synthetic closure request",
        "evidence": "Synthetic reviewed evidence",
        "occurred_at": stamp(),
    }
    assert j.post(f"/safety-cases/{row['id']}/actions", body, "safety_reviewer").status_code == 409
    row = case_event(
        j,
        row,
        "RECORD_EXTERNAL_RECEIPT",
        external_agency="Synthetic actual recipient",
        external_receipt="Synthetic manually attributed receipt",
    )
    assert case_event(j, row, "CLOSE")["state"] == "CLOSED"
