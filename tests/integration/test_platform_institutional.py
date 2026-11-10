"""Institutional runtime tests use real isolated databases, not provider success mocks."""

import asyncio
from datetime import UTC, datetime, timedelta

import pyotp
import pytest
from fastapi.testclient import TestClient
from lw_care_api.platform import db
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.main import create_platform_app
from lw_care_api.platform.security import digest, hash_password, issue_session
from sqlalchemy import func, select, update

ORIGIN = "http://localhost:3004"


def run(coroutine):
    return asyncio.run(coroutine)


def stamp(days=0):
    return (datetime.now(UTC) + timedelta(days=days)).isoformat(timespec="microseconds")


@pytest.fixture
def runtime(tmp_path):
    cfg = PlatformSettings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'platform.db').as_posix()}",
        data_key_hex="a1" * 32,
        web_origin=ORIGIN,
        authority_node_id=db.uid(),
    )
    app = create_platform_app(cfg)
    run(app.state.database.migrate())
    with TestClient(app) as client:
        yield app, client, cfg


def staff(app, role="REGISTRY_STEWARD", scope_type="GLOBAL", scope_id="GLOBAL"):
    account_id, secret = db.uid(), pyotp.random_base32()

    async def create():
        async with app.state.database.transaction() as session:
            await session.execute(
                db.accounts.insert().values(
                    id=account_id,
                    email=f"{account_id}@test.invalid",
                    name="Synthetic test staff",
                    password_hash=hash_password("Test-only-password-2026"),
                    totp_ciphertext=app.state.box.encrypt(secret),
                    totp_last_step=-1,
                    active=True,
                    created_at=stamp(),
                )
            )
            await session.execute(
                db.grants.insert().values(
                    id=db.uid(),
                    account_id=account_id,
                    role=role,
                    scope_type=scope_type,
                    scope_id=scope_id,
                    valid_from=stamp(-1),
                    valid_until=stamp(10),
                    revoked=False,
                    grantor="TEST_FIXTURE",
                )
            )
            token = await issue_session(session, account_id, 30)
            return {"Authorization": f"Bearer {token}", "Origin": ORIGIN}

    return account_id, secret, run(create())


def post(client, path, body, headers, key=None):
    return client.post(
        "/v1" + path, json=body, headers={**headers, "Idempotency-Key": key or db.uid()}
    )


def registry(app, client):
    account_id, _, headers = staff(app)
    _, _, admin = staff(app, "PLATFORM_ADMIN")
    region = post(
        client,
        "/organisation-units",
        {"name": "Synthetic region", "code": db.uid(), "kind": "REGION", "valid_from": stamp(-1)},
        admin,
    ).json()["resource"]
    zone = post(
        client,
        "/organisation-units",
        {
            "name": "Synthetic zone",
            "code": db.uid(),
            "kind": "ZONE",
            "parent_id": region["id"],
            "valid_from": stamp(-1),
        },
        admin,
    ).json()["resource"]
    operator = post(
        client,
        "/operators",
        {"name": "Synthetic operator", "external_reference": db.uid()},
        headers,
    ).json()["resource"]
    payload = {
        "operator_org_id": operator["id"],
        "zone_id": zone["id"],
        "site_name": "Synthetic clinic",
        "site_type": "COMMUNITY_PRIMARY",
        "ownership_category": "MEMBER_OWNED",
        "jurisdiction_profile": "TEST-ONLY",
        "external_reference": db.uid(),
        "address": "Synthetic test street, not a real site",
        "public_contact": "contact@test.invalid",
        "private_contact": "private@test.invalid",
        "services": ["Synthetic service"],
    }
    return account_id, headers, region, zone, payload


def test_production_fails_without_real_postgres_and_keys():
    cfg = PlatformSettings(
        database_url="sqlite+aiosqlite:///:memory:",
        data_key_hex="aa" * 32,
        web_origin="https://care.example.org",
        authority_node_id=db.uid(),
        jobs_secret="a" * 40,
    )
    with pytest.raises(ValueError, match="PostgreSQL"):
        create_platform_app(cfg)


def test_paid_model_configuration_is_rejected():
    cfg = PlatformSettings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        data_key_hex="a1" * 32,
        web_origin=ORIGIN,
        authority_node_id=db.uid(),
        openrouter_model="unapproved-paid-model",
    )
    with pytest.raises(ValueError, match="free OpenRouter"):
        create_platform_app(cfg)


def test_integration_probes_are_scoped_and_reject_arbitrary_input(runtime):
    app, client, _ = runtime
    _, _, registry_headers = staff(app)
    assert post(client, "/integrations/openrouter/verify", {}, registry_headers).status_code == 403
    _, _, admin_headers = staff(app, "PLATFORM_ADMIN")
    response = post(
        client,
        "/integrations/openrouter/verify",
        {"patient_notes": "never forward this"},
        admin_headers,
    )
    assert response.status_code == 422
    assert "never forward this" not in response.text
    assert (
        post(client, "/integrations/ai-control", {"enabled": "true"}, admin_headers).status_code
        == 422
    )
    assert post(client, "/integrations/openrouter/verify", {}, admin_headers).status_code == 503


def test_no_demo_records_or_dev_token_route(runtime):
    app, client, _ = runtime
    _, _, headers = staff(app)
    assert client.get("/v1/facilities", headers=headers).json()["items"] == []
    assert client.get("/v1/directory").json()["items"] == []
    assert client.post("/v1/auth/dev-token", headers={"Origin": ORIGIN}).status_code == 404
    assert client.get("/v1/facilities").status_code == 401
    assert client.post("/v1/organisation-units", json={}).status_code == 403
    assert client.get("/v1/ready").json()["status"] == "READY"


def test_password_totp_login_and_durable_revocation(runtime):
    app, client, cfg = runtime
    account_id, secret, _ = staff(app)
    payload = {
        "email": f"{account_id}@test.invalid",
        "password": "Test-only-password-2026",
        "otp": pyotp.TOTP(secret).now(),
    }
    assert (
        client.post("/v1/auth/login", json=payload, headers={"Origin": ORIGIN}).status_code == 200
    )
    assert client.get("/v1/auth/me").json()["id"] == account_id
    session_cookie = client.cookies.get("lwh_session")
    # A new process uses the same database, not a singleton identity map.
    replica = TestClient(create_platform_app(cfg))
    headers = {"Authorization": f"Bearer {session_cookie}", "Origin": ORIGIN}
    assert replica.get("/v1/auth/me", headers=headers).status_code == 200
    assert client.post("/v1/auth/logout", headers={"Origin": ORIGIN}).status_code == 204
    assert replica.get("/v1/auth/me", headers=headers).status_code == 401
    assert (
        client.post("/v1/auth/login", json=payload, headers={"Origin": ORIGIN}).status_code == 401
    )


def test_login_rate_limit_commits_failed_attempts_and_redacts_inputs(runtime):
    _, client, _ = runtime
    payload = {
        "email": "unknown@test.invalid",
        "password": "wrong-password-private",
        "otp": "123456",
    }
    for _ in range(8):
        assert (
            client.post("/v1/auth/login", json=payload, headers={"Origin": ORIGIN}).status_code
            == 401
        )
    assert (
        client.post("/v1/auth/login", json=payload, headers={"Origin": ORIGIN}).status_code == 429
    )
    payload["otp"] = "invalid-private-value"
    error = client.post("/v1/auth/login", json=payload, headers={"Origin": ORIGIN})
    assert error.status_code == 422
    assert "wrong-password-private" not in error.text and "invalid-private-value" not in error.text


def test_registration_idempotency_restart_and_public_privacy(runtime):
    app, client, cfg = runtime
    _, headers, _, _, payload = registry(app, client)
    key = db.uid()
    first = post(client, "/facilities", payload, headers, key)
    assert first.status_code == 200, first.text
    assert post(client, "/facilities", payload, headers, key).json() == first.json()
    different = post(
        client, "/facilities", {**payload, "site_name": "Changed content"}, headers, key
    )
    assert different.status_code == 409
    assert different.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSE"
    replica = TestClient(create_platform_app(cfg))
    stored = replica.get("/v1/facilities", headers=headers).json()["items"]
    assert len(stored) == 1 and stored[0]["private_contact"] == "private@test.invalid"
    assert client.get("/v1/directory").json()["items"] == []


def test_scope_substitution_expired_grant_and_admin_separation(runtime):
    app, client, _ = runtime
    _, headers, _, zone, payload = registry(app, client)
    facility = post(client, "/facilities", payload, headers).json()["resource"]
    _, _, other = staff(app, "REGISTRY_STEWARD", "ZONE", db.uid())
    assert client.get(f"/v1/facilities/{facility['id']}", headers=other).status_code == 404
    assert client.get("/v1/facilities", headers=other).json()["items"] == []
    _, _, admin = staff(app, "PLATFORM_ADMIN")
    assert client.get(f"/v1/facilities/{facility['id']}", headers=admin).status_code == 404
    account, _, scoped_headers = staff(app, "REGISTRY_STEWARD", "ZONE", zone["id"])
    assert client.get(f"/v1/facilities/{facility['id']}", headers=scoped_headers).status_code == 200

    async def expire():
        async with app.state.database.transaction() as session:
            await session.execute(
                update(db.grants)
                .where(db.grants.c.account_id == account)
                .values(valid_until=stamp(-1))
            )

    run(expire())
    assert client.get(f"/v1/facilities/{facility['id']}", headers=scoped_headers).status_code == 404


def test_version_guard_preserves_original_and_does_not_publish(runtime):
    app, client, _ = runtime
    _, headers, _, _, payload = registry(app, client)
    facility = post(client, "/facilities", payload, headers).json()["resource"]
    path = f"/facilities/{facility['id']}/verification"
    body = {
        "expected_version": 1,
        "identity_status": "VERIFIED",
        "statutory_status": "CHECKED",
        "reason": "Synthetic reviewed source",
    }
    assert post(client, path, body, headers).status_code == 200
    assert post(client, path, body, headers).status_code == 412
    assert (
        post(
            client,
            f"/facilities/{facility['id']}/publication",
            {"expected_version": 2, "action": "PUBLISH", "reason": "Must not bypass affiliation"},
            headers,
        ).status_code
        == 409
    )
    current = client.get(f"/v1/facilities/{facility['id']}", headers=headers).json()
    assert current["version"] == 2 and current["affiliation_status"] == "APPLICANT"


def test_complete_institutional_authority_and_publication_chain(runtime):
    app, client, _ = runtime
    _, headers, _, _, payload = registry(app, client)
    facility = post(client, "/facilities", payload, headers).json()["resource"]
    inspector, _, inspector_headers = staff(app, "INSPECTOR")
    reviewer, _, reviewer_headers = staff(app, "STANDARDS_REVIEWER")
    _, _, decider = staff(app, "STANDARDS_DECIDER")
    criteria_body = {
        "name": "Synthetic test criteria",
        "version": "1",
        "jurisdiction": "TEST-ONLY",
        "site_type": "COMMUNITY_PRIMARY",
        "requirements": [
            {"code": "TEST-ID", "description": "Synthetic identity evidence", "required": True}
        ],
        "adoption_reference": "TEST FIXTURE ONLY",
        "valid_from": stamp(-1),
        "valid_until": stamp(10),
    }
    criterion = post(client, "/criteria", criteria_body, decider).json()["resource"]
    application = post(
        client,
        "/applications",
        {"facility_id": facility["id"], "criteria_id": criterion["id"]},
        headers,
    ).json()["resource"]
    path = f"/applications/{application['id']}"
    # Missing actual evidence prevents submission, without touching affiliation.
    assert post(client, path + "/submit", {"expected_version": 1}, headers).status_code == 422
    evidence_id = db.uid()

    async def capture_controlled_test_evidence():
        async with app.state.database.transaction() as session:
            await session.execute(
                db.evidence.insert().values(
                    id=evidence_id,
                    application_id=application["id"],
                    criterion="TEST-ID",
                    object_key="test-fixture-only",
                    sha256="0" * 64,
                    filename="synthetic-test.txt",
                    media_type="text/plain",
                    size=1,
                    source="ISOLATED TEST FIXTURE",
                    expires_at=stamp(10),
                    scan_status="CLEAN",
                    uploaded_by=application["created_by"],
                    created_at=stamp(),
                )
            )

    run(capture_controlled_test_evidence())
    assert post(client, path + "/submit", {"expected_version": 1}, headers).status_code == 200
    assert (
        post(
            client,
            path + "/assignment",
            {"expected_version": 2, "inspector_id": inspector, "reviewer_id": reviewer},
            headers,
        ).status_code
        == 200
    )
    finding = {
        "expected_version": 3,
        "conflict_declared": False,
        "observed_at": stamp(-1),
        "findings": [
            {
                "criterion": "TEST-ID",
                "observation": "Synthetic evidence examined",
                "outcome": "MET",
                "evidence_ids": [evidence_id],
            }
        ],
    }
    assert post(client, path + "/inspections", finding, headers).status_code == 403
    assert post(client, path + "/inspections", finding, inspector_headers).status_code == 200
    assert (
        post(
            client,
            path + "/recommendation",
            {
                "expected_version": 4,
                "decision": "APPROVE",
                "reason": "Synthetic independent review",
            },
            reviewer_headers,
        ).status_code
        == 200
    )
    decision = {
        "expected_version": 5,
        "decision": "APPROVE",
        "reason": "Synthetic final decision",
        "scope": "Synthetic declared service",
        "conditions": "",
        "effective_at": stamp(-1),
        "expires_at": stamp(10),
        "intent_confirmed": True,
    }
    assert post(client, path + "/decisions", decision, reviewer_headers).status_code == 403
    assert post(client, path + "/decisions", decision, decider).status_code == 200
    assert client.get("/v1/directory").json()["items"] == []
    assert (
        post(
            client,
            f"/facilities/{facility['id']}/verification",
            {
                "expected_version": 2,
                "identity_status": "VERIFIED",
                "statutory_status": "CHECKED",
                "reason": "Synthetic verified source",
            },
            headers,
        ).status_code
        == 200
    )
    assert (
        post(
            client,
            f"/facilities/{facility['id']}/publication",
            {
                "expected_version": 3,
                "action": "PUBLISH",
                "reason": "Synthetic approved public projection",
            },
            headers,
        ).status_code
        == 200
    )
    public = client.get("/v1/directory").json()["items"]
    assert len(public) == 1 and "private_contact" not in public[0] and "created_by" not in public[0]
    assert (
        public[0]["readiness_status"] == "UNKNOWN" and public[0]["capability_status"] == "DECLARED"
    )

    async def inspect_history():
        async with app.state.database.transaction() as session:
            assert await session.scalar(select(func.count()).select_from(db.decisions)) == 1
            assert await session.scalar(select(func.count()).select_from(db.revisions)) >= 12
            assert await session.scalar(select(func.count()).select_from(db.outbox)) >= 12

    run(inspect_history())


def test_invitation_not_reported_sent_without_email_configuration(runtime):
    app, client, _ = runtime
    _, _, headers = staff(app, "PLATFORM_ADMIN")
    response = post(
        client,
        "/invitations",
        {
            "email": "nobody@test.invalid",
            "name": "Synthetic invitee",
            "role": "INSPECTOR",
            "scope_type": "GLOBAL",
            "valid_until": stamp(10),
        },
        headers,
    )
    assert response.status_code == 503

    async def verify_no_partial_invite():
        async with app.state.database.transaction() as session:
            assert await session.scalar(select(func.count()).select_from(db.invitations)) == 0

    run(verify_no_partial_invite())


def test_job_authentication_has_no_public_side_effect(runtime):
    _, client, _ = runtime
    assert client.get("/v1/internal/jobs").status_code == 401


def test_enrolment_activates_once_and_does_not_accept_caller_roles(runtime):
    app, client, _ = runtime
    account_id, raw = db.uid(), "test-only-invitation-with-at-least-32-characters"

    async def invitation():
        async with app.state.database.transaction() as session:
            await session.execute(
                db.accounts.insert().values(
                    id=account_id,
                    email="invite@test.invalid",
                    name="Synthetic invitee",
                    active=False,
                    created_at=stamp(),
                    totp_last_step=-1,
                )
            )
            await session.execute(
                db.invitations.insert().values(
                    id=db.uid(),
                    account_id=account_id,
                    token_hash=digest(raw),
                    expires_at=stamp(1),
                    used=False,
                    created_by="TEST_FIXTURE",
                )
            )

    run(invitation())
    response = client.post(
        "/v1/auth/enrol",
        json={"token": raw, "password": "Test-only-password-2026"},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200, response.text
    secret = response.json()["setup_key"]
    response = client.post(
        "/v1/auth/activate",
        json={"token": raw, "otp": pyotp.TOTP(secret).now()},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200
    assert client.get("/v1/auth/me").json()["grants"] == []
    assert (
        client.post(
            "/v1/auth/activate",
            json={"token": raw, "otp": pyotp.TOTP(secret).now()},
            headers={"Origin": ORIGIN},
        ).status_code
        == 401
    )


def test_revoked_grant_cannot_replay_cached_private_receipt(runtime):
    app, client, _ = runtime
    account_id, headers, _, _, payload = registry(app, client)
    key = db.uid()
    assert post(client, "/facilities", payload, headers, key).status_code == 200

    async def revoke():
        async with app.state.database.transaction() as session:
            await session.execute(
                update(db.grants).where(db.grants.c.account_id == account_id).values(revoked=True)
            )

    run(revoke())
    assert post(client, "/facilities", payload, headers, key).status_code == 404


def test_unconfigured_upload_exclusion_cannot_create_evidence_or_approve_application(runtime):
    app, client, _ = runtime
    assert client.get("/v1/service-capabilities").status_code == 401
    _, headers, _, _, body = registry(app, client)
    capability = client.get("/v1/service-capabilities", headers=headers)
    assert capability.status_code == 200
    assert capability.json()["evidence_upload"]["upload_attempt_permitted"] is False
    assert capability.json()["evidence_upload"]["state"] == "EXCLUDED_SCANNER_UNAVAILABLE"
    assert "s3_secret" not in capability.text and "clamav_host" not in capability.text
    facility = post(client, "/facilities", body, headers).json()["resource"]
    _, _, decider = staff(app, "STANDARDS_DECIDER")
    criteria = post(client, "/criteria", {
        "name": "Synthetic file-gate criteria", "version": "TEST-ONLY", "jurisdiction": "TEST-ONLY",
        "site_type": "COMMUNITY_PRIMARY", "requirements": [{"code": "FILE", "description": "Synthetic required file", "required": True}],
        "adoption_reference": "SYNTHETIC FIXTURE ONLY", "valid_from": stamp(-1), "valid_until": stamp(10),
    }, decider).json()["resource"]
    application = post(client, "/applications", {"facility_id": facility["id"], "criteria_id": criteria["id"]}, headers).json()["resource"]
    response = client.post(f"/v1/applications/{application['id']}/evidence", params={
        "criterion": "FILE", "filename": "synthetic.pdf", "source": "Synthetic test fixture", "expires_at": stamp(1),
    }, content=b"%PDF-1.7\nSYNTHETIC ONLY\n", headers={**headers, "Content-Type": "application/pdf", "Idempotency-Key": db.uid()})
    assert response.status_code == 503
    assert post(client, f"/applications/{application['id']}/submit", {"expected_version": 1}, headers).status_code == 422
    async def count():
        async with app.state.database.transaction() as session:
            return await session.scalar(select(func.count()).select_from(db.evidence))
    assert run(count()) == 0
