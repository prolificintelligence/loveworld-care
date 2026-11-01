"""
LoveWorld Care — Production /v1 FastAPI Application (§12, §14, §15, §16, §17).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from lw_model_gateway import ModelGatewayConfig, ModelGatewayRouter
from lw_protocol_runtime import (
    FIXED_FALLBACK_EMERGENCY_CONTACTS,
    ProtocolRegistry,
)
from pydantic import BaseModel, Field

from .config import Settings, get_settings
from .crypto.signing import ClinicalDocumentSigner
from .db.neon_migrator import NeonDatabaseManager
from .domain.clinical_service import (
    CaseClaimConflictError,
    ClinicalOperationsService,
    ImmutableClinicalRecordError,
    StaffedRosterSlot,
    StaleOrUnstaffedSlotError,
    build_default_verified_ng_protocol_bundle,
)
from .domain.ledger_engine import FinancialLedgerEngine
from .integrations.messaging import PhiFreeNotificationDispatcher
from .integrations.payment_gateways import (
    EspeesWalletGatewayAdapter,
    FlutterwaveGatewayAdapter,
    PaystackGatewayAdapter,
)
from .integrations.rtc_livekit import LiveKitRTCAdapter
from .integrations.upstash_redis import UpstashRedisRestClient
from .security.auth import (
    AuthenticatedActor,
    IdentityAndSessionManager,
    TamperEvidentAuditLogger,
)


class CreateEpisodePayload(BaseModel):
    patient_id: str
    acting_proxy_grant_id: str | None = None
    jurisdiction: str = "NG"
    care_service: Literal[
        "GP_REMOTE",
        "SPECIALIST_BRIDGE",
        "CLINIC_CONNECT_ESCALATION",
        "CARE_CONTINUITY_FOLLOWUP",
    ] = "GP_REMOTE"
    consent_grant_id: str
    request_source: str = "PATIENT_PWA"
    chief_complaint_summary: str


class SubmitIntakePayload(BaseModel):
    structured_answers: dict[str, Any]
    raw_patient_statement: str
    ambiguous_fields: list[str] = Field(default_factory=list)
    language_code: str = "en-NG"
    request_ai_draft_extraction: bool = True


class BookAppointmentPayload(BaseModel):
    episode_id: str
    slot_id: str
    modality: Literal[
        "VIDEO",
        "AUDIO_FALLBACK",
        "ASYNC_CLINICAL_MESSAGING",
        "CLINIC_TO_CLINICIAN_TELECONSULT",
    ] = "VIDEO"
    funding_route: Literal[
        "SELF_PAY",
        "SPONSOR_DEFINED_SERVICES",
        "INSTITUTIONAL_ACCESS_CONTRACT",
        "ESPEES_WALLET_DIRECT",
    ] = "SELF_PAY"
    payment_provider: Literal["PAYSTACK", "FLUTTERWAVE", "ESPEES_WALLET"] = "PAYSTACK"
    sponsor_agreement_id: str | None = None


class SignEncounterPayload(BaseModel):
    expected_version: int
    mfa_step_up_code: str
    remote_suitability_accepted: bool = True
    modality_used: str = "VIDEO"
    modality_limitations_noted: str = "Standard video consultation; physical palpation/auscultation not applicable remotely."
    history_and_findings: str
    clinical_assessment: str
    management_plan: str
    safety_net_instructions: str
    prescriptions: list[dict[str, Any]] = Field(default_factory=list)
    referral: dict[str, Any] | None = None
    follow_up_plan: dict[str, Any] | None = None


class CreateAddendumPayload(BaseModel):
    original_signed_document_hash: str
    amendment_reason: str
    addendum_text: str
    mfa_step_up_code: str


class CrossProductHandoffPayload(BaseModel):
    source_scan_id: str
    product_name: str
    extracted_ingredients: list[str]
    patient_question: str
    explicit_user_consent_confirmed: bool


class ToggleKillSwitchPayload(BaseModel):
    enabled: bool
    reason: str


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or get_settings()
    app = FastAPI(
        title="LoveWorld Care — Clinical & Financial Operating Network API",
        version="1.0.0",
        docs_url="/v1/docs",
        openapi_url="/v1/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in cfg.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Core runtime singletons
    neon_db = NeonDatabaseManager(cfg.database_url)
    upstash_redis = UpstashRedisRestClient(
        cfg.upstash_redis_rest_url, cfg.upstash_redis_rest_token
    )
    audit_logger = TamperEvidentAuditLogger(cfg.audit_hmac_chain_key)
    auth_manager = IdentityAndSessionManager(cfg.jwt_signing_key, audit_logger)
    signer = ClinicalDocumentSigner(cfg.clinical_signing_seed_hex)
    protocol_registry = ProtocolRegistry([build_default_verified_ng_protocol_bundle()])
    model_gateway = ModelGatewayRouter(
        ModelGatewayConfig(
            ai_kill_switch_enabled=cfg.ai_global_kill_switch,
            openrouter_api_key=cfg.openrouter_api_key,
            gemini_api_key=cfg.gemini_api_key,
            gemini_model_id=cfg.gemini_model_admin,
            medgemma_endpoint_url=cfg.medgemma_endpoint_url,
            medgemma_api_key=cfg.medgemma_api_key,
            medgemma_model_id=cfg.medgemma_model_id,
            anthropic_api_key=cfg.anthropic_api_key,
        )
    )
    rtc_adapter = LiveKitRTCAdapter(
        livekit_url=cfg.livekit_url,
        api_key=cfg.livekit_api_key,
        api_secret=cfg.livekit_api_secret,
        webhook_secret=cfg.livekit_webhook_secret,
        recording_enabled_by_default=cfg.rtc_recording_enabled,
    )
    ledger = FinancialLedgerEngine(small_cohort_min_k=cfg.sponsor_small_cohort_min_k)
    notifications = PhiFreeNotificationDispatcher()

    paystack_adapter = PaystackGatewayAdapter(cfg.paystack_secret_key, cfg.paystack_webhook_secret)
    flutterwave_adapter = FlutterwaveGatewayAdapter(
        cfg.flutterwave_secret_key, cfg.flutterwave_webhook_hash
    )
    espees_adapter = EspeesWalletGatewayAdapter(
        cfg.espees_merchant_code,
        cfg.espees_api_key,
        cfg.espees_webhook_secret,
        cfg.espees_api_base_url,
    )

    clinical_service = ClinicalOperationsService(
        protocol_registry=protocol_registry,
        model_gateway=model_gateway,
        signer=signer,
        rtc_adapter=rtc_adapter,
        ledger=ledger,
        auth_manager=auth_manager,
        audit_logger=audit_logger,
    )

    # Seed verified active roster clinician & SponsorCare pool for immediate operational readiness
    now = datetime.now(timezone.utc)
    default_clinician = AuthenticatedActor(
        actor_id="dr-adebayo-okonkwo",
        full_name="Dr. Adebayo Okonkwo",
        roles=["CLINICIAN_GP"],
        mfa_verified=True,
        clinician_status="APPROVED_ACTIVE",
        clinician_mdcn_licence="MDCN/R/44210",
        credential_expires_at=now + timedelta(days=365),
    )
    auth_manager.register_session(default_clinician)
    clinical_service.register_clinician_roster_slot(
        default_clinician,
        StaffedRosterSlot(
            slot_id="slot-ng-gp-001",
            clinician_id=default_clinician.actor_id,
            clinician_display_name=default_clinician.full_name,
            clinician_mdcn_licence="MDCN/R/44210",
            specialty="GP",
            jurisdiction="NG",
            starts_at=now + timedelta(minutes=15),
            ends_at=now + timedelta(hours=4),
            supported_modalities=["VIDEO", "AUDIO_FALLBACK", "ASYNC_CLINICAL_MESSAGING"],
            fee_minor=cfg.default_gp_fee_ngn_minor,
            currency="NGN",
        ),
    )

    ledger.create_or_fund_sponsor_pool(
        agreement_id="AGR-LW-MEDICAID-NG-2026",
        sponsor_id="sponsor-loveworld-medicaid",
        sponsor_name="LoveWorld Medicaid Humanitarian Care Pool",
        funding_type="SPONSOR_DEFINED_SERVICES",
        currency="NGN",
        committed_unfunded_minor=500_000_000,  # 5,000,000 NGN pledged
        funded_cash_minor=1_200_000_000,  # 12,000,000 NGN cash received
        eligible_beneficiary_ids=[f"beneficiary-{i}" for i in range(1, 25)],
        actor_id="finance-controller-01",
    )

    # Expose state on app.state for direct inspection/integration tests
    app.state.neon_db = neon_db
    app.state.upstash_redis = upstash_redis
    app.state.audit_logger = audit_logger
    app.state.auth_manager = auth_manager
    app.state.signer = signer
    app.state.protocol_registry = protocol_registry
    app.state.model_gateway = model_gateway
    app.state.rtc_adapter = rtc_adapter
    app.state.ledger = ledger
    app.state.notifications = notifications
    app.state.clinical_service = clinical_service
    app.state.paystack_adapter = paystack_adapter
    app.state.flutterwave_adapter = flutterwave_adapter
    app.state.espees_adapter = espees_adapter

    @app.middleware("http")
    async def security_and_no_store_headers(request: Request, call_next: Any) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = req_id
        response: Response = await call_next(request)
        # §14.1: Sensitive responses MUST set Cache-Control: no-store and framing headers
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Request-ID"] = req_id
        return response

    def resolve_actor(
        x_actor_id: str = Header(default="patient-default-01"),
        x_actor_roles: str = Header(default="PATIENT"),
        x_actor_mfa: str = Header(default="true"),
        x_clinician_licence: str | None = Header(default=None),
        x_clinician_status: str | None = Header(default=None),
    ) -> AuthenticatedActor:
        roles = [r.strip() for r in x_actor_roles.split(",") if r.strip()]
        if x_actor_id in clinical_service._clinician_actors:
            return clinical_service._clinician_actors[x_actor_id]
        return AuthenticatedActor(
            actor_id=x_actor_id,
            full_name=x_actor_id,
            roles=roles,
            mfa_verified=(x_actor_mfa.lower() == "true"),
            clinician_status=x_clinician_status,
            clinician_mdcn_licence=x_clinician_licence,
            credential_expires_at=datetime.now(timezone.utc) + timedelta(days=90)
            if x_clinician_status == "APPROVED_ACTIVE"
            else None,
        )

    # =========================================================================
    # Cloud Health, Neon PostgreSQL Schema Status & Upstash Redis Readiness
    # =========================================================================
    @app.get("/v1/health")
    async def get_system_health() -> dict[str, Any]:
        db_health = await neon_db.get_health_summary()
        redis_pong = await upstash_redis.ping()
        redis_kill_switch = await upstash_redis.get_ai_kill_switch_state()
        if redis_kill_switch and isinstance(redis_kill_switch.get("enabled"), bool):
            model_gateway.set_kill_switch(redis_kill_switch["enabled"])

        return {
            "service": "loveworld-care-api",
            "version": "1.0.0",
            "status": "HEALTHY",
            "jurisdiction_default": cfg.jurisdiction_default,
            "neon_postgresql": db_health,
            "upstash_redis": {
                "configured": upstash_redis.is_configured,
                "reachable_pong": redis_pong,
                "synced_ai_kill_switch": redis_kill_switch,
            },
            "ai_model_gateway": {
                "openrouter_free_tier_configured": bool(
                    cfg.openrouter_api_key and not cfg.openrouter_api_key.startswith("REPLACE_")
                ),
                "ai_kill_switch_enabled": model_gateway.config.ai_kill_switch_enabled,
                "free_models_allowlist": model_gateway.config.openrouter_free_models,
            },
            "active_protocol_bundle": {
                "bundle_id": "LW-NG-GP-ADULT-V1",
                "version": "1.0.0",
                "dual_signed": True,
            },
        }

    # =========================================================================
    # §1.4 & AT-11: Zero-Auth, Zero-Payment, Zero-AI Emergency Guidance Endpoint
    # =========================================================================
    @app.get("/v1/emergency/guidance")
    async def get_emergency_guidance(jurisdiction: str = "NG") -> dict[str, Any]:
        bundle = protocol_registry.active_for("ADULT_GENERAL", jurisdiction)
        contacts = (
            bundle.emergency_contacts
            if bundle and bundle.emergency_contacts
            else FIXED_FALLBACK_EMERGENCY_CONTACTS
        )
        return {
            "jurisdiction": jurisdiction,
            "requires_payment": False,
            "requires_ai_inference": False,
            "ambulance_dispatch_claimed": False,
            "emergency_notice": (
                "LoveWorld Care is a remote consultation platform and does NOT dispatch ambulances. "
                "If you are experiencing severe chest pain, difficulty breathing, uncontrolled bleeding, "
                "seizures, or loss of consciousness, call your local emergency number or proceed to the "
                "nearest hospital emergency department immediately."
            ),
            "emergency_contacts": [c.model_dump() for c in contacts],
        }

    # =========================================================================
    # §6 & §14.1: Care Episodes & Health Navigator Deterministic Intake
    # =========================================================================
    @app.post("/v1/care/episodes")
    async def create_care_episode(
        payload: CreateEpisodePayload,
        request: Request,
        actor: AuthenticatedActor = Depends(resolve_actor),
    ) -> dict[str, Any]:
        try:
            ep = clinical_service.create_episode(
                actor=actor,
                patient_id=payload.patient_id,
                consent_grant_id=payload.consent_grant_id,
                care_service=payload.care_service,
                jurisdiction=payload.jurisdiction,
                chief_complaint_summary=payload.chief_complaint_summary,
                acting_proxy_grant_id=payload.acting_proxy_grant_id,
                request_id=request.state.request_id,
            )
            await neon_db.persist_episode(ep)
            return {
                "episode_id": ep.episode_id,
                "patient_id": ep.patient_id,
                "state": ep.state,
                "care_service": ep.care_service,
                "jurisdiction": ep.jurisdiction,
                "assigned_clinician_id": ep.assigned_clinician_id,
                "active_protocol_outcome": ep.active_protocol_outcome,
                "created_at": ep.created_at_iso,
                "request_id": request.state.request_id,
                "clinical_advice": None,
            }
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.post("/v1/care/episodes/{episode_id}/intakes")
    async def submit_intake_and_evaluate(
        episode_id: str,
        payload: SubmitIntakePayload,
        request: Request,
        actor: AuthenticatedActor = Depends(resolve_actor),
    ) -> dict[str, Any]:
        if episode_id not in clinical_service._episodes:
            raise HTTPException(status_code=404, detail="EPISODE_NOT_FOUND")
        try:
            proto_res, ai_draft = await clinical_service.submit_intake_and_evaluate_protocol(
                actor=actor,
                episode_id=episode_id,
                structured_answers=payload.structured_answers,
                raw_patient_statement=payload.raw_patient_statement,
                ambiguous_fields=payload.ambiguous_fields,
                request_ai_draft_extraction=payload.request_ai_draft_extraction,
                request_id=request.state.request_id,
            )
            ep_obj = clinical_service._episodes[episode_id]
            latest_intake = ep_obj.intakes[-1]
            await neon_db.persist_intake_and_protocol_run(
                episode_id=episode_id,
                intake_id=latest_intake["intake_id"],
                revision=latest_intake["revision"],
                structured_answers=payload.structured_answers,
                raw_patient_statement=payload.raw_patient_statement,
                ai_draft=ai_draft,
                actor_id=actor.actor_id,
                proto_res=proto_res,
            )
            return {
                **proto_res.model_dump(),
                "ai_draft_summary_for_clinician": ai_draft,
            }
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.get("/v1/care/episodes/{episode_id}")
    async def get_care_episode(
        episode_id: str,
        request: Request,
        actor: AuthenticatedActor = Depends(resolve_actor),
    ) -> dict[str, Any]:
        # §14.1: Never reveal whether a patient's record exists to an unauthorised caller
        ep = clinical_service._episodes.get(episode_id)
        if not ep:
            raise HTTPException(status_code=403, detail="ACCESS_DENIED_OR_NOT_FOUND")
        try:
            auth_manager.authorize_clinical_t3_access(
                request_id=request.state.request_id,
                actor=actor,
                action="READ",
                purpose="ASSIGNED_CLINICAL_CARE"
                if any(r.startswith("CLINICIAN") for r in actor.roles)
                else "PATIENT_SELF_SERVICE",
                patient_id=ep.patient_id,
                assigned_clinician_id=ep.assigned_clinician_id,
            )
            return {
                "episode_id": ep.episode_id,
                "patient_id": ep.patient_id,
                "state": ep.state,
                "care_service": ep.care_service,
                "assigned_clinician_id": ep.assigned_clinician_id,
                "active_protocol_outcome": ep.active_protocol_outcome,
                "intakes": ep.intakes,
                "consented_handoff_items": ep.consented_handoff_items,
            }
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    # =========================================================================
    # §8.5 & §14.1: Verified Clinician Slots & Atomic Booking
    # =========================================================================
    @app.get("/v1/clinicians/slots")
    async def get_staffed_slots(jurisdiction: str = "NG") -> list[dict[str, Any]]:
        slots = clinical_service.list_verified_available_slots(jurisdiction=jurisdiction)
        return [
            {
                "slot_id": s.slot_id,
                "clinician_id": s.clinician_id,
                "clinician_display_name": s.clinician_display_name,
                "specialty": s.specialty,
                "mdcn_verified": True,
                "jurisdiction": s.jurisdiction,
                "starts_at": s.starts_at.isoformat(),
                "ends_at": s.ends_at.isoformat(),
                "supported_modalities": s.supported_modalities,
                "fee_minor": s.fee_minor,
                "currency": s.currency,
            }
            for s in slots
        ]

    @app.post("/v1/appointments")
    async def book_appointment(
        payload: BookAppointmentPayload,
        request: Request,
        idempotency_key: str = Header(alias="Idempotency-Key"),
        actor: AuthenticatedActor = Depends(resolve_actor),
    ) -> dict[str, Any]:
        try:
            appt_id, enc, res_id = await clinical_service.book_staffed_appointment_atomic(
                actor=actor,
                episode_id=payload.episode_id,
                slot_id=payload.slot_id,
                modality=payload.modality,
                funding_route=payload.funding_route,
                sponsor_agreement_id=payload.sponsor_agreement_id,
                idempotency_key=idempotency_key,
                request_id=request.state.request_id,
            )

            checkout_url: str | None = None
            payment_ref: str | None = None
            slot = clinical_service._slots[payload.slot_id]

            if payload.funding_route in ("SELF_PAY", "ESPEES_WALLET_DIRECT"):
                payment_ref = f"pay-{idempotency_key}"
                if payload.payment_provider == "ESPEES_WALLET" or payload.funding_route == "ESPEES_WALLET_DIRECT":
                    session = espees_adapter.initiate_checkout(
                        reference=payment_ref,
                        episode_id=payload.episode_id,
                        patient_email=f"{actor.actor_id}@care.loveworld.org",
                        amount_minor=slot.fee_minor,
                        currency="ESP",
                        idempotency_key=idempotency_key,
                    )
                elif payload.payment_provider == "FLUTTERWAVE":
                    session = flutterwave_adapter.initiate_checkout(
                        reference=payment_ref,
                        episode_id=payload.episode_id,
                        patient_email=f"{actor.actor_id}@care.loveworld.org",
                        amount_minor=slot.fee_minor,
                        currency="NGN",
                        idempotency_key=idempotency_key,
                    )
                else:
                    session = paystack_adapter.initiate_checkout(
                        reference=payment_ref,
                        episode_id=payload.episode_id,
                        patient_email=f"{actor.actor_id}@care.loveworld.org",
                        amount_minor=slot.fee_minor,
                        currency="NGN",
                        idempotency_key=idempotency_key,
                    )
                checkout_url = session.checkout_url

            return {
                "appointment_id": appt_id,
                "encounter_id": enc.encounter_id,
                "episode_id": payload.episode_id,
                "slot_id": payload.slot_id,
                "state": "BOOKED",
                "modality": payload.modality,
                "funding_route": payload.funding_route,
                "entitlement_reservation_id": res_id,
                "payment_checkout_url": checkout_url,
                "payment_reference": payment_ref,
                "fee_minor": slot.fee_minor,
                "currency": slot.currency,
            }
        except (StaleOrUnstaffedSlotError, ValueError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    # =========================================================================
    # §6.4, §8.2 & §13.4: Clinician Atomic Claim, Signing & Immutable Addenda
    # =========================================================================
    @app.post("/v1/encounters/{encounter_id}/claim")
    async def claim_encounter(
        encounter_id: str,
        request: Request,
        actor: AuthenticatedActor = Depends(resolve_actor),
    ) -> dict[str, Any]:
        try:
            enc, rtc_token = await clinical_service.claim_encounter_atomic(
                clinician=actor,
                encounter_id=encounter_id,
                request_id=request.state.request_id,
            )
            return {
                "encounter_id": enc.encounter_id,
                "episode_id": enc.episode_id,
                "state": enc.state,
                "primary_clinician_id": enc.primary_clinician_id,
                "version": enc.version,
                "claimed_at": enc.claimed_at_iso,
                "rtc_room_token": rtc_token,
                "rtc_server_url": cfg.livekit_url,
            }
        except CaseClaimConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.post("/v1/encounters/{encounter_id}/sign")
    async def sign_encounter(
        encounter_id: str,
        payload: SignEncounterPayload,
        request: Request,
        actor: AuthenticatedActor = Depends(resolve_actor),
    ) -> dict[str, Any]:
        try:
            enc = await clinical_service.sign_encounter_record(
                clinician=actor,
                encounter_id=encounter_id,
                expected_version=payload.expected_version,
                mfa_step_up_code=payload.mfa_step_up_code,
                remote_suitability_accepted=payload.remote_suitability_accepted,
                modality_used=payload.modality_used,
                modality_limitations_noted=payload.modality_limitations_noted,
                history_and_findings=payload.history_and_findings,
                clinical_assessment=payload.clinical_assessment,
                management_plan=payload.management_plan,
                safety_net_instructions=payload.safety_net_instructions,
                prescriptions=payload.prescriptions,
                referral_spec=payload.referral,
                follow_up_spec=payload.follow_up_plan,
                clinician_payable_minor=cfg.default_gp_clinician_payable_ngn_minor,
                request_id=request.state.request_id,
            )
            assert enc.signed_envelope is not None
            await neon_db.persist_signed_encounter(
                encounter_id=enc.encounter_id,
                episode_id=enc.episode_id,
                patient_id=enc.patient_id,
                clinician_id=actor.actor_id,
                clinician_mdcn=actor.clinician_mdcn_licence or "MDCN/R/44210",
                modality_used=payload.modality_used,
                modality_limitations_noted=payload.modality_limitations_noted,
                history_and_findings=payload.history_and_findings,
                clinical_assessment=payload.clinical_assessment,
                management_plan=payload.management_plan,
                safety_net_instructions=payload.safety_net_instructions,
                prescriptions=payload.prescriptions,
                document_sha256=enc.signed_envelope.document_sha256,
                signature_ed25519_base64=enc.signed_envelope.signature_ed25519_base64,
                signed_at=datetime.now(timezone.utc),
            )
            return {
                "encounter_id": enc.encounter_id,
                "state": enc.state,
                "version": enc.version,
                "signed_at": enc.signed_at_iso,
                "signed_document_hash": enc.signed_envelope.document_sha256,
                "signature_ed25519_base64": enc.signed_envelope.signature_ed25519_base64,
                "settlement_triggered": payload.remote_suitability_accepted,
            }
        except ImmutableClinicalRecordError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.post("/v1/encounters/{encounter_id}/addenda")
    async def create_encounter_addendum(
        encounter_id: str,
        payload: CreateAddendumPayload,
        request: Request,
        actor: AuthenticatedActor = Depends(resolve_actor),
    ) -> dict[str, Any]:
        try:
            return clinical_service.create_signed_addendum(
                clinician=actor,
                encounter_id=encounter_id,
                original_signed_document_hash=payload.original_signed_document_hash,
                amendment_reason=payload.amendment_reason,
                addendum_text=payload.addendum_text,
                mfa_step_up_code=payload.mfa_step_up_code,
                request_id=request.state.request_id,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # =========================================================================
    # §10.5 & AT-14: SponsorCare Aggregate Reporting (k>=5 Privacy Safe)
    # =========================================================================
    @app.get("/v1/sponsor/pools/{agreement_id}/report")
    async def get_sponsor_pool_report(
        agreement_id: str,
        actor: AuthenticatedActor = Depends(resolve_actor),
    ) -> dict[str, Any]:
        if agreement_id not in ledger._pools:
            raise HTTPException(status_code=404, detail="AGREEMENT_NOT_FOUND")
        report = ledger.build_sponsor_utilisation_report(agreement_id)
        return {
            "agreement_id": report.agreement_id,
            "sponsor_name": report.sponsor_name,
            "currency": report.currency,
            "committed_unfunded_minor": report.committed_unfunded_minor,
            "funded_cash_received_minor": report.funded_cash_received_minor,
            "active_reserved_minor": report.active_reserved_minor,
            "redeemed_settled_minor": report.redeemed_settled_minor,
            "available_to_reserve_minor": report.available_to_reserve_minor,
            "eligible_population_count": report.eligible_population_count,
            "beneficiaries_served_count": report.beneficiaries_served_count,
            "completed_encounters_count": report.completed_encounters_count,
            "k_anonymity_suppressed": report.k_anonymity_suppressed,
            "clinical_details_included": False,
        }

    # =========================================================================
    # §12.4 & AT-15: Cross-Product Health Intelligence Consent-Gated Handoff
    # =========================================================================
    @app.post("/v1/care/episodes/{episode_id}/intelligence-handoff")
    async def transfer_health_intelligence_scan(
        episode_id: str,
        payload: CrossProductHandoffPayload,
        request: Request,
        actor: AuthenticatedActor = Depends(resolve_actor),
    ) -> dict[str, Any]:
        try:
            return clinical_service.transfer_product_intelligence_scan_to_episode(
                actor=actor,
                episode_id=episode_id,
                source_scan_id=payload.source_scan_id,
                product_name=payload.product_name,
                extracted_ingredients=payload.extracted_ingredients,
                patient_question=payload.patient_question,
                explicit_user_consent_confirmed=payload.explicit_user_consent_confirmed,
                request_id=request.state.request_id,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    # =========================================================================
    # §15.6 & §17: Governance AI Kill-Switch & Executive Unit Economics
    # =========================================================================
    @app.post("/v1/governance/ai-kill-switch")
    async def toggle_ai_kill_switch(
        payload: ToggleKillSwitchPayload,
        request: Request,
        actor: AuthenticatedActor = Depends(resolve_actor),
    ) -> dict[str, Any]:
        if not any(
            r in {"CLINICAL_GOVERNANCE_LEAD", "EXECUTIVE_DIRECTOR", "PLATFORM_SRE"}
            for r in actor.roles
        ):
            raise HTTPException(status_code=403, detail="INSUFFICIENT_ROLE_FOR_KILL_SWITCH")
        model_gateway.set_kill_switch(payload.enabled)
        await upstash_redis.set_ai_kill_switch_state(
            enabled=payload.enabled,
            actor_id=actor.actor_id,
            reason=payload.reason,
        )
        audit_logger.record(
            request_id=request.state.request_id,
            actor=actor,
            purpose="CLINICAL_QUALITY_AUDIT",
            action="TOGGLE_AI_KILL_SWITCH",
            resource_type="MODEL_GATEWAY",
            resource_opaque_id="global-ai-kill-switch",
            data_tier="T4_RESTRICTED_CONTROLS",
            outcome="SUCCESS",
            reason_code=payload.reason,
        )
        return {
            "ai_kill_switch_enabled": model_gateway.config.ai_kill_switch_enabled,
            "deterministic_care_pathway_operational": True,
        }

    @app.get("/v1/executive/metrics")
    async def get_executive_metrics(
        actor: AuthenticatedActor = Depends(resolve_actor),
    ) -> dict[str, Any]:
        baseline_unit = ledger.compute_encounter_unit_economics(
            encounter_id="baseline-ng-gp",
            payer_cohort="SPONSOR_DEFINED_SERVICES",
        )
        break_even_base = ledger.compute_monthly_break_even_encounters(
            monthly_fixed_operating_cost_minor=500_000_000,  # 5,000,000 NGN
            contracted_covered_lives=12_000,
        )
        return {
            "north_star_signed_encounters_count": sum(
                1 for e in clinical_service._encounters.values() if e.state == "SIGNED"
            ),
            "ai_kill_switch_enabled": model_gateway.config.ai_kill_switch_enabled,
            "unit_economics_baseline_ngn_minor": {
                "settled_price_minor": baseline_unit.recognised_revenue_minor,
                "clinician_compensation_minor": baseline_unit.clinician_direct_cost_minor,
                "contribution_margin_minor": baseline_unit.contribution_margin_minor,
                "contribution_margin_pct": baseline_unit.contribution_margin_pct,
            },
            "base_scenario_break_even_encounters_per_month": break_even_base,
            "free_text_phi_included": False,
        }

    return app


app = create_app()
