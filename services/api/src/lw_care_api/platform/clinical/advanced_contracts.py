"""Phase 5 native extension LWH-EXT-CLINICAL-030..039; no adopted clinical rules seeded."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from ..contracts import StrictModel
from .contracts import Coding, Context, Quantity, Short, Text, Versioned


class Action(Versioned):
    patient_id: UUID | None = None
    action: Short
    occurred_at: datetime
    intent_confirmed: Literal[True]


class Capacity(StrictModel):
    service: Short
    max_open_encounters: int = Field(ge=0, le=100000)
    resources_evidence: Text
    policy_reference: Text
    starts_at: datetime
    ends_at: datetime
    require_roster: bool = Field(strict=True)
    require_admission_order: bool = Field(strict=True)
    intent_confirmed: Literal[True]


class Shift(StrictModel):
    service: Short
    account_id: UUID
    capability: Literal["CARE", "NURSING", "DIAGNOSTICS", "PHARMACY", "PROCEDURE"]
    capacity: int = Field(ge=1, le=10000)
    starts_at: datetime
    ends_at: datetime
    policy_reference: Text
    reason: Text
    intent_confirmed: Literal[True]


class CapacityRevision(Capacity):
    expected_version: int = Field(ge=1)
    reason: Text


class Handover(Context):
    expected_encounter_version: int = Field(ge=1)
    recipient_id: UUID
    capability: Literal["CARE", "NURSING"]
    summary: Text
    due_at: datetime
    reason: Text
    intent_confirmed: Literal[True]


class AdmissionOrder(Context):
    signed_note_id: UUID
    intended_ward: Short
    reason: Text
    policy_reference: Text
    intent_confirmed: Literal[True]


class BedHold(Context):
    admission_order_id: UUID
    expected_order_version: int = Field(ge=1)
    bed_id: UUID
    expected_bed_version: int = Field(ge=1)
    expires_at: datetime
    reason: Text
    intent_confirmed: Literal[True]


class WardEvent(Versioned):
    patient_id: UUID
    action: Literal[
        "LEAVE",
        "RETURN",
        "SELF_DISCHARGE",
        "DEATH",
        "RELEASE_BED",
        "DECLINE_TRANSFER",
        "ACCEPT_NURSING",
    ]
    occurred_at: datetime
    signed_summary_id: UUID | None = None
    policy_reference: Text
    instructions: Text | None = None
    medication_reconciliation: Text | None = None
    follow_up_owner_id: UUID | None = None
    expected_return_at: datetime | None = None
    actual_evidence: Text
    expected_bed_version: int | None = Field(default=None, ge=1)
    intent_confirmed: Literal[True]

    @model_validator(mode="after")
    def disposition_evidence(self):
        if self.action in {"LEAVE", "SELF_DISCHARGE", "DEATH"} and not all(
            (
                self.signed_summary_id,
                self.instructions,
                self.medication_reconciliation,
                self.follow_up_owner_id,
            )
        ):
            raise ValueError(
                "A final or leave disposition requires the signed summary, reviewed plan and follow-up owner"
            )
        if self.action == "RELEASE_BED" and self.expected_bed_version is None:
            raise ValueError("Releasing a bed requires its current source version")
        return self


class Nursing(Context):
    assessment: Text
    plan: Text
    escalation: Text
    source: Text
    amends_id: UUID | None = None
    amendment_reason: Text | None = None
    intent_confirmed: Literal[True]


class Fluid(Context):
    direction: Literal["INTAKE", "OUTPUT"]
    route_or_source: Short
    quantity: Quantity
    unit: Short
    method: Short
    source: Text
    amends_id: UUID | None = None
    amendment_reason: Text | None = None
    intent_confirmed: Literal[True]


class Measurement(StrictModel):
    code: Coding
    value: Decimal | None = Field(default=None, max_digits=24, decimal_places=8)
    unit: Short | None = None
    absent_reason: Short | None = None
    source: Text

    @model_validator(mode="after")
    def actual_value(self):
        if (
            (self.value is None) == (self.absent_reason is None)
            or self.value is not None
            and not self.unit
        ):
            raise ValueError("Record an actual value/unit or explicit missingness")
        return self


class Specialty(Context):
    programme_id: UUID | None = None
    source: Text
    policy_reference: Text
    amends_id: UUID | None = None
    amendment_reason: Text | None = None
    intent_confirmed: Literal[True]


class Labour(Specialty):
    dating_source: Text
    dating_uncertainty: Text
    gestation_days: int | None = Field(default=None, ge=0)
    labour_stage_as_assessed: Short
    observations: list[Measurement] = Field(min_length=1, max_length=30)
    assessment: Text
    plan: Text
    review_owner_id: UUID
    review_due_at: datetime


class Infant(StrictModel):
    patient_id: UUID
    encounter_id: UUID
    birth_order: int = Field(ge=1)
    outcome: Literal["LIVE_BIRTH", "STILLBIRTH", "UNKNOWN"]
    occurred_at: datetime
    relationship_evidence: Text
    observations: list[Measurement] = Field(min_length=1, max_length=20)
    follow_up_owner_id: UUID
    follow_up_due_at: datetime


class Birth(Specialty):
    signed_note_id: UUID
    mode_as_recorded: Short
    maternal_outcome: Text
    actual_team: list[UUID] = Field(min_length=1, max_length=30)
    infants: list[Infant] = Field(min_length=1, max_length=10)
    maternal_review_owner_id: UUID
    maternal_review_due_at: datetime


class Growth(Specialty):
    age_context: Text
    measurements: list[Measurement] = Field(min_length=1, max_length=20)
    interpretation_as_assessed: Text
    review_owner_id: UUID
    review_due_at: datetime


class Immunisation(Specialty):
    administration_id: UUID
    dispense_id: UUID
    schedule_reference: Text
    next_review_owner_id: UUID
    next_review_due_at: datetime


class ReconciledMedicine(StrictModel):
    medicine_id: UUID | None = None
    external_description: Text | None = None
    source: Text
    assessment: Literal["CONTINUE", "STOP", "CHANGE", "UNKNOWN", "NOT_TAKEN"]
    reason: Text


class Reconciliation(Context):
    transition: Literal["ADMISSION", "TRANSFER", "REVIEW", "DISCHARGE"]
    allergy_review: Text
    items: list[ReconciledMedicine] = Field(min_length=1, max_length=100)
    unresolved_owner_id: UUID
    review_due_at: datetime
    instructions: Text
    policy_reference: Text
    intent_confirmed: Literal[True]


class StockHold(Context):
    medication_id: UUID
    expected_medication_version: int = Field(ge=1)
    lot_id: UUID
    expected_lot_version: int = Field(ge=1)
    quantity: Quantity
    unit: Short
    expires_at: datetime
    reason: Text
    intent_confirmed: Literal[True]


class Adjustment(StrictModel):
    lot_id: UUID
    expected_lot_version: int = Field(ge=1)
    quantity: Decimal = Field(max_digits=18, decimal_places=6)
    unit: Short
    disposition: Literal["AVAILABLE", "QUARANTINED"]
    physical_evidence: Text
    policy_reference: Text
    reason: Text
    intent_confirmed: Literal[True]


class StockReturn(Adjustment):
    dispense_id: UUID
    patient_id: UUID


class Substitution(Context):
    medication_id: UUID
    expected_medication_version: int = Field(ge=1)
    replacement_product_id: UUID
    prescriber_id: UUID
    reason: Text
    policy_reference: Text
    intent_confirmed: Literal[True]


class SubstituteDecision(Action):
    action: Literal["APPROVE", "REJECT"]
    replacement_medication_id: UUID | None = None


class Anaesthesia(Specialty):
    procedure_id: UUID
    phase: Literal["PRE_ASSESSMENT", "INDUCTION", "MAINTENANCE", "EMERGENCE", "RECOVERY"]
    technique: Short
    observations: list[Measurement] = Field(min_length=1, max_length=30)
    medication_evidence: Text
    airway_and_monitoring: Text
    complications: Text
    plan: Text


class Device(Specialty):
    procedure_id: UUID
    device_identifier: Short
    manufacturer: Short
    model: Short
    serial_or_lot: Short
    expires_at: datetime | None = None
    actual_disposition: Literal["IMPLANTED", "USED", "REMOVED"]
    actual_evidence: Text


class Recall(Context):
    source_id: UUID
    issuer_reference: Text
    action_plan: Text
    owner_id: UUID
    due_at: datetime
    intent_confirmed: Literal[True]


class Instructions(Context):
    signed_summary_id: UUID
    language: Short
    instructions: Text
    warning_and_contact_plan: Text
    pending_work_explained: Text
    medicine_plan: Text
    review_owner_id: UUID
    review_due_at: datetime
    communication: Literal["PREPARED", "GIVEN_IN_PERSON", "ACTUAL_AUTHORISED_COMMUNICATION"]
    communication_evidence: Text
    intent_confirmed: Literal[True]


class Infusion(Specialty):
    medication_id: UUID
    expected_medication_version: int = Field(ge=1)
    action: Literal["START", "RATE_CHANGE", "MONITOR", "STOP"]
    actual_rate: Quantity | None = None
    rate_unit: Short | None = None
    actual_volume: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    volume_unit: Short | None = None
    manual_check_reference: Text
    witness_id: UUID
