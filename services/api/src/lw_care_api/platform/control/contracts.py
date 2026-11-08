"""Typed control commands; adoption and review are explicit human actions."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from ..contracts import StrictModel


class Evidence(StrictModel):
    evidence: str = Field(min_length=3, max_length=12000)
    intent_confirmed: Literal[True]


class Factor(StrictModel):
    password: str = Field(min_length=1, max_length=256, repr=False)
    otp: str = Field(pattern=r"^\d{6}$", repr=False)


class RecoveryRequest(StrictModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class RecoveryProof(StrictModel):
    token: str = Field(min_length=32, max_length=200, repr=False)
    method: Literal["AUTHENTICATOR", "BACKUP_CODE", "INDEPENDENT_REVIEW"]
    proof: str = Field(default="", max_length=200, repr=False)


class RecoverySetup(StrictModel):
    token: str = Field(min_length=32, max_length=200, repr=False)
    password: str = Field(min_length=14, max_length=256, repr=False)


class RecoveryFinish(StrictModel):
    token: str = Field(min_length=32, max_length=200, repr=False)
    otp: str = Field(pattern=r"^\d{6}$", repr=False)


class RecoveryReview(Factor, Evidence):
    decision: Literal["APPROVE", "REJECT"]


class Coverage(Evidence):
    facility_id: UUID
    account_id: UUID
    services: list[str] = Field(min_length=1, max_length=50)
    valid_from: datetime
    valid_until: datetime
    adoption_reference: str = Field(min_length=3, max_length=12000)

    @model_validator(mode="after")
    def interval(self):
        if self.valid_until <= self.valid_from:
            raise ValueError("Coverage dates must be ordered")
        return self


class ProcessingLocation(StrictModel):
    service: Literal["API", "DATABASE", "STORAGE", "BACKUP", "SUPPORT", "AI"]
    provider: str = Field(min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=200)


class PolicyPackage(Evidence):
    name: str = Field(min_length=3, max_length=200)
    package_version: str = Field(min_length=1, max_length=40)
    jurisdiction: str = Field(min_length=3, max_length=80)
    facility_id: UUID | None = None
    operator: str = Field(min_length=3, max_length=500)
    custodian: str = Field(min_length=3, max_length=500)
    services: list[str] = Field(min_length=1, max_length=50)
    populations: list[str] = Field(min_length=1, max_length=50)
    exclusions: str = Field(min_length=3, max_length=12000)
    practice_authority: str = Field(min_length=3, max_length=12000)
    processing_authority: str = Field(min_length=3, max_length=12000)
    processing_locations: list[ProcessingLocation] = Field(min_length=1, max_length=30)
    retention_and_rights_reference: str = Field(min_length=3, max_length=12000)
    clinical_content_references: list[str] = Field(min_length=1, max_length=100)
    coverage_and_escalation_reference: str = Field(min_length=3, max_length=12000)
    training_evidence: str = Field(min_length=3, max_length=12000)
    backup_restore_evidence: str = Field(min_length=3, max_length=12000)
    local_continuity_evidence: str = Field(min_length=3, max_length=12000)
    funding_support_evidence: str = Field(min_length=3, max_length=12000)
    financial_policy_reference: str | None = Field(default=None, min_length=3, max_length=12000)
    source_references: list[str] = Field(min_length=1, max_length=100)
    valid_from: datetime
    valid_until: datetime

    @model_validator(mode="after")
    def interval(self):
        if self.valid_until <= self.valid_from:
            raise ValueError("Package dates must be ordered")
        if not {"API", "DATABASE", "STORAGE", "BACKUP"}.issubset(
            {row.service for row in self.processing_locations}
        ):
            raise ValueError("Record actual API, database, storage and backup processing locations")
        return self


class PackageReview(Evidence):
    review_kind: Literal["CLINICAL", "PRIVACY", "TECHNICAL", "FINANCE"]
    decision: Literal["APPROVE", "REJECT"]


class Offboard(Factor, Evidence):
    account_id: UUID
    coordinator_id: UUID


class HandoverOffer(Evidence):
    expected_version: int = Field(ge=1)
    successor_id: UUID


class HandoverAccept(Evidence):
    expected_version: int = Field(ge=1)
    patient_id: UUID


class JobRetry(Evidence):
    provider_reconciled: bool = Field(strict=True)
