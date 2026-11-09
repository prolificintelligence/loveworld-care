"""Synthetic patient/family journeys; no adopted policy or external email success is invented."""

import pyotp
import pytest
from lw_care_api.platform import db
from lw_care_api.platform.clinical import tables as clinical
from lw_care_api.platform.personal import tables as t
from lw_care_api.platform.security import issue_session
from sqlalchemy import func, select, update
from test_platform_clinical import ORIGIN, run, stamp
from test_platform_clinical import journey as clinical_fixture


class PersonalJourney:
    def __init__(self, care):
        self.care, self.app, self.client, self.actors = care, care.app, care.client, care.actors

    def get(self, path, actor="person"):
        return self.client.get("/v1/personal" + path, headers=self.actors[actor][1])

    def post(self, path, body, actor="person", key=None):
        return self.client.post(
            "/v1/personal" + path,
            json=body,
            headers=self.actors[actor][1] | {"Origin": ORIGIN, "Idempotency-Key": key or db.uid()},
        )

    def create(self, path, body, actor="person", key=None):
        response = self.post(path, body, actor, key)
        assert response.status_code == 200, (path, response.text)
        return response.json()["resource"]

    def patient(self, name="Synthetic personal patient"):
        return self.care.create(
            "/patients",
            {
                "display_name": name,
                "provisional": False,
                "identity_evidence": "Synthetic identity verification",
                "sex": "UNKNOWN",
            },
        )

    def claim(self, actor="person", relation="SELF"):
        return self.create(
            "/links",
            {
                "facility_id": self.care.facility,
                "relationship": relation,
                "patient_reference": "Synthetic presented registration reference",
                "relationship_basis": "Synthetic actual identity or representative evidence",
            },
            actor,
        )

    def review_body(self, patient, expected=1, permissions=None):
        return {
            "expected_version": expected,
            "decision": "APPROVE",
            "patient_id": patient["id"],
            "expected_patient_version": patient["version"],
            "permissions": permissions or ["READ", "REQUEST", "SHARE"],
            "valid_until": stamp(5),
            "review_at": stamp(2),
            "authority_type": "SYNTHETIC_ONLY",
            "evidence_examined": "Synthetic independently checked identity and authority",
            "policy_reference": "Synthetic policy for engineering tests only",
            "reason": "Synthetic independent review",
            "intent_confirmed": True,
        }

    def link(self, patient, actor="person", relation="SELF", permissions=None):
        claim = self.claim(actor, relation)
        return self.create(
            f"/staff/links/{claim['id']}/review",
            self.review_body(patient, permissions=permissions),
            "records",
        )

    def release(self, link, note, **changes):
        return self.create(
            f"/staff/links/{link['id']}/releases",
            {
                "source_id": note["id"],
                "expected_source_version": note["version"],
                "kind": "PLAN",
                "title": "Reviewed care plan",
                "readable_text": "Synthetic patient-readable follow-up guidance",
                "release_basis": "Synthetic actual release decision",
                "intent_confirmed": True,
                **changes,
            },
            "clinician",
        )

    def routing(self):
        service = self.create(
            f"/staff/{self.care.facility}/services",
            {
                "name": "Synthetic non-urgent care team",
                "primary_id": self.actors["clinician"][0],
                "fallback_id": self.actors["outsider"][0],
                "response_minutes": 60,
                "valid_until": stamp(3),
                "policy_reference": "Synthetic staffed response commitment",
                "intent_confirmed": True,
            },
            "governor",
        )
        for actor in ("clinician", "outsider"):
            service = self.create(
                f"/staff/services/{service['id']}/actions",
                {
                    "expected_version": service["version"],
                    "action": "ACCEPT_DUTY",
                    "reason": "Synthetic personal duty acceptance",
                },
                actor,
            )
        return service


@pytest.fixture
def personal(tmp_path):
    for care in clinical_fixture.__wrapped__(tmp_path):

        async def seed(care=care):
            async with care.app.state.database.transaction() as session:
                for name in ("person", "caregiver", "other"):
                    identifier = db.uid()
                    await session.execute(
                        db.accounts.insert().values(
                            id=identifier,
                            name="Synthetic " + name,
                            email=name + "@synthetic.invalid",
                            active=True,
                            totp_last_step=-1,
                            created_at=db.now(),
                        )
                    )
                    token = await issue_session(session, identifier, 30)
                    care.actors[name] = (identifier, {"Authorization": "Bearer " + token})

        run(seed())
        yield PersonalJourney(care)


def test_personal_enrolment_verifies_email_and_mfa_without_granting_staff_roles(personal):
    j = personal
    j.app.state.settings.resend_api_key = "synthetic-not-a-sending-key"
    j.app.state.settings.email_from = "synthetic@example.invalid"
    payload = {"email": "New.Person@synthetic.invalid", "name": "Synthetic new person"}
    response = j.client.post("/v1/personal/enrolment", json=payload, headers={"Origin": ORIGIN})
    assert response.status_code == 202 and "account_id" not in response.json()
    assert (
        j.client.post("/v1/personal/enrolment", json=payload, headers={"Origin": ORIGIN}).json()
        == response.json()
    )
    assert (
        j.client.post(
            "/v1/personal/enrolment",
            json=payload | {"email": "not-an-email"},
            headers={"Origin": ORIGIN},
        ).status_code
        == 422
    )

    async def token():
        async with j.app.state.database.transaction() as session:
            account = await session.scalar(
                select(db.accounts.c.id).where(db.accounts.c.email == payload["email"].lower())
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(db.grants)
                    .where(db.grants.c.account_id == account)
                )
                == 0
            )
            queue = (
                (await session.execute(select(db.outbox).where(db.outbox.c.resource_id == account)))
                .mappings()
                .one()
            )
            assert (
                queue["delivered_at"] is None
                and queue["payload"]["purpose"] == "PERSONAL_ENROLMENT"
            )
            return j.app.state.box.decrypt(queue["payload"]["token_ciphertext"])

    raw = run(token())
    setup = j.client.post(
        "/v1/auth/enrol",
        json={"token": raw, "password": "Synthetic private password 12345"},
        headers={"Origin": ORIGIN},
    )
    assert setup.status_code == 200
    active = j.client.post(
        "/v1/auth/activate",
        json={"token": raw, "otp": pyotp.TOTP(setup.json()["setup_key"]).now()},
        headers={"Origin": ORIGIN},
    )
    assert active.status_code == 200
    context = j.client.get("/v1/personal/context").json()
    assert context["items"] == [] and context["account"]["grants"] == []
    assert j.client.get(f"/v1/clinical/{j.care.facility}/staff").status_code == 403


def test_link_review_is_independent_subject_bound_and_expires_after_identity_change(personal):
    j = personal
    patient = j.patient()
    claim = j.claim()
    assert j.get(f"/links/{claim['id']}/care").status_code == 403
    assert (
        j.post(f"/staff/links/{claim['id']}/review", j.review_body(patient), "admin").status_code
        == 403
    )
    link = j.create(f"/staff/links/{claim['id']}/review", j.review_body(patient), "records")
    assert j.get(f"/links/{link['id']}/care", "other").status_code == 404
    assert j.get(f"/links/{link['id']}/care").status_code == 200
    duplicate = j.claim("other")
    assert (
        j.post(
            f"/staff/links/{duplicate['id']}/review", j.review_body(patient), "records"
        ).status_code
        == 409
    )
    own = j.claim("records")
    assert (
        j.post(f"/staff/links/{own['id']}/review", j.review_body(patient), "records").status_code
        == 403
    )
    corrected = j.care.create(
        f"/patients/{patient['id']}/corrections",
        {
            "expected_version": patient["version"],
            "display_name": "Synthetic corrected identity",
            "provisional": False,
            "identity_evidence": "Synthetic identity verification",
            "sex": "UNKNOWN",
            "reason": "Synthetic corrected identifying information",
        },
    )
    assert corrected["version"] > patient["version"]
    assert j.get(f"/links/{link['id']}/care").status_code == 403
    assert not next(r for r in j.get("/context").json()["items"] if r["id"] == link["id"])["usable"]


def test_representative_scope_is_specific_and_revocation_blocks_replays(personal):
    j = personal
    patient = j.patient()
    own = j.link(patient)
    share = j.create(
        f"/links/{own['id']}/share",
        {
            "recipient_account_id": j.actors["caregiver"][0],
            "relationship_basis": "Synthetic patient request for bounded support",
            "intent_confirmed": True,
        },
    )
    assert j.get(f"/links/{share['id']}/care", "caregiver").status_code == 403
    assert (
        j.post(f"/staff/links/{share['id']}/review", j.review_body(patient), "records").status_code
        == 422
    )
    proxy = j.create(
        f"/staff/links/{share['id']}/review",
        j.review_body(patient, permissions=["READ"]),
        "records",
    )
    assert j.get(f"/links/{proxy['id']}/services", "caregiver").status_code == 403
    assert j.get(f"/links/{own['id']}/care", "caregiver").status_code == 404
    patient, encounter = j.care.encounter(patient)
    note = j.care.note(patient, encounter)
    j.release(own, note)
    assert j.get(f"/links/{proxy['id']}/care", "caregiver").json()["items"] == []
    j.release(proxy, note)
    assert len(j.get(f"/links/{proxy['id']}/care", "caregiver").json()["items"]) == 1
    j.create(
        f"/links/{proxy['id']}/revoke",
        {"expected_version": proxy["version"], "reason": "Synthetic self-authorised revocation"},
    )
    assert j.get(f"/links/{proxy['id']}/care", "caregiver").status_code == 403
    assert j.get(f"/links/{proxy['id']}/access-history", "caregiver").status_code == 403


def test_releases_never_expose_raw_notes_and_amendments_withdraw_obsolete_views(personal):
    j = personal
    patient, encounter = j.care.encounter(j.patient())
    link = j.link(patient)
    note = j.care.note(patient, encounter)
    released = j.release(link, note)
    care = j.get(f"/links/{link['id']}/care")
    assert care.status_code == 200 and care.json()["items"][0]["id"] == released["id"]
    assert "Synthetic clinical narrative" not in care.text
    amended = j.care.note(
        patient, encounter, amends_id=note["id"], amendment_reason="Synthetic source correction"
    )
    assert j.get(f"/links/{link['id']}/care").json()["items"] == []
    assert (
        j.post(
            f"/staff/links/{link['id']}/releases",
            {
                "source_id": note["id"],
                "expected_source_version": note["version"],
                "kind": "PLAN",
                "title": "Obsolete source",
                "readable_text": "Synthetic obsolete summary",
                "release_basis": "Synthetic denied release",
                "intent_confirmed": True,
            },
            "clinician",
        ).status_code
        == 409
    )
    j.release(link, amended)
    restricted = j.care.note(patient, encounter, confidentiality="RESTRICTED")
    denied = j.post(
        f"/staff/links/{link['id']}/releases",
        {
            "source_id": restricted["id"],
            "expected_source_version": restricted["version"],
            "kind": "PLAN",
            "title": "Restricted source",
            "readable_text": "Synthetic restricted summary",
            "release_basis": "Synthetic denied release",
            "intent_confirmed": True,
        },
        "clinician",
    )
    assert denied.status_code == 403


def test_owned_care_requests_preserve_receipts_handover_and_responsibility_after_revocation(
    personal,
):
    j = personal
    link = j.link(j.patient())
    service = j.routing()
    key = db.uid()
    body = {
        "service_id": service["id"],
        "kind": "SELF_REPORT",
        "text": "Synthetic self-report, not verified adherence",
    }
    created = j.post(f"/links/{link['id']}/requests", body, key=key)
    assert created.status_code == 200
    assert j.post(f"/links/{link['id']}/requests", body, key=key).json() == created.json()
    request = created.json()["resource"]
    assert request["state"] == "SUBMITTED" and request["accepted_at"] is None
    assert j.get(f"/requests/{request['id']}", "other").status_code == 404
    assert j.get(f"/staff/requests/{request['id']}", "admin").status_code == 404

    def action(action, actor="clinician", **extra):
        return j.create(
            f"/staff/requests/{request['id']}/actions",
            {
                "expected_version": request["version"],
                "action": action,
                "reason": "Synthetic actual human care action",
                **extra,
            },
            actor,
        )

    request = action("ACCEPT")
    request = action("OFFER_HANDOVER", successor_id=j.actors["outsider"][0])
    assert request["owner_name"] == "Synthetic clinician" and request["handover_pending"]
    request = action("ACCEPT_HANDOVER", "outsider")
    assert request["owner_name"] == "Synthetic outsider"
    request = action("RESPOND", "outsider", text="Synthetic actual human response")
    detail = j.get(f"/requests/{request['id']}").json()
    assert {r["sender_type"] for r in detail["items"]} == {"PATIENT_REPORTED", "HUMAN_CARE_TEAM"}
    j.create(
        f"/links/{link['id']}/revoke",
        {"expected_version": link["version"], "reason": "Synthetic access withdrawal"},
    )
    assert j.post(f"/links/{link['id']}/requests", body, key=key).status_code == 403
    assert j.get(f"/requests/{request['id']}").status_code == 403
    assert j.get(f"/staff/requests/{request['id']}", "outsider").status_code == 200
    request = action(
        "CLOSE", "outsider", text="Synthetic closure with retained responsibility evidence"
    )
    assert request["state"] == "CLOSED"


def test_unaccepted_or_paused_services_cannot_receive_and_preferences_remain_account_scoped(
    personal,
):
    j = personal
    link = j.link(j.patient())
    service = j.routing()
    assert len(j.get(f"/links/{link['id']}/services").json()["items"]) == 1
    j.create(
        f"/staff/services/{service['id']}/actions",
        {
            "expected_version": service["version"],
            "action": "PAUSE",
            "reason": "Synthetic recipient service pause",
        },
        "outsider",
    )
    assert j.get(f"/links/{link['id']}/services").json()["items"] == []
    assert (
        j.post(
            f"/links/{link['id']}/requests",
            {"service_id": service["id"], "kind": "CARE", "text": "Synthetic care request"},
        ).status_code
        == 409
    )
    j.create("/preferences", {"expected_version": 0, "in_app_reminders": True})
    assert j.get("/context").json()["preferences"]["in_app_reminders"]
    assert not j.get("/context", "other").json()["preferences"]["in_app_reminders"]
    assert (
        j.post("/preferences", {"expected_version": 0, "in_app_reminders": False}).status_code
        == 412
    )


def test_expiry_and_staff_revocation_take_effect_without_changing_clinical_sources(personal):
    j = personal
    patient = j.patient()
    link = j.link(patient)

    async def expire():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                update(t.links).where(t.links.c.id == link["id"]).values(review_at=stamp(-1))
            )

    run(expire())
    assert j.get(f"/links/{link['id']}/care").status_code == 403

    async def revoke():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                update(db.grants)
                .where(db.grants.c.account_id == j.actors["records"][0])
                .values(revoked=True)
            )
            assert (
                await session.scalar(
                    select(clinical.records.c.version).where(clinical.records.c.id == patient["id"])
                )
                == patient["version"]
            )

    run(revoke())
    assert j.get(f"/staff/{j.care.facility}/links", "records").status_code == 403


def test_named_fallback_can_personally_accept_after_owner_is_restricted(personal):
    j = personal
    link = j.link(j.patient())
    service = j.routing()
    request = j.create(
        f"/links/{link['id']}/requests",
        {"service_id": service["id"], "kind": "CARE", "text": "Synthetic actual care request"},
    )
    body = {
        "expected_version": request["version"],
        "action": "ACCEPT",
        "reason": "Synthetic personal acceptance",
    }
    request = j.create(f"/staff/requests/{request['id']}/actions", body, "clinician")

    async def restrict():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                update(db.accounts)
                .where(db.accounts.c.id == j.actors["clinician"][0])
                .values(active=False)
            )

    run(restrict())
    request = j.create(
        f"/staff/requests/{request['id']}/actions",
        body | {"expected_version": request["version"]},
        "outsider",
    )
    assert request["owner_name"] == "Synthetic outsider" and request["state"] == "ACCEPTED"
