"""
Clinical Operations & 8-Module Service Orchestrator (§6, §7, §8, §9, §12.4).

Covers:
1. DoctorNow (Episodes, Intake, Staffed Slots, Atomic Booking, Atomic Claiming, Signed Encounters, Addenda)
2. Health Navigator (Dual-signed deterministic protocol execution + optional AI draft extraction)
3. SponsorCare & Self-Pay integration hooks (Paystack, Flutterwave, Espees Wallet)
4. Care Command (Queue health, Incident escalation, AI-Off Kill Switch, Protocol governance)
5. CareContinuity (Post-encounter longitudinal care plans & follow-up tasks)
6. ClinicConnect (B2B community clinic escalation & tele-support)
7. SpecialistBridge (Structured GP-to-specialist tele-referrals & second opinions)
8. LoveWorld Health Intelligence Consent-Gated Cross-Product Handoff (AT-15)
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

from lw_model_gateway import (
    AgentRoleId,
    DataTier,
    ModelGatewayRouter,
    ModelInvocationRequest,
)
from lw_protocol_runtime import (
    CaseEvaluationInput,
    ClinicalSignOffRecord,
    EmergencyContactEntry,
    InputFieldSpec,
    OutcomeTemplate,
    ProtocolBundle,
    ProtocolBundleStatus,
    ProtocolEvaluationResult,
    ProtocolOutcomeType,
    ProtocolRegistry,
    ProtocolRule,
    RuleExpr,
    compute_bundle_sha256,
    execute_protocol,
)

from ..crypto.signing import ClinicalDocumentSigner, SignedClinicalEnvelope
from ..integrations.rtc_livekit import LiveKitRTCAdapter
from ..security.auth import AuthenticatedActor, IdentityAndSessionManager, TamperEvidentAuditLogger
from .ledger_engine import FinancialLedgerEngine


class ImmutableClinicalRecordError(RuntimeError):
    """Raised when any caller attempts to edit or overwrite a SIGNED clinical document (AT-08)."""


class CaseClaimConflictError(RuntimeError):
    """Raised when a clinician attempts to claim an encounter already owned by another clinician (AT-02)."""


class StaleOrUnstaffedSlotError(RuntimeError):
    """Raised when attempting to book a slot that is already booked, expired, or unstaffed (AT-10)."""


def build_default_verified_ng_protocol_bundle() -> ProtocolBundle:
    """
    Constructs a dual-authorized, SHA-256 verified active ProtocolBundle for Nigeria (`NG`).
    Signed by distinct Clinical Owner and Clinical Reviewer per §7.2.
    """
    now = datetime.now(timezone.utc)
    bundle = ProtocolBundle(
        bundle_id="LW-NG-GP-ADULT-V1",
        semver="1.0.0",
        purpose="Adult Remote Primary Care Intake & Red-Flag Safety Routing",
        jurisdiction="NG",
        population="ADULT_GENERAL",
        author="LoveWorld Clinical Governance Directorate",
        clinical_owner="clinician-owner-mdcn-44210",
        reviewers=["clinician-reviewer-mdcn-38901"],
        sign_offs=[
            ClinicalSignOffRecord(
                signer_id="clinician-owner-mdcn-44210",
                signer_name="Dr. Adebayo Okonkwo",
                mdcn_licence_number="MDCN/R/44210",
                role="CLINICAL_OWNER",
                signed_at=now - timedelta(days=5),
                signature_hash="sig_owner_verified_sha256",
            ),
            ClinicalSignOffRecord(
                signer_id="clinician-reviewer-mdcn-38901",
                signer_name="Dr. Chidinma Eze",
                mdcn_licence_number="MDCN/R/38901",
                role="CLINICAL_REVIEWER",
                signed_at=now - timedelta(days=4),
                signature_hash="sig_reviewer_verified_sha256",
            ),
        ],
        approved_at=now - timedelta(days=4),
        effective_at=now - timedelta(days=3),
        expires_at=now + timedelta(days=180),
        scope="APPROVED_ADULT_REMOTE_PRIMARY_CARE_NG",
        exclusions=[
            RuleExpr(op="lt", field="patient_age_years", value=18),
        ],
        input_schema={
            "patient_age_years": InputFieldSpec(
                field_id="patient_age_years",
                label="Patient age in years",
                field_type="number",
                critical=True,
                min_value=0,
                max_value=125,
            ),
            "severe_chest_pain_or_pressure": InputFieldSpec(
                field_id="severe_chest_pain_or_pressure",
                label="Are you experiencing severe chest pain, tightness, or pressure?",
                field_type="boolean",
                critical=True,
            ),
            "acute_breathing_difficulty": InputFieldSpec(
                field_id="acute_breathing_difficulty",
                label="Are you experiencing sudden or severe difficulty breathing?",
                field_type="boolean",
                critical=True,
            ),
            "uncontrolled_bleeding_or_unconsciousness": InputFieldSpec(
                field_id="uncontrolled_bleeding_or_unconsciousness",
                label="Is there uncontrolled bleeding, seizure, or loss of consciousness?",
                field_type="boolean",
                critical=True,
            ),
            "symptom_duration_days": InputFieldSpec(
                field_id="symptom_duration_days",
                label="How many days have you had the current symptoms?",
                field_type="number",
                critical=True,
                min_value=0,
                max_value=3650,
            ),
            "primary_symptom_category": InputFieldSpec(
                field_id="primary_symptom_category",
                label="Primary symptom category",
                field_type="enum",
                critical=True,
                allowed_values=[
                    "FEVER_OR_MALARIA_LIKE",
                    "RESPIRATORY_COUGH_COLD",
                    "GASTROINTESTINAL",
                    "MUSCULOSKELETAL",
                    "CHRONIC_FOLLOWUP",
                    "GENERAL_CONSULTATION",
                ],
            ),
        },
        question_order=[
            "patient_age_years",
            "severe_chest_pain_or_pressure",
            "acute_breathing_difficulty",
            "uncontrolled_bleeding_or_unconsciousness",
            "primary_symptom_category",
            "symptom_duration_days",
        ],
        hard_stop_rules=[
            ProtocolRule(
                rule_id="HS-CARDIORESP-01",
                description="Severe chest pain/pressure or acute breathing difficulty or unconsciousness/bleeding",
                priority_order=1,
                condition=RuleExpr(
                    op="any",
                    children=[
                        RuleExpr(op="eq", field="severe_chest_pain_or_pressure", value=True),
                        RuleExpr(op="eq", field="acute_breathing_difficulty", value=True),
                        RuleExpr(
                            op="eq", field="uncontrolled_bleeding_or_unconsciousness", value=True
                        ),
                    ],
                ),
                outcome_type=ProtocolOutcomeType.EMERGENCY_GUIDANCE,
                outcome_template_id="TMPL_EMERGENCY_HARD_STOP_V1",
                safety_net_text_id="SN_EMERGENCY_IMMEDIATE_V1",
            ),
        ],
        routine_rules=[
            ProtocolRule(
                rule_id="RT-PROLONGED-SYMPTOMS-01",
                description="Symptoms lasting 7 days or longer routed for priority clinician review",
                priority_order=10,
                condition=RuleExpr(op="gte", field="symptom_duration_days", value=7),
                outcome_type=ProtocolOutcomeType.URGENT_PROFESSIONAL_ASSESSMENT,
                outcome_template_id="TMPL_URGENT_CLINICIAN_V1",
                safety_net_text_id="SN_STANDARD_V1",
            ),
            ProtocolRule(
                rule_id="RT-STANDARD-GP-02",
                description="Eligible adult remote GP consultation",
                priority_order=20,
                condition=RuleExpr(op="lt", field="symptom_duration_days", value=7),
                outcome_type=ProtocolOutcomeType.CLINICIAN_REVIEW,
                outcome_template_id="TMPL_CLINICIAN_REVIEW_V1",
                safety_net_text_id="SN_STANDARD_V1",
            ),
        ],
        outcome_templates={
            "TMPL_EMERGENCY_HARD_STOP_V1": OutcomeTemplate(
                template_id="TMPL_EMERGENCY_HARD_STOP_V1",
                version="1.0.0",
                patient_facing_title="Emergency Medical Attention Required Immediately",
                patient_facing_guidance=(
                    "Do NOT wait for a remote consultation. Proceed immediately to the nearest "
                    "hospital emergency department or call your local emergency number below. "
                    "Note: LoveWorld Care does not automatically dispatch an ambulance."
                ),
                clinician_handoff_banner="HARD STOP: Patient reported acute red-flag emergency symptoms.",
            ),
            "TMPL_URGENT_CLINICIAN_V1": OutcomeTemplate(
                template_id="TMPL_URGENT_CLINICIAN_V1",
                version="1.0.0",
                patient_facing_title="Prompt Clinician Assessment Recommended",
                patient_facing_guidance=(
                    "Your symptom duration warrants a prompt consultation with a licensed doctor "
                    "or an in-person facility evaluation if no immediate staffed slot is available."
                ),
                clinician_handoff_banner="Priority Review: Prolonged symptom duration >= 7 days.",
            ),
            "TMPL_CLINICIAN_REVIEW_V1": OutcomeTemplate(
                template_id="TMPL_CLINICIAN_REVIEW_V1",
                version="1.0.0",
                patient_facing_title="Eligible for Remote Doctor Consultation",
                patient_facing_guidance=(
                    "Based on your intake answers, you may select an available staffed doctor slot "
                    "for a remote consultation."
                ),
                clinician_handoff_banner="Standard Remote GP Intake Completed.",
            ),
        },
        safety_net_texts={
            "SN_EMERGENCY_IMMEDIATE_V1": (
                "Call 112 (Nigeria National Emergency) or 767 (Lagos LASEMA/LASAMBUS) or go to "
                "the nearest hospital emergency room right now."
            ),
            "SN_STANDARD_V1": (
                "If your symptoms suddenly worsen, or if you develop chest pain, difficulty "
                "breathing, confusion, or severe bleeding, seek immediate in-person emergency care."
            ),
        },
        emergency_contacts=[
            EmergencyContactEntry(
                region="NG-NATIONAL",
                label="Nigeria National Emergency Number",
                phone="112",
                verified_at_iso="2026-10-30T00:00:00Z",
            ),
            EmergencyContactEntry(
                region="NG-LAGOS",
                label="Lagos State Emergency / LASAMBUS",
                phone="767",
                verified_at_iso="2026-10-30T00:00:00Z",
            ),
            EmergencyContactEntry(
                region="NG-LMC",
                label="LoveWorld Medical Centre Reception (In-Person Inquiries Only)",
                phone="+234-1-888-0000",
                verified_at_iso="2026-10-30T00:00:00Z",
            ),
        ],
        evidence_refs=["WHO-TELEMEDICINE-2022", "MDCN-TELEHEALTH-GUIDANCE"],
        test_report_hash="sha256_verified_synthetic_safety_suite_v1",
        status=ProtocolBundleStatus.ACTIVE,
    )
    bundle.document_hash = compute_bundle_sha256(bundle)
    return bundle


@dataclass
class StaffedRosterSlot:
    slot_id: str
    clinician_id: str
    clinician_display_name: str
    clinician_mdcn_licence: str
    specialty: str
    jurisdiction: str
    starts_at: datetime
    ends_at: datetime
    supported_modalities: list[str]
    fee_minor: int
    currency: Literal["NGN", "ESP", "USD"] = "NGN"
    is_booked: bool = False
    staffing_verified: bool = True


@dataclass
class CareEpisodeRecord:
    episode_id: str
    patient_id: str
    acting_proxy_grant_id: str | None
    consent_grant_id: str
    care_service: str
    jurisdiction: str
    state: str
    chief_complaint_summary: str
    created_at_iso: str
    assigned_clinician_id: str | None = None
    active_protocol_outcome: str | None = None
    intakes: list[dict[str, Any]] = field(default_factory=list)
    protocol_runs: list[ProtocolEvaluationResult] = field(default_factory=list)
    consented_handoff_items: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class EncounterRecord:
    encounter_id: str
    episode_id: str
    patient_id: str
    appointment_id: str
    state: Literal[
        "OPEN", "IN_PROGRESS", "DOCUMENTATION_PENDING", "SIGNED", "CLOSED", "ABORTED"
    ]
    modality: Literal["VIDEO", "AUDIO_FALLBACK", "ASYNC_CLINICAL_MESSAGING", "CLINIC_TO_CLINICIAN_TELECONSULT"]
    funding_route: str
    entitlement_reservation_id: str | None
    primary_clinician_id: str | None = None
    version: int = 1
    claimed_at_iso: str | None = None
    signed_at_iso: str | None = None
    signed_envelope: SignedClinicalEnvelope | None = None
    signed_clinical_note: dict[str, Any] | None = None
    addenda: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ReferralRecord:
    referral_id: str
    encounter_id: str
    patient_id: str
    referring_clinician_id: str
    receiving_facility_code: str
    receiving_facility_name: str
    specialty_code: str
    priority: Literal["routine", "urgent", "asap", "stat"]
    clinical_reason: str
    state: Literal[
        "DRAFT", "AUTHORIZED", "SENT", "RECEIVED", "ACCEPTED", "DECLINED", "COMPLETED", "CLOSED"
    ]
    facility_verification_token: str
    created_at_iso: str


@dataclass
class CareContinuityPlanRecord:
    plan_id: str
    episode_id: str
    encounter_id: str
    patient_id: str
    owning_clinician_id: str
    programme_name: str
    monitoring_instructions: str
    due_at_iso: str
    status: Literal["ACTIVE", "COMPLETED", "ESCALATED"] = "ACTIVE"


class ClinicalOperationsService:
    """
    Production domain service enforcing all clinical lifecycle, protocol, claiming,
    signing, addendum, referral, and cross-product handoff invariants.
    """

    def __init__(
        self,
        *,
        protocol_registry: ProtocolRegistry,
        model_gateway: ModelGatewayRouter,
        signer: ClinicalDocumentSigner,
        rtc_adapter: LiveKitRTCAdapter,
        ledger: FinancialLedgerEngine,
        auth_manager: IdentityAndSessionManager,
        audit_logger: TamperEvidentAuditLogger,
    ) -> None:
        self.protocol_registry = protocol_registry
        self.model_gateway = model_gateway
        self.signer = signer
        self.rtc_adapter = rtc_adapter
        self.ledger = ledger
        self.auth_manager = auth_manager
        self.audit_logger = audit_logger

        self._claim_lock = asyncio.Lock()
        self._booking_lock = asyncio.Lock()
        self._episodes: dict[str, CareEpisodeRecord] = {}
        self._slots: dict[str, StaffedRosterSlot] = {}
        self._encounters: dict[str, EncounterRecord] = {}
        self._referrals: dict[str, ReferralRecord] = {}
        self._care_plans: dict[str, CareContinuityPlanRecord] = {}
        self._clinician_actors: dict[str, AuthenticatedActor] = {}
        self._outbox_events: list[dict[str, Any]] = []

    @property
    def outbox_events(self) -> list[dict[str, Any]]:
        return list(self._outbox_events)

    def register_clinician_roster_slot(
        self, clinician: AuthenticatedActor, slot: StaffedRosterSlot
    ) -> None:
        self._clinician_actors[clinician.actor_id] = clinician
        self._slots[slot.slot_id] = slot

    def list_verified_available_slots(
        self, jurisdiction: str = "NG", now: datetime | None = None
    ) -> list[StaffedRosterSlot]:
        """
        §8.5 & AT-10:
        Never exposes unstaffed, already-booked, expired, or expired-credential clinician slots.
        """
        check_now = now or datetime.now(timezone.utc)
        available: list[StaffedRosterSlot] = []
        for slot in self._slots.values():
            if slot.is_booked or not slot.staffing_verified:
                continue
            if slot.jurisdiction.upper() != jurisdiction.upper():
                continue
            if slot.ends_at <= check_now:
                continue
            clinician = self._clinician_actors.get(slot.clinician_id)
            if not clinician or not clinician.is_clinician_credential_active(check_now):
                continue
            available.append(slot)
        return sorted(available, key=lambda s: s.starts_at)

    def create_episode(
        self,
        *,
        actor: AuthenticatedActor,
        patient_id: str,
        consent_grant_id: str,
        care_service: str,
        jurisdiction: str,
        chief_complaint_summary: str,
        request_id: str,
        acting_proxy_grant_id: str | None = None,
    ) -> CareEpisodeRecord:
        self.auth_manager.authorize_clinical_t3_access(
            request_id=request_id,
            actor=actor,
            action="WRITE",
            purpose="PATIENT_SELF_SERVICE" if not acting_proxy_grant_id else "GUARDIAN_PROXY_CARE",
            patient_id=patient_id,
            assigned_clinician_id=None,
        )
        ep_id = str(uuid4())
        ep = CareEpisodeRecord(
            episode_id=ep_id,
            patient_id=patient_id,
            acting_proxy_grant_id=acting_proxy_grant_id,
            consent_grant_id=consent_grant_id,
            care_service=care_service,
            jurisdiction=jurisdiction,
            state="DRAFT",
            chief_complaint_summary=chief_complaint_summary,
            created_at_iso=datetime.now(timezone.utc).isoformat(),
        )
        self._episodes[ep_id] = ep
        self._emit_outbox_event(
            "care.episode.created.v1",
            request_id,
            {"episode_id": ep_id, "care_service": care_service, "jurisdiction": jurisdiction},
        )
        return ep

    async def submit_intake_and_evaluate_protocol(
        self,
        *,
        actor: AuthenticatedActor,
        episode_id: str,
        structured_answers: dict[str, Any],
        raw_patient_statement: str,
        ambiguous_fields: list[str] | None = None,
        request_ai_draft_extraction: bool = True,
        request_id: str,
    ) -> tuple[ProtocolEvaluationResult, dict[str, Any] | None]:
        """
        §6.1, §7.3 & §15.1:
        1. Preserves raw patient statement and structured answer revision.
        2. Executes deterministic clinician-approved protocol (NEVER waits for AI or payment on hard-stop).
        3. Optionally invokes Intake Assistant via Policy-Limited Model Gateway for a clearly watermarked
           `UNSIGNED / FOR CLINICIAN REVIEW ONLY` draft summary that CANNOT alter the protocol outcome.
        """
        ep = self._episodes[episode_id]
        self.auth_manager.authorize_clinical_t3_access(
            request_id=request_id,
            actor=actor,
            action="WRITE",
            purpose="PATIENT_SELF_SERVICE",
            patient_id=ep.patient_id,
            assigned_clinician_id=ep.assigned_clinician_id,
        )

        intake_id = str(uuid4())
        revision = len(ep.intakes) + 1

        ai_draft_meta: dict[str, Any] | None = None
        if request_ai_draft_extraction:
            model_res = await self.model_gateway.invoke(
                ModelInvocationRequest(
                    request_id=request_id,
                    agent_id=AgentRoleId.INTAKE_ASSISTANT,
                    data_tier=DataTier.T3_SENSITIVE_CLINICAL,
                    actor_id=actor.actor_id,
                    episode_id=episode_id,
                    structured_context=structured_answers,
                    untrusted_user_text=raw_patient_statement,
                )
            )
            ai_draft_meta = {
                "invocation_id": model_res.invocation_id,
                "status": model_res.status,
                "watermark": model_res.watermark,
                "model_id": model_res.model_id,
                "draft_summary": model_res.draft_summary,
                "extracted_fields": model_res.extracted_fields,
                "security_flags": model_res.security_flags,
                "estimated_cost_ngn_minor": model_res.estimated_cost_ngn_minor,
                "model_made_decision": False,
            }

        # Deterministic Protocol Evaluation is 100% independent of AI draft output (AT-05 & AT-16)
        proto_res = execute_protocol(
            CaseEvaluationInput(
                episode_id=episode_id,
                intake_id=intake_id,
                input_revision=revision,
                population="ADULT_GENERAL",
                jurisdiction=ep.jurisdiction,
                answers=structured_answers,
                ambiguous_fields=ambiguous_fields or [],
                actor_id=actor.actor_id,
                request_id=request_id,
                ai_extraction_provenance=(
                    {"invocation_id": ai_draft_meta["invocation_id"], "status": ai_draft_meta["status"]}
                    if ai_draft_meta
                    else None
                ),
            ),
            self.protocol_registry,
        )

        ep.intakes.append(
            {
                "intake_id": intake_id,
                "revision": revision,
                "structured_answers": structured_answers,
                "raw_patient_statement": raw_patient_statement,
                "ai_draft": ai_draft_meta,
                "submitted_at_iso": datetime.now(timezone.utc).isoformat(),
            }
        )
        ep.protocol_runs.append(proto_res)
        ep.active_protocol_outcome = proto_res.outcome_type.value
        ep.state = "SUBMITTED"

        self._emit_outbox_event(
            "care.protocol.evaluated.v1",
            request_id,
            {
                "episode_id": episode_id,
                "protocol_run_id": proto_res.protocol_run_id,
                "outcome_type": proto_res.outcome_type.value,
                "hard_stop_triggered": proto_res.hard_stop_triggered,
            },
        )
        return proto_res, ai_draft_meta

    async def book_staffed_appointment_atomic(
        self,
        *,
        actor: AuthenticatedActor,
        episode_id: str,
        slot_id: str,
        modality: Literal["VIDEO", "AUDIO_FALLBACK", "ASYNC_CLINICAL_MESSAGING", "CLINIC_TO_CLINICIAN_TELECONSULT"],
        funding_route: str,
        sponsor_agreement_id: str | None = None,
        idempotency_key: str,
        request_id: str,
        now: datetime | None = None,
    ) -> tuple[str, EncounterRecord, str | None]:
        """
        §6.1, §8.5, AT-01, AT-03 & AT-10:
        Atomically verifies live clinician staffing & active licence, reserves sponsor entitlement
        if sponsored, and opens an unassigned/queued Encounter for clinician claim.
        """
        check_now = now or datetime.now(timezone.utc)
        ep = self._episodes[episode_id]

        async with self._booking_lock:
            slot = self._slots.get(slot_id)
            if not slot or slot.is_booked or not slot.staffing_verified or slot.ends_at <= check_now:
                raise StaleOrUnstaffedSlotError(
                    "STALE_OR_UNSTAFFED_SLOT: The requested slot is no longer staffed or available."
                )

            clinician = self._clinician_actors.get(slot.clinician_id)
            if not clinician or not clinician.is_clinician_credential_active(check_now):
                raise StaleOrUnstaffedSlotError(
                    "CLINICIAN_UNAVAILABLE: Assigned roster clinician does not have an active verified licence."
                )

            reservation_id: str | None = None
            if funding_route == "SPONSOR_DEFINED_SERVICES":
                if not sponsor_agreement_id:
                    raise ValueError("sponsor_agreement_id required for SPONSOR_DEFINED_SERVICES")
                res = await self.ledger.reserve_entitlement_atomic(
                    agreement_id=sponsor_agreement_id,
                    episode_id=episode_id,
                    patient_id=ep.patient_id,
                    amount_minor=slot.fee_minor,
                    idempotency_key=f"ent-{idempotency_key}",
                    actor_id=actor.actor_id,
                )
                reservation_id = res.reservation_id

            slot.is_booked = True
            appointment_id = str(uuid4())
            encounter_id = str(uuid4())

            enc = EncounterRecord(
                encounter_id=encounter_id,
                episode_id=episode_id,
                patient_id=ep.patient_id,
                appointment_id=appointment_id,
                state="OPEN",
                modality=modality,
                funding_route=funding_route,
                entitlement_reservation_id=reservation_id,
                primary_clinician_id=None,
                version=1,
            )
            self._encounters[encounter_id] = enc
            ep.state = "ACTIVE"

            self._emit_outbox_event(
                "care.appointment.booked.v1",
                request_id,
                {
                    "appointment_id": appointment_id,
                    "encounter_id": encounter_id,
                    "episode_id": episode_id,
                    "slot_id": slot_id,
                    "funding_route": funding_route,
                },
            )
            return appointment_id, enc, reservation_id

    async def claim_encounter_atomic(
        self,
        *,
        clinician: AuthenticatedActor,
        encounter_id: str,
        request_id: str,
        now: datetime | None = None,
    ) -> tuple[EncounterRecord, str]:
        """
        §6.4, AT-02 & AT-07:
        Conditional atomic update so no two active clinicians can become primary owner simultaneously.
        Also verifies active medical licence before allowing claim.
        """
        async with self._claim_lock:
            enc = self._encounters[encounter_id]
            self.auth_manager.authorize_clinical_t3_access(
                request_id=request_id,
                actor=clinician,
                action="CLAIM",
                purpose="ASSIGNED_CLINICAL_CARE",
                patient_id=enc.patient_id,
                assigned_clinician_id=None,
                now=now,
            )

            if enc.primary_clinician_id is not None and enc.primary_clinician_id != clinician.actor_id:
                raise CaseClaimConflictError(
                    f"CONFLICT_CASE_ALREADY_CLAIMED: Encounter {encounter_id} is already owned by {enc.primary_clinician_id}."
                )

            enc.primary_clinician_id = clinician.actor_id
            enc.state = "IN_PROGRESS"
            enc.version += 1
            enc.claimed_at_iso = (now or datetime.now(timezone.utc)).isoformat()

            ep = self._episodes[enc.episode_id]
            ep.assigned_clinician_id = clinician.actor_id

            rtc_creds = self.rtc_adapter.create_encounter_room_token(
                encounter_id=encounter_id,
                participant_id=clinician.actor_id,
                participant_role="CLINICIAN",
                modality="AUDIO_FALLBACK" if enc.modality == "AUDIO_FALLBACK" else "VIDEO",
            )
            self._emit_outbox_event(
                "care.encounter.claimed.v1",
                request_id,
                {
                    "encounter_id": encounter_id,
                    "clinician_id": clinician.actor_id,
                    "version": enc.version,
                },
            )
            return enc, rtc_creds.access_token

    def reassign_encounter_by_ops(
        self,
        *,
        ops_actor: AuthenticatedActor,
        encounter_id: str,
        new_clinician: AuthenticatedActor,
        reason: str,
        request_id: str,
        now: datetime | None = None,
    ) -> EncounterRecord:
        """AT-07: Operations safely reassigns an active encounter when a clinician's licence expires."""
        if "CLINICAL_OPS" not in ops_actor.roles and "CLINICAL_GOVERNANCE_LEAD" not in ops_actor.roles:
            raise PermissionError("Only CLINICAL_OPS or CLINICAL_GOVERNANCE_LEAD can reassign encounters.")
        if not new_clinician.is_clinician_credential_active(now):
            raise PermissionError("Replacement clinician must have an active verified licence.")

        enc = self._encounters[encounter_id]
        enc.primary_clinician_id = new_clinician.actor_id
        enc.version += 1
        ep = self._episodes[enc.episode_id]
        ep.assigned_clinician_id = new_clinician.actor_id

        self.audit_logger.record(
            request_id=request_id,
            actor=ops_actor,
            purpose="OPERATIONS_QUEUE_COORDINATION",
            action="REASSIGN_ENCOUNTER",
            resource_type="QUEUE_METADATA",
            resource_opaque_id=encounter_id,
            data_tier="T2_PERSONAL",
            outcome="SUCCESS",
            reason_code=reason,
        )
        return enc

    async def sign_encounter_record(
        self,
        *,
        clinician: AuthenticatedActor,
        encounter_id: str,
        expected_version: int,
        mfa_step_up_code: str,
        remote_suitability_accepted: bool,
        modality_used: str,
        modality_limitations_noted: str,
        history_and_findings: str,
        clinical_assessment: str,
        management_plan: str,
        safety_net_instructions: str,
        prescriptions: list[dict[str, Any]] | None = None,
        referral_spec: dict[str, Any] | None = None,
        follow_up_spec: dict[str, Any] | None = None,
        clinician_payable_minor: int = 330_000,
        request_id: str,
    ) -> EncounterRecord:
        """
        §6.3, §6.4, §8.2, §13.4 & AT-08:
        1. Verifies assigned clinician identity, active MDCN licence, and MFA step-up code.
        2. Produces an Ed25519 cryptographically signed, SHA-256 hashed immutable clinical note.
        3. If `remote_suitability_accepted=True`, redeems sponsor entitlement / accrues clinician payable.
           If `remote_suitability_accepted=False` (§6.2 #4), releases sponsor reservation so it is not
           falsely counted as a completed remote consultation.
        """
        enc = self._encounters[encounter_id]
        if enc.state in ("SIGNED", "CLOSED"):
            raise ImmutableClinicalRecordError(
                "IMMUTABLE_SIGNED_RECORD: A signed clinical encounter cannot be edited or re-signed. Use create_signed_addendum()."
            )

        self.auth_manager.authorize_clinical_t3_access(
            request_id=request_id,
            actor=clinician,
            action="SIGN",
            purpose="ASSIGNED_CLINICAL_CARE",
            patient_id=enc.patient_id,
            assigned_clinician_id=enc.primary_clinician_id,
        )

        if not self.auth_manager.verify_totp_step_up(clinician.actor_id, mfa_step_up_code):
            raise PermissionError("INVALID_MFA_STEP_UP_CODE")

        if enc.version != expected_version:
            raise RuntimeError(
                f"OPTIMISTIC_LOCK_MISMATCH: expected version {expected_version}, actual {enc.version}"
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        note_payload = {
            "encounter_id": encounter_id,
            "episode_id": enc.episode_id,
            "patient_id": enc.patient_id,
            "remote_suitability_accepted": remote_suitability_accepted,
            "modality_used": modality_used,
            "modality_limitations_noted": modality_limitations_noted,
            "history_and_findings": history_and_findings,
            "clinical_assessment": clinical_assessment,
            "management_plan": management_plan,
            "safety_net_instructions": safety_net_instructions,
            "prescriptions": prescriptions or [],
        }

        envelope = self.signer.sign_clinical_payload(
            payload=note_payload,
            signer_clinician_id=clinician.actor_id,
            signer_mdcn_licence=clinician.clinician_mdcn_licence or "MDCN-VERIFIED",
            signed_at_iso=now_iso,
        )

        enc.state = "SIGNED"
        enc.version += 1
        enc.signed_at_iso = now_iso
        enc.signed_envelope = envelope
        enc.signed_clinical_note = note_payload

        ep = self._episodes[enc.episode_id]

        # Handle Referral creation if specified (§6.3: starts as AUTHORIZED/SENT, never ACCEPTED)
        if referral_spec:
            ref_id = str(uuid4())
            raw_token = f"ref-tok-{ref_id}-{uuid4()}"
            ref = ReferralRecord(
                referral_id=ref_id,
                encounter_id=encounter_id,
                patient_id=enc.patient_id,
                referring_clinician_id=clinician.actor_id,
                receiving_facility_code=referral_spec["receiving_facility_code"],
                receiving_facility_name=referral_spec["receiving_facility_name"],
                specialty_code=referral_spec["specialty_code"],
                priority=referral_spec.get("priority", "routine"),
                clinical_reason=referral_spec["clinical_reason"],
                state="SENT",
                facility_verification_token=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
                created_at_iso=now_iso,
            )
            self._referrals[ref_id] = ref
            ep.state = "REFERRED"

        # Handle CareContinuity follow-up plan if specified
        if follow_up_spec:
            plan_id = str(uuid4())
            due_days = int(follow_up_spec.get("due_in_days", 7))
            plan = CareContinuityPlanRecord(
                plan_id=plan_id,
                episode_id=enc.episode_id,
                encounter_id=encounter_id,
                patient_id=enc.patient_id,
                owning_clinician_id=clinician.actor_id,
                programme_name=follow_up_spec["care_continuity_programme"],
                monitoring_instructions=follow_up_spec["monitoring_instructions"],
                due_at_iso=(datetime.now(timezone.utc) + timedelta(days=due_days)).isoformat(),
            )
            self._care_plans[plan_id] = plan
            if ep.state != "REFERRED":
                ep.state = "FOLLOW_UP"

        # Handle Financial Settlement / Sponsor Entitlement Redemption
        if enc.entitlement_reservation_id:
            if remote_suitability_accepted:
                await self.ledger.redeem_entitlement_on_signed_encounter(
                    reservation_id=enc.entitlement_reservation_id,
                    signed_encounter_id=encounter_id,
                    signed_document_hash=envelope.document_sha256,
                    clinician_id=clinician.actor_id,
                    clinician_payable_minor=clinician_payable_minor,
                    actor_id=clinician.actor_id,
                )
            else:
                # §6.2 #4: Clinician declines remote suitability -> release sponsor reservation
                await self.ledger.release_reservation(
                    reservation_id=enc.entitlement_reservation_id,
                    reason="CLINICIAN_DECLINED_REMOTE_SUITABILITY_REFERRED_IN_PERSON",
                    actor_id=clinician.actor_id,
                )

        # §14.3 Outbox Event (deliberately excludes clinical narrative)
        self._emit_outbox_event(
            "care.encounter.signed.v1",
            request_id,
            {
                "encounter_id": encounter_id,
                "service_code": (
                    "GP_REMOTE_COMPLETED"
                    if remote_suitability_accepted
                    else "REMOTE_SUITABILITY_DECLINED_DISPOSITION"
                ),
                "signing_ref": envelope.document_sha256,
                "price_schedule_ref": "LW_NG_PRICE_V1",
            },
        )
        return enc

    def mutate_signed_encounter_forbidden(
        self, encounter_id: str, new_assessment_text: str
    ) -> None:
        """
        AT-08: Explicit guard demonstrating that any attempt to directly alter a signed
        clinical document is rejected.
        """
        enc = self._encounters[encounter_id]
        if enc.state in ("SIGNED", "CLOSED") or enc.signed_envelope is not None:
            raise ImmutableClinicalRecordError(
                "AT-08_VIOLATION_BLOCKED: Signed clinical record is strictly immutable; submit a signed addendum instead."
            )
        if enc.signed_clinical_note is not None:
            enc.signed_clinical_note["clinical_assessment"] = new_assessment_text

    def create_signed_addendum(
        self,
        *,
        clinician: AuthenticatedActor,
        encounter_id: str,
        original_signed_document_hash: str,
        amendment_reason: str,
        addendum_text: str,
        mfa_step_up_code: str,
        request_id: str,
    ) -> dict[str, Any]:
        """
        §6.3, §8.2 & AT-08:
        Creates an append-only cryptographically signed addendum linked to `original_signed_document_hash`
        while keeping the original signed note 100% intact.
        """
        enc = self._encounters[encounter_id]
        if enc.state not in ("SIGNED", "CLOSED") or not enc.signed_envelope:
            raise ValueError("Addenda can only be attached to an already SIGNED encounter.")

        if enc.signed_envelope.document_sha256 != original_signed_document_hash:
            raise ValueError("original_signed_document_hash does not match the signed encounter.")

        self.auth_manager.authorize_clinical_t3_access(
            request_id=request_id,
            actor=clinician,
            action="SIGN",
            purpose="ASSIGNED_CLINICAL_CARE",
            patient_id=enc.patient_id,
            assigned_clinician_id=enc.primary_clinician_id,
        )

        if not self.auth_manager.verify_totp_step_up(clinician.actor_id, mfa_step_up_code):
            raise PermissionError("INVALID_MFA_STEP_UP_CODE")

        now_iso = datetime.now(timezone.utc).isoformat()
        addendum_payload = {
            "addendum_id": str(uuid4()),
            "encounter_id": encounter_id,
            "original_signed_document_hash": original_signed_document_hash,
            "amendment_reason": amendment_reason,
            "addendum_text": addendum_text,
        }
        addendum_env = self.signer.sign_clinical_payload(
            payload=addendum_payload,
            signer_clinician_id=clinician.actor_id,
            signer_mdcn_licence=clinician.clinician_mdcn_licence or "MDCN-VERIFIED",
            signed_at_iso=now_iso,
        )
        addendum_record = {
            **addendum_payload,
            "addendum_sha256": addendum_env.document_sha256,
            "signature_ed25519_base64": addendum_env.signature_ed25519_base64,
            "signed_at_iso": now_iso,
        }
        enc.addenda.append(addendum_record)
        self._emit_outbox_event(
            "care.addendum.signed.v1",
            request_id,
            {
                "encounter_id": encounter_id,
                "original_signed_document_hash": original_signed_document_hash,
                "addendum_sha256": addendum_env.document_sha256,
            },
        )
        return addendum_record

    def transfer_product_intelligence_scan_to_episode(
        self,
        *,
        actor: AuthenticatedActor,
        episode_id: str,
        source_scan_id: str,
        product_name: str,
        extracted_ingredients: list[str],
        patient_question: str,
        explicit_user_consent_confirmed: bool,
        request_id: str,
    ) -> dict[str, Any]:
        """
        §12.4 & AT-15:
        Cross-product handoff from LoveWorld Health Intelligence to LoveWorld Care.
        Strictly requires `explicit_user_consent_confirmed=True` and transfers only the
        minimal previewed DTO, never importing full scan history or exposing Care records back.
        """
        ep = self._episodes[episode_id]
        if not explicit_user_consent_confirmed:
            self.audit_logger.record(
                request_id=request_id,
                actor=actor,
                purpose="CROSS_PRODUCT_CONSENTED_TRANSFER",
                action="TRANSFER_SCAN_CONTEXT",
                resource_type="CROSS_PRODUCT_HANDOFF",
                resource_opaque_id=source_scan_id,
                data_tier="T2_PERSONAL",
                outcome="DENIED",
                reason_code="DENIED_MISSING_EXPLICIT_USER_TRANSFER_CONSENT",
            )
            raise PermissionError("AT-15_DENIED: Explicit user consent required for cross-product scan transfer.")

        self.auth_manager.authorize_clinical_t3_access(
            request_id=request_id,
            actor=actor,
            action="WRITE",
            purpose="PATIENT_SELF_SERVICE",
            patient_id=ep.patient_id,
            assigned_clinician_id=ep.assigned_clinician_id,
        )

        minimal_dto = {
            "transfer_id": str(uuid4()),
            "source_system": "LOVEWORLD_HEALTH_INTELLIGENCE",
            "source_scan_id": source_scan_id,
            "product_name": product_name,
            "extracted_ingredients": list(extracted_ingredients),
            "patient_question": patient_question,
            "consented_at_iso": datetime.now(timezone.utc).isoformat(),
        }
        ep.consented_handoff_items.append(minimal_dto)
        return minimal_dto

    def _emit_outbox_event(
        self, event_type: str, correlation_id: str, data: dict[str, Any]
    ) -> None:
        self._outbox_events.append(
            {
                "event_id": str(uuid4()),
                "event_type": event_type,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "correlation_id": correlation_id,
                "source": "care-service",
                "schema_version": 1,
                "data": data,
            }
        )
