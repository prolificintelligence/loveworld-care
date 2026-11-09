"""Versioned institutional reporting commands (PRD-004..008, SPEC-007/008/014)."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dateutil.zoneinfo import get_zonefile_instance
from pydantic import Field, field_validator, model_validator

from ..contracts import StrictModel

Text = Annotated[str, Field(min_length=3, max_length=12000)]
Short = Annotated[str, Field(min_length=1, max_length=200)]
Nonnegative = Annotated[Decimal, Field(ge=0, max_digits=24, decimal_places=8)]
Stream = Literal["FACILITY_ACTIVITY", "ZONE_COMMUNITY", "REGIONAL_COORDINATION"]
ScopeType = Literal["GLOBAL", "REGION", "ZONE", "FACILITY"]


class Versioned(StrictModel):
    expected_version: int = Field(ge=1)
    reason: Text


class Scope(StrictModel):
    scope_type: ScopeType
    scope_id: UUID | None = None


class Definition(StrictModel):
    metric_id: str = Field(pattern=r"^LWH-MET-\d{3}$")
    definition_version: str = Field(min_length=1, max_length=40)
    name: Short
    stream: Stream
    formula: Literal["COUNT", "RATIO", "DECIMAL"]
    unit: Short
    aggregation: Literal["SUM", "RATIO_OF_SUMS", "NONE"]
    numerator_is_subset: bool = Field(default=False, strict=True)
    scale: Decimal = Field(default=Decimal(1), gt=0, max_digits=12, decimal_places=6)
    source_selector: Literal["MANUAL", "EMR_COMPLETED_ENCOUNTERS"]
    numerator_definition: Text
    denominator_definition: Text
    population_definition: Text
    inclusion_exclusion: Text
    dimensions: list[Short] = Field(min_length=1, max_length=20)
    maximum_value: Nonnegative | None = None
    warning_change_fraction: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=6
    )
    less_or_equal_metric: str | None = Field(default=None, pattern=r"^LWH-MET-\d{3}$")
    adoption_reference: Text
    template_reconciliation: Text
    valid_from: datetime
    valid_until: datetime
    intent_confirmed: Literal[True]

    @model_validator(mode="after")
    def semantics(self):
        if self.valid_until <= self.valid_from:
            raise ValueError("Definition validity must be ordered")
        if self.formula == "RATIO" and self.aggregation == "SUM":
            raise ValueError("Ratios cannot be added")
        if self.formula != "RATIO" and self.aggregation == "RATIO_OF_SUMS":
            raise ValueError("Ratio-of-sums requires a ratio definition")
        if self.metric_id == "LWH-MET-011" and self.aggregation != "NONE":
            raise ValueError(
                "Distinct people cannot be added across reporting units without reviewed identity reconciliation"
            )
        if self.source_selector == "EMR_COMPLETED_ENCOUNTERS" and (
            self.metric_id != "LWH-MET-010"
            or self.formula != "COUNT"
            or self.stream != "FACILITY_ACTIVITY"
        ):
            raise ValueError(
                "The completed-encounter extractor applies only to the facility service-contact definition"
            )
        return self


class Obligation(Scope):
    template_id: UUID | None = None
    template_version: int | None = Field(default=None, ge=1)
    stream: Stream
    period_start: datetime
    period_end: datetime
    due_at: datetime
    timezone: str = Field(min_length=1, max_length=80)
    definition_ids: list[UUID] = Field(min_length=1, max_length=45)
    adoption_reference: Text

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            # Windows lacks a system IANA database. The already-pinned dateutil
            # distribution supplies the identifier catalogue; period instants
            # remain explicitly submitted UTC-aware values, never guessed offsets.
            if value not in get_zonefile_instance().zones:
                raise ValueError("Use a recognised IANA reporting time zone") from exc
        except ValueError as exc:
            raise ValueError("Use a recognised IANA reporting time zone") from exc
        return value

    @model_validator(mode="after")
    def period(self):
        if (self.template_id is None) != (self.template_version is None):
            raise ValueError("Supply both template identifier and adopted version")
        if self.period_end <= self.period_start or self.due_at < self.period_end:
            raise ValueError("Reporting period and deadline must be ordered")
        if self.scope_type == "GLOBAL" or self.scope_id is None:
            raise ValueError("An obligation requires an actual facility, zone or region")
        return self


class MetricValue(StrictModel):
    definition_id: UUID
    completeness: Literal["VALUE", "NIL", "PARTIAL", "UNKNOWN", "MISSING", "NOT_APPLICABLE"]
    value: Nonnegative | None = None
    numerator: Nonnegative | None = None
    denominator: Nonnegative | None = None
    source_reference: str | None = Field(default=None, max_length=3000)
    explanation: str | None = Field(default=None, max_length=3000)
    extract_id: UUID | None = None

    @model_validator(mode="after")
    def missingness(self):
        if self.completeness in {"UNKNOWN", "MISSING", "NOT_APPLICABLE"} and (
            any(v is not None for v in (self.value, self.numerator, self.denominator))
            or not self.explanation
        ):
            raise ValueError("Absent values require a reason and cannot also contain a number")
        if self.completeness == "NIL" and self.value != 0:
            raise ValueError("An explicit nil count requires value zero")
        if self.completeness == "PARTIAL" and not self.explanation:
            raise ValueError("Partial coverage requires its limitation")
        return self


class ReturnDraft(StrictModel):
    expected_version: int = Field(ge=0)
    values: list[MetricValue] = Field(min_length=1, max_length=45)
    source_method: Text
    reconciliation: Text
    reason: Text


class Attest(Versioned):
    intent_confirmed: Literal[True]


class Review(Attest):
    decision: Literal["VERIFY", "RETURN_FOR_CORRECTION"]
    evidence_examined: Text
    method: Text
    verification_scope: Text
    warning_overrides: dict[str, Text] = Field(default_factory=dict, max_length=100)


class Import(StrictModel):
    expected_version: int = Field(ge=0)
    csv_text: str = Field(min_length=1, max_length=524288)
    source_method: Text
    reconciliation: Text


class DisclosurePolicy(StrictModel):
    name: Short
    policy_version: str = Field(min_length=1, max_length=40)
    purpose: Literal["DIRECTORATE_OVERSIGHT", "STRATEGIC_LEADERSHIP"]
    allowed_metric_ids: list[str] = Field(min_length=1, max_length=45)
    minimum_units: int = Field(strict=True, ge=2, le=1000)
    minimum_cell: int = Field(strict=True, ge=2, le=10000)
    minimum_change: int = Field(strict=True, ge=2, le=10000)
    allow_partial: bool = Field(strict=True)
    adoption_reference: Text
    risk_assessment: Text
    valid_from: datetime
    valid_until: datetime
    intent_confirmed: Literal[True]


class Cohort(Scope):
    name: Short
    obligation_ids: list[UUID] = Field(min_length=1, max_length=500)
    policy_id: UUID


class Snapshot(StrictModel):
    cohort_id: UUID


class SnapshotReview(StrictModel):
    decision: Literal["RELEASE", "REJECT"]
    reason: Text
    intent_confirmed: Literal[True]


class EventCategory(StrictModel):
    name: Short
    category_version: str = Field(min_length=1, max_length=40)
    definition: Text
    acknowledgement_minutes: int = Field(strict=True, ge=1, le=43200)
    escalation_owner_id: UUID
    adoption_reference: Text
    external_reporting_obligations: Text
    external_receipt_required: bool = Field(strict=True)
    valid_from: datetime
    valid_until: datetime
    intent_confirmed: Literal[True]


class DutyWindow(Scope):
    account_id: UUID
    valid_from: datetime
    valid_until: datetime
    evidence: Text


class Evidence(StrictModel):
    evidence: Text


class SafetyCase(Scope):
    category_id: UUID
    occurred_at: datetime
    source: Text
    location_precision: Short
    description: Text
    urgent: bool = Field(strict=True)
    immediate_local_action: Text


class CaseAction(Versioned):
    action: Literal[
        "ASSIGN",
        "OFFER_HANDOVER",
        "ACCEPT_HANDOVER",
        "ACKNOWLEDGE",
        "START_REVIEW",
        "VERIFY",
        "UNSUBSTANTIATED",
        "DUPLICATE",
        "CLOSE",
        "REOPEN",
        "RECORD_EXTERNAL_RECEIPT",
    ]
    reviewer_id: UUID | None = None
    related_case_id: UUID | None = None
    evidence: Text
    contributing_factors: str | None = Field(default=None, max_length=12000)
    external_agency: str | None = Field(default=None, max_length=200)
    external_receipt: str | None = Field(default=None, max_length=3000)
    occurred_at: datetime


class Action(Scope):
    title: Short
    intended_result: Text
    source_type: Literal["RETURN", "SAFETY_CASE", "SNAPSHOT", "JUSTIFIED_REQUEST"]
    source_id: UUID | None = None
    justification: Text
    owner_id: UUID
    fallback_id: UUID
    reviewer_id: UUID
    due_at: datetime
    review_at: datetime
    resources: Text
    resource_state: Literal["NOT_REQUIRED", "AWAITING_APPROVAL", "APPROVED"]
    budget_authority: Text
    dependencies: Text


class ActionUpdate(Versioned):
    action: Literal[
        "ACCEPT",
        "START",
        "BLOCK",
        "PROGRESS",
        "SUBMIT_EVIDENCE",
        "ACCEPT_COMPLETION",
        "REJECT_COMPLETION",
        "REOPEN",
        "OFFER_HANDOVER",
        "ACCEPT_HANDOVER",
        "RESOURCE_APPROVAL",
        "OUTCOME_REVIEW",
    ]
    evidence: Text
    successor_id: UUID | None = None
    outcome: str | None = Field(default=None, max_length=12000)
    limitations: str | None = Field(default=None, max_length=12000)
    follow_up_at: datetime | None = None
