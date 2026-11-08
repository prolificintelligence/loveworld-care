"""Persisted operating-control journeys; no simulated provider success."""

import asyncio
from datetime import UTC, datetime, timedelta

import pyotp
import pytest
from fastapi.testclient import TestClient
from lw_care_api.platform import db
from lw_care_api.platform.clinical import tables as clinical
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.control import tables as t
from lw_care_api.platform.control.jobs import claim, clinical_reconciliation, dispatch, finish
from lw_care_api.platform.main import create_platform_app
from lw_care_api.platform.security import hash_password, issue_session
from sqlalchemy import func, select, update

ORIGIN = "http://localhost:3004"
PASSWORD = "Synthetic-controls-password-2026"


def run(value):
    return asyncio.run(value)


def stamp(days=0):
    return (datetime.now(UTC) + timedelta(days=days)).isoformat(timespec="microseconds")


class Controls:
    def __init__(self, app, client, actors, facility):
        self.app, self.client, self.actors, self.facility = app, client, actors, facility

    def headers(self, name):
        return {
            "Authorization": "Bearer " + self.actors[name][1],
            "Origin": ORIGIN,
            "Idempotency-Key": db.uid(),
        }

    def factor(self, name):
        return {"password": PASSWORD, "otp": pyotp.TOTP(self.actors[name][2]).now()}

    def post(self, path, body, name="admin", key=None):
        headers = self.headers(name)
        headers["Idempotency-Key"] = key or db.uid()
        return self.client.post("/v1" + path, json=body, headers=headers)

    def create(self, path, body, name="admin", key=None):
        response = self.post(path, body, name, key)
        assert response.status_code == 200, (path, response.text)
        return response.json()["resource"]

    def get(self, path, name="admin"):
        return self.client.get("/v1" + path, headers=self.headers(name))

    def public(self, path, body):
        return self.client.post("/v1/auth/recovery/" + path, json=body, headers={"Origin": ORIGIN})

    def codes(self):
        return self.create("/auth/recovery-codes", self.factor("target"), "target")

    def request(self):
        response = self.public("request", {"email": "target@synthetic.invalid"})
        assert response.status_code == 202, response.text

        async def queued():
            async with self.app.state.database.transaction() as session:
                job = (
                    (await session.execute(select(t.jobs).where(t.jobs.c.kind == "RECOVERY_EMAIL")))
                    .mappings()
                    .one()
                )
                import json

                return json.loads(self.app.state.box.decrypt(job["payload_ciphertext"]))

        return run(queued())

    def package(self, **changes):
        return self.create(
            "/operations/policy-packages",
            {
                "name": "Synthetic activation package",
                "package_version": db.uid(),
                "jurisdiction": "SYNTHETIC-ONLY",
                "facility_id": self.facility,
                "operator": "Synthetic legal operator",
                "custodian": "Synthetic records custodian",
                "services": ["GENERAL"],
                "populations": ["Synthetic adult population"],
                "exclusions": "Synthetic service exclusions",
                "practice_authority": "Synthetic adopted practice evidence",
                "processing_authority": "Synthetic adopted processing authority",
                "processing_locations": [
                    {
                        "service": service,
                        "provider": "Synthetic isolated provider",
                        "location": "Synthetic test location",
                    }
                    for service in ("API", "DATABASE", "STORAGE", "BACKUP")
                ],
                "retention_and_rights_reference": "Synthetic adopted record rules",
                "clinical_content_references": ["Synthetic reviewed clinical content"],
                "coverage_and_escalation_reference": "Synthetic actual duty coverage",
                "training_evidence": "Synthetic observed competence",
                "backup_restore_evidence": "Synthetic restore evidence",
                "local_continuity_evidence": "Synthetic local continuity qualification",
                "funding_support_evidence": "Synthetic approved operating support",
                "source_references": ["Synthetic evidence reference"],
                "valid_from": stamp(-1),
                "valid_until": stamp(10),
                "evidence": "SYNTHETIC TEST ONLY, NO REAL APPROVAL",
                "intent_confirmed": True,
                **changes,
            },
            "proposer",
        )

    def review_package(self, package, kind, name):
        return self.create(
            f"/operations/policy-packages/{package['id']}/review",
            {
                "review_kind": kind,
                "decision": "APPROVE",
                "evidence": "Synthetic independently examined evidence",
                "intent_confirmed": True,
            },
            name,
        )

    def task(self):
        prefix = f"/clinical/{self.facility}"
        patient = self.create(
            prefix + "/patients",
            {"display_name": "Synthetic control patient", "provisional": True, "sex": "UNKNOWN"},
            "target",
        )
        encounter = self.create(
            prefix + "/encounters",
            {
                "patient_id": patient["id"],
                "service": "GENERAL",
                "encounter_type": "AMBULATORY",
                "arrival": "WALK_IN",
                "complaint": "SYNTHETIC_PRIVATE_NARRATIVE",
                "occurred_at": stamp(-1),
            },
            "target",
        )
        task = self.create(
            prefix + "/tasks",
            {
                "patient_id": patient["id"],
                "encounter_id": encounter["id"],
                "title": "SYNTHETIC_PRIVATE_TASK",
                "instructions": "SYNTHETIC_PRIVATE_INSTRUCTIONS",
                "occurred_at": stamp(-1),
                "owner_id": self.actors["target"][0],
                "due_at": stamp(-0.1),
            },
            "target",
        )
        return patient, encounter, task

    def reconcile(self):
        async def apply():
            async with self.app.state.database.transaction() as session:
                return await clinical_reconciliation(
                    session, self.app.state.settings, self.app.state.box
                )

        return run(apply())


async def seed_controls(app):
    cfg = app.state.settings
    actors = {}
    facility, other, region, zone, operator = (db.uid() for _ in range(5))
    roles = {
        "admin": "PLATFORM_ADMIN",
        "proposer": "CLINICAL_GOVERNOR",
        "clinical": "CLINICAL_GOVERNOR",
        "privacy": "PRIVACY_OFFICER",
        "technical": "PLATFORM_ADMIN",
        "reviewer1": "IDENTITY_REVIEWER",
        "reviewer2": "IDENTITY_REVIEWER",
        "target": "CLINICAL_STAFF",
        "successor": "CLINICAL_STAFF",
        "outsider": "CLINICAL_STAFF",
    }
    password_hash = hash_password(PASSWORD)

    async def seed():
        async with app.state.database.transaction() as session:
            for name, role in roles.items():
                identifier = db.uid()
                secret = pyotp.random_base32()
                await session.execute(
                    db.accounts.insert().values(
                        id=identifier,
                        email=name + "@synthetic.invalid",
                        name="Synthetic " + name,
                        active=True,
                        password_hash=password_hash,
                        totp_ciphertext=app.state.box.encrypt(secret),
                        totp_last_step=-1,
                        created_at=db.now(),
                    )
                )
                local = role == "CLINICAL_STAFF"
                await session.execute(
                    db.grants.insert().values(
                        id=db.uid(),
                        account_id=identifier,
                        role=role,
                        scope_type="FACILITY" if local else "GLOBAL",
                        scope_id=(other if name == "outsider" else facility) if local else "GLOBAL",
                        valid_from=stamp(-1),
                        valid_until=stamp(20),
                        revoked=False,
                        grantor="SYNTHETIC_TEST",
                    )
                )
                actors[name] = (identifier, await issue_session(session, identifier, 30), secret)
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
            for identifier in (facility, other):
                await session.execute(
                    db.facilities.insert().values(
                        id=identifier,
                        operator_id=operator,
                        zone_id=zone,
                        name="Synthetic isolated facility",
                        site_type="COMMUNITY_PRIMARY",
                        ownership="MEMBER_OWNED",
                        jurisdiction="SYNTHETIC-ONLY",
                        external_reference=identifier,
                        address="Synthetic",
                        public_contact="public@synthetic.invalid",
                        private_contact="private@synthetic.invalid",
                        services=["GENERAL"],
                        identity_status="VERIFIED",
                        statutory_status="CHECKED",
                        version=1,
                        created_by=actors["admin"][0],
                        created_at=db.now(),
                        updated_at=db.now(),
                    )
                )
                await session.execute(
                    clinical.sites.insert().values(
                        id=db.uid(),
                        facility_id=identifier,
                        authority_node_id=cfg.authority_node_id,
                        authority_epoch="TEST-1",
                        services=["GENERAL"],
                        policy_reference="Synthetic existing site scope",
                        manual_medicine_policy="Synthetic manual care policy",
                        valid_from=stamp(-1),
                        valid_until=stamp(20),
                        active=True,
                        version=1,
                        approved_by=actors["clinical"][0],
                    )
                )
            for name in ("target", "successor", "outsider"):
                await session.execute(
                    clinical.privileges.insert().values(
                        id=db.uid(),
                        facility_id=other if name == "outsider" else facility,
                        account_id=actors[name][0],
                        services=["GENERAL"],
                        capabilities=["REGISTER", "CARE", "NURSING"],
                        professional_reference="Synthetic verified professional authority",
                        valid_from=stamp(-1),
                        valid_until=stamp(20),
                        revoked=False,
                        approved_by=actors["clinical"][0],
                    )
                )

    await seed()
    return actors, facility


@pytest.fixture
def controls(tmp_path):
    cfg = PlatformSettings(
        environment="test",
        dispatch_recovery_after_commit=False,
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'controls.db').as_posix()}",
        data_key_hex="d4" * 32,
        web_origin=ORIGIN,
        authority_node_id=db.uid(),
        resend_api_key="synthetic-not-a-sending-key",
        email_from="Synthetic <sender@synthetic.invalid>",
        jobs_secret="synthetic-job-secret-for-isolated-tests-only",
    )
    app = create_platform_app(cfg)
    run(app.state.database.migrate())

    actors, facility = run(seed_controls(app))
    with TestClient(app) as client:
        yield Controls(app, client, actors, facility)


def test_recovery_request_does_not_enumerate_or_send_in_request(controls):
    j = controls
    actual = j.public("request", {"email": "target@synthetic.invalid"})
    missing = j.public("request", {"email": "missing@synthetic.invalid"})
    assert actual.status_code == missing.status_code == 202 and actual.json() == missing.json()

    async def counts():
        async with j.app.state.database.transaction() as session:
            return await session.scalar(
                select(func.count()).select_from(t.jobs)
            ), await session.scalar(select(func.count()).select_from(t.recoveries))

    assert run(counts()) == (1, 1)
    assert j.public("request", {"email": "target@synthetic.invalid"}).status_code == 202
    assert run(counts()) == (1, 1)


def test_backup_codes_have_one_effect_and_are_not_stored_plaintext(controls):
    j = controls
    body = j.factor("target")
    key = db.uid()
    first = j.create("/auth/recovery-codes", body, "target", key)
    second = j.create("/auth/recovery-codes", body, "target", key)
    assert first == second and len(first["codes"]) == 10

    async def rows():
        async with j.app.state.database.transaction() as session:
            return [dict(r) for r in (await session.execute(select(t.backup_codes))).mappings()]

    stored = run(rows())
    assert len(stored) == 10 and not any(code in str(stored) for code in first["codes"])
    assert j.post("/auth/recovery-codes", body, "target").status_code == 401


def test_email_alone_cannot_reset_authenticator(controls):
    j = controls
    queued = j.request()
    token = queued["token"]
    assert (
        j.public("setup", {"token": token, "password": "A-new-synthetic-password-2026"}).status_code
        == 409
    )
    assert (
        j.public(
            "prove", {"token": token, "method": "BACKUP_CODE", "proof": "invalid-code"}
        ).status_code
        == 401
    )
    assert (
        j.public("setup", {"token": token, "password": "A-new-synthetic-password-2026"}).status_code
        == 409
    )


def test_verified_recovery_preserves_identity_and_grants_and_revokes_sessions(controls):
    j = controls
    codes = j.codes()
    token = j.request()["token"]
    before = j.get("/auth/me", "target").json()
    assert (
        j.public(
            "prove", {"token": token, "method": "BACKUP_CODE", "proof": codes["codes"][0]}
        ).json()["status"]
        == "AUTHORIZED"
    )
    body = {"token": token, "password": "A-new-synthetic-password-2026"}
    setup = j.public("setup", body)
    assert setup.status_code == 200
    assert setup.json() == j.public("setup", body).json()
    assert (
        j.public("setup", {**body, "password": "Another-synthetic-password-2026"}).status_code
        == 409
    )
    response = j.public(
        "complete", {"token": token, "otp": pyotp.TOTP(setup.json()["setup_key"]).now()}
    )
    assert response.status_code == 200
    assert j.get("/auth/me", "target").status_code == 401
    current = j.client.get("/v1/auth/me").json()
    assert current["id"] == before["id"] and current["grants"] == before["grants"]
    assert (
        j.public(
            "complete", {"token": token, "otp": pyotp.TOTP(setup.json()["setup_key"]).now()}
        ).status_code
        == 401
    )


def test_recovery_requires_two_distinct_current_identity_reviewers(controls):
    j = controls
    queued = j.request()
    token = queued["token"]
    assert (
        j.public("prove", {"token": token, "method": "INDEPENDENT_REVIEW"}).json()["status"]
        == "REVIEW_REQUIRED"
    )
    body = {
        "decision": "APPROVE",
        "evidence": "Synthetic independent identity verification",
        "intent_confirmed": True,
    }
    assert (
        j.post(
            f"/operations/recoveries/{queued['recovery_id']}/review",
            {**body, **j.factor("admin")},
            "admin",
        ).status_code
        == 403
    )
    first = j.create(
        f"/operations/recoveries/{queued['recovery_id']}/review",
        {**body, **j.factor("reviewer1")},
        "reviewer1",
    )
    assert first["state"] == "REVIEW_REQUIRED"
    assert (
        j.public("setup", {"token": token, "password": "A-new-synthetic-password-2026"}).status_code
        == 409
    )
    second = j.create(
        f"/operations/recoveries/{queued['recovery_id']}/review",
        {**body, **j.factor("reviewer2")},
        "reviewer2",
    )
    assert second["state"] == "AUTHORIZED"


def test_expired_recovery_is_rejected_and_secrets_not_echoed(controls):
    j = controls
    queued = j.request()

    async def expire():
        async with j.app.state.database.transaction() as session:
            await session.execute(update(t.recoveries).values(expires_at=stamp(-1)))

    run(expire())
    response = j.public(
        "prove", {"token": queued["token"], "method": "AUTHENTICATOR", "proof": "000000"}
    )
    assert response.status_code == 401 and queued["token"] not in response.text
    invalid = j.public("setup", {"token": queued["token"], "password": "SECRET"})
    assert (
        invalid.status_code == 422
        and "SECRET" not in invalid.text
        and queued["token"] not in invalid.text
    )


def test_package_adoption_requires_distinct_domain_reviews(controls):
    j = controls
    package = j.package()
    assert package["state"] == "AWAITING_REVIEW"
    body = {
        "review_kind": "CLINICAL",
        "decision": "APPROVE",
        "evidence": "Synthetic review",
        "intent_confirmed": True,
    }
    assert (
        j.post(f"/operations/policy-packages/{package['id']}/review", body, "proposer").status_code
        == 403
    )
    j.review_package(package, "CLINICAL", "clinical")
    j.review_package(package, "PRIVACY", "privacy")
    assert j.get("/operations/policy-packages").json()["items"][0]["state"] == "AWAITING_REVIEW"
    assert j.review_package(package, "TECHNICAL", "technical")["state"] == "ADOPTED"


def test_new_activation_requires_current_package_and_withdrawal_blocks_new_writes(controls):
    j = controls
    prefix = f"/clinical/{j.facility}"
    body = {
        "expected_version": 1,
        "services": ["GENERAL"],
        "policy_reference": "Synthetic applicable policy",
        "manual_medicine_policy": "Synthetic manual care",
        "valid_from": stamp(),
        "valid_until": stamp(2),
        "intent_confirmed": True,
    }
    assert j.post(prefix + "/activation", body, "clinical").status_code == 409
    package = j.package()
    for kind, name in (
        ("CLINICAL", "clinical"),
        ("PRIVACY", "privacy"),
        ("TECHNICAL", "technical"),
    ):
        j.review_package(package, kind, name)
    result = j.create(
        prefix + "/activation", {**body, "activation_package_id": package["id"]}, "clinical"
    )
    assert result["version"] == 2
    j.create(
        "/operations/policy-packages/" + package["id"] + "/withdraw",
        {"evidence": "Synthetic authority withdrawal", "intent_confirmed": True},
        "privacy",
    )
    assert (
        j.post(
            prefix + "/patients",
            {"display_name": "Synthetic", "provisional": True, "sex": "UNKNOWN"},
            "target",
        ).status_code
        == 403
    )


def test_task_index_is_atomic_and_reconciliation_is_not_task_completion(controls):
    j = controls
    _, _, task = j.task()

    async def count():
        async with j.app.state.database.transaction() as session:
            return await session.scalar(select(func.count()).select_from(t.obligations))

    assert run(count()) == 1
    assert j.reconcile()["new_alerts"] == 1 and j.reconcile()["new_alerts"] == 0
    alert = j.get("/operations/alerts", "target").json()["items"][0]
    assert "SYNTHETIC_PRIVATE" not in str(alert)
    receipt = j.create(
        f"/operations/alerts/{alert['id']}/acknowledge",
        {"evidence": "Synthetic operational acknowledgement", "intent_confirmed": True},
        "target",
    )
    assert receipt["clinical_task_completed"] is False
    assert (
        j.get(f"/clinical/{j.facility}/records/{task['id']}", "target").json()["status"]
        == "ASSIGNED"
    )
    assert j.get("/operations/alerts", "outsider").json()["items"] == []


def test_job_leases_recover_after_restart_and_old_worker_cannot_finish(controls):
    j = controls
    j.request()
    first = run(claim(j.app.state.database))
    assert first
    assert run(claim(j.app.state.database)) is None

    async def expire():
        async with j.app.state.database.transaction() as session:
            await session.execute(update(t.jobs).values(lease_until=stamp(-1)))

    run(expire())
    second = run(claim(j.app.state.database))
    assert second["id"] == first["id"] and second["attempts"] == 2
    assert run(finish(j.app.state.database, first, "RETRY_PROVIDER_UNKNOWN", None)) is False
    assert run(finish(j.app.state.database, second, "RETRY_PROVIDER_UNKNOWN", None)) is True


def test_missing_delivery_dependency_is_real_retry_not_success(controls):
    j = controls
    j.request()
    job = run(claim(j.app.state.database))
    j.app.state.settings.resend_api_key = ""
    outcome, receipt = run(
        dispatch(j.app.state.database, j.app.state.settings, j.app.state.box, job)
    )
    assert outcome == "RETRY_DEPENDENCY_UNAVAILABLE" and receipt is None
    run(finish(j.app.state.database, job, outcome, receipt))
    row = j.get("/operations/jobs").json()["items"][0]
    assert (
        row["state"] == "RETRY"
        and row["provider_receipt"] is None
        and "payload_ciphertext" not in row
    )


def test_provider_window_requires_reconciliation_before_retry(controls):
    j = controls
    j.request()

    async def old():
        async with j.app.state.database.transaction() as session:
            await session.execute(update(t.jobs).values(first_attempt_at=stamp(-2)))

    run(old())
    assert run(claim(j.app.state.database)) is None
    row = j.get("/operations/jobs").json()["items"][0]
    assert row["state"] == "RECONCILIATION_REQUIRED"
    body = {
        "evidence": "Synthetic provider reconciliation evidence",
        "intent_confirmed": True,
        "provider_reconciled": False,
    }
    assert j.post(f"/operations/jobs/{row['id']}/retry", body).status_code == 409
    result = j.create(f"/operations/jobs/{row['id']}/retry", {**body, "provider_reconciled": True})
    assert result["provider_delivery_claimed"] is False


def test_offboarding_restricts_account_and_needs_personal_handover_acceptance(controls):
    j = controls
    patient, _, task = j.task()
    case = j.create(
        "/operations/offboarding",
        {
            "account_id": j.actors["target"][0],
            "coordinator_id": j.actors["clinical"][0],
            "evidence": "Synthetic actual offboarding authority",
            "intent_confirmed": True,
            **j.factor("admin"),
        },
    )
    assert case["account_restricted"] is True and case["offboarding_complete"] is False
    assert j.get("/auth/me", "target").status_code == 401
    rows = j.get("/operations/handovers", "clinical").json()["items"]
    item = next(row for row in rows if row["source_id"] == task["id"])
    offer = j.create(
        f"/operations/handovers/{item['id']}/offer",
        {
            "expected_version": 1,
            "successor_id": j.actors["successor"][0],
            "evidence": "Synthetic accepted professional candidate",
            "intent_confirmed": True,
        },
        "clinical",
    )
    assert offer["ownership_transferred"] is False
    accepted = j.create(
        f"/operations/handovers/{item['id']}/accept",
        {
            "expected_version": 2,
            "patient_id": patient["id"],
            "evidence": "Synthetic independent patient confirmation and accepted responsibility",
            "intent_confirmed": True,
        },
        "successor",
    )
    assert accepted["ownership_transferred"] is True
    source = j.get(f"/clinical/{j.facility}/records/{task['id']}", "successor").json()
    assert source["data"]["owner_id"] == j.actors["successor"][0] and source["status"] == "ACCEPTED"


def test_current_stack_and_offline_scope_are_truthful(controls):
    j = controls
    data = j.get("/operations/context").json()
    assert (
        data["offline_care"]["scope"] == "CORE"
        and data["offline_care"]["current_cloud_requires_wan"] is True
    )
    assert data["delivery"]["continuous_worker_deployment"] == "DEFERRED_OUTSIDE_CURRENT_STACK"
    assert j.client.get("/v1/ready").json()["schema_version"] == 6
    assert j.client.get("/v1/operations/context").status_code == 401


def test_credential_recovery_proof_is_rate_limited_persistently(controls):
    j = controls
    token = j.request()["token"]
    statuses = [
        j.public(
            "prove", {"token": token, "method": "BACKUP_CODE", "proof": "not-a-valid-code"}
        ).status_code
        for _ in range(12)
    ]
    assert 401 in statuses and 429 in statuses


def test_changed_task_cancels_old_notice_and_does_not_send_clinical_content(controls):
    j = controls
    patient, _, task = j.task()
    j.reconcile()
    job = run(claim(j.app.state.database))
    assert job
    j.create(
        f"/clinical/{j.facility}/tasks/{task['id']}/actions",
        {
            "patient_id": patient["id"],
            "expected_version": 1,
            "action": "ACCEPT",
            "reason": "Synthetic actual acceptance",
            "evidence": "Synthetic task acceptance",
        },
        "target",
    )
    outcome, receipt = run(
        dispatch(j.app.state.database, j.app.state.settings, j.app.state.box, job)
    )
    assert outcome.startswith("CANCELLED") and receipt is None
    row = j.get("/operations/alerts", "target").json()["items"][0]
    assert row["state"] == "SOURCE_CHANGED" and row["superseded_at"]


def test_wrong_scope_and_stale_patient_handover_are_denied(controls):
    j = controls
    patient, _, task = j.task()
    j.create(
        "/operations/offboarding",
        {
            "account_id": j.actors["target"][0],
            "coordinator_id": j.actors["clinical"][0],
            "evidence": "Synthetic actual authority",
            "intent_confirmed": True,
            **j.factor("admin"),
        },
    )
    item = next(
        row
        for row in j.get("/operations/handovers", "clinical").json()["items"]
        if row["source_id"] == task["id"]
    )
    body = {
        "expected_version": 1,
        "successor_id": j.actors["outsider"][0],
        "evidence": "Synthetic proposal",
        "intent_confirmed": True,
    }
    assert j.post(f"/operations/handovers/{item['id']}/offer", body, "clinical").status_code == 403
    j.create(
        f"/operations/handovers/{item['id']}/offer",
        {**body, "successor_id": j.actors["successor"][0]},
        "clinical",
    )
    assert j.get(f"/operations/handovers/{item['id']}/context", "admin").status_code == 404
    preview = j.get(f"/operations/handovers/{item['id']}/context", "successor")
    assert (
        preview.status_code == 200
        and preview.json()["patient"]["id"] == patient["id"]
        and "SYNTHETIC_PRIVATE" not in preview.text
    )
    assert (
        j.post(
            f"/operations/handovers/{item['id']}/accept",
            {
                "expected_version": 2,
                "patient_id": db.uid(),
                "evidence": "Synthetic wrong identity",
                "intent_confirmed": True,
            },
            "successor",
        ).status_code
        == 412
    )


def test_policy_receipt_is_denied_after_role_revocation(controls):
    j = controls
    package = j.package()

    async def revoke():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                update(db.grants)
                .where(db.grants.c.account_id == j.actors["privacy"][0])
                .values(revoked=True)
            )

    run(revoke())
    assert (
        j.post(
            f"/operations/policy-packages/{package['id']}/review",
            {
                "review_kind": "PRIVACY",
                "decision": "APPROVE",
                "evidence": "Synthetic source examined",
                "intent_confirmed": True,
            },
            "privacy",
        ).status_code
        == 403
    )


def test_schema_three_compatibility_preserves_existing_cloud_readiness(controls):
    j = controls

    async def compatibility():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                db.schema_versions.delete().where(db.schema_versions.c.version > 3)
            )

    run(compatibility())
    assert (
        j.client.get("/v1/ready").status_code == 200
        and j.client.get("/v1/ready").json()["schema_version"] == 3
    )
    assert j.get("/operations/context").status_code == 503
    assert j.client.get("/v1/clinical/sites").status_code == 401


def test_accepted_coverage_routes_previously_unowned_alert_without_completing_source(controls):
    j = controls
    _, _, task = j.task()

    async def restrict():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                update(db.accounts)
                .where(db.accounts.c.id == j.actors["target"][0])
                .values(active=False)
            )

    run(restrict())
    j.reconcile()
    alert = j.get("/operations/alerts", "clinical").json()["items"][0]
    assert alert["state"] == "UNOWNED"
    duty = j.create(
        "/operations/coverage",
        {
            "facility_id": j.facility,
            "account_id": j.actors["successor"][0],
            "services": ["GENERAL"],
            "valid_from": stamp(-1),
            "valid_until": stamp(1),
            "adoption_reference": "Synthetic actual coverage authority",
            "evidence": "Synthetic signed roster",
            "intent_confirmed": True,
        },
        "clinical",
    )
    assert j.get("/operations/alerts", "successor").json()["items"] == []
    receipt = j.create(
        f"/operations/coverage/{duty['id']}/accept",
        {"evidence": "Synthetic personally accepted duty", "intent_confirmed": True},
        "successor",
    )
    assert receipt["updated_alert_routes"] == 1
    routed = j.get("/operations/alerts", "successor").json()["items"][0]
    assert (
        routed["fallback_id"] == j.actors["successor"][0]
        and routed["source_id"] == task["id"]
        and routed["source_resolved_at"] is None
    )
