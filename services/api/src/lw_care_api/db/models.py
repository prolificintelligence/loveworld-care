"""
Schema-Isolated PostgreSQL Models & Database-Level Immutability Controls (§12.2, §13.1–13.4).

Isolated Schemas:
1. `identity`         — Users, Sessions, MFA, ProxyAuthority, ClinicianCredentials
2. `care_clinical`    — T3 Sensitive Clinical: Episodes, Intakes, ProtocolRuns, Appointments,
                        Encounters, ClinicalDocuments (immutable once SIGNED), Addenda,
                        Prescriptions, Referrals, CarePlans, FollowUpTasks
3. `finance_ledger`   — Agreements, SponsorPools, EntitlementReservations, Payments,
                        DoubleEntryJournalLines (append-only), ProviderPayables, MakerCheckerQueue
4. `governance_audit` — T4 Restricted Controls: TamperEvidentAuditEvents (append-only),
                        BreakGlassGrants, TransactionalOutbox, ClinicalIncidents
5. `analytics`        — T1 De-identified Encounter Economics & Aggregate Sponsor Utilisation
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


# =============================================================================
# 1. Schema: identity
# =============================================================================


class UserIdentityModel(Base):
    __tablename__ = "identity_users"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "identity"}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    phone_e164: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    roles_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    mfa_totp_secret: Mapped[str | None] = mapped_column(String(128))
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(16), default="NG", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProxyAuthorityModel(Base):
    __tablename__ = "identity_proxy_authorities"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "identity"}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    representative_user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_document_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    allowed_scopes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by_actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ClinicianCredentialModel(Base):
    __tablename__ = "identity_clinician_credentials"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "identity"}

    clinician_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mdcn_licence_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    specialty: Mapped[str] = mapped_column(String(64), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(16), default="NG", nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(32), default="APPLIED", nullable=False)
    licence_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    indemnity_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_by_actor_id: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ConsentGrantModel(Base):
    __tablename__ = "identity_consent_grants"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "identity"}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    granted_by_actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


# =============================================================================
# 2. Schema: care_clinical (T3 Sensitive Clinical)
# =============================================================================


class CareEpisodeModel(Base):
    __tablename__ = "care_episodes"
    __table_args__ = (
        CheckConstraint(
            "state IN ('DRAFT','SUBMITTED','ACTIVE','FOLLOW_UP','REFERRED','CLOSED','WITHDRAWN','EXPIRED','CANCELLED')",
            name="ck_care_episode_state",
        ),
        {"schema": "care_clinical"},
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    acting_proxy_grant_id: Mapped[str | None] = mapped_column(String(64))
    consent_grant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    care_service: Mapped[str] = mapped_column(String(64), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(16), default="NG", nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="DRAFT", nullable=False)
    chief_complaint_summary: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_clinician_id: Mapped[str | None] = mapped_column(String(64), index=True)
    active_protocol_outcome: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IntakeAnswerSetModel(Base):
    __tablename__ = "care_intake_answer_sets"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "care_clinical"}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    episode_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    structured_answers_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    raw_patient_statement: Mapped[str] = mapped_column(Text, nullable=False)
    language_code: Mapped[str] = mapped_column(String(16), default="en-NG", nullable=False)
    ai_draft_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    submitted_by_actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProtocolRunModel(Base):
    __tablename__ = "care_protocol_runs"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "care_clinical"}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    episode_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    intake_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    protocol_bundle_id: Mapped[str] = mapped_column(String(64), nullable=False)
    protocol_version: Mapped[str] = mapped_column(String(32), nullable=False)
    protocol_document_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    outcome_type: Mapped[str] = mapped_column(String(64), nullable=False)
    hard_stop_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    executed_rule_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    fired_rule_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    unresolved_fields_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    approved_content_id: Mapped[str] = mapped_column(String(128), nullable=False)
    clinician_override_reason: Mapped[str | None] = mapped_column(Text)
    clinician_override_actor_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AppointmentModel(Base):
    __tablename__ = "care_appointments"
    __table_args__ = (
        CheckConstraint(
            "state IN ('REQUESTED','OFFERED','BOOKED','CHECKED_IN','FULFILLED','NO_SHOW','CANCELLED','EXPIRED')",
            name="ck_care_appointment_state",
        ),
        {"schema": "care_clinical"},
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    episode_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    slot_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    clinician_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="BOOKED", nullable=False)
    modality: Mapped[str] = mapped_column(String(32), nullable=False)
    funding_route: Mapped[str] = mapped_column(String(64), nullable=False)
    fee_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    entitlement_reservation_id: Mapped[str | None] = mapped_column(String(64))
    payment_reference: Mapped[str | None] = mapped_column(String(128))
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EncounterModel(Base):
    __tablename__ = "care_encounters"
    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN','IN_PROGRESS','DOCUMENTATION_PENDING','SIGNED','CLOSED','ABORTED')",
            name="ck_care_encounter_status",
        ),
        CheckConstraint(
            "(status NOT IN ('SIGNED','CLOSED')) OR (signed_at IS NOT NULL AND signed_document_hash IS NOT NULL)",
            name="ck_care_encounter_signed_invariant",
        ),
        {"schema": "care_clinical"},
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    episode_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    appointment_id: Mapped[str | None] = mapped_column(String(64), index=True)
    clinician_id: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="OPEN", nullable=False)
    modality: Mapped[str] = mapped_column(String(32), default="VIDEO", nullable=False)
    version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
    remote_suitability_accepted: Mapped[bool | None] = mapped_column(Boolean)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    signed_document_hash: Mapped[str | None] = mapped_column(String(128))
    signature_ed25519_base64: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ClinicalDocumentModel(Base):
    """
    §6.3 & §13.4: Once written as SIGNED, this row is strictly immutable.
    Amendments MUST be written to `care_clinical.care_clinical_addenda`.
    """

    __tablename__ = "care_clinical_documents"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "care_clinical"}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    encounter_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    author_clinician_id: Mapped[str] = mapped_column(String(64), nullable=False)
    author_mdcn_licence: Mapped[str] = mapped_column(String(64), nullable=False)
    modality_used: Mapped[str] = mapped_column(String(32), nullable=False)
    modality_limitations_noted: Mapped[str] = mapped_column(Text, nullable=False)
    history_and_findings: Mapped[str] = mapped_column(Text, nullable=False)
    clinical_assessment: Mapped[str] = mapped_column(Text, nullable=False)
    management_plan: Mapped[str] = mapped_column(Text, nullable=False)
    safety_net_instructions: Mapped[str] = mapped_column(Text, nullable=False)
    prescriptions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    document_sha256: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    signature_ed25519_base64: Mapped[str] = mapped_column(Text, nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ClinicalAddendumModel(Base):
    __tablename__ = "care_clinical_addenda"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "care_clinical"}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    encounter_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    original_signed_document_hash: Mapped[str] = mapped_column(
        String(128), index=True, nullable=False
    )
    author_clinician_id: Mapped[str] = mapped_column(String(64), nullable=False)
    amendment_reason: Mapped[str] = mapped_column(Text, nullable=False)
    addendum_text: Mapped[str] = mapped_column(Text, nullable=False)
    addendum_sha256: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    signature_ed25519_base64: Mapped[str] = mapped_column(Text, nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ReferralModel(Base):
    __tablename__ = "care_referrals"
    __table_args__ = (
        CheckConstraint(
            "state IN ('DRAFT','AUTHORIZED','SENT','RECEIVED','ACCEPTED','DECLINED','COMPLETED','CLOSED')",
            name="ck_care_referral_state",
        ),
        {"schema": "care_clinical"},
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    encounter_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    referring_clinician_id: Mapped[str] = mapped_column(String(64), nullable=False)
    receiving_facility_code: Mapped[str] = mapped_column(String(64), nullable=False)
    receiving_facility_name: Mapped[str] = mapped_column(String(255), nullable=False)
    specialty_code: Mapped[str] = mapped_column(String(64), nullable=False)
    priority: Mapped[str] = mapped_column(String(32), default="routine", nullable=False)
    clinical_reason: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="AUTHORIZED", nullable=False)
    facility_verification_token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


# =============================================================================
# 3. Schema: finance_ledger
# =============================================================================


class SponsorPoolModel(Base):
    __tablename__ = "finance_sponsor_pools"
    __table_args__ = (
        CheckConstraint("funded_cash_minor >= 0", name="ck_pool_funded_non_negative"),
        CheckConstraint("active_reserved_minor >= 0", name="ck_pool_reserved_non_negative"),
        CheckConstraint("redeemed_minor >= 0", name="ck_pool_redeemed_non_negative"),
        CheckConstraint(
            "funded_cash_minor >= active_reserved_minor + redeemed_minor",
            name="ck_pool_no_overspend",
        ),
        {"schema": "finance_ledger"},
    )

    agreement_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    sponsor_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    sponsor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    funding_type: Mapped[str] = mapped_column(String(64), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    committed_unfunded_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    funded_cash_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    active_reserved_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    redeemed_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    eligible_beneficiary_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EntitlementReservationModel(Base):
    __tablename__ = "finance_entitlement_reservations"
    __table_args__ = (
        CheckConstraint("amount_minor >= 0", name="ck_entitlement_amount_non_negative"),
        CheckConstraint(
            "state IN ('AVAILABLE','RESERVED','REDEEMED','RELEASED','EXPIRED','SUSPENDED','REVERSED')",
            name="ck_entitlement_state",
        ),
        UniqueConstraint("episode_id", "state", name="uq_active_episode_reservation"),
        {"schema": "finance_ledger"},
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agreement_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    episode_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="RESERVED", nullable=False)
    redeemed_encounter_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    redeemed_signed_doc_hash: Mapped[str | None] = mapped_column(String(128))
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DoubleEntryLedgerLineModel(Base):
    """
    Immutable balanced double-entry journal lines (§10.3, §13.2, §17.1).
    Separates `LOVEWORLD_CARE_OPERATOR` and `PROLIFIC_INTELLIGENCE` economic books.
    """

    __tablename__ = "finance_ledger_entries"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="ck_ledger_positive_amount"),
        CheckConstraint("direction IN ('DEBIT','CREDIT')", name="ck_ledger_direction"),
        {"schema": "finance_ledger"},
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    journal_batch_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    economic_book: Mapped[str] = mapped_column(
        String(64), default="LOVEWORLD_CARE_OPERATOR", nullable=False
    )
    account_code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    source_event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_reference_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


# =============================================================================
# 4. Schema: governance_audit (T4 Restricted Controls)
# =============================================================================


class AuditEventModel(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_actor_occurred", "actor_id", "occurred_at"),
        {"schema": "governance_audit"},
    )

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    sequence_number: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    request_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_roles_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_opaque_id: Mapped[str] = mapped_column(String(128), nullable=False)
    data_tier: Mapped[str] = mapped_column(String(32), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    break_glass_grant_id: Mapped[str | None] = mapped_column(String(64))
    previous_entry_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)


class TransactionalOutboxModel(Base):
    __tablename__ = "transactional_outbox"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "governance_audit"}

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StaffedRosterSlotModel(Base):
    __tablename__ = "care_staffed_slots"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "care_clinical"}

    slot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    clinician_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    clinician_display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    clinician_mdcn_licence: Mapped[str] = mapped_column(String(64), nullable=False)
    specialty: Mapped[str] = mapped_column(String(64), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(16), default="NG", nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supported_modalities_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    fee_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="NGN", nullable=False)
    is_booked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    staffing_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ProtocolBundleModel(Base):
    __tablename__ = "care_protocol_bundles"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "care_clinical"}

    bundle_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    semver: Mapped[str] = mapped_column(String(32), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(16), default="NG", nullable=False)
    population: Mapped[str] = mapped_column(String(64), default="ADULT_GENERAL", nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    clinical_owner: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewers_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    document_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    bundle_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EncounterEconomicsFactModel(Base):
    __tablename__ = "encounter_unit_economics_facts"
    __table_args__: ClassVar[dict[str, str]] = {"schema": "analytics"}

    encounter_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payer_cohort: Mapped[str] = mapped_column(String(64), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    recognised_revenue_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    clinician_direct_cost_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_variable_cost_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    contribution_margin_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


# =============================================================================
# Raw PostgreSQL Schema Isolation & Immutability Triggers DDL (§12.2 & §13.4)
# =============================================================================

POSTGRES_SCHEMA_AND_IMMUTABILITY_DDL_STATEMENTS = [
    "CREATE SCHEMA IF NOT EXISTS identity",
    "CREATE SCHEMA IF NOT EXISTS care_clinical",
    "CREATE SCHEMA IF NOT EXISTS finance_ledger",
    "CREATE SCHEMA IF NOT EXISTS governance_audit",
    "CREATE SCHEMA IF NOT EXISTS analytics",
    """
    CREATE OR REPLACE FUNCTION governance_audit.enforce_append_only_immutability()
    RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'Illegal mutation on immutable table %.%: records are strictly append-only.',
            TG_TABLE_SCHEMA, TG_TABLE_NAME;
    END;
    $$ LANGUAGE plpgsql
    """,
]

POSTGRES_IMMUTABILITY_TRIGGER_STATEMENTS = [
    "DROP TRIGGER IF EXISTS trg_immutable_signed_clinical_documents ON care_clinical.care_clinical_documents",
    """
    CREATE TRIGGER trg_immutable_signed_clinical_documents
    BEFORE UPDATE OR DELETE ON care_clinical.care_clinical_documents
    FOR EACH ROW EXECUTE FUNCTION governance_audit.enforce_append_only_immutability()
    """,
    "DROP TRIGGER IF EXISTS trg_immutable_clinical_addenda ON care_clinical.care_clinical_addenda",
    """
    CREATE TRIGGER trg_immutable_clinical_addenda
    BEFORE UPDATE OR DELETE ON care_clinical.care_clinical_addenda
    FOR EACH ROW EXECUTE FUNCTION governance_audit.enforce_append_only_immutability()
    """,
    "DROP TRIGGER IF EXISTS trg_immutable_finance_ledger_entries ON finance_ledger.finance_ledger_entries",
    """
    CREATE TRIGGER trg_immutable_finance_ledger_entries
    BEFORE UPDATE OR DELETE ON finance_ledger.finance_ledger_entries
    FOR EACH ROW EXECUTE FUNCTION governance_audit.enforce_append_only_immutability()
    """,
    "DROP TRIGGER IF EXISTS trg_immutable_governance_audit_events ON governance_audit.audit_events",
    """
    CREATE TRIGGER trg_immutable_governance_audit_events
    BEFORE UPDATE OR DELETE ON governance_audit.audit_events
    FOR EACH ROW EXECUTE FUNCTION governance_audit.enforce_append_only_immutability()
    """,
]
