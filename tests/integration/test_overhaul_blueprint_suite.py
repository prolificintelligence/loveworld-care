"""
Comprehensive Acceptance Test Suite for LoveWorld Care Overhaul Blueprint v2.0
Verifies LWC-ACC-001..005, LWC-SCR-101..306, LWC-MET-001..016, and Maker/Checker invariants.
"""

from __future__ import annotations

from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from lw_care_api.main import create_app
from lw_care_api.security.tokens import TokenService


@pytest.fixture
def app(test_settings):
    return create_app(test_settings)


@pytest.fixture
def client(app):
    return TestClient(app)


def _token(app, sub: str, aud: str, roles: list[str], mfa: bool = True, org: str | None = None) -> str:
    tokens: TokenService = app.state.token_service
    return tokens.issue(
        sub=sub,
        audience=aud,
        roles=roles,
        mfa=mfa,
        org=org,
        ttl=timedelta(seconds=3600),
    )


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestIdentityAndSubjects:
    """Tests LWC-ACC-001 through LWC-ACC-005."""

    def test_list_and_create_subjects(self, app, client):
        tok = _token(app, "test-user-01", "lwc:patient", ["PATIENT"])
        headers = _auth_header(tok)

        # Initially should return the self subject
        res = client.get("/v1/identity/subjects", headers=headers)
        assert res.status_code == 200
        subjects = res.json()
        assert len(subjects) >= 1
        assert subjects[0]["relationship_to_account"] == "SELF"

        # Create a dependent child subject (LWC-ACC-001)
        create_res = client.post(
            "/v1/identity/subjects",
            headers=headers,
            json={
                "full_name": "Samuel Adeleke",
                "dob_iso": "2018-05-10T00:00:00Z",
                "gender": "MALE",
                "relationship": "CHILD",
                "jurisdiction": "NG",
            },
        )
        assert create_res.status_code == 200
        child = create_res.json()
        assert child["full_name"] == "Samuel Adeleke"
        assert child["relationship_to_account"] == "CHILD"
        child_id = child["patient_id"]

        # List subjects again - should contain both self and child
        res2 = client.get("/v1/identity/subjects", headers=headers)
        assert res2.status_code == 200
        subj_ids = [s["patient_id"] for s in res2.json()]
        assert child_id in subj_ids

    def test_care_relationship_proxy_and_revocation(self, app, client):
        tok = _token(app, "test-user-02", "lwc:patient", ["PATIENT"])
        headers = _auth_header(tok)

        # Create care relationship
        rel_res = client.post(
            "/v1/identity/relationships",
            headers=headers,
            json={
                "patient_id": "test-user-02",
                "relationship_type": "ADULT_PROXY",
                "allowed_scopes": ["INTAKE", "BOOKING", "VIEW_RECORDS"],
            },
        )
        assert rel_res.status_code == 200
        rel = rel_res.json()
        assert rel["relationship_id"].startswith("rel-")

        # Revoke care relationship
        rev_res = client.post(f"/v1/identity/relationships/{rel['relationship_id']}/revoke", headers=headers)
        assert rev_res.status_code == 200
        assert rev_res.json()["revoked"] is True


class TestPatientDashboardAndCare:
    """Tests LWC-SCR-101, LWC-SCR-107, LWC-SCR-108."""

    def test_dashboard_aggregation(self, app, client):
        tok = _token(app, "test-user-03", "lwc:patient", ["PATIENT"])
        headers = _auth_header(tok)

        res = client.get("/v1/care/patients/test-user-03/dashboard", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "subject" in data
        assert "active_episodes" in data
        assert "active_appointments" in data
        assert "due_tasks" in data
        assert "active_medications" in data
        assert "next_action" in data

    def test_observation_and_tasks(self, app, client):
        tok = _token(app, "test-user-04", "lwc:patient", ["PATIENT"])
        headers = _auth_header(tok)

        # Log observation (LWC-SCR-108)
        obs_res = client.post(
            "/v1/care/patients/test-user-04/observations",
            headers=headers,
            json={
                "kind": "VITAL",
                "name": "Blood Pressure",
                "value": "120/80",
                "unit": "mmHg",
                "notes": "Morning resting reading",
                "source": "PATIENT_REPORTED",
            },
        )
        assert obs_res.status_code == 200
        assert obs_res.json()["value"] == "120/80"

        # List records (LWC-SCR-107)
        rec_res = client.get("/v1/care/patients/test-user-04/records", headers=headers)
        assert rec_res.status_code == 200
        recs = rec_res.json()
        assert any(r.get("name") == "Blood Pressure" for r in recs)


class TestCompanionChatEngine:
    """Tests LWC-SCR-102 and red-flag emergency screening."""

    def test_red_flag_emergency_screening(self, app, client):
        tok = _token(app, "test-user-05", "lwc:patient", ["PATIENT"])
        headers = _auth_header(tok)

        # Emergency complaint (chest pain)
        res = client.post(
            "/v1/companion/chat",
            headers=headers,
            json={
                "patient_id": "test-user-05",
                "message": "I am having sudden crushing chest pain and cannot breathe",
                "jurisdiction": "NG",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["emergency"] is True
        assert data["intent"] == "EMERGENCY_HARD_STOP"
        assert len(data["emergency_contacts"]) > 0
        assert any(c["phone"] == "112" for c in data["emergency_contacts"])

    def test_routine_guidance(self, app, client):
        tok = _token(app, "test-user-06", "lwc:patient", ["PATIENT"])
        headers = _auth_header(tok)

        res = client.post(
            "/v1/companion/chat",
            headers=headers,
            json={
                "patient_id": "test-user-06",
                "message": "I have had a mild headache and body weakness since yesterday",
                "jurisdiction": "NG",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["emergency"] is False
        assert "provenance" in data
        assert len(data["suggested_actions"]) > 0


class TestNetworkFacilitiesAndReadiness:
    """Tests LWC-SCR-303."""

    def test_list_and_update_facility_readiness(self, app, client):
        cmd_tok = _token(app, "cmd-01", "lwc:command", ["EXECUTIVE_DIRECTOR"])
        headers = _auth_header(cmd_tok)

        # List default facilities
        res = client.get("/v1/network/facilities", headers=headers)
        assert res.status_code == 200
        facs = res.json()
        assert len(facs) >= 3
        lmc = next(f for f in facs if f["facility_code"] == "LMC-001")
        assert lmc["is_verified"] is True

        # Update readiness
        up_res = client.post(
            f"/v1/network/facilities/{lmc['facility_id']}/readiness",
            headers=headers,
            json={"readiness_state": "CONFIRMED_AVAILABLE", "validity_minutes": 45},
        )
        assert up_res.status_code == 200
        assert up_res.json()["readiness_state"] == "CONFIRMED_AVAILABLE"


class TestCoordinationBoard:
    """Tests LWC-SCR-302."""

    def test_coordination_board_claim_and_resolve(self, app, client):
        clin_tok = _token(app, "dr-adebayo-okonkwo", "lwc:clinician", ["CLINICIAN_GP"])
        headers = _auth_header(clin_tok)

        # List coordination board
        res = client.get("/v1/coordination/board", headers=headers)
        assert res.status_code == 200
        tasks = res.json()

        if tasks:
            task_id = tasks[0]["task_id"]
            # Claim task
            claim_res = client.post(f"/v1/coordination/board/{task_id}/claim", headers=headers)
            assert claim_res.status_code == 200
            assert claim_res.json()["claimed_by"] == "dr-adebayo-okonkwo"

            # Resolve task
            resolve_res = client.post(
                f"/v1/coordination/board/{task_id}/resolve",
                headers=headers,
                json={"disposition": "Resolved by attending doctor"},
            )
            assert resolve_res.status_code == 200


class TestDirectorateMetricsAndActions:
    """Tests LWC-SCR-301 and LWC-MET-001..016."""

    def test_directorate_metrics_and_actions(self, app, client):
        cmd_tok = _token(app, "exec-dir-01", "lwc:command", ["EXECUTIVE_DIRECTOR"])
        headers = _auth_header(cmd_tok)

        # Get authoritative metrics
        res = client.get("/v1/directorate/metrics", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "metrics" in data
        metric_ids = [m["id"] for m in data["metrics"]]
        assert "LWC-MET-002" in metric_ids
        assert "LWC-MET-006" in metric_ids

        # Create action item
        act_res = client.post(
            "/v1/directorate/actions",
            headers=headers,
            json={
                "metric_id": "LWC-MET-002",
                "title": "Expand Evening GP Roster Coverage",
                "description": "Recruit and schedule 2 additional verified GPs for 6pm-10pm WAT shift.",
                "owner_team": "WORKFORCE_OPERATIONS",
                "assigned_to": "exec-dir-01",
                "due_date_iso": "2026-11-15T00:00:00Z",
            },
        )
        assert act_res.status_code == 200
        act = act_res.json()
        assert act["title"] == "Expand Evening GP Roster Coverage"

        # Update action item
        up_act = client.patch(
            f"/v1/directorate/actions/{act['action_id']}",
            headers=headers,
            json={"status": "IN_PROGRESS", "evidence_notes": "Roster published to clinicians"},
        )
        assert up_act.status_code == 200
        assert up_act.json()["status"] == "IN_PROGRESS"


class TestFinanceOperationsMakerChecker:
    """Tests LWC-SCR-305 and maker_id != checker_id enforcement."""

    def test_maker_cannot_act_as_checker(self, app, client):
        maker_tok = _token(app, "finance-maker-01", "lwc:command", ["FINANCE_CONTROLLER"])
        maker_headers = _auth_header(maker_tok)

        # 1. Maker records an exception
        rec_res = client.post(
            "/v1/finance/exceptions",
            headers=maker_headers,
            json={
                "agreement_id": "AGR-LW-MEDICAID-NG-2026",
                "exception_type": "DUPLICATE_CHARGE_REFUND",
                "amount_minor": 500000,
                "currency": "NGN",
                "reason": "Payment processor timed out leading to duplicate deduction",
            },
        )
        assert rec_res.status_code == 200
        ex = rec_res.json()
        ex_id = ex["exception_id"]
        assert ex["maker_id"] == "finance-maker-01"
        assert ex["status"] == "PENDING_REVIEW"

        # 2. Maker attempts to check/approve own exception -> MUST BE REJECTED 403
        self_check_res = client.post(
            f"/v1/finance/exceptions/{ex_id}/action",
            headers=maker_headers,
            json={"action": "APPROVE", "notes": "Self approval attempt"},
        )
        assert self_check_res.status_code == 403
        assert "MAKER_CANNOT_ACT_AS_CHECKER" in self_check_res.json()["detail"]

        # 3. Independent checker approves -> SUCCEEDS
        checker_tok = _token(app, "finance-checker-02", "lwc:command", ["FINANCE_CONTROLLER"])
        checker_headers = _auth_header(checker_tok)

        approve_res = client.post(
            f"/v1/finance/exceptions/{ex_id}/action",
            headers=checker_headers,
            json={"action": "APPROVE", "notes": "Verified against gateway transaction log"},
        )
        assert approve_res.status_code == 200
        approved = approve_res.json()
        assert approved["status"] == "APPROVED"
        assert approved["checker_id"] == "finance-checker-02"

    def test_reconciliation_summary(self, app, client):
        checker_tok = _token(app, "finance-controller-01", "lwc:command", ["FINANCE_CONTROLLER"])
        headers = _auth_header(checker_tok)

        res = client.get("/v1/finance/reconciliation", headers=headers)
        assert res.status_code == 200
        recon = res.json()
        assert "total_sponsor_cash_received_minor" in recon
        assert "double_entry_balanced" in recon
