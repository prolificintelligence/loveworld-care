"""Typed commands for LWH-PRD-023 and the LWH-FRM-022 representative authority fields."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from ..contracts import Invite, StrictModel

Permission = Literal["READ", "REQUEST", "SHARE"]


class Enrolment(StrictModel):
    name: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=3, max_length=254)

    @field_validator("email")
    @classmethod
    def normalised_email(cls, value):
        return Invite.email_format(value)


class LinkRequest(StrictModel):
    facility_id: UUID
    relationship: Literal["SELF", "REPRESENTATIVE"]
    patient_reference: str = Field(min_length=3, max_length=500)
    relationship_basis: str = Field(min_length=3, max_length=2000)


class Decision(StrictModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=4000)


class LinkReview(Decision):
    decision: Literal["APPROVE", "DENY"]
    patient_id: UUID | None = None
    expected_patient_version: int | None = Field(default=None, ge=1)
    permissions: list[Permission] = Field(default_factory=list, max_length=3)
    valid_until: datetime | None = None
    review_at: datetime | None = None
    authority_type: str = Field(min_length=3, max_length=500)
    evidence_examined: str = Field(min_length=5, max_length=4000)
    policy_reference: str = Field(min_length=5, max_length=2000)
    intent_confirmed: Literal[True]


class Share(StrictModel):
    recipient_account_id: UUID
    relationship_basis: str = Field(min_length=5, max_length=2000)
    intent_confirmed: Literal[True]


class Service(StrictModel):
    name: str = Field(min_length=3, max_length=160)
    primary_id: UUID
    fallback_id: UUID
    response_minutes: int = Field(ge=15, le=10080)
    valid_until: datetime
    policy_reference: str = Field(min_length=5, max_length=2000)
    intent_confirmed: Literal[True]


class ServiceAction(Decision):
    action: Literal["ACCEPT_DUTY", "PAUSE"]


class Release(StrictModel):
    source_id: UUID
    expected_source_version: int = Field(ge=1)
    kind: Literal["PLAN", "MEDICINE", "APPOINTMENT", "RESULT", "TIMELINE"]
    title: str = Field(min_length=3, max_length=160)
    readable_text: str = Field(min_length=5, max_length=8000)
    release_basis: str = Field(min_length=5, max_length=2000)
    due_at: datetime | None = None
    intent_confirmed: Literal[True]


class Withdrawal(StrictModel):
    reason: str = Field(min_length=5, max_length=2000)


class CareRequest(StrictModel):
    service_id: UUID
    kind: Literal["CARE", "CORRECTION", "SELF_REPORT"]
    text: str = Field(min_length=5, max_length=4000)


class RequestAction(Decision):
    action: Literal["ACCEPT", "RESPOND", "CLOSE", "OFFER_HANDOVER", "ACCEPT_HANDOVER"]
    text: str | None = Field(default=None, min_length=5, max_length=4000)
    successor_id: UUID | None = None


class Reply(Decision):
    text: str = Field(min_length=5, max_length=4000)


class Preferences(StrictModel):
    expected_version: int = Field(ge=0)
    in_app_reminders: bool = Field(strict=True)


class Search(StrictModel):
    query: str = Field(min_length=2, max_length=160)
    after: str = Field(default="", max_length=80)
