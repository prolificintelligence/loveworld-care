"""Typed institutional commands, mapped to the LWH canonical forms in the implementation register."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

Role = Literal[
    "PLATFORM_ADMIN",
    "REGISTRY_STEWARD",
    "FACILITY_ADMIN",
    "ZONE_COORDINATOR",
    "REGIONAL_COORDINATOR",
    "INSPECTOR",
    "STANDARDS_REVIEWER",
    "STANDARDS_DECIDER",
    "CLINICAL_GOVERNOR",
    "CLINICAL_STAFF",
    "DATA_GOVERNOR",
    "REPORTING_OFFICER",
    "DATA_REVIEWER",
    "DATA_ANALYST",
    "EXECUTIVE_VIEWER",
    "PROGRAMME_OWNER",
    "SAFETY_REPORTER",
    "SAFETY_REVIEWER",
    "IDENTITY_REVIEWER",
    "PRIVACY_OFFICER",
    "FINANCE_GOVERNOR",
    "CONTENT_EDITOR",
    "POLICY_OWNER",
    "CONTENT_PUBLISHER",
]
SiteType = Literal[
    "COMMUNITY_PRIMARY", "INPATIENT_HOSPITAL", "MATERNAL_CHILD", "SPECIALIST_DIAGNOSTIC"
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*")
    @classmethod
    def normalise_dates(cls, value):
        if isinstance(value, datetime):
            if value.tzinfo is None:
                raise ValueError("An explicit time zone is required")
            return value.astimezone(UTC)
        return value

    @field_serializer("*", when_used="json")
    def serialise_dates(self, value):
        return value.isoformat(timespec="microseconds") if isinstance(value, datetime) else value


class AiControl(StrictModel):
    enabled: bool = Field(strict=True)


class Login(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)
    otp: str = Field(pattern=r"^\d{6}$")


class Enrol(StrictModel):
    token: str = Field(min_length=32, max_length=128)
    password: str = Field(min_length=14, max_length=256)


class ConfirmEnrolment(StrictModel):
    token: str = Field(min_length=32, max_length=128)
    otp: str = Field(pattern=r"^\d{6}$")


class Invite(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    name: str = Field(min_length=2, max_length=160)
    role: Role
    scope_type: Literal["GLOBAL", "REGION", "ZONE", "FACILITY"]
    scope_id: UUID | None = None
    valid_until: datetime

    @field_validator("email")
    @classmethod
    def email_format(cls, value):
        import re

        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Supply a valid email address")
        return value.lower()


class Unit(StrictModel):
    name: str = Field(min_length=2, max_length=160)
    code: str = Field(min_length=2, max_length=80)
    kind: Literal["REGION", "ZONE"]
    parent_id: UUID | None = None
    valid_from: datetime
    valid_until: datetime | None = None


class Operator(StrictModel):
    name: str = Field(min_length=2, max_length=160)
    external_reference: str = Field(min_length=3, max_length=160)


class Facility(StrictModel):
    operator_org_id: UUID
    zone_id: UUID
    site_name: str = Field(min_length=2, max_length=200)
    site_type: SiteType
    ownership_category: Literal["MINISTRY", "MEMBER_OWNED", "EXTERNAL"]
    jurisdiction_profile: str = Field(min_length=2, max_length=80)
    external_reference: str = Field(min_length=3, max_length=200)
    address: str = Field(min_length=5, max_length=2000)
    public_contact: str = Field(min_length=3, max_length=200)
    private_contact: str = Field(min_length=3, max_length=254)
    services: list[str] = Field(min_length=1, max_length=60)

    @field_validator("services")
    @classmethod
    def service_values(cls, value):
        if any(not s.strip() or len(s) > 120 for s in value):
            raise ValueError("Each service must contain 1 to 120 characters")
        return list(dict.fromkeys(s.strip() for s in value))


class Criterion(StrictModel):
    code: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=5, max_length=3000)
    required: bool


class CriteriaSet(StrictModel):
    name: str = Field(min_length=3, max_length=200)
    version: str = Field(min_length=1, max_length=40)
    jurisdiction: str = Field(min_length=2, max_length=80)
    site_type: SiteType
    requirements: list[Criterion] = Field(min_length=1, max_length=100)
    adoption_reference: str = Field(min_length=5, max_length=3000)
    valid_from: datetime
    valid_until: datetime


class Versioned(StrictModel):
    expected_version: int = Field(ge=1)


class Application(StrictModel):
    facility_id: UUID
    criteria_id: UUID


class Verification(Versioned):
    identity_status: Literal["VERIFIED", "DISPUTED"]
    statutory_status: Literal["PENDING", "CHECKED", "EXPIRED", "DISPUTED", "NOT_APPLICABLE"]
    reason: str = Field(min_length=5, max_length=3000)


class Assignment(Versioned):
    inspector_id: UUID
    reviewer_id: UUID


class Finding(StrictModel):
    criterion: str = Field(min_length=2, max_length=120)
    observation: str = Field(min_length=5, max_length=5000)
    outcome: Literal["MET", "NOT_MET", "NOT_OBSERVED"]
    evidence_ids: list[UUID] = Field(min_length=1, max_length=40)


class Inspection(Versioned):
    conflict_declared: bool
    observed_at: datetime
    findings: list[Finding] = Field(min_length=1, max_length=100)


class Recommendation(Versioned):
    decision: Literal["APPROVE", "CONDITIONAL", "REJECT"]
    reason: str = Field(min_length=5, max_length=5000)


class Decision(Recommendation):
    scope: str = Field(min_length=3, max_length=3000)
    conditions: str = Field(default="", max_length=5000)
    effective_at: datetime
    expires_at: datetime
    intent_confirmed: Literal[True]


class Publication(Versioned):
    action: Literal["PUBLISH", "WITHDRAW"]
    reason: str = Field(min_length=5, max_length=3000)
