"""Synthetic Phase 5 engineering journeys; these are not adopted clinical protocols/UAT."""

from decimal import Decimal

import pytest
from lw_care_api.platform import db
from lw_care_api.platform.clinical import flow_index as fi
from lw_care_api.platform.clinical import tables as t
from sqlalchemy import select, update
from test_platform_clinical import coding, run, stamp
from test_platform_clinical import journey as stored_journey


@pytest.fixture
def care(tmp_path):
    yield from stored_journey.__wrapped__(tmp_path)


def actual(**extra):
    return {
        "reason": "Synthetic actual engineering observation",
        "occurred_at": stamp(-1),
        "intent_confirmed": True,
        **extra,
    }


def team(j, patient, encounter, actor="nurse", capability="NURSING"):
    current = j.get(f"/records/{encounter['id']}").json()
    j.create(
        f"/encounters/{encounter['id']}/team",
        {
            "patient_id": patient["id"],
            "expected_version": current["version"],
            "account_id": j.actors[actor][0],
            "capability": capability,
            "reason": "Synthetic actual team offer",
        },
    )
    current = j.get(f"/records/{encounter['id']}").json()
    j.create(
        f"/encounters/{encounter['id']}/join",
        {
            "patient_id": patient["id"],
            "expected_version": current["version"],
            "reason": "Synthetic personal acceptance",
            "intent_confirmed": True,
        },
        actor,
    )


def task(j, patient, encounter):
    return j.create(
        "/tasks",
        {
            **j.context(patient, encounter),
            "title": "Synthetic unresolved follow-up",
            "instructions": "Keep actual responsibility",
            "owner_id": j.actors["clinician"][0],
            "due_at": stamp(1),
        },
    )


def offer(j, patient, encounter):
    current = j.get(f"/records/{encounter['id']}").json()
    return j.create(
        "/workflows/handovers",
        {
            **j.context(patient, encounter),
            "expected_encounter_version": current["version"],
            "recipient_id": j.actors["outsider"][0],
            "capability": "CARE",
            "summary": "Synthetic exact current work",
            "due_at": stamp(1),
            **actual(),
        },
    )


def test_capacity_uses_personally_accepted_roster_and_retains_ownership_at_shift_end(care):
    j = care
    config = {
        "service": "GENERAL",
        "max_open_encounters": 1,
        "resources_evidence": "Synthetic actual room/equipment capacity",
        "policy_reference": "SYNTHETIC_NOT_A_REAL_ADOPTION",
        "starts_at": stamp(-1),
        "ends_at": stamp(2),
        "require_roster": True,
        "require_admission_order": True,
        "intent_confirmed": True,
    }
    assert j.post("/workflows/capacity", config, "admin").status_code == 403
    capacity = j.create("/workflows/capacity", config, "governor")
    shift = j.create(
        "/workflows/shifts",
        {
            "service": "GENERAL",
            "account_id": j.actors["clinician"][0],
            "capability": "CARE",
            "capacity": 1,
            "starts_at": stamp(-1),
            "ends_at": stamp(2),
            "policy_reference": "Synthetic shift policy",
            "reason": "Synthetic qualified service offer",
            "intent_confirmed": True,
        },
        "governor",
    )
    patient = j.patient()
    body = {
        "patient_id": patient["id"],
        "service": "GENERAL",
        "encounter_type": "AMBULATORY",
        "arrival": "WALK_IN",
        "complaint": "Synthetic test only",
        "occurred_at": stamp(-1),
    }
    assert j.post("/encounters", body).status_code == 409
    shift = j.create(
        f"/workflows/shifts/{shift['id']}/actions", actual(expected_version=1, action="ACCEPT")
    )
    encounter = j.create("/encounters", body)
    assert j.post("/encounters", body).status_code == 409
    j.create(
        f"/workflows/shifts/{shift['id']}/actions",
        actual(expected_version=shift["version"], action="END"),
    )
    assert (
        j.get(f"/records/{encounter['id']}").json()["data"]["owner_id"] == j.actors["clinician"][0]
    )
    assert j.get(f"/patients/{patient['id']}/chart", "governor").status_code == 403
    revised = j.create(
        f"/workflows/capacity/{capacity['id']}/revisions",
        {
            **config,
            "expected_version": 1,
            "max_open_encounters": 0,
            "reason": "Synthetic actual resource restriction",
        },
        "governor",
    )
    assert revised["version"] == 2 and revised["data"]["max_open_encounters"] == 0
    future = j.create(
        "/workflows/shifts",
        {
            "service": "GENERAL",
            "account_id": j.actors["clinician"][0],
            "capability": "CARE",
            "capacity": 1,
            "starts_at": shift["data"]["ends_at"],
            "ends_at": stamp(3),
            "policy_reference": "Synthetic actual staffing policy",
            "reason": "Synthetic later coverage",
            "intent_confirmed": True,
        },
        "governor",
    )
    withdrawn = j.create(
        f"/workflows/shifts/{future['id']}/actions",
        actual(expected_version=1, action="WITHDRAW"),
        "governor",
    )
    assert (
        withdrawn["status"] == "WITHDRAWN"
        and j.get(f"/records/{encounter['id']}").json()["data"]["owner_id"]
        == j.actors["clinician"][0]
    )


def test_handover_decline_stale_work_and_acceptance_preserve_actual_result_owner(care):
    j = care
    patient, encounter = j.encounter()
    order = j.order(patient, encounter, "IMAGING")
    original = task(j, patient, encounter)
    first = offer(j, patient, encounter)
    assert j.get(f"/records/{original['id']}", "outsider").status_code == 403
    j.create(
        f"/workflows/handovers/{first['id']}/actions",
        actual(patient_id=patient["id"], expected_version=1, action="DECLINE"),
        "outsider",
    )
    assert (
        j.get(f"/records/{encounter['id']}").json()["data"]["owner_id"] == j.actors["clinician"][0]
    )
    second = offer(j, patient, encounter)
    task(j, patient, encounter)
    assert (
        j.post(
            f"/workflows/handovers/{second['id']}/actions",
            actual(patient_id=patient["id"], expected_version=1, action="ACCEPT"),
            "outsider",
        ).status_code
        == 409
    )
    j.create(
        f"/workflows/handovers/{second['id']}/actions",
        actual(patient_id=patient["id"], expected_version=1, action="CANCEL"),
    )
    third = offer(j, patient, encounter)
    accepted = j.create(
        f"/workflows/handovers/{third['id']}/actions",
        actual(patient_id=patient["id"], expected_version=1, action="ACCEPT"),
        "outsider",
    )
    assert accepted["status"] == "ACCEPTED"
    assert (
        j.get(f"/records/{original['id']}", "outsider").json()["data"]["owner_id"]
        == j.actors["outsider"][0]
    )
    assert (
        j.get(f"/records/{order['id']}", "outsider").json()["data"]["result_owner_id"]
        == j.actors["outsider"][0]
    )
    mine = j.get("/worklist?kind=task", "outsider").json()["items"]
    assert len(mine) >= 2 and all(
        row["data"]["owner_id"] == j.actors["outsider"][0] for row in mine
    )


@pytest.mark.parametrize("final_action", ["SELF_DISCHARGE", "DEATH"])
def test_bed_hold_and_leave_self_discharge_separate_actual_bed_release(care, final_action):
    j = care
    patient, encounter = j.encounter()
    team(j, patient, encounter)
    note = j.note(patient, encounter)
    bed = j.create("/beds", {"ward": "Synthetic ward", "label": "Synthetic exclusive bed"})
    order = j.create(
        "/workflows/admission-orders",
        {
            **j.context(patient, encounter),
            "signed_note_id": note["id"],
            "intended_ward": "Synthetic ward",
            "policy_reference": "Synthetic adopted test workflow",
            **actual(),
        },
    )
    hold = j.create(
        "/workflows/bed-holds",
        {
            **j.context(patient, encounter),
            "admission_order_id": order["id"],
            "expected_order_version": 1,
            "bed_id": bed["id"],
            "expected_bed_version": 1,
            "expires_at": stamp(1),
            **actual(),
        },
        "nurse",
    )
    assert j.get("/beds").json()["items"][0]["reservation_status"] == "HELD"
    other, other_encounter = j.encounter()
    other_note = j.note(other, other_encounter)
    direct = {
        **j.context(other, other_encounter),
        "bed_id": bed["id"],
        "expected_bed_version": 1,
        "responsible_clinician_id": j.actors["clinician"][0],
        "responsible_nurse_id": j.actors["nurse"][0],
        "indication": "Synthetic inpatient admission",
        "signed_admission_note_id": other_note["id"],
    }
    assert j.post("/admissions", direct).status_code == 409
    stay = j.create(
        "/admissions",
        {
            **direct,
            **j.context(patient, encounter),
            "signed_admission_note_id": note["id"],
            "admission_order_id": order["id"],
        },
    )
    assert j.get(f"/records/{hold['id']}").json()["status"] == "CONSUMED"
    body = {
        "patient_id": patient["id"],
        "signed_summary_id": note["id"],
        "policy_reference": "Synthetic special disposition policy",
        "instructions": "Synthetic actual plan",
        "medication_reconciliation": "Synthetic reviewed medicine history",
        "follow_up_owner_id": j.actors["clinician"][0],
        "actual_evidence": "Synthetic actual event",
        **actual(),
    }
    stay = j.create(
        f"/workflows/stays/{stay['id']}/events",
        {
            **body,
            "expected_version": stay["version"],
            "action": "LEAVE",
            "expected_return_at": stamp(1),
        },
    )
    assert (
        stay["status"] == "ON_LEAVE" and j.get("/beds").json()["items"][0]["stay_id"] == stay["id"]
    )
    stay = j.create(
        f"/workflows/stays/{stay['id']}/events",
        {**body, "expected_version": stay["version"], "action": "RETURN"},
    )
    stay = j.create(
        f"/workflows/stays/{stay['id']}/events",
        {**body, "expected_version": stay["version"], "action": final_action},
    )
    assert j.get("/beds").json()["items"][0]["stay_id"] == stay["id"]
    bed_now = j.get("/beds").json()["items"][0]
    j.create(
        f"/workflows/stays/{stay['id']}/events",
        {
            **body,
            "expected_version": stay["version"],
            "expected_bed_version": bed_now["version"],
            "action": "RELEASE_BED",
        },
        "nurse",
    )
    assert j.get("/beds").json()["items"][0]["stay_id"] is None
    assert j.get("/worklist?kind=task").json()["items"]


def test_nursing_corrections_and_structured_twins_keep_distinct_chart_authority(care):
    j = care
    mother, maternal = j.encounter()
    team(j, mother, maternal)
    nursing = j.create(
        "/workflows/nursing-assessments",
        {
            **j.context(mother, maternal),
            "assessment": "Synthetic observed facts",
            "plan": "Synthetic bedside plan",
            "escalation": "Synthetic actual escalation evidence",
            "source": "Synthetic nurse",
            "intent_confirmed": True,
        },
        "nurse",
    )
    amended = j.create(
        "/workflows/nursing-assessments",
        {
            **j.context(mother, maternal),
            "assessment": "Synthetic corrected observed facts",
            "plan": "Synthetic bedside plan",
            "escalation": "Synthetic actual escalation evidence",
            "source": "Synthetic nurse",
            "amends_id": nursing["id"],
            "amendment_reason": "Synthetic actual correction",
            "intent_confirmed": True,
        },
        "nurse",
    )
    assert (
        amended["id"] != nursing["id"]
        and j.get(f"/records/{nursing['id']}").json()["data"]["assessment"]
        == "Synthetic observed facts"
    )
    infants = [j.encounter(j.patient("Synthetic infant " + str(i))) for i in range(2)]
    measurement = {
        "code": coding(),
        "absent_reason": "NOT_OBSERVED_IN_SYNTHETIC_TEST",
        "source": "Synthetic engineering fixture",
    }
    body = {
        **j.context(mother, maternal),
        "source": "Synthetic birth documentation",
        "policy_reference": "SYNTHETIC_NOT_REAL_ADOPTION",
        "signed_note_id": j.note(mother, maternal)["id"],
        "mode_as_recorded": "SYNTHETIC_ONLY",
        "maternal_outcome": "Synthetic recorded outcome",
        "actual_team": [j.actors["clinician"][0]],
        "infants": [
            {
                "patient_id": infant["id"],
                "encounter_id": encounter["id"],
                "birth_order": i + 1,
                "outcome": "UNKNOWN",
                "occurred_at": stamp(-1),
                "relationship_evidence": "Synthetic actual identity relationship",
                "observations": [measurement],
                "follow_up_owner_id": j.actors["clinician"][0],
                "follow_up_due_at": stamp(1),
            }
            for i, (infant, encounter) in enumerate(infants)
        ],
        "maternal_review_owner_id": j.actors["clinician"][0],
        "maternal_review_due_at": stamp(1),
        "intent_confirmed": True,
    }
    result = j.create("/workflows/births", body)
    for infant, _encounter in infants:
        links = [
            row
            for row in j.get(f"/patients/{infant['id']}/chart").json()["items"]
            if row["kind"] == "birth_link"
        ]
        assert links[0]["data"]["source_id"] == result["id"]
        assert j.get(f"/patients/{infant['id']}/chart", "nurse").status_code == 403
    assert (
        j.post(
            "/workflows/births", {**body, "infants": [body["infants"][0], body["infants"][0]]}
        ).status_code
        == 409
    )
    growth = j.create(
        "/workflows/growth",
        {
            **j.context(*infants[0]),
            "source": "Synthetic actual observation",
            "policy_reference": "Synthetic manual measurement policy",
            "age_context": "AGE_UNCERTAIN_SYNTHETIC",
            "measurements": [measurement],
            "interpretation_as_assessed": "UNKNOWN_NO_REFERENCE_ADOPTED",
            "review_owner_id": j.actors["clinician"][0],
            "review_due_at": stamp(1),
            "intent_confirmed": True,
        },
    )
    assert growth["data"]["automated_percentiles_or_schedule"] == "UNAVAILABLE_NOT_INFERRED"


def test_stock_reservation_and_independent_return_have_one_physical_effect(care):
    j = care
    patient, encounter = j.encounter()
    product, medication = j.medicine(patient, encounter)
    lot = j.create(
        "/stock",
        {
            "product_id": product["id"],
            "batch": "SYNTHETIC_RESERVED",
            "expires_at": stamp(4),
            "quantity": "10",
            "unit": "TEST_UNIT",
            "evidence": "Synthetic actual physical receipt",
        },
        "pharmacy",
    )
    hold = j.create(
        "/workflows/stock-holds",
        {
            **j.context(patient, encounter),
            "medication_id": medication["id"],
            "expected_medication_version": medication["version"],
            "lot_id": lot["id"],
            "expected_lot_version": 1,
            "quantity": "8",
            "unit": "TEST_UNIT",
            "expires_at": stamp(1),
            **actual(),
        },
        "pharmacy",
    )
    board = j.get("/stock", "pharmacy").json()["items"][0]
    assert Decimal(board["reserved_quantity"]) == 8 and Decimal(board["unreserved_quantity"]) == 2
    supply = {
        **j.context(patient, encounter),
        "medication_id": medication["id"],
        "expected_order_version": medication["version"],
        "lot_id": lot["id"],
        "expected_lot_version": 1,
        "quantity": "4",
        "verification": "Synthetic exact product",
        "patient_identity_check": "Synthetic two identifiers",
    }
    assert j.post("/dispenses", supply, "pharmacy").status_code == 409
    dispensed = j.create("/dispenses", {**supply, "reservation_id": hold["id"]}, "pharmacy")
    proposal = j.create(
        "/workflows/stock-returns",
        {
            "patient_id": patient["id"],
            "dispense_id": dispensed["id"],
            "lot_id": lot["id"],
            "expected_lot_version": 2,
            "quantity": "1",
            "unit": "TEST_UNIT",
            "disposition": "QUARANTINED",
            "physical_evidence": "Synthetic physically returned item",
            "policy_reference": "Synthetic return procedure",
            "reason": "Synthetic verified unused return",
            "intent_confirmed": True,
        },
        "pharmacy",
    )
    witness = actual(patient_id=patient["id"], expected_version=1, action="APPROVE")
    assert (
        j.post(
            f"/workflows/stock-movements/{proposal['id']}/witness", witness, "pharmacy"
        ).status_code
        == 409
    )
    key = db.uid()
    j.create(f"/workflows/stock-movements/{proposal['id']}/witness", witness, "clinician", key)
    j.create(f"/workflows/stock-movements/{proposal['id']}/witness", witness, "clinician", key)
    current = j.get("/stock", "pharmacy").json()["items"][0]
    assert Decimal(current["quantity"]) == 7 and current["status"] == "QUARANTINED"
    assert j.get(f"/records/{dispensed['id']}", "pharmacy").json()["status"] == "DISPENSED"


def test_migration_gate_index_rebuild_and_revocation_before_receipt(care):
    j = care
    patient, encounter = j.encounter()
    created = task(j, patient, encounter)

    async def rebuild():
        async with j.app.state.database.transaction() as session:
            await session.execute(fi.index.delete().where(fi.index.c.record_id == created["id"]))
        count = await fi.rebuild(j.app.state.database, j.app.state.box)
        async with j.app.state.database.transaction() as session:
            indexed = await session.scalar(
                select(fi.index.c.indexed_version).where(fi.index.c.record_id == created["id"])
            )
        return count, indexed

    count, indexed = run(rebuild())
    assert count >= 3 and indexed == created["version"]
    body = {
        **j.context(patient, encounter),
        "assessment": "Synthetic documented evidence",
        "plan": "Synthetic plan",
        "escalation": "Synthetic escalation evidence",
        "source": "Synthetic actual observer",
        "intent_confirmed": True,
    }
    key = db.uid()
    j.create("/workflows/nursing-assessments", body, "clinician", key)

    async def revoke():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                update(t.privileges)
                .where(t.privileges.c.account_id == j.actors["clinician"][0])
                .values(revoked=True)
            )

    run(revoke())
    assert j.post("/workflows/nursing-assessments", body, "clinician", key).status_code == 403

    async def stage():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                db.schema_versions.delete().where(db.schema_versions.c.version > 6)
            )

    run(stage())
    assert j.client.get("/v1/ready").json()["schema_version"] == 6
    assert j.post("/workflows/nursing-assessments", body).status_code == 503


def test_substitution_requires_independent_prescriber_and_exact_signed_replacement(care):
    j = care
    patient, encounter = j.encounter()
    product, medication = j.medicine(patient, encounter)
    # The first prescription prohibits substitution, so its refusal remains real.
    replacement_product = j.create(
        "/products", {**product["data"], "code": {**coding(), "code": db.uid()}}, "pharmacy"
    )
    body = {
        **j.context(patient, encounter),
        "medication_id": medication["id"],
        "expected_medication_version": medication["version"],
        "replacement_product_id": replacement_product["id"],
        "prescriber_id": j.actors["clinician"][0],
        "policy_reference": "Synthetic substitution policy",
        **actual(),
    }
    assert j.post("/workflows/substitutions", body, "pharmacy").status_code == 409
    original = j.create(
        "/medications",
        {
            **j.context(patient, encounter),
            **{
                key: medication["data"][key]
                for key in (
                    "product_id",
                    "indication",
                    "dose",
                    "dose_unit",
                    "route",
                    "timing",
                    "starts_at",
                    "stops_at",
                    "manual_safety_review",
                    "reconciliation",
                )
            },
            "substitution": "PHARMACIST_APPROVED_EQUIVALENT",
        },
    )
    for version, action, actor in [(1, "SIGN", "clinician"), (2, "VERIFY", "pharmacy")]:
        original = j.create(
            f"/medications/{original['id']}/actions",
            {
                "patient_id": patient["id"],
                "expected_version": version,
                "action": action,
                "safety_review": "Synthetic manual review",
                "reason": "Synthetic intentional medication action",
                "intent_confirmed": True,
            },
            actor,
        )
    proposal = j.create(
        "/workflows/substitutions",
        {
            **body,
            "medication_id": original["id"],
            "expected_medication_version": original["version"],
        },
        "pharmacy",
    )
    replacement = j.create(
        "/medications",
        {
            **j.context(patient, encounter),
            **{
                key: medication["data"][key]
                for key in (
                    "indication",
                    "dose",
                    "dose_unit",
                    "route",
                    "timing",
                    "starts_at",
                    "stops_at",
                    "manual_safety_review",
                    "reconciliation",
                )
            },
            "product_id": replacement_product["id"],
            "substitution": "NOT_PERMITTED",
        },
    )
    decision = actual(
        patient_id=patient["id"],
        expected_version=1,
        action="APPROVE",
        replacement_medication_id=replacement["id"],
    )
    assert (
        j.post(f"/workflows/substitutions/{proposal['id']}/decision", decision).status_code == 409
    )
    j.create(
        f"/medications/{replacement['id']}/actions",
        {
            "patient_id": patient["id"],
            "expected_version": 1,
            "action": "SIGN",
            "safety_review": "Synthetic manual review",
            "reason": "Synthetic actual prescriber intent",
            "intent_confirmed": True,
        },
    )
    approved = j.create(f"/workflows/substitutions/{proposal['id']}/decision", decision)
    assert (
        approved["status"] == "APPROVED"
        and j.get(f"/records/{original['id']}").json()["status"] == "STOPPED"
    )
    assert j.get(f"/records/{medication['id']}").json()["status"] == "VERIFIED"


def test_actual_immunisation_and_infusion_witness_are_not_inferred(care):
    j = care
    patient, encounter = j.encounter()
    team(j, patient, encounter)
    product, medication = j.medicine(patient, encounter)
    lot = j.create(
        "/stock",
        {
            "product_id": product["id"],
            "batch": "SYNTHETIC_IMMUNISATION_ONLY",
            "expires_at": stamp(4),
            "quantity": "10",
            "unit": "TEST_UNIT",
            "evidence": "Synthetic actual supply",
        },
        "pharmacy",
    )
    dispensed = j.create(
        "/dispenses",
        {
            **j.context(patient, encounter),
            "medication_id": medication["id"],
            "expected_order_version": 3,
            "lot_id": lot["id"],
            "expected_lot_version": 1,
            "quantity": "1",
            "verification": "Synthetic exact product",
            "patient_identity_check": "Synthetic independent identifiers",
        },
        "pharmacy",
    )
    slot = stamp(-1)
    occurrence = j.post(
        f"/medications/{medication['id']}/occurrence",
        {"patient_id": patient["id"], "scheduled_at": slot},
    ).json()
    given = j.create(
        "/administrations",
        {
            **j.context(patient, encounter),
            "medication_id": medication["id"],
            "expected_order_version": 3,
            "occurrence_key": occurrence["occurrence_key"],
            "scheduled_at": slot,
            "outcome": "GIVEN",
            "dose": "1",
            "dose_unit": "TEST_UNIT",
            "route": "TEST_ROUTE",
            "reason": "Synthetic actual event only",
            "patient_identity_check": "Synthetic identity evidence",
        },
        "nurse",
    )
    recorded = j.create(
        "/workflows/immunisations",
        {
            **j.context(patient, encounter),
            "administration_id": given["id"],
            "dispense_id": dispensed["id"],
            "schedule_reference": "SYNTHETIC_NOT_A_REAL_VACCINE_SCHEDULE",
            "next_review_owner_id": j.actors["clinician"][0],
            "next_review_due_at": stamp(1),
            "source": "Synthetic actual chain test",
            "policy_reference": "Synthetic manual documentation policy",
            "intent_confirmed": True,
        },
        "nurse",
    )
    assert recorded["data"]["automated_schedule_generated"] is False
    infusion = j.create(
        "/workflows/infusions",
        {
            **j.context(patient, encounter),
            "medication_id": medication["id"],
            "expected_medication_version": 3,
            "action": "MONITOR",
            "source": "Synthetic observation only",
            "policy_reference": "Synthetic manual review policy",
            "manual_check_reference": "SYNTHETIC_NO_DOSING_CALCULATION",
            "witness_id": j.actors["clinician"][0],
            "intent_confirmed": True,
        },
        "nurse",
    )
    assert infusion["data"]["witness_state"] == "AWAITING_PERSONAL_ATTESTATION"
    witness = actual(patient_id=patient["id"], expected_version=1, action="ATTEST")
    assert (
        j.post(f"/workflows/infusions/{infusion['id']}/witness", witness, "nurse").status_code
        == 403
    )
    receipt = j.create(f"/workflows/infusions/{infusion['id']}/witness", witness)
    assert receipt["data"]["witness_id"] == j.actors["clinician"][0]
    assert j.get(f"/records/{infusion['id']}").json()["version"] == 1


def test_procedure_monitoring_device_trace_and_owned_recall(care):
    j = care
    patient, encounter = j.encounter()
    consent = j.create(
        "/consents",
        {
            **j.context(patient, encounter),
            "intervention": "SYNTHETIC_ENGINEERING_ONLY",
            "decision": "CONSENTED",
            "capacity_assessment": "Synthetic actual assessment",
            "decision_maker": "Synthetic test subject",
            "representative_authority": "Synthetic subject decision",
            "explanation": "Synthetic actual explanation",
            "policy_reference": "Synthetic policy",
            "valid_until": stamp(3),
            "intent_confirmed": True,
        },
    )
    procedure = j.create(
        "/procedures",
        {
            **j.context(patient, encounter),
            "code": coding(),
            "indication": "Synthetic engineering workflow",
            "consent_id": consent["id"],
            "team_ids": [j.actors["clinician"][0]],
            "site": "SYNTHETIC_SITE",
            "readiness_evidence": "Synthetic actual readiness",
            "safety_policy_reference": "Synthetic actual policy",
            "result_owner_id": j.actors["clinician"][0],
        },
    )
    specialty = {
        **j.context(patient, encounter),
        "source": "Synthetic actual documentation",
        "policy_reference": "Synthetic policy reference",
        "intent_confirmed": True,
    }
    device_body = {
        **specialty,
        "procedure_id": procedure["id"],
        "device_identifier": "SYNTHETIC_UDI_ONLY",
        "manufacturer": "Synthetic source",
        "model": "Synthetic device",
        "serial_or_lot": "SYNTHETIC_TRACE_001",
        "actual_disposition": "USED",
        "actual_evidence": "Synthetic actual use",
    }
    assert j.post("/workflows/devices", device_body).status_code == 409
    for version, action in [(1, "SIGN_IN"), (2, "TIME_OUT"), (3, "PERFORM")]:
        procedure = j.create(
            f"/procedures/{procedure['id']}/actions",
            {
                "patient_id": patient["id"],
                "expected_version": version,
                "action": action,
                "participants": [j.actors["clinician"][0]],
                "findings": "Synthetic actual safety checks",
                "reason": "Synthetic actual procedural attestation",
                "actual_procedure": "Synthetic actual event" if action == "PERFORM" else None,
                "complications": "SYNTHETIC_UNKNOWN",
                "specimens": "SYNTHETIC_NONE",
                "implants_devices": "Synthetic exact device source",
                "occurred_at": stamp(-1),
                "intent_confirmed": True,
            },
        )
    monitoring = j.create(
        "/workflows/anaesthesia",
        {
            **specialty,
            "procedure_id": procedure["id"],
            "phase": "MAINTENANCE",
            "technique": "SYNTHETIC_NO_CLINICAL_ADVICE",
            "observations": [
                {
                    "code": coding(),
                    "absent_reason": "UNKNOWN",
                    "source": "Synthetic observed missingness",
                }
            ],
            "medication_evidence": "Synthetic no dosing supplied",
            "airway_and_monitoring": "Synthetic manual source",
            "complications": "SYNTHETIC_UNKNOWN",
            "plan": "Synthetic actual follow-up",
        },
    )
    assert monitoring["data"]["automated_score_or_dose_inferred"] is False
    device = j.create("/workflows/devices", device_body)
    traced = j.get("/worklist?kind=device_use&trace=SYNTHETIC_TRACE_001").json()["items"]
    assert [row["id"] for row in traced] == [device["id"]]
    assert j.get("/worklist?kind=device_use&trace=WRONG").json()["items"] == []
    recall = j.create(
        "/workflows/recalls",
        {
            **j.context(patient, encounter),
            "source_id": device["id"],
            "issuer_reference": "Synthetic actual recall notice",
            "action_plan": "Synthetic responsible clinical review",
            "owner_id": j.actors["clinician"][0],
            "due_at": stamp(1),
            "intent_confirmed": True,
        },
    )
    assert recall["data"]["exposure_or_harm_inferred"] is False
    assert any(
        row["data"].get("source_id") == recall["id"]
        for row in j.get("/worklist?kind=task").json()["items"]
    )


def test_nursing_owned_task_and_work_index_recovery_do_not_erase_care(care):
    j = care
    patient, encounter = j.encounter()
    team(j, patient, encounter)
    care_task = j.create(
        "/tasks",
        {
            **j.context(patient, encounter),
            "owner_capability": "NURSING",
            "title": "Synthetic actual nursing review",
            "instructions": "Synthetic unresolved bedside care",
            "owner_id": j.actors["nurse"][0],
            "due_at": stamp(1),
        },
        "nurse",
    )
    assert any(
        row["id"] == care_task["id"]
        for row in j.get("/worklist?kind=task", "nurse").json()["items"]
    )
    for version, action in [(1, "ACCEPT"), (2, "COMPLETE")]:
        care_task = j.create(
            f"/tasks/{care_task['id']}/actions",
            {
                "patient_id": patient["id"],
                "expected_version": version,
                "action": action,
                "reason": "Synthetic actual nursing action",
                "evidence": "Synthetic observed completion",
            },
            "nurse",
        )
    assert care_task["status"] == "COMPLETED"

    async def corrupt_index():
        async with j.app.state.database.transaction() as session:
            await session.execute(
                update(fi.index)
                .where(fi.index.c.record_id == care_task["id"])
                .values(indexed_version=0)
            )

    run(corrupt_index())
    assert not run(j.app.state.database.ready())
    assert j.get("/worklist?kind=task", "nurse").status_code == 503
    assert j.get(f"/records/{care_task['id']}", "nurse").json()["status"] == "COMPLETED"
    run(fi.rebuild(j.app.state.database, j.app.state.box, j.app.state.settings))
    assert run(j.app.state.database.ready())


def test_allergy_safety_context_survives_chart_pagination(care):
    j = care
    patient, encounter = j.encounter()
    allergy = j.create(
        "/allergies",
        {
            **j.context(patient, encounter),
            "assessment": "KNOWN",
            "agent": "SYNTHETIC_NONCLINICAL_AGENT",
            "reaction": "SYNTHETIC_OBSERVED_REACTION",
            "severity": "UNKNOWN",
            "source": "Synthetic attributed assessment",
        },
    )
    for _ in range(25):
        task(j, patient, encounter)
    page = j.get(f"/patients/{patient['id']}/chart").json()
    without_source = False
    while True:
        assert any(row["id"] == allergy["id"] for row in page["allergy_assessments"])
        without_source |= not any(row["id"] == allergy["id"] for row in page["items"])
        if not page["next_cursor"]:
            break
        page = j.get(f"/patients/{patient['id']}/chart?after={page['next_cursor']}").json()
    assert without_source
