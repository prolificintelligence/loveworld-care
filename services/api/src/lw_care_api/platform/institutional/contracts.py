"""Intentional lifecycle commands; no invented criteria, ministry wording or schedules."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, HttpUrl

from ..contracts import StrictModel
from ..control.contracts import Evidence


class Versioned(Evidence):
    expected_version: int = Field(ge=1)


class MasterChange(Evidence):
    kind: Literal["ZONE_REGION", "FACILITY_ZONE", "CLOSE_SITE", "LINK_DUPLICATE", "SITE_PROFILE"]
    resource_id: UUID
    target_id: UUID | None = None
    expected_version: int = Field(ge=1)
    effective_at: datetime | None = None
    custody_owner_id: UUID | None = None
    continuity_plan: str = Field(default="", max_length=12000)
    same_site_verified: bool = False
    site_name: str | None = Field(default=None, min_length=2, max_length=200)
    address: str | None = Field(default=None, min_length=5, max_length=2000)
    public_contact: str | None = Field(default=None, min_length=3, max_length=200)
    services: list[str] | None = Field(default=None, min_length=1, max_length=60)


class Review(Versioned):
    decision: Literal["APPROVE", "REJECT"]


class CaseOpen(Evidence):
    facility_id: UUID
    kind: Literal["RENEWAL", "NONCOMPLIANCE", "APPEAL", "REINSTATEMENT"]
    criteria_id: UUID
    base_decision_id: UUID | None = None
    respondent_id: UUID
    due_at: datetime
    calendar_authority_reference: str = Field(min_length=5, max_length=4000)


class Assign(Versioned):
    inspector_id: UUID
    reviewer_id: UUID
    competence_reference: str = Field(min_length=5, max_length=4000)


class Observation(StrictModel):
    criterion: str = Field(min_length=2, max_length=120)
    outcome: Literal["MET", "NOT_MET", "NOT_OBSERVED"]
    observation: str = Field(min_length=5, max_length=5000)
    evidence_ids: list[UUID] = Field(default_factory=list, max_length=40)
    due_at: datetime


class Inspection(Versioned):
    conflict_declared: Literal[False]
    observed_at: datetime
    findings: list[Observation] = Field(min_length=1, max_length=100)


class Response(Versioned):
    completion_evidence: str = Field(min_length=5, max_length=6000)
    evidence_ids: list[UUID] = Field(min_length=1, max_length=40)
    corrective_plan_id: UUID | None = None


class CorrectivePlan(Versioned):
    required_action: str = Field(min_length=5, max_length=6000)
    due_at: datetime
    deadline_authority_reference: str = Field(min_length=5, max_length=4000)


class CorrectivePlanReview(Versioned):
    plan_id: UUID
    decision: Literal["AGREE", "RETURN"]


class FindingReview(Versioned):
    response_id: UUID
    decision: Literal["RESOLVE", "RETURN"]


class Recommend(Versioned):
    action: Literal[
        "APPROVE",
        "CONDITIONAL",
        "RENEW",
        "REJECT",
        "SUSPEND",
        "REMOVE",
        "REINSTATE",
        "UPHOLD",
        "REMIT",
    ]


class Notice(Versioned):
    text: str = Field(min_length=5, max_length=12000)
    authority_reference: str = Field(min_length=5, max_length=4000)
    response_due: datetime


class AssignmentOffer(Versioned):
    assignment_kind: Literal["RESPONDENT", "INSPECTOR", "REVIEWER"]
    successor_id: UUID


class NoticeDelivery(Evidence):
    observed_at: datetime
    channel: Literal["IN_PERSON", "REGISTERED_POST", "OTHER_VERIFIED"]
    delivery_reference: str = Field(min_length=5, max_length=4000)


class AssignmentAccept(Versioned):
    assignment_kind: Literal["RESPONDENT", "INSPECTOR", "REVIEWER"]


class Decide(Recommend):
    scope: str = Field(min_length=3, max_length=3000)
    conditions: str = Field(default="", max_length=6000)
    expires_at: datetime | None = None
    custody_owner_id: UUID | None = None
    continuity_plan: str = Field(default="", max_length=12000)
    urgent_protective_action: bool = False
    protective_authority_reference: str = Field(default="", max_length=4000)


class ContentSource(StrictModel):
    title: str = Field(min_length=3, max_length=250)
    url: HttpUrl
    version_reference: str = Field(min_length=1, max_length=500)


class Content(Evidence):
    facility_id: UUID | None = None
    title: str = Field(min_length=3, max_length=250)
    kind: Literal[
        "HEALTH_EDUCATION", "CLINICAL_GUIDANCE", "PATIENT_RIGHTS", "MINISTRY_POLICY", "FAITH"
    ]
    audience: Literal["PUBLIC", "STAFF"]
    language: str = Field(
        min_length=2, max_length=40, pattern=r"^[A-Za-z]{2,8}(-[A-Za-z0-9]{1,8})*$"
    )
    jurisdictions: list[str] = Field(min_length=1, max_length=50)
    body: str = Field(min_length=10, max_length=60000)
    correction_summary: str = Field(default="", max_length=2000)
    purpose: str = Field(min_length=5, max_length=2000)
    support_text: str = Field(min_length=5, max_length=3000)
    support_url: HttpUrl
    licence_reference: str = Field(min_length=3, max_length=4000)
    sources: list[ContentSource] = Field(min_length=1, max_length=40)
    valid_from: datetime
    valid_until: datetime
    review_due_at: datetime


class Revision(Content):
    expected_version: int = Field(ge=1)


class ContentReview(Versioned):
    decision: Literal["APPROVE", "REJECT"]
    qualification_reference: str = Field(min_length=5, max_length=4000)


class Distribute(Versioned):
    recipient_ids: list[UUID] = Field(min_length=1, max_length=100)


class ContentReceipt(Evidence):
    revision_id: UUID
    kind: Literal["READ", "ACKNOWLEDGED", "SELF_REPORTED_UNDERSTANDING", "FEEDBACK"]
    feedback: str = Field(default="", max_length=4000)
    jurisdiction: str = Field(default="", max_length=80)
