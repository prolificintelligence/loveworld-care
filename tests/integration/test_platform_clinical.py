"""Synthetic EMR journeys against durable isolated databases, without provider mocks."""

import asyncio
import base64
import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from lw_care_api.platform import db
from lw_care_api.platform.clinical import store as s
from lw_care_api.platform.clinical import tables as t
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.main import create_platform_app
from lw_care_api.platform.security import issue_session
from sqlalchemy import select, update

ORIGIN = "http://localhost:3004"
CAPABILITIES = [
    "REGISTER",
    "CARE",
    "NURSING",
    "PRESCRIBE",
    "PHARMACY",
    "DIAGNOSTICS",
    "PROCEDURE",
    "RECORDS",
    "SENSITIVE",
    "FINANCE",
    "CASHIER",
]


def stamp(days=0):
    return (datetime.now(UTC) + timedelta(days=days)).isoformat(timespec="microseconds")


def run(value):
    return asyncio.run(value)


def coding(display="Synthetic test concept"):
    return {"system": "urn:lwh:test-only", "code": "TEST", "display": display, "version": "test-1"}


class Journey:
    def __init__(self, app, client, facility, actors):
        self.app, self.client, self.facility, self.actors = app, client, facility, actors
        self.prefix = "/v1/clinical/" + facility

    def post(self, path, body, actor="clinician", key=None):
        return self.client.post(
            self.prefix + path,
            json=body,
            headers={
                **self.actors[actor][1],
                "Origin": ORIGIN,
                "Idempotency-Key": key or db.uid(),
            },
        )

    def create(self, path, body, actor="clinician", key=None):
        response = self.post(path, body, actor, key)
        assert response.status_code == 200, (path, response.text)
        return response.json()["resource"]

    def get(self, path, actor="clinician"):
        return self.client.get(self.prefix + path, headers=self.actors[actor][1])

    def patient(self, name="Synthetic patient", identifier=None):
        return self.create(
            "/patients",
            {
                "display_name": name,
                "provisional": True,
                "sex": "UNKNOWN",
                "local_identifier": identifier,
            },
        )

    def encounter(self, patient=None):
        patient = patient or self.patient()
        result = self.create(
            "/encounters",
            {
                "patient_id": patient["id"],
                "service": "GENERAL",
                "encounter_type": "AMBULATORY",
                "arrival": "EMERGENCY",
                "complaint": "Synthetic assessment only",
                "occurred_at": stamp(-1),
            },
        )
        return patient, result

    def context(self, patient, encounter):
        return {
            "patient_id": patient["id"],
            "encounter_id": encounter["id"],
            "occurred_at": stamp(-1),
        }

    def note(self, patient, encounter, **extra):
        note = self.create(
            "/notes",
            {
                **self.context(patient, encounter),
                "note_type": "CONSULTATION",
                "narrative": "Synthetic clinical narrative for verification",
                "source": "Synthetic actual test author",
                **extra,
            },
        )
        return self.create(
            f"/notes/{note['id']}/sign",
            {
                "patient_id": patient["id"],
                "expected_version": 1,
                "reason": "Test signing intent",
                "intent_confirmed": True,
            },
        )

    def order(self, patient, encounter, order_type="LABORATORY"):
        order = self.create(
            "/orders",
            {
                **self.context(patient, encounter),
                "order_type": order_type,
                "code": coding(),
                "clinical_question": "Synthetic diagnostic question",
                "priority": "MANUAL_TEST_PRIORITY",
                "result_owner_id": self.actors["clinician"][0],
            },
        )
        order = self.create(
            f"/orders/{order['id']}/actions",
            {
                "patient_id": patient["id"],
                "expected_version": 1,
                "action": "SIGN",
                "reason": "Actual test order intent",
                "intent_confirmed": True,
            },
        )
        return self.create(
            f"/orders/{order['id']}/actions",
            {
                "patient_id": patient["id"],
                "expected_version": 2,
                "action": "ACCEPT",
                "reason": "Synthetic department acceptance",
                "intent_confirmed": True,
            },
            "diagnostics",
        )

    def medicine(self, patient, encounter):
        product = self.create(
            "/products",
            {
                "code": {**coding("NON-CLINICAL TEST PRODUCT"), "code": db.uid()},
                "ingredient": "Synthetic non-clinical ingredient",
                "form": "TEST_FORM",
                "strength": "TEST_STRENGTH",
                "strength_unit": "TEST_UNIT",
                "permitted_routes": ["TEST_ROUTE"],
                "formulary_reference": "TEST-ONLY approval evidence",
                "valid_until": stamp(10),
            },
            "pharmacy",
        )
        medicine = self.create(
            "/medications",
            {
                **self.context(patient, encounter),
                "product_id": product["id"],
                "indication": "Synthetic test",
                "dose": "1",
                "dose_unit": "TEST_UNIT",
                "route": "TEST_ROUTE",
                "timing": "TEST_ONLY_MANUAL_SLOT",
                "starts_at": stamp(-2),
                "stops_at": stamp(2),
                "substitution": "NOT_PERMITTED",
                "manual_safety_review": "Synthetic documented manual review",
                "reconciliation": "Synthetic medicine reconciliation",
            },
        )
        for version, action, actor in [(1, "SIGN", "clinician"), (2, "VERIFY", "pharmacy")]:
            medicine = self.create(
                f"/medications/{medicine['id']}/actions",
                {
                    "patient_id": patient["id"],
                    "expected_version": version,
                    "action": action,
                    "reason": "Synthetic actual check",
                    "safety_review": "TEST ONLY manual safety check",
                    "intent_confirmed": True,
                },
                actor,
            )
        return product, medicine


@pytest.fixture
def journey(tmp_path):
    cfg = PlatformSettings(
        environment="test",
        enforce_activation_dossiers=False,
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'clinical.db').as_posix()}",
        data_key_hex="b2" * 32,
        web_origin=ORIGIN,
        authority_node_id=db.uid(),
    )
    app = create_platform_app(cfg)
    run(app.state.database.migrate())
    facility, region, zone, operator = db.uid(), db.uid(), db.uid(), db.uid()
    actors = {}

    async def seed():
        async with app.state.database.transaction() as session:
            for label, role in [
                ("governor", "CLINICAL_GOVERNOR"),
                ("admin", "PLATFORM_ADMIN"),
                ("clinician", "CLINICAL_STAFF"),
                ("nurse", "CLINICAL_STAFF"),
                ("pharmacy", "CLINICAL_STAFF"),
                ("diagnostics", "CLINICAL_STAFF"),
                ("outsider", "CLINICAL_STAFF"),
                ("records", "CLINICAL_STAFF"),
            ]:
                identifier = db.uid()
                await session.execute(
                    db.accounts.insert().values(
                        id=identifier,
                        email=f"{label}@synthetic.invalid",
                        name="Synthetic " + label,
                        active=True,
                        totp_last_step=-1,
                        created_at=db.now(),
                    )
                )
                await session.execute(
                    db.grants.insert().values(
                        id=db.uid(),
                        account_id=identifier,
                        role=role,
                        scope_type="GLOBAL" if role != "CLINICAL_STAFF" else "FACILITY",
                        scope_id="GLOBAL" if role != "CLINICAL_STAFF" else facility,
                        valid_from=stamp(-2),
                        valid_until=stamp(20),
                        revoked=False,
                        grantor="TEST_FIXTURE",
                    )
                )
                token = await issue_session(session, identifier, 30)
                actors[label] = (identifier, {"Authorization": "Bearer " + token})
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
            await session.execute(
                db.facilities.insert().values(
                    id=facility,
                    operator_id=operator,
                    zone_id=zone,
                    name="Synthetic facility",
                    site_type="INPATIENT_HOSPITAL",
                    ownership="MEMBER_OWNED",
                    jurisdiction="TEST",
                    external_reference=facility,
                    address="Synthetic",
                    public_contact="test@synthetic.invalid",
                    private_contact="test@synthetic.invalid",
                    services=["GENERAL"],
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
        j = Journey(app, client, facility, actors)
        j.create(
            "/activation",
            {
                "expected_version": 0,
                "services": ["GENERAL", "PHARMACY"],
                "policy_reference": "Synthetic site activation, never operational approval",
                "manual_medicine_policy": "Synthetic adopted test manual process",
                "valid_from": stamp(-2),
                "valid_until": stamp(15),
                "intent_confirmed": True,
            },
            "governor",
        )
        for name, capabilities in [
            ("clinician", CAPABILITIES),
            ("nurse", ["NURSING", "REGISTER"]),
            ("pharmacy", ["PHARMACY"]),
            ("diagnostics", ["DIAGNOSTICS"]),
            ("outsider", ["CARE", "REGISTER"]),
            ("records", ["RECORDS"]),
        ]:
            j.create(
                "/privileges",
                {
                    "account_id": actors[name][0],
                    "services": ["GENERAL", "PHARMACY"],
                    "capabilities": capabilities,
                    "professional_reference": "Synthetic verification only",
                    "valid_from": stamp(-1),
                    "valid_until": stamp(10),
                    "intent_confirmed": True,
                },
                "governor",
            )
        yield j


def test_administration_never_implies_chart_authority(journey):
    j = journey
    patient, encounter = j.encounter()
    note = j.note(patient, encounter)
    for actor in ("admin", "governor", "outsider", "pharmacy", "diagnostics"):
        assert j.get(f"/records/{note['id']}", actor).status_code == 403
        assert j.get(f"/patients/{patient['id']}/chart", actor).status_code == 403
    assert (
        j.post(
            "/privileges",
            {
                "account_id": j.actors["governor"][0],
                "services": ["GENERAL"],
                "capabilities": ["CARE"],
                "professional_reference": "Unacceptable self approval",
                "valid_from": stamp(-1),
                "valid_until": stamp(2),
                "intent_confirmed": True,
            },
            "governor",
        ).status_code
        == 403
    )


def test_patient_search_provisional_identity_and_encryption(journey):
    j = journey
    patient = j.patient("Synthetic ConfidentialPerson", "LOCAL-TEST-0001")
    found = j.post("/patient-search", {"query": "ConfidentialPerson"})
    assert found.status_code == 200 and found.json()["items"][0]["id"] == patient["id"]
    assert (
        j.post(
            "/patients",
            {
                "display_name": "Other person",
                "provisional": True,
                "sex": "UNKNOWN",
                "local_identifier": "LOCAL-TEST-0001",
            },
        ).status_code
        == 409
    )
    assert j.post("/patient-search", {"query": "*"}).status_code == 422

    async def inspect():
        async with j.app.state.database.transaction() as session:
            raw = (
                (await session.execute(select(t.records).where(t.records.c.id == patient["id"])))
                .mappings()
                .one()
            )
            assert "ConfidentialPerson" not in str(dict(raw))
            operations = (await session.execute(select(t.operations))).mappings().all()
            assert "ConfidentialPerson" not in str(operations)

    run(inspect())


def test_signed_note_addendum_context_conflict_and_restart(journey):
    j = journey
    patient, encounter = j.encounter()
    other = j.patient("Separate synthetic person")
    body = {
        **j.context(patient, encounter),
        "note_type": "CONSULTATION",
        "narrative": "Original synthetic evidence",
        "source": "Actual test clinician",
    }
    note = j.create("/notes", body)
    assert (
        j.post(
            f"/notes/{note['id']}/sign",
            {
                "patient_id": other["id"],
                "expected_version": 1,
                "reason": "Wrong context test",
                "intent_confirmed": True,
            },
        ).status_code
        == 409
    )
    signed = j.create(
        f"/notes/{note['id']}/sign",
        {
            "patient_id": patient["id"],
            "expected_version": 1,
            "reason": "Actual intent",
            "intent_confirmed": True,
        },
    )
    assert signed["status"] == "SIGNED"
    assert (
        j.post(
            f"/notes/{note['id']}/draft",
            {**body, "expected_version": 2, "narrative": "Attempted overwrite"},
        ).status_code
        == 409
    )
    addendum = j.note(
        patient, encounter, amends_id=note["id"], amendment_reason="Preserve prior signed evidence"
    )
    assert addendum["data"]["amends_id"] == note["id"]
    history = j.get(f"/records/{note['id']}/history").json()
    previous = "0" * 64
    for item in history["items"]:
        assert item["previous_hash"] == previous
        assert (
            hashlib.sha256(s.canonical(item["source"]).encode()).hexdigest() == item["payload_hash"]
        )
        s.signing_key(j.app.state.settings).public_key().verify(
            base64.b64decode(item["signature"]), bytes.fromhex(item["payload_hash"])
        )
        previous = item["payload_hash"]
    restarted = create_platform_app(j.app.state.settings)
    with TestClient(restarted) as client:
        response = client.get(j.prefix + f"/records/{note['id']}", headers=j.actors["clinician"][1])
        assert (
            response.status_code == 200
            and response.json()["data"]["narrative"] == body["narrative"]
        )


def test_clinical_idempotency_reauth_and_stale_versions(journey):
    j = journey
    body = {"display_name": "Retry synthetic identity", "provisional": True, "sex": "UNKNOWN"}
    key = db.uid()
    first = j.post("/patients", body, key=key)
    assert first.status_code == 200
    assert j.post("/patients", body, key=key).json() == first.json()
    assert (
        j.post("/patients", {**body, "display_name": "Different request"}, key=key).status_code
        == 409
    )
    privilege = next(
        p
        for p in j.get("/privileges", "governor").json()["items"]
        if p["account_id"] == j.actors["clinician"][0]
    )
    j.create(f"/privileges/{privilege['id']}/revoke", {}, "governor")
    assert j.post("/patients", body, key=key).status_code == 403


def test_diagnostic_chain_correction_and_result_after_discharge(journey):
    j = journey
    patient, encounter = j.encounter()
    order = j.order(patient, encounter)
    specimen = j.create(
        "/specimens",
        {
            **j.context(patient, encounter),
            "order_id": order["id"],
            "accession": "SYNTHETIC-ACCESSION",
            "specimen_type": "TEST_ONLY",
            "label_check": "Actual synthetic identity match",
            "condition": "Synthetic condition evidence",
        },
        "diagnostics",
    )
    for action, version in [("COLLECT", 1), ("RECEIVE", 2), ("ANALYSE", 3)]:
        specimen = j.create(
            f"/specimens/{specimen['id']}/actions",
            {
                "patient_id": patient["id"],
                "expected_version": version,
                "action": action,
                "reason": "Synthetic actual chain event",
                "evidence": "Synthetic actual chain evidence",
                "occurred_at": stamp(-1),
            },
            "diagnostics",
        )
    summary = j.note(patient, encounter, note_type="DISCHARGE")
    j.create(
        f"/encounters/{encounter['id']}/complete",
        {
            "patient_id": patient["id"],
            "expected_version": 1,
            "reason": "Synthetic disposition",
            "disposition": "HOME",
            "signed_summary_id": summary["id"],
            "instructions": "Synthetic instructions",
            "medication_reconciliation": "Synthetic reconciliation",
            "follow_up_plan": "Synthetic result owner remains assigned",
            "occurred_at": stamp(-1),
            "intent_confirmed": True,
        },
    )
    observation = {
        **j.context(patient, encounter),
        "code": coding(),
        "value_decimal": "1",
        "unit": "TEST_UNIT",
        "method": "Synthetic method",
        "source": "Synthetic diagnostic device",
        "verification": "CLINICIAN_RECORDED",
    }
    body = {
        **j.context(patient, encounter),
        "order_id": order["id"],
        "specimen_id": specimen["id"],
        "observations": [observation],
        "interpretation": "Synthetic report",
        "method": "Synthetic test method",
        "reference_context": "No clinical reference range adopted in synthetic test",
        "source": "Synthetic diagnostic author",
        "critical": True,
        "critical_policy_reference": "Synthetic test critical flag policy",
    }
    result = j.create("/results", body, "diagnostics")
    result = j.create(
        f"/results/{result['id']}/actions",
        {
            "patient_id": patient["id"],
            "expected_version": 1,
            "action": "RELEASE",
            "clinical_response": "Actual synthetic verification",
            "reason": "Synthetic report release",
            "intent_confirmed": True,
        },
        "diagnostics",
    )
    for action, version in [("ACKNOWLEDGE", 2), ("REVIEW", 3), ("COMMUNICATE", 4)]:
        result = j.create(
            f"/results/{result['id']}/actions",
            {
                "patient_id": patient["id"],
                "expected_version": version,
                "action": action,
                "clinical_response": "Actual synthetic response and contact evidence",
                "reason": "Synthetic actual action",
                "intent_confirmed": True,
            },
        )
    assert result["data"]["communicated_at"]
    correction = j.create(
        "/results",
        {**body, "corrects_id": result["id"], "correction_reason": "Retain both source reports"},
        "diagnostics",
    )
    j.create(
        f"/results/{correction['id']}/actions",
        {
            "patient_id": patient["id"],
            "expected_version": 1,
            "action": "RELEASE",
            "clinical_response": "Actual correction check",
            "reason": "Synthetic correction",
            "intent_confirmed": True,
        },
        "diagnostics",
    )
    tasks = j.get("/worklist?kind=task").json()["items"]
    assert len(tasks) == 3 and all(
        task["data"]["owner_id"] == j.actors["clinician"][0] for task in tasks
    )
    assert (
        j.get(f"/records/{result['id']}", "diagnostics").json()["data"]["interpretation"]
        == "Synthetic report"
    )


def test_medication_stock_and_duplicate_administration(journey):
    j = journey
    patient, encounter = j.encounter()
    product, medication = j.medicine(patient, encounter)
    lot = j.create(
        "/stock",
        {
            "product_id": product["id"],
            "batch": "TEST-BATCH",
            "expires_at": stamp(5),
            "quantity": "10",
            "unit": "TEST_STOCK_UNIT",
            "evidence": "Synthetic received stock evidence",
        },
        "pharmacy",
    )
    body = {
        **j.context(patient, encounter),
        "medication_id": medication["id"],
        "expected_order_version": 3,
        "lot_id": lot["id"],
        "expected_lot_version": 1,
        "quantity": "2",
        "verification": "Synthetic actual verification",
        "patient_identity_check": "Synthetic two-identifier test",
    }
    key = db.uid()
    dispense = j.create("/dispenses", body, "pharmacy", key)
    assert j.create("/dispenses", body, "pharmacy", key)["id"] == dispense["id"]
    assert Decimal(j.get("/stock", "pharmacy").json()["items"][0]["quantity"]) == 8
    slot = stamp(-1)
    occurrence = j.post(
        f"/medications/{medication['id']}/occurrence",
        {"patient_id": patient["id"], "scheduled_at": slot},
    ).json()
    administration = {
        **j.context(patient, encounter),
        "medication_id": medication["id"],
        "expected_order_version": 3,
        "occurrence_key": occurrence["occurrence_key"],
        "scheduled_at": slot,
        "outcome": "GIVEN",
        "dose": "1",
        "dose_unit": "TEST_UNIT",
        "route": "TEST_ROUTE",
        "reason": "Synthetic actual event",
        "patient_identity_check": "Synthetic identity check",
    }
    first = j.create("/administrations", administration)
    assert first["status"] == "GIVEN"
    assert j.post("/administrations", administration).status_code == 409
    assert j.post("/administrations", {**administration, "dose": "2"}).status_code == 409
    j.create(
        f"/medications/{medication['id']}/actions",
        {
            "patient_id": patient["id"],
            "expected_version": 3,
            "action": "STOP",
            "reason": "Synthetic stop",
            "safety_review": "Synthetic review",
            "intent_confirmed": True,
        },
    )
    assert j.post("/administrations", administration).status_code == 409


def test_admission_bed_collision_and_discharge(journey):
    j = journey
    patient, encounter = j.encounter()
    summary = j.note(patient, encounter, note_type="DISCHARGE")
    bed = j.create("/beds", {"ward": "Synthetic ward", "label": "T1"})
    body = {
        **j.context(patient, encounter),
        "bed_id": bed["id"],
        "expected_bed_version": 1,
        "responsible_clinician_id": j.actors["clinician"][0],
        "responsible_nurse_id": j.actors["nurse"][0],
        "indication": "Synthetic admission",
        "signed_admission_note_id": summary["id"],
    }
    stay = j.create("/admissions", body)
    assert j.get(f"/patients/{patient['id']}/chart", "nurse").status_code == 403
    accepted = j.create(
        f"/workflows/stays/{stay['id']}/events",
        {
            "patient_id": patient["id"],
            "expected_version": stay["version"],
            "action": "ACCEPT_NURSING",
            "occurred_at": stamp(-1),
            "policy_reference": "Synthetic actual nursing receipt policy",
            "actual_evidence": "Synthetic personal patient and ward receipt",
            "reason": "Synthetic personal acceptance",
            "intent_confirmed": True,
        },
        "nurse",
    )
    assert j.get("/beds").json()["items"][0]["stay_id"] == stay["id"]
    other_patient, other_encounter = j.encounter()
    other_summary = j.note(other_patient, other_encounter)
    assert (
        j.post(
            "/admissions",
            {
                **body,
                **j.context(other_patient, other_encounter),
                "signed_admission_note_id": other_summary["id"],
            },
        ).status_code
        == 409
    )
    j.create(
        f"/stays/{stay['id']}/actions",
        {
            "patient_id": patient["id"],
            "expected_version": accepted["version"],
            "action": "DISCHARGE",
            "reason": "Synthetic actual discharge",
            "signed_summary_id": summary["id"],
            "instructions": "Synthetic instructions",
            "medication_reconciliation": "Synthetic reconciliation",
            "occurred_at": stamp(-1),
            "intent_confirmed": True,
        },
    )
    assert j.get("/beds").json()["items"][0]["stay_id"] is None
    assert j.get(f"/patients/{patient['id']}/chart", "nurse").status_code == 200


@pytest.mark.parametrize(
    "path,body",
    [
        ("/patients", {"display_name": "Unverified", "provisional": False, "sex": "UNKNOWN"}),
        (
            "/patients",
            {
                "display_name": "Impossible date",
                "provisional": True,
                "sex": "UNKNOWN",
                "birth_date": "2999-01-01",
            },
        ),
        ("/patient-search", {"query": "*"}),
    ],
)
def test_unknowns_and_invalid_inputs_fail_without_inventing_facts(journey, path, body):
    assert journey.post(path, body).status_code == 422


def test_sensitive_notes_and_entered_error_preserve_source(journey):
    j = journey
    patient, encounter = j.encounter()
    note = j.note(patient, encounter, confidentiality="RESTRICTED", note_type="MENTAL_HEALTH")
    admission_note = j.note(patient, encounter)
    bed = j.create("/beds", {"ward": "Synthetic ward", "label": "Sensitive-test"})
    stay = j.create(
        "/admissions",
        {
            **j.context(patient, encounter),
            "bed_id": bed["id"],
            "expected_bed_version": 1,
            "responsible_clinician_id": j.actors["clinician"][0],
            "responsible_nurse_id": j.actors["nurse"][0],
            "indication": "Synthetic admission",
            "signed_admission_note_id": admission_note["id"],
        },
    )
    assert j.get(f"/patients/{patient['id']}/chart", "nurse").status_code == 403
    j.create(
        f"/workflows/stays/{stay['id']}/events",
        {
            "patient_id": patient["id"],
            "expected_version": stay["version"],
            "action": "ACCEPT_NURSING",
            "occurred_at": stamp(-1),
            "policy_reference": "Synthetic actual nursing receipt policy",
            "actual_evidence": "Synthetic personal patient and ward receipt",
            "reason": "Synthetic personal acceptance",
            "intent_confirmed": True,
        },
        "nurse",
    )
    chart = j.get(f"/patients/{patient['id']}/chart", "nurse").json()
    assert chart["withheld_records"] >= 1 and note["id"] not in {r["id"] for r in chart["items"]}
    assert j.get(f"/records/{note['id']}", "nurse").status_code == 403
    error = j.create(
        f"/records/{note['id']}/entered-in-error",
        {
            "patient_id": patient["id"],
            "expected_version": 2,
            "reason": "Synthetic incorrect source",
            "intent_confirmed": True,
        },
    )
    assert error["data"]["target_id"] == note["id"]
    correction = j.note(
        patient,
        encounter,
        confidentiality="RESTRICTED",
        note_type="MENTAL_HEALTH",
        amends_id=note["id"],
        amendment_reason="Correction of retained entered-in-error source",
    )
    assert correction["data"]["amends_id"] == note["id"]
    assert j.get(f"/records/{note['id']}").json()["data"]["narrative"] == note["data"]["narrative"]


def test_consent_withdrawal_blocks_new_procedure(journey):
    j = journey
    patient, encounter = j.encounter()
    consent_body = {
        **j.context(patient, encounter),
        "intervention": "Synthetic planned test procedure",
        "decision": "CONSENTED",
        "capacity_assessment": "Synthetic capacity assessment",
        "decision_maker": "Synthetic patient",
        "representative_authority": "Synthetic self authority",
        "explanation": "Synthetic explanation",
        "policy_reference": "TEST-ONLY consent policy",
        "valid_until": stamp(2),
        "intent_confirmed": True,
    }
    consent = j.create("/consents", consent_body)
    procedure_body = {
        **j.context(patient, encounter),
        "code": coding(),
        "indication": "Synthetic procedure indication",
        "site": "TEST_SITE",
        "consent_id": consent["id"],
        "team_ids": [j.actors["clinician"][0]],
        "readiness_evidence": "Synthetic readiness evidence",
        "safety_policy_reference": "Synthetic adopted policy",
        "result_owner_id": j.actors["clinician"][0],
    }
    j.create("/procedures", procedure_body)
    j.create("/consents", {**consent_body, "decision": "WITHDRAWN", "supersedes_id": consent["id"]})
    assert j.post("/procedures", procedure_body).status_code == 409


def test_expired_privilege_and_activation_stop_clinical_writes(journey):
    j = journey
    patient, encounter = j.encounter()

    async def expire():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                update(t.privileges)
                .where(t.privileges.c.account_id == j.actors["clinician"][0])
                .values(valid_until=stamp(-1))
            )

    run(expire())
    assert j.get(f"/patients/{patient['id']}/chart").status_code == 403
    assert (
        j.post(
            "/notes",
            {
                **j.context(patient, encounter),
                "note_type": "CONSULTATION",
                "narrative": "Blocked",
                "source": "Expired test user",
            },
        ).status_code
        == 403
    )


from decimal import Decimal  # synthetic exact quantities, never clinical dosing guidance


def test_sharing_scope_revocation_and_cached_download(journey):
    j = journey
    patient, encounter = j.encounter()
    note = j.note(patient, encounter)
    grant = j.create(
        "/sharing-grants",
        {
            **j.context(patient, encounter),
            "recipient": "TEST-RECEIVER",
            "purpose": "REFERRAL",
            "record_ids": [note["id"]],
            "lawful_authority": "Synthetic patient decision",
            "decision_maker": "Synthetic patient",
            "authority_evidence": "Synthetic documented authority",
            "valid_until": stamp(2),
            "intent_confirmed": True,
        },
    )
    body = {
        "patient_id": patient["id"],
        "sharing_grant_id": grant["id"],
        "recipient": "TEST-RECEIVER",
        "purpose": "REFERRAL",
    }
    assert j.post("/disclosures", {**body, "recipient": "WRONG-RECEIVER"}).status_code == 403
    key = db.uid()
    disclosure = j.create("/disclosures", body, key=key)
    assert [r["id"] for r in disclosure["package"]["sources"]] == [note["id"]]
    assert disclosure["data"]["receiver_acceptance"] == "NOT_RECORDED"
    j.create(
        f"/sharing-grants/{grant['id']}/revoke",
        {
            "patient_id": patient["id"],
            "expected_version": 1,
            "reason": "Synthetic sharing withdrawal",
            "intent_confirmed": True,
        },
    )
    assert j.post("/disclosures", body, key=key).status_code == 403


def test_referral_does_not_complete_without_actual_acceptance(journey):
    j = journey
    patient, encounter = j.encounter()
    note = j.note(patient, encounter)
    grant = j.create(
        "/sharing-grants",
        {
            **j.context(patient, encounter),
            "recipient": "TEST-RECEIVER",
            "purpose": "REFERRAL",
            "record_ids": [note["id"]],
            "lawful_authority": "Synthetic patient decision",
            "decision_maker": "Synthetic patient",
            "authority_evidence": "Synthetic documented authority",
            "valid_until": stamp(2),
            "intent_confirmed": True,
        },
    )
    referral = j.create(
        "/referrals",
        {
            **j.context(patient, encounter),
            "destination": "TEST-RECEIVER",
            "reason": "Synthetic referral",
            "summary_note_id": note["id"],
            "sharing_grant_id": grant["id"],
            "owner_id": j.actors["clinician"][0],
        },
    )
    action = {
        "patient_id": patient["id"],
        "expected_version": 1,
        "action": "REQUEST",
        "reason": "Synthetic actual request",
        "occurred_at": stamp(-1),
    }
    j.create(f"/referrals/{referral['id']}/actions", action)
    assert (
        j.post(
            f"/referrals/{referral['id']}/actions",
            {**action, "expected_version": 2, "action": "TRANSFER"},
        ).status_code
        == 409
    )
    assert (
        j.post(
            f"/referrals/{referral['id']}/actions",
            {**action, "expected_version": 2, "action": "RECORD_ACCEPTANCE"},
        ).status_code
        == 422
    )
    j.create(
        f"/referrals/{referral['id']}/actions",
        {
            **action,
            "expected_version": 2,
            "action": "RECORD_ACCEPTANCE",
            "receiver_name": "Synthetic receiving professional",
            "acceptance_evidence": "Synthetic actual acceptance evidence",
        },
    )
    transferred = j.create(
        f"/referrals/{referral['id']}/actions",
        {
            **action,
            "expected_version": 3,
            "action": "TRANSFER",
            "actual_handover": "Synthetic actual handover",
        },
    )
    assert transferred["status"] == "TRANSFERRED"


def test_scheduling_conflicts_and_unclaimed_arrival(journey):
    j = journey
    patient = j.patient()
    body = {
        "patient_id": patient["id"],
        "service": "GENERAL",
        "clinician_id": j.actors["clinician"][0],
        "starts_at": stamp(2),
        "ends_at": stamp(3),
        "reason": "Synthetic future commitment",
    }
    appointments = [j.create("/appointments", body) for _ in range(2)]
    action = {
        "patient_id": patient["id"],
        "expected_version": 1,
        "action": "CONFIRM",
        "reason": "Actual synthetic acceptance",
    }
    j.create(f"/appointments/{appointments[0]['id']}/actions", action)
    assert j.post(f"/appointments/{appointments[1]['id']}/actions", action).status_code == 409
    arrival = j.create(
        "/encounters",
        {
            "patient_id": patient["id"],
            "service": "GENERAL",
            "encounter_type": "EMERGENCY",
            "arrival": "EMERGENCY",
            "complaint": "Synthetic urgent arrival",
            "occurred_at": stamp(-1),
        },
        "nurse",
    )
    assert arrival["data"]["owner_id"] is None
    assert any(r["id"] == arrival["id"] for r in j.get("/worklist?kind=encounter").json()["items"])
    claim = {
        "patient_id": patient["id"],
        "expected_version": 1,
        "reason": "Synthetic accountable claim",
        "intent_confirmed": True,
    }
    accepted = j.create(f"/encounters/{arrival['id']}/claim", claim)
    assert accepted["data"]["owner_id"] == j.actors["clinician"][0]
    assert (
        j.post(
            f"/encounters/{arrival['id']}/claim", {**claim, "expected_version": 2}, "outsider"
        ).status_code
        == 409
    )


def test_clinical_programme_review_retains_followup(journey):
    j = journey
    patient, encounter = j.encounter()
    programme = j.create(
        "/programmes",
        {
            **j.context(patient, encounter),
            "programme_type": "MATERNAL",
            "policy_reference": "Synthetic adopted programme",
            "goals": "Synthetic agreed goals",
            "baseline": "Synthetic baseline with uncertainty",
            "review_at": stamp(2),
            "responsible_id": j.actors["clinician"][0],
        },
    )
    reviewed = j.create(
        f"/programmes/{programme['id']}/reviews",
        {
            "patient_id": patient["id"],
            "expected_version": 1,
            "reason": "Synthetic actual review",
            "findings": "Synthetic sourced findings",
            "plan": "Synthetic reviewed plan",
            "next_review_at": stamp(3),
            "occurred_at": stamp(-1),
        },
    )
    assert len(reviewed["data"]["reviews"]) == 1
    assert len(j.get("/worklist?kind=task").json()["items"]) == 2


def test_financial_effects_are_balanced_actual_and_idempotent(journey):
    j = journey
    patient, encounter = j.encounter()
    summary = j.note(patient, encounter, note_type="DISCHARGE")
    tariff = j.create(
        "/tariffs",
        {
            "code": "TEST-TARIFF",
            "description": "Synthetic test service tariff",
            "currency": "NGN",
            "amount_minor": 100,
            "approval_reference": "Synthetic price authority, no production tariff",
            "valid_until": stamp(5),
        },
    )
    invoice_body = {
        "patient_id": patient["id"],
        "service_record_id": encounter["id"],
        "tariff_id": tariff["id"],
        "actual_service_evidence": "Synthetic actual fulfilment",
    }
    assert j.post("/invoices", invoice_body).status_code == 409
    j.create(
        f"/encounters/{encounter['id']}/complete",
        {
            "patient_id": patient["id"],
            "expected_version": 1,
            "reason": "Synthetic disposition",
            "disposition": "HOME",
            "signed_summary_id": summary["id"],
            "instructions": "Synthetic instructions",
            "medication_reconciliation": "Synthetic reconciliation",
            "follow_up_plan": "Synthetic actual follow-up plan",
            "occurred_at": stamp(-1),
            "intent_confirmed": True,
        },
    )
    invoice = j.create("/invoices", invoice_body)
    key = db.uid()
    body = {
        "patient_id": patient["id"],
        "invoice_id": invoice["id"],
        "expected_invoice_version": 1,
        "amount_minor": 100,
        "currency": "NGN",
        "receipt_reference": "SYNTHETIC-CASH-0001",
        "actual_cash_evidence": "Synthetic cash physically received",
        "received_at": stamp(-1),
        "intent_confirmed": True,
    }
    receipt = j.create("/cash-receipts", body, key=key)
    assert j.create("/cash-receipts", body, key=key)["id"] == receipt["id"]
    assert j.get(f"/records/{invoice['id']}").json()["status"] == "PAID"

    async def check():
        async with j.app.state.database.transaction() as session:
            legs = (await session.execute(select(t.ledger))).mappings().all()
            assert len(legs) == 4 and sum(r["amount_minor"] for r in legs) == 0

    run(check())


def test_denied_sensitive_reads_are_audited(journey):
    j = journey
    patient, encounter = j.encounter()
    note = j.note(patient, encounter)
    assert j.get(f"/records/{note['id']}", "admin").status_code == 403

    async def check():
        async with j.app.state.database.transaction() as session:
            rows = list(
                (
                    await session.execute(
                        select(t.audit).where(t.audit.c.actor_id == j.actors["admin"][0])
                    )
                ).mappings()
            )
            assert any(r["outcome"] == "DENIED" for r in rows)

    run(check())


def test_procedure_transfusion_and_accepted_clinical_handover(journey):
    j = journey
    patient, encounter = j.encounter()
    successor = j.actors["outsider"][0]
    j.create(
        "/privileges",
        {
            "account_id": successor,
            "services": ["GENERAL"],
            "capabilities": ["PROCEDURE"],
            "professional_reference": "Synthetic additional procedure verification",
            "valid_from": stamp(-1),
            "valid_until": stamp(5),
            "intent_confirmed": True,
        },
        "governor",
    )
    j.create(
        f"/encounters/{encounter['id']}/team",
        {
            "patient_id": patient["id"],
            "expected_version": 1,
            "account_id": successor,
            "capability": "CARE",
            "reason": "Synthetic treating invitation",
        },
    )
    j.create(
        f"/encounters/{encounter['id']}/join",
        {
            "patient_id": patient["id"],
            "expected_version": 2,
            "reason": "Actual synthetic treating acceptance",
            "intent_confirmed": True,
        },
        "outsider",
    )
    consent = j.create(
        "/consents",
        {
            **j.context(patient, encounter),
            "intervention": "Synthetic procedure and component",
            "decision": "CONSENTED",
            "capacity_assessment": "Synthetic assessment",
            "decision_maker": "Synthetic patient",
            "representative_authority": "Synthetic self authority",
            "explanation": "Synthetic actual explanation",
            "policy_reference": "Synthetic adopted consent policy",
            "valid_until": stamp(2),
            "intent_confirmed": True,
        },
    )
    procedure = j.create(
        "/procedures",
        {
            **j.context(patient, encounter),
            "code": coding(),
            "indication": "Synthetic procedure",
            "site": "TEST SITE",
            "consent_id": consent["id"],
            "team_ids": [j.actors["clinician"][0], successor],
            "readiness_evidence": "Synthetic actual preparation",
            "safety_policy_reference": "Synthetic adopted phases",
            "result_owner_id": j.actors["clinician"][0],
        },
    )

    def action(phase, version, **extra):
        return {
            "patient_id": patient["id"],
            "expected_version": version,
            "action": phase,
            "reason": "Synthetic actual event",
            "findings": "Synthetic actual findings",
            "participants": [j.actors["clinician"][0]],
            "occurred_at": stamp(-1),
            "intent_confirmed": True,
            **extra,
        }

    j.create(f"/procedures/{procedure['id']}/actions", action("SIGN_IN", 1))
    j.create(f"/procedures/{procedure['id']}/actions", action("TIME_OUT", 2))
    transfusion = j.create(
        "/transfusions",
        {
            **j.context(patient, encounter),
            "procedure_id": procedure["id"],
            "component_identifier": "SYNTHETIC-NOT-A-BLOOD-UNIT",
            "component_type": "TEST_ONLY",
            "blood_bank_authorisation": "Synthetic actual bank authority",
            "compatibility_evidence": "Synthetic bank evidence",
            "patient_unit_check": "Synthetic actual patient and component check",
            "witness_id": successor,
        },
    )
    start = {
        "patient_id": patient["id"],
        "expected_version": 1,
        "action": "START",
        "reason": "Synthetic actual event",
        "observation": "Synthetic independent witnessed start",
        "witness_id": j.actors["clinician"][0],
        "occurred_at": stamp(-1),
        "intent_confirmed": True,
    }
    assert j.post(f"/transfusions/{transfusion['id']}/actions", start).status_code == 403
    j.create(f"/transfusions/{transfusion['id']}/actions", start, "outsider")
    completed = j.create(
        f"/transfusions/{transfusion['id']}/actions",
        {**start, "expected_version": 2, "action": "COMPLETE"},
        "outsider",
    )
    assert completed["status"] == "COMPLETED"
    j.create(
        f"/procedures/{procedure['id']}/actions",
        action(
            "PERFORM",
            3,
            actual_procedure="Synthetic actually performed",
            specimens="Synthetic explicit none",
            implants_devices="Synthetic explicit none",
            complications="Synthetic explicit none",
        ),
    )
    j.create(f"/procedures/{procedure['id']}/actions", action("SIGN_OUT", 4))
    j.create(
        f"/procedures/{procedure['id']}/actions",
        action("OFFER_HANDOVER", 5, successor_id=successor),
    )
    accepted = j.create(
        f"/procedures/{procedure['id']}/actions",
        action("ACCEPT_HANDOVER", 6, participants=[successor]),
        "outsider",
    )
    assert accepted["status"] == "HANDED_OVER" and accepted["data"]["responsible_id"] == successor


def test_identity_link_requires_independent_review_and_never_merges_charts(journey):
    j = journey
    first, second = j.patient("Synthetic first identity"), j.patient("Synthetic second identity")
    link = j.create(
        "/identity-links",
        {
            "patient_id": first["id"],
            "other_patient_id": second["id"],
            "evidence": "Synthetic reviewed identity sources",
            "reason": "Synthetic proposed crosswalk",
        },
        "records",
    )
    action = {
        "patient_id": first["id"],
        "expected_version": 1,
        "action": "ACCEPT",
        "reason": "Synthetic independent review",
    }
    assert j.post(f"/identity-links/{link['id']}/actions", action, "records").status_code == 403
    accepted = j.create(f"/identity-links/{link['id']}/actions", action)
    assert accepted["status"] == "ACCEPTED"
    assert (
        j.get(f"/records/{first['id']}").json()["data"]["display_name"]
        == "Synthetic first identity"
    )
    assert (
        j.get(f"/records/{second['id']}").json()["data"]["display_name"]
        == "Synthetic second identity"
    )


def test_entered_in_error_order_blocks_further_actual_execution(journey):
    j = journey
    patient, encounter = j.encounter()
    product, medication = j.medicine(patient, encounter)
    j.create(
        f"/records/{medication['id']}/entered-in-error",
        {
            "patient_id": patient["id"],
            "expected_version": 3,
            "reason": "Synthetic source entered in error",
            "intent_confirmed": True,
        },
    )
    assert j.get(f"/records/{medication['id']}").json()["use_restriction"] == "ENTERED_IN_ERROR"
    lot = j.create(
        "/stock",
        {
            "product_id": product["id"],
            "batch": "ERROR-PROOF",
            "expires_at": stamp(3),
            "quantity": "3",
            "unit": "TEST_UNIT",
            "evidence": "Synthetic test receipt",
        },
        "pharmacy",
    )
    response = j.post(
        "/dispenses",
        {
            **j.context(patient, encounter),
            "medication_id": medication["id"],
            "expected_order_version": 3,
            "lot_id": lot["id"],
            "expected_lot_version": 1,
            "quantity": "1",
            "verification": "Synthetic attempted execution",
            "patient_identity_check": "Synthetic check",
        },
        "pharmacy",
    )
    assert (
        response.status_code == 409
        and response.json()["error"]["code"] == "RECORD_ENTERED_IN_ERROR"
    )
    assert Decimal(j.get("/stock", "pharmacy").json()["items"][0]["quantity"]) == 3
