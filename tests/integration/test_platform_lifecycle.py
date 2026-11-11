"""Stored institutional and publication journeys. All fixture facts are synthetic."""

import pyotp
import pytest
from lw_care_api.platform import db
from lw_care_api.platform.institutional import tables as t
from lw_care_api.platform.reporting.store import scope_for
from lw_care_api.platform.security import issue_session
from sqlalchemy import func, select, update
from test_platform_controls import controls as stored_controls
from test_platform_controls import run, stamp


async def seed_lifecycle(app, actors, facility):
    roles = {
        "admin2": "PLATFORM_ADMIN",
        "registry": "REGISTRY_STEWARD",
        "registry2": "REGISTRY_STEWARD",
        "applicant": "FACILITY_ADMIN",
        "applicant2": "FACILITY_ADMIN",
        "inspector": "INSPECTOR",
        "reviewer": "STANDARDS_REVIEWER",
        "decider": "STANDARDS_DECIDER",
        "appeal_inspector": "INSPECTOR",
        "appeal_reviewer": "STANDARDS_REVIEWER",
        "appeal_decider": "STANDARDS_DECIDER",
        "editor": "CONTENT_EDITOR",
        "publisher": "CONTENT_PUBLISHER",
        "policy": "POLICY_OWNER",
    }
    async with app.state.database.transaction() as session:
        password = await session.scalar(
            select(db.accounts.c.password_hash).where(db.accounts.c.id == actors["target"][0])
        )
        for name, role in roles.items():
            identifier, secret = db.uid(), pyotp.random_base32()
            await session.execute(
                db.accounts.insert().values(
                    id=identifier,
                    name="Synthetic " + name,
                    email=name + "@lifecycle.synthetic.invalid",
                    active=True,
                    password_hash=password,
                    totp_ciphertext=app.state.box.encrypt(secret),
                    totp_last_step=-1,
                    created_at=db.now(),
                )
            )
            local = role == "FACILITY_ADMIN"
            await session.execute(
                db.grants.insert().values(
                    id=db.uid(),
                    account_id=identifier,
                    role=role,
                    scope_type="FACILITY" if local else "GLOBAL",
                    scope_id=facility if local else "GLOBAL",
                    valid_from=stamp(-30),
                    valid_until=stamp(40),
                    revoked=False,
                    grantor="SYNTHETIC_TEST_ONLY",
                )
            )
            actors[name] = (identifier, await issue_session(session, identifier, 60), secret)
        await session.execute(update(db.units).values(valid_from=stamp(-30)))
        await session.execute(
            update(db.facilities)
            .where(db.facilities.c.id == facility)
            .values(
                created_at=stamp(-20),
                identity_status="VERIFIED",
                affiliation_status="ACTIVE",
                affiliation_expires_at=stamp(20),
                affiliation_scope="Synthetic original scope",
                publication_status="PUBLISHED",
            )
        )
        criteria, application, head, file_id, region2, zone2 = [db.uid() for _ in range(6)]
        await session.execute(
            db.units.insert().values(
                id=region2,
                kind="REGION",
                name="Synthetic second region",
                code=region2,
                version=1,
                valid_from=stamp(-30),
            )
        )
        await session.execute(
            db.units.insert().values(
                id=zone2,
                kind="ZONE",
                name="Synthetic second zone",
                code=zone2,
                parent_id=region2,
                version=1,
                valid_from=stamp(-30),
            )
        )
        await session.execute(
            db.criteria.insert().values(
                id=criteria,
                name="SYNTHETIC_ONLY_CRITERIA",
                version="TEST-1",
                jurisdiction="SYNTHETIC-ONLY",
                site_type="COMMUNITY_PRIMARY",
                requirements=[
                    {"code": "SAFE", "description": "Synthetic required control", "required": True}
                ],
                adoption_reference="SYNTHETIC_NOT_AN_INSTITUTIONAL_ADOPTION",
                adopted_by=actors["decider"][0],
                valid_from=stamp(-30),
                valid_until=stamp(40),
            )
        )
        await session.execute(
            db.applications.insert().values(
                id=application,
                facility_id=facility,
                criteria_id=criteria,
                state="DECIDED",
                inspector_id=actors["inspector"][0],
                reviewer_id=actors["reviewer"][0],
                created_by=actors["applicant"][0],
                version=5,
            )
        )
        await session.execute(
            db.decisions.insert().values(
                id=head,
                application_id=application,
                decider_id=actors["decider"][0],
                decision="APPROVE",
                reason="Synthetic original decision",
                scope="Synthetic original scope",
                conditions="",
                effective_at=stamp(-10),
                expires_at=stamp(20),
                created_at=stamp(-10),
            )
        )
        # Synthetic pre-existing accepted-evidence metadata exercises workflow guards;
        # this is not a malware-scanner or production-file qualification result.
        await session.execute(
            db.evidence.insert().values(
                id=file_id,
                application_id=application,
                criterion="SAFE",
                object_key="synthetic-test-only/not-a-production-object",
                sha256="a" * 64,
                filename="synthetic-only.pdf",
                media_type="application/pdf",
                size=1,
                source="SYNTHETIC_PREEXISTING_ACCEPTED_EVIDENCE",
                expires_at=stamp(35),
                scan_status="CLEAN",
                uploaded_by=actors["applicant"][0],
                created_at=stamp(-10),
            )
        )
    return {
        "criteria": criteria,
        "application": application,
        "head": head,
        "file": file_id,
        "region2": region2,
        "zone2": zone2,
    }


@pytest.fixture
def lifecycle(tmp_path):
    for j in stored_controls.__wrapped__(tmp_path):
        j.facts = run(seed_lifecycle(j.app, j.actors, j.facility))
        yield j


def case(j, kind="RENEWAL"):
    return j.create(
        "/institutional/cases",
        {
            "facility_id": j.facility,
            "kind": kind,
            "criteria_id": j.facts["criteria"],
            "respondent_id": j.actors["applicant"][0],
            "due_at": stamp(5),
            "calendar_authority_reference": "Synthetic actual calendar fixture",
            "evidence": "Synthetic scoped case",
            "intent_confirmed": True,
        },
        "applicant",
    )


def advance(j, row, *, outcome="MET", action="RENEW", appeal=False):
    inspector = "appeal_inspector" if appeal else "inspector"
    reviewer = "appeal_reviewer" if appeal else "reviewer"
    row = j.create(
        f"/institutional/cases/{row['id']}/assign",
        {
            "expected_version": row["version"],
            "inspector_id": j.actors[inspector][0],
            "reviewer_id": j.actors[reviewer][0],
            "competence_reference": "Synthetic independently verified competence",
            "evidence": "Synthetic assignment",
            "intent_confirmed": True,
        },
        reviewer,
    )
    row = j.create(
        f"/institutional/cases/{row['id']}/inspect",
        {
            "expected_version": row["version"],
            "conflict_declared": False,
            "observed_at": stamp(-1),
            "findings": [
                {
                    "criterion": "SAFE",
                    "outcome": outcome,
                    "observation": "Synthetic independently observed finding",
                    "evidence_ids": [j.facts["file"]] if outcome == "MET" else [],
                    "due_at": stamp(2),
                }
            ],
            "evidence": "Synthetic actual inspection",
            "intent_confirmed": True,
        },
        inspector,
    )
    if outcome == "MET":
        row = j.create(
            f"/institutional/cases/{row['id']}/recommend",
            {
                "expected_version": row["version"],
                "action": action,
                "evidence": "Synthetic independent recommendation",
                "intent_confirmed": True,
            },
            reviewer,
        )
    return row


def decide_body(row, action="RENEW"):
    return {
        "expected_version": row["version"],
        "action": action,
        "scope": "Synthetic reviewed recognition scope",
        "conditions": "",
        "expires_at": stamp(30),
        "evidence": "Synthetic intentional central decision",
        "intent_confirmed": True,
    }


def agree_corrective_plan(j, finding, owner="applicant", reviewer="reviewer"):
    proposed = j.create(f"/institutional/findings/{finding['id']}/corrective-plan", {
        "expected_version": finding["version"], "required_action": "Synthetic actual agreed corrective work",
        "due_at": stamp(3), "deadline_authority_reference": "Synthetic actual deadline authority",
        "evidence": "Synthetic personally proposed plan", "intent_confirmed": True,
    }, owner)
    return j.create(f"/institutional/findings/{finding['id']}/corrective-plan-review", {
        "expected_version": proposed["version"], "plan_id": proposed["corrective_plan"]["plan_id"],
        "decision": "AGREE", "evidence": "Synthetic independent plan agreement", "intent_confirmed": True,
    }, reviewer)


def content(j, kind="HEALTH_EDUCATION", audience="PUBLIC"):
    return {
        "facility_id": None,
        "title": "Synthetic approved-information workflow",
        "kind": kind,
        "audience": audience,
        "language": "en",
        "jurisdictions": ["SYNTHETIC-ONLY"],
        "body": "SYNTHETIC_ENGINEERING_TEXT_ONLY_NO_MEDICAL_GUIDANCE",
        "correction_summary": "Synthetic engineering change explanation only",
        "purpose": "Synthetic workflow verification only",
        "support_text": "Synthetic service contact reference",
        "support_url": "https://example.invalid/support",
        "licence_reference": "Synthetic permission fixture only",
        "sources": [
            {
                "title": "Synthetic source fixture",
                "url": "https://example.invalid/source",
                "version_reference": "SYNTHETIC-1",
            }
        ],
        "valid_from": stamp(-1),
        "valid_until": stamp(20),
        "review_due_at": stamp(10),
        "evidence": "Synthetic editorial intent",
        "intent_confirmed": True,
    }


def publish(j, body=None, article=None):
    body = body or content(j)
    article = (
        j.create("/institutional/articles", body, "editor")
        if article is None
        else j.create(
            f"/institutional/articles/{article['id']}/revise",
            {**body, "expected_version": article["version"]},
            "editor",
        )
    )
    article = j.create(
        f"/institutional/articles/{article['id']}/submit",
        {
            "expected_version": article["version"],
            "evidence": "Synthetic submission",
            "intent_confirmed": True,
        },
        "editor",
    )
    reviewer = "clinical" if body["kind"] in {"HEALTH_EDUCATION", "CLINICAL_GUIDANCE"} else "policy"
    article = j.create(
        f"/institutional/articles/{article['id']}/review",
        {
            "expected_version": article["version"],
            "decision": "APPROVE",
            "qualification_reference": "Synthetic independently appointed reviewer",
            "evidence": "Synthetic review of sources and applicability",
            "intent_confirmed": True,
        },
        reviewer,
    )
    return j.create(
        f"/institutional/articles/{article['id']}/publish",
        {
            "expected_version": article["version"],
            "evidence": "Synthetic distinct publication decision",
            "intent_confirmed": True,
        },
        "publisher",
    )


def test_reviewed_zone_transfer_preserves_historical_scope(lifecycle):
    j = lifecycle

    async def before():
        async with j.app.state.database.transaction() as session:
            zone = (
                (
                    await session.execute(
                        select(db.units).where(
                            db.units.c.id
                            == select(db.facilities.c.zone_id)
                            .where(db.facilities.c.id == j.facility)
                            .scalar_subquery()
                        )
                    )
                )
                .mappings()
                .one()
            )
            return dict(zone), await scope_for(session, "FACILITY", j.facility, at=stamp(-1))

    zone, old = run(before())
    proposal = j.create(
        "/institutional/changes",
        {
            "kind": "ZONE_REGION",
            "resource_id": zone["id"],
            "target_id": j.facts["region2"],
            "expected_version": zone["version"],
            "evidence": "Synthetic authorised hierarchy transfer",
            "intent_confirmed": True,
        },
    )
    assert (
        j.post(
            f"/institutional/changes/{proposal['id']}/review",
            {
                "expected_version": 1,
                "decision": "APPROVE",
                "evidence": "Self review",
                "intent_confirmed": True,
            },
        ).status_code
        == 409
    )
    j.create(
        f"/institutional/changes/{proposal['id']}/review",
        {
            "expected_version": 1,
            "decision": "APPROVE",
            "evidence": "Synthetic independent approval",
            "intent_confirmed": True,
        },
        "admin2",
    )
    assert j.get("/institutional/changes").json()["items"][0]["state"] == "APPLIED"

    async def after():
        async with j.app.state.database.transaction() as session:
            return await scope_for(session, "FACILITY", j.facility), await scope_for(
                session, "FACILITY", j.facility, at=stamp(-1)
            )

    current, historical = run(after())
    assert (
        current["region_id"] == j.facts["region2"] and historical["region_id"] == old["region_id"]
    )


def test_hierarchy_cycle_and_future_transfer_are_not_silently_applied(lifecycle):
    j = lifecycle
    assert (
        j.post(
            "/institutional/changes",
            {
                "kind": "ZONE_REGION",
                "resource_id": j.facts["region2"],
                "target_id": j.facts["zone2"],
                "expected_version": 1,
                "evidence": "Invalid typed cycle",
                "intent_confirmed": True,
            },
        ).status_code
        == 409
    )
    zone = next(
        row
        for row in j.get("/institutional/catalogue?kind=units").json()["items"]
        if row["kind"] == "ZONE" and row["id"] != j.facts["zone2"]
    )
    proposal = j.create(
        "/institutional/changes",
        {
            "kind": "ZONE_REGION",
            "resource_id": zone["id"],
            "target_id": j.facts["region2"],
            "expected_version": 1,
            "effective_at": stamp(1),
            "evidence": "Synthetic future transfer",
            "intent_confirmed": True,
        },
    )
    j.create(
        f"/institutional/changes/{proposal['id']}/review",
        {
            "expected_version": 1,
            "decision": "APPROVE",
            "evidence": "Synthetic independent future review",
            "intent_confirmed": True,
        },
        "admin2",
    )
    assert j.get("/institutional/changes").json()["items"][0]["state"] == "SCHEDULED"


def test_site_closure_keeps_active_care_and_requires_personal_custody(lifecycle):
    j = lifecycle
    patient, _encounter, _task = j.task()
    facility = j.get(f"/facilities/{j.facility}", "registry").json()
    change = j.create(
        "/institutional/changes",
        {
            "kind": "CLOSE_SITE",
            "resource_id": j.facility,
            "expected_version": facility["version"],
            "custody_owner_id": j.actors["clinical"][0],
            "continuity_plan": "Synthetic explicit open care and records custody plan",
            "evidence": "Synthetic reviewed site closure",
            "intent_confirmed": True,
        },
        "registry",
    )
    j.create(
        f"/institutional/changes/{change['id']}/review",
        {
            "expected_version": 1,
            "decision": "APPROVE",
            "evidence": "Synthetic independent registry review",
            "intent_confirmed": True,
        },
        "registry2",
    )
    offers = j.get("/institutional/custody", "clinical").json()["items"]
    assert offers[0]["state"] == "AWAITING_ACCEPTANCE" and offers[0]["open_record_count"] >= 2
    rejected = j.post(
        f"/clinical/{j.facility}/patients",
        {"display_name": "Synthetic blocked intake", "provisional": True, "sex": "UNKNOWN"},
        "target",
    )
    assert rejected.status_code == 409
    result = j.create(
        f"/institutional/custody/{offers[0]['id']}/accept",
        {
            "expected_version": 1,
            "evidence": "Synthetic personal custody acceptance",
            "intent_confirmed": True,
        },
        "clinical",
    )
    assert result["clinical_tasks_closed"] is False
    assert j.client.get("/v1/directory").json()["items"] == []
    assert (
        j.get(f"/clinical/{j.facility}/patients/{patient['id']}/chart", "target").status_code == 200
    )


def test_renewal_retains_prior_decision_and_requires_central_independence(lifecycle):
    j = lifecycle
    row = advance(j, case(j))
    assert (
        j.post(f"/institutional/cases/{row['id']}/decide", decide_body(row), "reviewer").status_code
        == 403
    )
    result = j.create(f"/institutional/cases/{row['id']}/decide", decide_body(row), "decider")
    assert result["affiliation_status"] == "ACTIVE" and result["publication_reapproval_required"]

    async def preserved():
        async with j.app.state.database.transaction() as session:
            return await session.scalar(
                select(func.count()).select_from(db.decisions)
            ), await session.scalar(select(func.count()).select_from(t.decisions))

    assert run(preserved()) == (1, 1)


def test_finding_response_does_not_resolve_without_independent_review(lifecycle):
    j = lifecycle
    row = advance(j, case(j), outcome="NOT_MET")
    finding = j.get(f"/institutional/cases/{row['id']}", "reviewer").json()["findings"][0]
    finding = agree_corrective_plan(j, finding)
    response = j.create(
        f"/institutional/findings/{finding['id']}/respond",
        {
            "expected_version": finding["version"],
            "completion_evidence": "Synthetic actual correction proof",
            "evidence_ids": [j.facts["file"]],
            "evidence": "Synthetic personal response",
            "intent_confirmed": True,
        },
        "applicant",
    )
    assert response["resolved"] is False
    assert (
        j.post(
            f"/institutional/cases/{row['id']}/recommend",
            {
                "expected_version": row["version"],
                "action": "RENEW",
                "evidence": "Premature recommendation",
                "intent_confirmed": True,
            },
            "reviewer",
        ).status_code
        == 409
    )
    j.create(
        f"/institutional/findings/{finding['id']}/review",
        {
            "expected_version": response["version"],
            "response_id": response["response_id"],
            "decision": "RESOLVE",
            "evidence": "Synthetic independent verification",
            "intent_confirmed": True,
        },
        "reviewer",
    )
    assert (
        j.get(f"/institutional/cases/{row['id']}", "reviewer").json()["findings"][0]["state"]
        == "RESOLVED"
    )


def test_notice_acknowledgement_does_not_waive_response_window(lifecycle):
    j = lifecycle
    row = advance(j, case(j, "NONCOMPLIANCE"), action="SUSPEND")
    notice = j.create(
        f"/institutional/cases/{row['id']}/notices",
        {
            "expected_version": row["version"],
            "text": "Synthetic adverse notice and review route",
            "authority_reference": "Synthetic adopted notice procedure",
            "response_due": stamp(1),
            "evidence": "Synthetic notice intent",
            "intent_confirmed": True,
        },
        "decider",
    )
    j.create(
        f"/institutional/notices/{notice['id']}/acknowledge",
        {"evidence": "Synthetic acknowledgement only", "intent_confirmed": True},
        "applicant",
    )
    body = {
        **decide_body(row, "SUSPEND"),
        "custody_owner_id": j.actors["clinical"][0],
        "continuity_plan": "Synthetic protective continuity plan",
    }
    assert j.post(f"/institutional/cases/{row['id']}/decide", body, "decider").status_code == 409
    result = j.create(
        f"/institutional/cases/{row['id']}/decide",
        {
            **body,
            "urgent_protective_action": True,
            "protective_authority_reference": "Synthetic adopted urgent protective authority",
        },
        "decider",
    )
    assert result["affiliation_status"] == "SUSPENDED"
    appeal = case(j, "APPEAL")
    assert (
        j.get(f"/facilities/{j.facility}", "registry").json()["affiliation_status"] == "SUSPENDED"
    )
    assert (
        j.post(
            f"/institutional/cases/{appeal['id']}/assign",
            {
                "expected_version": 1,
                "inspector_id": j.actors["inspector"][0],
                "reviewer_id": j.actors["reviewer"][0],
                "competence_reference": "Synthetic wrong prior team",
                "evidence": "Invalid appeal team",
                "intent_confirmed": True,
            },
            "reviewer",
        ).status_code
        == 409
    )


def test_case_reassignment_waits_for_personal_acceptance(lifecycle):
    j = lifecycle
    row = case(j)
    offered = j.create(
        f"/institutional/cases/{row['id']}/assignment-offer",
        {
            "expected_version": row["version"],
            "assignment_kind": "RESPONDENT",
            "successor_id": j.actors["applicant2"][0],
            "evidence": "Synthetic absent-owner handover",
            "intent_confirmed": True,
        },
        "reviewer",
    )
    assert (
        offered["respondent_id"] == j.actors["applicant"][0]
        and offered["ownership_transferred"] is False
    )
    accepted = j.create(
        f"/institutional/cases/{row['id']}/assignment-accept",
        {
            "expected_version": offered["version"],
            "assignment_kind": "RESPONDENT",
            "evidence": "Synthetic personal acceptance",
            "intent_confirmed": True,
        },
        "applicant2",
    )
    assert (
        accepted["respondent_id"] == j.actors["applicant2"][0]
        and accepted["prior_authorship_preserved"]
    )


def test_wrong_facility_and_unavailable_scanner_fail_closed(lifecycle):
    j = lifecycle
    row = case(j)
    assert j.get(f"/institutional/cases/{row['id']}", "outsider").status_code in {403, 404}
    headers = j.headers("applicant")
    headers["Content-Type"] = "application/pdf"
    response = j.client.post(
        f"/v1/institutional/cases/{row['id']}/files",
        params={
            "criterion": "SAFE",
            "filename": "synthetic.pdf",
            "source": "Synthetic actual source",
            "expires_at": stamp(5),
            "expected_version": 1,
        },
        content=b"%PDF-1.7 synthetic only",
        headers=headers,
    )
    assert response.status_code == 503


def test_unreviewed_policy_is_never_public_and_wrong_reviewer_is_denied(lifecycle):
    j = lifecycle
    article = j.create("/institutional/articles", content(j, "MINISTRY_POLICY"), "editor")
    assert j.client.get(f"/v1/knowledge/{article['id']}").status_code == 404
    assert (
        j.post(
            f"/institutional/articles/{article['id']}/publish",
            {
                "expected_version": article["version"],
                "evidence": "Unapproved publication",
                "intent_confirmed": True,
            },
            "publisher",
        ).status_code
        == 409
    )
    submitted = j.create(
        f"/institutional/articles/{article['id']}/submit",
        {
            "expected_version": article["version"],
            "evidence": "Synthetic policy submission",
            "intent_confirmed": True,
        },
        "editor",
    )
    assert (
        j.post(
            f"/institutional/articles/{article['id']}/review",
            {
                "expected_version": submitted["version"],
                "decision": "APPROVE",
                "qualification_reference": "Clinical role cannot approve ministry wording",
                "evidence": "Wrong authority",
                "intent_confirmed": True,
            },
            "clinical",
        ).status_code
        == 403
    )


def test_publication_has_sources_applicability_and_no_draft_or_feedback_leak(lifecycle):
    j = lifecycle
    article = publish(j)
    result = j.client.get(f"/v1/knowledge/{article['id']}")
    assert result.status_code == 200 and result.json()["body_served"]
    assert (
        result.json()["content"]["sources"] and result.json()["care_acceptance_inferred"] is False
    )
    assert "evidence" not in result.json()["content"]
    assert j.client.get("/v1/knowledge?jurisdiction=WRONG").json()["items"] == []


def test_clinical_publication_needs_applicability_selection(lifecycle):
    j = lifecycle
    article = publish(j, content(j, "CLINICAL_GUIDANCE"))
    result = j.client.get(f"/v1/knowledge/{article['id']}").json()
    assert result["body_served"] is False and "content" not in result
    assert j.client.get(f"/v1/knowledge/{article['id']}?jurisdiction=SYNTHETIC-ONLY").json()[
        "body_served"
    ]


def test_correction_propagates_to_portal_and_old_receipts_do_not_ack_new_text(lifecycle):
    j = lifecycle
    article = publish(j, content(j, audience="STAFF"))
    first_revision = article["published_revision_id"]
    article = j.create(
        f"/institutional/articles/{article['id']}/distribute",
        {
            "expected_version": article["version"],
            "recipient_ids": [j.actors["target"][0]],
            "evidence": "Synthetic staff portal distribution",
            "intent_confirmed": True,
        },
        "publisher",
    )
    delivery = j.get("/institutional/inbox", "target").json()["items"][0]
    j.create(
        f"/institutional/inbox/{delivery['id']}/receipt",
        {
            "revision_id": first_revision,
            "kind": "READ",
            "evidence": "Synthetic explicit read",
            "intent_confirmed": True,
        },
        "target",
    )
    corrected = publish(
        j,
        {**content(j, audience="STAFF"), "body": "SYNTHETIC_CORRECTED_ENGINEERING_TEXT_ONLY"},
        article,
    )
    assert j.get("/institutional/inbox", "target").json()["items"][0]["state"] == "UPDATE_REQUIRED"
    assert (
        j.post(
            f"/institutional/inbox/{delivery['id']}/receipt",
            {
                "revision_id": first_revision,
                "kind": "ACKNOWLEDGED",
                "evidence": "Stale acknowledgement",
                "intent_confirmed": True,
            },
            "target",
        ).status_code
        == 409
    )
    receipt = j.create(
        f"/institutional/inbox/{delivery['id']}/receipt",
        {
            "revision_id": corrected["published_revision_id"],
            "kind": "ACKNOWLEDGED",
            "evidence": "Synthetic current acknowledgement",
            "intent_confirmed": True,
        },
        "target",
    )
    assert receipt["clinical_outcome_inferred"] is False
    assert j.client.get(f"/v1/knowledge/{article['id']}").status_code == 404


def test_withdrawal_never_serves_original_body_as_current(lifecycle):
    j = lifecycle
    article = publish(j)
    j.create(
        f"/institutional/articles/{article['id']}/withdraw",
        {
            "expected_version": article["version"],
            "evidence": "Synthetic meaningful correction/withdrawal",
            "intent_confirmed": True,
        },
        "publisher",
    )
    response = j.client.get(f"/v1/knowledge/{article['id']}")
    assert response.status_code == 410 and "SYNTHETIC_ENGINEERING_TEXT" not in response.text
    assert j.client.get("/v1/knowledge").json()["items"] == []


def test_schema_five_staging_and_current_authority_before_receipt(lifecycle):
    j = lifecycle

    async def stage():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                db.schema_versions.delete().where(db.schema_versions.c.version > 5)
            )

    run(stage())
    assert j.client.get("/v1/ready").json()["schema_version"] == 5
    assert j.get("/institutional/context").status_code == 503


def test_duplicate_link_preserves_both_clinical_identities(lifecycle):
    j = lifecycle
    patient, _encounter, _task = j.task()
    targets = j.get("/institutional/catalogue?kind=facilities", "registry").json()["items"]
    canonical = next(row for row in targets if row["id"] != j.facility)
    source = next(row for row in targets if row["id"] == j.facility)
    body = {
        "kind": "LINK_DUPLICATE",
        "resource_id": j.facility,
        "target_id": canonical["id"],
        "expected_version": source["version"],
        "custody_owner_id": j.actors["clinical"][0],
        "continuity_plan": "Synthetic records continuity without patient merging",
        "evidence": "Synthetic reviewed same-site evidence",
        "intent_confirmed": True,
    }
    assert j.post("/institutional/changes", body, "registry").status_code == 409
    proposal = j.create("/institutional/changes", {**body, "same_site_verified": True}, "registry")
    j.create(
        f"/institutional/changes/{proposal['id']}/review",
        {
            "expected_version": 1,
            "decision": "APPROVE",
            "evidence": "Synthetic independent duplicate verification",
            "intent_confirmed": True,
        },
        "registry2",
    )
    assert j.get(f"/facilities/{j.facility}", "registry").json()["identity_status"] == "LINKED"
    assert (
        j.get(f"/clinical/{j.facility}/patients/{patient['id']}/chart", "target").status_code == 200
    )


def test_expiry_is_not_silently_extended_by_opening_renewal(lifecycle):
    j = lifecycle

    async def expire():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                update(db.facilities)
                .where(db.facilities.c.id == j.facility)
                .values(affiliation_expires_at=stamp(-1))
            )

    run(expire())
    assert j.get(f"/facilities/{j.facility}", "registry").json()["affiliation_status"] == "EXPIRED"
    case(j)
    assert j.get(f"/facilities/{j.facility}", "registry").json()["affiliation_status"] == "EXPIRED"
    assert j.client.get("/v1/directory").json()["items"] == []


def test_revoked_reviewer_cannot_supply_cached_approval_to_publication(lifecycle):
    j = lifecycle
    article = j.create("/institutional/articles", content(j), "editor")
    article = j.create(
        f"/institutional/articles/{article['id']}/submit",
        {
            "expected_version": article["version"],
            "evidence": "Synthetic submission",
            "intent_confirmed": True,
        },
        "editor",
    )
    article = j.create(
        f"/institutional/articles/{article['id']}/review",
        {
            "expected_version": article["version"],
            "decision": "APPROVE",
            "qualification_reference": "Synthetic qualified review",
            "evidence": "Synthetic review",
            "intent_confirmed": True,
        },
        "clinical",
    )

    async def revoke():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                update(db.grants)
                .where(db.grants.c.account_id == j.actors["clinical"][0])
                .values(revoked=True)
            )

    run(revoke())
    assert (
        j.post(
            f"/institutional/articles/{article['id']}/publish",
            {
                "expected_version": article["version"],
                "evidence": "Stale reviewer authority",
                "intent_confirmed": True,
            },
            "publisher",
        ).status_code
        == 409
    )


def test_current_permission_precedes_cached_institutional_receipt(lifecycle):
    j = lifecycle
    key = db.uid()
    body = content(j)
    first = j.post("/institutional/articles", body, "editor", key)
    assert first.status_code == 200

    async def revoke():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                update(db.grants)
                .where(db.grants.c.account_id == j.actors["editor"][0])
                .values(revoked=True)
            )

    run(revoke())
    assert j.post("/institutional/articles", body, "editor", key).status_code == 403


def test_scheduled_closure_with_revoked_custodian_restricts_new_intake(lifecycle):
    j = lifecycle
    patient, _encounter, _task = j.task()
    facility = j.get(f"/facilities/{j.facility}", "registry").json()
    proposal = j.create(
        "/institutional/changes",
        {
            "kind": "CLOSE_SITE",
            "resource_id": j.facility,
            "expected_version": facility["version"],
            "effective_at": stamp(1),
            "custody_owner_id": j.actors["clinical"][0],
            "continuity_plan": "Synthetic continuity plan requiring a qualified custodian",
            "evidence": "Synthetic reviewed scheduled closure",
            "intent_confirmed": True,
        },
        "registry",
    )
    j.create(
        f"/institutional/changes/{proposal['id']}/review",
        {
            "expected_version": 1,
            "decision": "APPROVE",
            "evidence": "Independent review",
            "intent_confirmed": True,
        },
        "registry2",
    )

    async def authority_expires_before_effect():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                update(db.grants)
                .where(db.grants.c.account_id == j.actors["clinical"][0])
                .values(revoked=True)
            )
            await session.execute(
                update(t.changes)
                .where(t.changes.c.id == proposal["id"])
                .values(effective_at=stamp(-1))
            )

    run(authority_expires_before_effect())
    result = j.get(f"/institutional/changes/{proposal['id']}", "registry").json()
    assert result["change"]["state"] == "BLOCKED_SOURCE_OR_AUTHORITY_CHANGED"
    assert j.client.get("/v1/directory").json()["items"] == []
    assert (
        j.post(
            f"/clinical/{j.facility}/patients",
            {"display_name": "Blocked intake", "provisional": True, "sex": "UNKNOWN"},
            "target",
        ).status_code
        == 409
    )
    assert (
        j.get(f"/clinical/{j.facility}/patients/{patient['id']}/chart", "target").status_code == 200
    )


def test_cancelled_future_change_is_not_materialised(lifecycle):
    j = lifecycle
    zone = next(
        row
        for row in j.get("/institutional/catalogue?kind=units").json()["items"]
        if row["kind"] == "ZONE" and row["id"] != j.facts["zone2"]
    )
    proposal = j.create(
        "/institutional/changes",
        {
            "kind": "ZONE_REGION",
            "resource_id": zone["id"],
            "target_id": j.facts["region2"],
            "expected_version": zone["version"],
            "effective_at": stamp(1),
            "evidence": "Synthetic future transfer",
            "intent_confirmed": True,
        },
    )
    j.create(
        f"/institutional/changes/{proposal['id']}/review",
        {
            "expected_version": 1,
            "decision": "APPROVE",
            "evidence": "Independent review",
            "intent_confirmed": True,
        },
        "admin2",
    )
    current = j.get(f"/institutional/changes/{proposal['id']}").json()["change"]
    cancelled = j.create(
        f"/institutional/changes/{proposal['id']}/cancel",
        {
            "expected_version": current["version"],
            "evidence": "Synthetic cancellation before effect",
            "intent_confirmed": True,
        },
    )
    assert cancelled["state"] == "CANCELLED"
    actual = next(
        row
        for row in j.get("/institutional/catalogue?kind=units").json()["items"]
        if row["id"] == zone["id"]
    )
    assert actual["parent_id"] == zone["parent_id"]


def test_staff_clinical_guidance_requires_applicable_country_for_body_and_receipt(lifecycle):
    j = lifecycle
    article = publish(j, content(j, "CLINICAL_GUIDANCE", "STAFF"))
    j.create(
        f"/institutional/articles/{article['id']}/distribute",
        {
            "expected_version": article["version"],
            "recipient_ids": [j.actors["target"][0]],
            "evidence": "Synthetic portal delivery",
            "intent_confirmed": True,
        },
        "publisher",
    )
    delivery = j.get("/institutional/inbox", "target").json()["items"][0]
    path = f"/institutional/inbox/{delivery['id']}"
    assert j.get(path, "target").json()["body_served"] is False
    assert j.get(path + "?jurisdiction=WRONG", "target").status_code == 404
    assert j.get(path + "?jurisdiction=SYNTHETIC-ONLY", "target").json()["body_served"] is True
    body = {
        "revision_id": article["published_revision_id"],
        "kind": "READ",
        "evidence": "Synthetic actual read",
        "intent_confirmed": True,
    }
    assert j.post(path + "/receipt", body, "target").status_code == 409
    assert (
        j.create(path + "/receipt", {**body, "jurisdiction": "SYNTHETIC-ONLY"}, "target")[
            "clinical_outcome_inferred"
        ]
        is False
    )


def test_editorial_dossier_retains_qualified_review_and_paginates_versions(lifecycle):
    j = lifecycle
    article = publish(j)
    dossier = j.get(f"/institutional/articles/{article['id']}", "publisher").json()
    assert (
        dossier["reviews"][0]["qualification_reference"]
        == "Synthetic independently appointed reviewer"
    )
    assert dossier["reviews"][0]["evidence"]
    assert (
        j.post(
            f"/institutional/articles/{article['id']}/revise",
            {**content(j), "correction_summary": "", "expected_version": article["version"]},
            "editor",
        ).status_code
        == 409
    )
    for _ in range(3):
        article = publish(j, content(j), article)
    dossier = j.get(f"/institutional/articles/{article['id']}", "publisher").json()
    assert len(dossier["revisions"]) == 3 and dossier["next_sequence"] == 2
    earlier = j.get(
        f"/institutional/articles/{article['id']}/revisions?before_sequence=2", "publisher"
    ).json()
    assert len(earlier["items"]) == 1 and earlier["items"][0]["sequence"] == 1
    history = j.get(f"/institutional/history/articles/{article['id']}", "publisher").json()
    assert len(history["items"]) == 1 and history["next_cursor"]
