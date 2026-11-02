"""
I1 boundary evidence (§25.2): audience/role/MFA/ownership/org matrix, token integrity,
revocation, and fail-closed production configuration (ADR-0002, ADR-0003, ADR-0005).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient
from lw_care_api.config import InsecureConfigurationError
from lw_care_api.main import create_app
from lw_care_api.security.tokens import TokenService

from conftest import make_test_settings

# One representative identity per audience (MFA on, so only audience/role is under test).
IDENTITIES = {
    "lwc:patient": {"sub": "pat-matrix", "roles": ["PATIENT"]},
    "lwc:clinician": {"sub": "dr-adebayo-okonkwo", "roles": ["CLINICIAN_GP"]},
    "lwc:command": {"sub": "exec-01", "roles": ["EXECUTIVE_DIRECTOR", "FINANCE_CONTROLLER"]},
    "lwc:sponsor": {
        "sub": "sponsor-admin-01",
        "roles": ["SPONSOR_ADMIN"],
        "org": "sponsor-loveworld-medicaid",
    },
}
ALL = set(IDENTITIES)

# (method, path, json body, extra headers, audiences that may pass the auth layer)
ROUTES = [
    ("POST", "/v1/care/episodes", {}, {}, {"lwc:patient"}),
    ("POST", "/v1/care/episodes/x/intakes", {}, {}, {"lwc:patient"}),
    ("GET", "/v1/care/episodes/x", None, {}, {"lwc:patient", "lwc:clinician"}),
    ("POST", "/v1/appointments", {}, {"Idempotency-Key": "k"}, {"lwc:patient"}),
    ("GET", "/v1/encounters", None, {}, {"lwc:clinician"}),
    ("POST", "/v1/encounters/x/claim", None, {}, {"lwc:clinician"}),
    ("POST", "/v1/encounters/x/sign", {}, {}, {"lwc:clinician"}),
    ("POST", "/v1/encounters/x/addenda", {}, {}, {"lwc:clinician"}),
    ("GET", "/v1/sponsor/pools/AGR-LW-MEDICAID-NG-2026/report", None, {}, {"lwc:sponsor", "lwc:command"}),
    ("POST", "/v1/care/episodes/x/intelligence-handoff", {}, {}, {"lwc:patient"}),
    ("POST", "/v1/governance/ai-kill-switch", {}, {}, {"lwc:command"}),
    ("GET", "/v1/executive/metrics", None, {}, {"lwc:command"}),
]


@pytest.fixture
def app(test_settings):
    return create_app(test_settings)


@pytest.fixture
def client(app):
    return TestClient(app)


def _headers(app, audience: str, **override: object) -> dict[str, str]:
    ident = {**IDENTITIES[audience], **override}
    token = app.state.token_service.issue(
        sub=ident["sub"],
        audience=audience,
        roles=ident["roles"],
        mfa=ident.get("mfa", True),
        org=ident.get("org"),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("method,path,body,extra,allowed", ROUTES)
def test_route_audience_matrix(app, client, method, path, body, extra, allowed) -> None:
    # No token at all
    res = client.request(method, path, json=body, headers=extra)
    assert res.status_code == 401, (path, "anonymous")

    # Legacy identity headers are ignored entirely
    spoof = {**extra, "X-Actor-Id": "dr-adebayo-okonkwo", "X-Actor-Roles": "CLINICIAN_GP,PLATFORM_SRE"}
    assert client.request(method, path, json=body, headers=spoof).status_code == 401

    for audience in ALL:
        res = client.request(method, path, json=body, headers={**extra, **_headers(app, audience)})
        if audience in allowed:
            assert res.status_code != 401, (path, audience, res.text)
        else:
            assert res.status_code == 401, (path, audience, res.status_code)
            assert res.json()["detail"] == "TOKEN_AUDIENCE_NOT_PERMITTED"


def test_public_routes_remain_open(client) -> None:
    assert client.get("/v1/emergency/guidance").status_code == 200
    assert client.get("/v1/clinicians/slots").status_code == 200
    assert client.get("/v1/auth/jwks").json()["keys"][0]["crv"] == "Ed25519"


# --------------------------------------------------------------------------- token integrity
def test_tampered_foreign_and_expired_tokens_rejected(app, client) -> None:
    good = _headers(app, "lwc:patient")["Authorization"].split(" ")[1]
    head, payload, sig = good.split(".")
    tampered = f"{head}.{payload}.{sig[:-2]}{'A' if sig[-2] != 'A' else 'B'}{sig[-1]}"
    assert client.get("/v1/auth/me", headers={"Authorization": f"Bearer {tampered}"}).json()[
        "detail"
    ] == "TOKEN_INVALID"

    foreign = TokenService(signing_seed_hex="22" * 32, issuer=app.state.settings.token_issuer)
    foreign_tok = foreign.issue(sub="pat-x", audience="lwc:patient", roles=["PATIENT"], mfa=True)
    assert client.get("/v1/auth/me", headers={"Authorization": f"Bearer {foreign_tok}"}).status_code == 401

    expired = app.state.token_service.issue(
        sub="pat-x", audience="lwc:patient", roles=["PATIENT"], mfa=True, ttl=timedelta(seconds=-5)
    )
    res = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert res.json()["detail"] == "TOKEN_EXPIRED"

    none_alg = jwt.encode({"sub": "x", "aud": "lwc:command"}, key=None, algorithm="none")
    assert client.get("/v1/auth/me", headers={"Authorization": f"Bearer {none_alg}"}).status_code == 401


def test_role_smuggled_into_wrong_audience_rejected(app, client) -> None:
    with pytest.raises(ValueError):
        app.state.token_service.issue(
            sub="p", audience="lwc:patient", roles=["PATIENT", "SPONSOR_ADMIN"], mfa=True
        )
    now = datetime.now(timezone.utc)
    forged = jwt.encode(
        {
            "iss": app.state.settings.token_issuer,
            "aud": "lwc:patient",
            "sub": "p",
            "roles": ["PATIENT", "PLATFORM_SRE"],
            "mfa": True,
            "sid": "s",
            "jti": "j",
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=5),
        },
        app.state.token_service._private_key,
        algorithm="EdDSA",
    )
    res = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert res.json()["detail"] == "TOKEN_ROLE_NOT_PERMITTED_FOR_AUDIENCE"


def test_logout_revokes_session(app, client) -> None:
    headers = _headers(app, "lwc:patient")
    assert client.get("/v1/auth/me", headers=headers).status_code == 200
    assert client.post("/v1/auth/logout", headers=headers).status_code == 204
    res = client.get("/v1/auth/me", headers=headers)
    assert res.status_code == 401 and res.json()["detail"] == "TOKEN_REVOKED"


# --------------------------------------------------------------------------- staff controls
def test_clinician_credentials_come_from_roster_not_token(app, client) -> None:
    rostered = client.get("/v1/auth/me", headers=_headers(app, "lwc:clinician")).json()
    assert rostered["clinician_credential_active"] is True
    impostor = client.get(
        "/v1/auth/me", headers=_headers(app, "lwc:clinician", sub="dr-not-credentialed")
    ).json()
    assert impostor["clinician_credential_active"] is False


def test_staff_mutations_require_mfa(app, client) -> None:
    res = client.post(
        "/v1/encounters/x/claim", headers=_headers(app, "lwc:clinician", mfa=False)
    )
    assert res.status_code == 403 and res.json()["detail"] == "DENIED_MFA_REQUIRED"


def test_kill_switch_role_and_mfa(app, client) -> None:
    body = {"enabled": True, "reason": "matrix-test"}
    support = _headers(app, "lwc:command", sub="support-1", roles=["SUPPORT_AGENT"])
    assert client.post("/v1/governance/ai-kill-switch", json=body, headers=support).status_code == 403

    lead_no_mfa = _headers(
        app, "lwc:command", sub="gov-1", roles=["CLINICAL_GOVERNANCE_LEAD"], mfa=False
    )
    assert client.post("/v1/governance/ai-kill-switch", json=body, headers=lead_no_mfa).status_code == 403

    lead = _headers(app, "lwc:command", sub="gov-1", roles=["CLINICAL_GOVERNANCE_LEAD"])
    res = client.post("/v1/governance/ai-kill-switch", json=body, headers=lead)
    assert res.status_code == 200 and res.json()["ai_kill_switch_enabled"] is True


# --------------------------------------------------------------------------- ownership & org
def _create_episode(client, headers, patient_id: str) -> str:
    res = client.post(
        "/v1/care/episodes",
        headers=headers,
        json={
            "patient_id": patient_id,
            "consent_grant_id": "consent-x",
            "chief_complaint_summary": "synthetic",
        },
    )
    assert res.status_code == 200, res.text
    return res.json()["episode_id"]


def test_patient_cannot_act_on_another_patients_episode(app, client) -> None:
    alice = _headers(app, "lwc:patient", sub="pat-alice")
    bob = _headers(app, "lwc:patient", sub="pat-bob")
    episode_id = _create_episode(client, alice, "pat-alice")

    # Bob cannot create an episode in Alice's name, read it, book on it, or attach data to it.
    assert client.post(
        "/v1/care/episodes",
        headers=bob,
        json={"patient_id": "pat-alice", "consent_grant_id": "c", "chief_complaint_summary": "s"},
    ).status_code == 403
    assert client.get(f"/v1/care/episodes/{episode_id}", headers=bob).status_code == 403
    book = client.post(
        "/v1/appointments",
        headers={**bob, "Idempotency-Key": "bob-1"},
        json={"episode_id": episode_id, "slot_id": "slot-ng-gp-001"},
    )
    assert book.status_code == 403
    handoff = client.post(
        f"/v1/care/episodes/{episode_id}/intelligence-handoff",
        headers=bob,
        json={
            "source_scan_id": "s",
            "product_name": "p",
            "extracted_ingredients": [],
            "patient_question": "q",
            "explicit_user_consent_confirmed": True,
        },
    )
    assert handoff.status_code == 403


def test_sponsor_sees_only_own_org_and_no_clinical_data(app, client) -> None:
    path = "/v1/sponsor/pools/AGR-LW-MEDICAID-NG-2026/report"
    own = client.get(path, headers=_headers(app, "lwc:sponsor"))
    assert own.status_code == 200
    assert own.json()["clinical_details_included"] is False

    other_org = _headers(app, "lwc:sponsor", org="sponsor-someone-else")
    missing = client.get("/v1/sponsor/pools/AGR-DOES-NOT-EXIST/report", headers=other_org)
    cross = client.get(path, headers=other_org)
    # Same response for "not yours" and "does not exist": existence is not revealed.
    assert cross.status_code == missing.status_code == 403
    assert cross.json() == missing.json()

    no_org = _headers(app, "lwc:sponsor", org=None)
    assert client.get(path, headers=no_org).status_code == 403

    ops = _headers(app, "lwc:command", sub="ops-1", roles=["CLINICAL_OPS"])
    assert client.get(path, headers=ops).status_code == 403


# --------------------------------------------------------------------------- fail-closed config
def _safe_production(tmp_path: Path, **overrides: object):
    values: dict[str, object] = {
        "environment": "production",
        "database_url": "postgresql+asyncpg://u:p@db.internal:5432/lwc",
        "cors_origins": "https://care.loveworld.org,https://clinician.care.loveworld.org",
        "jwt_signing_key": "a" * 64,
        "session_cookie_secret": "b" * 64,
        "clinical_signing_seed_hex": "c" * 64,
        "audit_hmac_chain_key": "d" * 64,
        "token_signing_seed_hex": "e" * 64,
        "livekit_api_key": "APIrealkey",
        "livekit_api_secret": "f" * 48,
        "livekit_webhook_secret": "g" * 48,
        "paystack_secret_key": "sk_live_realvalue",
        "paystack_webhook_secret": "whsec_realvalue",
    }
    values.update(overrides)
    return make_test_settings(tmp_path, **values)


def test_production_refuses_shipped_defaults(tmp_path) -> None:
    with pytest.raises(InsecureConfigurationError) as exc:
        create_app(make_test_settings(tmp_path, environment="production", token_signing_seed_hex=""))
    message = str(exc.value)
    assert "clinical_signing_seed_hex still uses the shipped default" in message
    assert "database_url points at SQLite" in message
    assert "localhost" in message


@pytest.mark.parametrize(
    "override,expected",
    [
        ({"paystack_secret_key": "sk_live_REPLACE_ME"}, "placeholder"),
        ({"cors_origins": "*"}, "non-production origin"),
        ({"cors_origins": "http://care.loveworld.org"}, "non-HTTPS"),
        ({"token_signing_seed_hex": "abcd"}, "32 bytes"),
    ],
)
def test_production_refuses_each_unsafe_value(tmp_path, override, expected) -> None:
    with pytest.raises(InsecureConfigurationError, match=expected):
        create_app(_safe_production(tmp_path, **override))


def test_safe_production_boots_without_dev_surface_or_synthetic_data(tmp_path) -> None:
    app = create_app(_safe_production(tmp_path))
    client = TestClient(app)
    assert client.post("/v1/auth/dev-token", json={}).status_code in (404, 405)
    assert client.get("/v1/docs").status_code == 404
    # No synthetic clinician or sponsor pool is seeded in production.
    assert client.get("/v1/clinicians/slots").json() == []
    assert app.state.ledger._pools == {}


def test_email_magic_link_flow(app, client) -> None:
    # 1. Invalid email returns 400
    res_bad = client.post("/v1/auth/magic-link/request", json={"email": "invalid-email"})
    assert res_bad.status_code == 400

    # 2. Request magic link
    res = client.post("/v1/auth/magic-link/request", json={"email": "patient@care.loveworld.org"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SENT"
    token = data["verification_token"]
    assert token is not None

    # 3. Verify magic link issues lwc:patient token
    verify_res = client.post("/v1/auth/magic-link/verify", json={"token": token})
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["token_type"] == "Bearer"
    assert verify_data["patient_id"].startswith("pat-")
    access_token = verify_data["access_token"]

    # 4. Token works against protected patient route
    ep_res = client.post(
        "/v1/care/episodes",
        json={
            "patient_id": verify_data["patient_id"],
            "care_service": "GP_REMOTE",
            "consent_grant_id": "consent-01",
            "chief_complaint_summary": "Headache test",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert ep_res.status_code in (200, 201)

    # 5. Single-use enforcement (reused token fails)
    reused = client.post("/v1/auth/magic-link/verify", json={"token": token})
    assert reused.status_code == 401
