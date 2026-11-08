"""EMR command contracts: PRD-012/015..021/024 and SPEC-018/019.

Clinical content is entered by the responsible professional. No clinical thresholds,
product catalogue, dose schedule or professional approval is seeded by this module.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from ..contracts import StrictModel

Text = Annotated[str, Field(min_length=1, max_length=12000)]
Short = Annotated[str, Field(min_length=1, max_length=160)]
Capability = Literal[
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
Quantity = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=6)]


class Activation(StrictModel):
    activation_package_id: UUID | None = None
    expected_version: int = Field(ge=0)
    services: list[Short] = Field(min_length=1, max_length=50)
    policy_reference: Text
    manual_medicine_policy: Text
    valid_from: datetime
    valid_until: datetime
    intent_confirmed: Literal[True]


class Privilege(StrictModel):
    account_id: UUID
    services: list[Short] = Field(min_length=1, max_length=50)
    capabilities: list[Capability] = Field(min_length=1, max_length=11)
    professional_reference: Text
    valid_from: datetime
    valid_until: datetime
    intent_confirmed: Literal[True]


class Versioned(StrictModel):
    expected_version: int = Field(ge=1)
    reason: Text


class Patient(StrictModel):
    display_name: Short
    provisional: bool = Field(strict=True)
    local_identifier: str | None = Field(default=None, min_length=1, max_length=120)
    birth_date: date | None = None
    birth_date_estimated: bool = Field(default=False, strict=True)
    sex: Literal["FEMALE", "MALE", "OTHER", "UNKNOWN"]
    phone: str | None = Field(default=None, max_length=80)
    address: str | None = Field(default=None, max_length=2000)
    identity_evidence: str | None = Field(default=None, max_length=3000)

    @model_validator(mode="after")
    def facts(self):
        if self.birth_date and self.birth_date > date.today():
            raise ValueError("Birth date cannot be in the future")
        if not self.provisional and not self.identity_evidence:
            raise ValueError("Record the evidence for confirmed identity")
        return self


class PatientCorrection(Patient):
    expected_version: int = Field(ge=1)
    reason: Text


class Context(StrictModel):
    patient_id: UUID
    encounter_id: UUID
    occurred_at: datetime


class Encounter(StrictModel):
    patient_id: UUID
    service: Short
    encounter_type: Literal["AMBULATORY", "EMERGENCY", "INPATIENT", "MATERNAL", "SPECIALIST"]
    arrival: Literal["BOOKED", "WALK_IN", "REFERRED", "EMERGENCY"]
    complaint: Text
    occurred_at: datetime


class Triage(Versioned):
    patient_id: UUID
    urgency: Short
    policy_reference: Text
    assessment: Text
    occurred_at: datetime


class Disposition(Versioned):
    patient_id: UUID
    disposition: Literal[
        "HOME", "ADMITTED", "REFERRED", "TRANSFERRED", "SELF_DISCHARGE", "DECEASED"
    ]
    signed_summary_id: UUID
    instructions: Text
    medication_reconciliation: Text
    follow_up_plan: Text
    occurred_at: datetime
    intent_confirmed: Literal[True]


class Note(Context):
    note_type: Literal[
        "CONSULTATION",
        "NURSING",
        "DISCHARGE",
        "ANTENATAL",
        "LABOUR",
        "BIRTH",
        "POSTNATAL",
        "NEWBORN",
        "CHILD_HEALTH",
        "IMMUNISATION",
        "CHRONIC_CARE",
        "MENTAL_HEALTH",
        "REHABILITATION",
        "ANAESTHESIA",
        "RECOVERY",
    ]
    narrative: Text
    history: str | None = Field(default=None, max_length=12000)
    examination: str | None = Field(default=None, max_length=12000)
    assessment: str | None = Field(default=None, max_length=12000)
    plan: str | None = Field(default=None, max_length=12000)
    source: Text
    confidentiality: Literal["STANDARD", "RESTRICTED"] = "STANDARD"
    amends_id: UUID | None = None
    amendment_reason: str | None = Field(default=None, min_length=3, max_length=3000)

    @model_validator(mode="after")
    def amendment(self):
        if self.amends_id and not self.amendment_reason:
            raise ValueError("An addendum/correction must identify its reason")
        return self


class NoteEdit(Note):
    expected_version: int = Field(ge=1)


class Sign(Versioned):
    patient_id: UUID
    intent_confirmed: Literal[True]


class Coding(StrictModel):
    system: Short
    code: Short
    display: Short
    version: Short


class Observation(Context):
    code: Coding
    value_decimal: Decimal | None = Field(default=None, max_digits=24, decimal_places=8)
    value_text: str | None = Field(default=None, max_length=4000)
    absent_reason: str | None = Field(default=None, max_length=1000)
    unit: str | None = Field(default=None, max_length=80)
    method: Short
    source: Text
    verification: Literal["CLINICIAN_RECORDED", "PATIENT_REPORTED", "EXTERNAL_UNVERIFIED"]

    @model_validator(mode="after")
    def value_semantics(self):
        if (
            sum(v is not None for v in (self.value_decimal, self.value_text, self.absent_reason))
            != 1
        ):
            raise ValueError("Supply exactly one typed value or an explicit absent reason")
        if self.value_decimal is not None and not self.unit:
            raise ValueError("A numeric observation requires its actual unit")
        return self


class Problem(Context):
    code: Coding
    certainty: Literal["SUSPECTED", "CONFIRMED", "HISTORICAL"]
    clinical_status: Literal["ACTIVE", "RESOLVED", "INACTIVE"]
    source: Text
    description: Text


class Allergy(Context):
    assessment: Literal["UNKNOWN", "NOT_ASSESSED", "NONE_KNOWN", "KNOWN"]
    agent: str | None = Field(default=None, max_length=500)
    reaction: str | None = Field(default=None, max_length=2000)
    severity: Literal["UNKNOWN", "MILD", "MODERATE", "SEVERE"] = "UNKNOWN"
    source: Text

    @model_validator(mode="after")
    def known_agent(self):
        if self.assessment == "KNOWN" and (not self.agent or not self.reaction):
            raise ValueError("Known allergy requires agent and reaction evidence")
        if self.assessment != "KNOWN" and (self.agent or self.reaction):
            raise ValueError("An agent/reaction requires a known allergy assessment")
        return self


class Consent(Context):
    intervention: Text
    decision: Literal["CONSENTED", "REFUSED", "WITHDRAWN", "OTHER_LAWFUL_AUTHORITY"]
    capacity_assessment: Text
    decision_maker: Short
    representative_authority: Text
    explanation: Text
    policy_reference: Text
    valid_until: datetime
    supersedes_id: UUID | None = None
    intent_confirmed: Literal[True]


class Task(Context):
    owner_capability: Literal["CARE", "NURSING"] = "CARE"
    title: Short
    instructions: Text
    owner_id: UUID
    due_at: datetime
    source_id: UUID | None = None


class TaskAction(Versioned):
    patient_id: UUID
    action: Literal[
        "ACCEPT", "START", "COMPLETE", "BLOCK", "REOPEN", "OFFER_HANDOVER", "ACCEPT_HANDOVER"
    ]
    successor_id: UUID | None = None
    evidence: Text


class Order(Context):
    order_type: Literal["LABORATORY", "IMAGING", "SERVICE"]
    code: Coding
    clinical_question: Text
    priority: Short
    result_owner_id: UUID


class OrderAction(Versioned):
    patient_id: UUID
    action: Literal["SIGN", "ACCEPT", "START", "HOLD", "CANCEL", "REJECT"]
    intent_confirmed: Literal[True]


class Specimen(Context):
    order_id: UUID
    accession: Short
    specimen_type: Short
    label_check: Text
    condition: Text


class SpecimenAction(Versioned):
    patient_id: UUID
    action: Literal["COLLECT", "RECEIVE", "REJECT", "ANALYSE"]
    evidence: Text
    occurred_at: datetime


class Result(Context):
    order_id: UUID
    specimen_id: UUID | None = None
    observations: list[Observation] = Field(min_length=1, max_length=100)
    interpretation: Text
    method: Text
    reference_context: Text
    source: Text
    critical: bool = Field(strict=True)
    critical_policy_reference: str | None = Field(default=None, max_length=3000)
    study_identifier: str | None = Field(default=None, max_length=200)
    corrects_id: UUID | None = None
    correction_reason: str | None = Field(default=None, max_length=3000)

    @model_validator(mode="after")
    def result_context(self):
        if self.critical and not self.critical_policy_reference:
            raise ValueError("A critical flag requires its applicable clinical policy")
        if self.corrects_id and not self.correction_reason:
            raise ValueError("A corrected report requires its reason")
        for observation in self.observations:
            if (observation.patient_id, observation.encounter_id) != (
                self.patient_id,
                self.encounter_id,
            ):
                raise ValueError("Result observations must match the report patient and encounter")
        return self


class ResultAction(Versioned):
    patient_id: UUID
    action: Literal["RELEASE", "ACKNOWLEDGE", "REVIEW", "COMMUNICATE"]
    clinical_response: Text
    intent_confirmed: Literal[True]


class Product(StrictModel):
    code: Coding
    ingredient: Text
    form: Short
    strength: Short
    strength_unit: Short
    permitted_routes: list[Short] = Field(min_length=1, max_length=20)
    formulary_reference: Text
    valid_until: datetime


class Medication(Context):
    product_id: UUID
    indication: Text
    dose: Quantity
    dose_unit: Short
    route: Short
    timing: Text
    starts_at: datetime
    stops_at: datetime
    substitution: Literal["NOT_PERMITTED", "PHARMACIST_APPROVED_EQUIVALENT"]
    manual_safety_review: Text
    reconciliation: Text

    @model_validator(mode="after")
    def timing_range(self):
        if self.stops_at <= self.starts_at:
            raise ValueError("Stop time must follow start time")
        return self


class MedicationAction(Versioned):
    patient_id: UUID
    action: Literal["SIGN", "VERIFY", "HOLD", "RESUME", "STOP"]
    safety_review: Text
    intent_confirmed: Literal[True]


class Lot(StrictModel):
    product_id: UUID
    batch: Short
    expires_at: datetime
    quantity: Quantity
    unit: Short
    evidence: Text


class LotAction(Versioned):
    action: Literal["QUARANTINE", "RECALL", "RELEASE"]


class Dispense(Context):
    reservation_id: UUID | None = None
    medication_id: UUID
    expected_order_version: int = Field(ge=1)
    lot_id: UUID
    expected_lot_version: int = Field(ge=1)
    quantity: Quantity
    verification: Text
    patient_identity_check: Text


class Administration(Context):
    medication_id: UUID
    expected_order_version: int = Field(ge=1)
    occurrence_key: str = Field(min_length=8, max_length=160)
    scheduled_at: datetime
    outcome: Literal["GIVEN", "OMITTED", "REFUSED", "HELD"]
    dose: Quantity | None = None
    dose_unit: str | None = Field(default=None, max_length=160)
    route: str | None = Field(default=None, max_length=160)
    reason: Text
    patient_identity_check: Text

    @model_validator(mode="after")
    def actual_dose(self):
        if self.outcome == "GIVEN" and (not self.dose or not self.dose_unit or not self.route):
            raise ValueError("Actual administration requires dose, unit and route")
        if self.outcome != "GIVEN" and self.dose is not None:
            raise ValueError("An omitted dose cannot also be recorded as given")
        return self


class Bed(StrictModel):
    ward: Short
    label: Short


class Admission(Context):
    admission_order_id: UUID | None = None
    bed_id: UUID
    expected_bed_version: int = Field(ge=1)
    responsible_clinician_id: UUID
    responsible_nurse_id: UUID
    indication: Text
    signed_admission_note_id: UUID


class StayAction(Versioned):
    patient_id: UUID
    action: Literal["OFFER_TRANSFER", "ACCEPT_TRANSFER", "DISCHARGE"]
    receiving_bed_id: UUID | None = None
    receiving_clinician_id: UUID | None = None
    receiving_nurse_id: UUID | None = None
    signed_summary_id: UUID | None = None
    instructions: str | None = Field(default=None, max_length=12000)
    medication_reconciliation: str | None = Field(default=None, max_length=12000)
    occurred_at: datetime
    intent_confirmed: Literal[True]


class Programme(Context):
    programme_type: Literal[
        "MATERNAL", "NEWBORN", "CHILD", "CHRONIC", "MENTAL_HEALTH", "REHABILITATION"
    ]
    policy_reference: Text
    goals: Text
    baseline: Text
    review_at: datetime
    responsible_id: UUID
    linked_patient_id: UUID | None = None
    relationship_evidence: str | None = Field(default=None, max_length=3000)


class ProgrammeReview(Versioned):
    patient_id: UUID
    findings: Text
    plan: Text
    next_review_at: datetime
    occurred_at: datetime


class Procedure(Context):
    code: Coding
    indication: Text
    site: Short
    consent_id: UUID
    team_ids: list[UUID] = Field(min_length=1, max_length=30)
    readiness_evidence: Text
    safety_policy_reference: Text
    result_owner_id: UUID


class ProcedureAction(Versioned):
    patient_id: UUID
    action: Literal[
        "SIGN_IN", "TIME_OUT", "PERFORM", "SIGN_OUT", "OFFER_HANDOVER", "ACCEPT_HANDOVER", "CANCEL"
    ]
    findings: Text
    participants: list[UUID] = Field(min_length=1, max_length=30)
    actual_procedure: str | None = Field(default=None, max_length=12000)
    specimens: str | None = Field(default=None, max_length=4000)
    implants_devices: str | None = Field(default=None, max_length=4000)
    complications: str | None = Field(default=None, max_length=4000)
    successor_id: UUID | None = None
    occurred_at: datetime
    intent_confirmed: Literal[True]


class Transfusion(Context):
    procedure_id: UUID
    component_identifier: Short
    component_type: Short
    blood_bank_authorisation: Text
    compatibility_evidence: Text
    patient_unit_check: Text
    witness_id: UUID


class TransfusionAction(Versioned):
    patient_id: UUID
    action: Literal["START", "MONITOR", "STOP", "COMPLETE", "REACTION"]
    observation: Text
    witness_id: UUID
    occurred_at: datetime
    intent_confirmed: Literal[True]


class Referral(Context):
    destination: Text
    reason: Text
    summary_note_id: UUID
    sharing_grant_id: UUID
    owner_id: UUID


class ReferralAction(Versioned):
    patient_id: UUID
    action: Literal["REQUEST", "RECORD_ACCEPTANCE", "TRANSFER", "CLOSE", "CANCEL"]
    receiver_name: str | None = Field(default=None, max_length=200)
    acceptance_evidence: str | None = Field(default=None, max_length=4000)
    actual_handover: str | None = Field(default=None, max_length=4000)
    occurred_at: datetime


class RecordError(Versioned):
    patient_id: UUID
    intent_confirmed: Literal[True]


class SharingGrant(Context):
    recipient: Short
    purpose: Literal["REFERRAL", "CONTINUITY", "PATIENT_COPY"]
    record_ids: list[UUID] = Field(min_length=1, max_length=200)
    lawful_authority: Text
    decision_maker: Short
    authority_evidence: Text
    valid_until: datetime
    intent_confirmed: Literal[True]


class Disclosure(StrictModel):
    patient_id: UUID
    sharing_grant_id: UUID
    recipient: Short
    purpose: Literal["REFERRAL", "CONTINUITY", "PATIENT_COPY"]


class Appointment(StrictModel):
    patient_id: UUID
    service: Short
    clinician_id: UUID
    starts_at: datetime
    ends_at: datetime
    reason: Text

    @model_validator(mode="after")
    def time_range(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("End time must follow start time")
        return self


class AppointmentAction(Versioned):
    patient_id: UUID
    action: Literal["CONFIRM", "ARRIVE", "NO_SHOW", "CANCEL"]


class IdentityLink(StrictModel):
    patient_id: UUID
    other_patient_id: UUID
    evidence: Text
    reason: Text


class IdentityLinkAction(Versioned):
    patient_id: UUID
    action: Literal["ACCEPT", "DISPUTE", "REVOKE"]


class Tariff(StrictModel):
    code: Short
    description: Text
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    amount_minor: int = Field(strict=True, gt=0, le=10**12)
    approval_reference: Text
    valid_until: datetime


class Invoice(StrictModel):
    patient_id: UUID
    service_record_id: UUID
    tariff_id: UUID
    actual_service_evidence: Text


class CashReceipt(StrictModel):
    patient_id: UUID
    invoice_id: UUID
    expected_invoice_version: int = Field(ge=1)
    amount_minor: int = Field(strict=True, gt=0, le=10**12)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    receipt_reference: Short
    actual_cash_evidence: Text
    received_at: datetime
    intent_confirmed: Literal[True]


class Search(StrictModel):
    query: str = Field(min_length=2, max_length=160)
    after: str = Field(default="", max_length=36)


class TeamOffer(Versioned):
    patient_id: UUID
    account_id: UUID
    capability: Literal["CARE", "NURSING"]


class Occurrence(StrictModel):
    patient_id: UUID
    scheduled_at: datetime
