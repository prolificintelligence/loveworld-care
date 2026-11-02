"""
LoveWorld Care — Production /v1 FastAPI Application (§12, §14, §15, §16, §17).
"""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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
    CareContinuityPlanRecord,
    CareEpisodeRecord,
    CareRelationshipRecord,
    CareTaskRecord,
    CaseClaimConflictError,
    ClinicalObservationRecord,
    ClinicalOperationsService,
    CoordinationTaskRecord,
    DirectorateActionRecord,
    EncounterRecord,
    FacilityRecord,
    ImmutableClinicalRecordError,
    MedicationInstructionRecord,
    PatientSubjectRecord,
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
from .security.tokens import (
    AUD_CLINICIAN,
    AUD_COMMAND,
    AUD_PATIENT,
    AUD_SPONSOR,
    STAFF_AUDIENCES,
    TokenClaims,
    TokenError,
    TokenService,
)

CLINICIAN_ROLES = frozenset({"CLINICIAN_GP", "CLINICIAN_SPECIALIST"})
KILL_SWITCH_ROLES = frozenset({"CLINICAL_GOVERNANCE_LEAD", "EXECUTIVE_DIRECTOR", "PLATFORM_SRE"})
EXECUTIVE_METRICS_ROLES = frozenset(
    {"EXECUTIVE_DIRECTOR", "FINANCE_CONTROLLER", "CLINICAL_GOVERNANCE_LEAD"}
)


class DevTokenPayload(BaseModel):
    """Development/test only. Production tokens are issued by the real login flows."""

    sub: str
    audience: Literal["lwc:patient", "lwc:clinician", "lwc:command", "lwc:sponsor"]
    roles: list[str]
    mfa: bool = False
    org: str | None = None
    ttl_minutes: int = Field(default=30, ge=1, le=480)


class MagicLinkRequestPayload(BaseModel):
    email: str
    redirect_url: str | None = None


class MagicLinkVerifyPayload(BaseModel):
    token: str


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


class CreateSubjectPayload(BaseModel):
    full_name: str
    dob_iso: str
    gender: str = "UNSPECIFIED"
    relationship: str = "SELF"
    jurisdiction: str = "NG"


class CreateCareRelationshipPayload(BaseModel):
    patient_id: str
    relationship_type: str = "ADULT_PROXY"
    allowed_scopes: list[str] = Field(
        default_factory=lambda: [
            "INTAKE",
            "BOOKING",
            "VIEW_RECORDS",
            "CARE_PLAN",
            "REMINDERS",
            "PAYMENTS",
        ]
    )


class CreateCarePlanPayload(BaseModel):
    episode_id: str
    encounter_id: str
    programme_name: str
    monitoring_instructions: str
    due_at_iso: str
    goals: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)


class PrescribeMedicationPayload(BaseModel):
    encounter_id: str
    medication_name: str
    dosage_instructions: str
    frequency_per_day: int = 1
    duration_days: int = 7
    clinical_indication: str = ""


class RecordAdherencePayload(BaseModel):
    status: Literal["TAKEN", "SKIPPED", "ISSUE"] = "TAKEN"
    notes: str | None = None


class CreateCareTaskPayload(BaseModel):
    episode_id: str | None = None
    encounter_id: str | None = None
    assigned_to: Literal["PATIENT", "CLINICIAN", "COORDINATOR"] = "PATIENT"
    task_type: Literal[
        "MEDICATION_REMINDER",
        "CHECK_IN",
        "RESULT_REVIEW",
        "FOLLOW_UP",
        "REFERRAL_FOLLOW_UP",
        "CLINICAL_REVIEW",
    ] = "FOLLOW_UP"
    title: str
    description: str = ""
    due_at_iso: str


class ResolveCareTaskPayload(BaseModel):
    self_reported: bool = True
    notes: str | None = None


class RecordObservationPayload(BaseModel):
    kind: Literal["SYMPTOM", "VITAL", "LAB_RESULT", "DOCUMENT"] = "VITAL"
    name: str
    value: str
    unit: str | None = None
    notes: str | None = None
    source: Literal["PATIENT_REPORTED", "CLINICIAN_ENTERED", "LAB_UPLOAD"] = "PATIENT_REPORTED"


class CompanionChatPayload(BaseModel):
    patient_id: str | None = None
    message: str
    jurisdiction: str = "NG"


class ResolveCoordinationTaskPayload(BaseModel):
    disposition: str


class AcceptReferralPayload(BaseModel):
    receiving_facility_code: str


class DeclineReferralPayload(BaseModel):
    decline_reason: str


class FacilityRegistrationPayload(BaseModel):
    facility_id: str
    facility_name: str
    facility_code: str
    address: str
    jurisdiction: str = "NG"
    geocoordinates: dict[str, float] = Field(default_factory=dict)
    services: list[str] = Field(default_factory=list)
    hours: str = "24/7"
    contact_phone: str = ""
    is_verified: bool = True
    readiness_state: Literal["CONFIRMED_AVAILABLE", "STALE", "UNAVAILABLE"] = "CONFIRMED_AVAILABLE"
    validity_minutes: int = 60


class FacilityReadinessPayload(BaseModel):
    readiness_state: Literal["CONFIRMED_AVAILABLE", "STALE", "UNAVAILABLE"] = "CONFIRMED_AVAILABLE"
    validity_minutes: int = 30


class CreateFinanceExceptionPayload(BaseModel):
    agreement_id: str | None = None
    encounter_id: str | None = None
    exception_type: str
    amount_minor: int
    currency: str = "NGN"
    reason: str


class ActionFinanceExceptionPayload(BaseModel):
    action: Literal["APPROVE", "REJECT", "REMEDIATE"]
    notes: str


class CreateDirectorateActionPayload(BaseModel):
    metric_id: str
    title: str
    description: str
    owner_team: str
    assigned_to: str
    due_date_iso: str


class UpdateDirectorateActionPayload(BaseModel):
    status: Literal["OPEN", "IN_PROGRESS", "RESOLVED"]
    evidence_notes: str = ""


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or get_settings()
    # ADR-0003: fail closed. Production refuses default/placeholder secrets, SQLite, or
    # non-HTTPS / localhost CORS origins.
    cfg.assert_safe_for_runtime()
    app = FastAPI(
        title="LoveWorld Care — Clinical & Financial Operating Network API",
        version="1.0.0",
        docs_url=None if cfg.is_production else "/v1/docs",
        openapi_url="/v1/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in cfg.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    token_service = TokenService(
        signing_seed_hex=cfg.token_signing_seed_hex or TokenService.generate_seed_hex(),
        issuer=cfg.token_issuer,
        default_ttl=timedelta(minutes=cfg.access_token_ttl_minutes),
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

    # Synthetic roster clinician & SponsorCare pool for development/test ONLY. In production,
    # clinicians enter the roster exclusively through verified credentialing (§8.1), and
    # sponsor pools are funded through finance-approved agreements (§10.2).
    now = datetime.now(timezone.utc)
    if not cfg.is_production:
        _seed_non_production_fixtures(cfg, auth_manager, clinical_service, ledger, now)

    # Expose state on app.state for direct inspection/integration tests
    app.state.token_service = token_service
    app.state.settings = cfg
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

    # =========================================================================
    # ADR-0002/0003: Verified bearer-token identity. Client identity headers are ignored.
    # =========================================================================
    bearer_scheme = HTTPBearer(auto_error=False)

    def _unauthorized(code: str) -> HTTPException:
        return HTTPException(
            status_code=401, detail=code, headers={"WWW-Authenticate": 'Bearer error="invalid_token"'}
        )

    def _actor_from_claims(claims: TokenClaims) -> AuthenticatedActor:
        if CLINICIAN_ROLES & set(claims.roles):
            # §8.1 / AT-07: licence, status and expiry come from the server-side roster only.
            registered = clinical_service._clinician_actors.get(claims.sub)
            if registered is not None:
                return replace(
                    registered, mfa_verified=claims.mfa, session_id=claims.sid
                )
        return AuthenticatedActor(
            actor_id=claims.sub,
            full_name=claims.sub,
            roles=list(claims.roles),
            mfa_verified=claims.mfa,
            session_id=claims.sid,
        )

    def authenticated(
        *audiences: str,
        roles: frozenset[str] | None = None,
        require_mfa: bool = False,
    ) -> Any:
        allowed_audiences = frozenset(audiences)

        async def dependency(
            request: Request,
            credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        ) -> AuthenticatedActor:
            if credentials is None or credentials.scheme.lower() != "bearer":
                raise _unauthorized("TOKEN_MISSING")
            try:
                claims = token_service.verify(credentials.credentials, allowed_audiences)
            except TokenError as exc:
                if exc.code == "TOKEN_AUDIENCE_NOT_PERMITTED":
                    # AT-06: out-of-scope access attempts are denied AND audited.
                    identity = token_service.identify_for_audit(credentials.credentials)
                    if identity is not None:
                        audit_logger.record(
                            request_id=request.state.request_id,
                            actor=AuthenticatedActor(
                                actor_id=identity[0],
                                full_name=identity[0],
                                roles=list(identity[1]),
                                mfa_verified=False,
                            ),
                            purpose="ACCESS_CONTROL",
                            action=f"{request.method} {request.url.path}",
                            resource_type="API_ROUTE",
                            resource_opaque_id=request.url.path,
                            data_tier="T4_RESTRICTED_CONTROLS",
                            outcome="DENIED",
                            reason_code="DENIED_AUDIENCE_NOT_PERMITTED",
                        )
                raise _unauthorized(exc.code) from exc
            if roles is not None and not (roles & set(claims.roles)):
                raise HTTPException(status_code=403, detail="INSUFFICIENT_ROLE")
            staff_mutation = claims.aud in STAFF_AUDIENCES and request.method != "GET"
            if (require_mfa or staff_mutation) and not claims.mfa:
                raise HTTPException(status_code=403, detail="DENIED_MFA_REQUIRED")
            request.state.token_claims = claims
            return _actor_from_claims(claims)

        return dependency

    def _assert_patient_owns_episode(
        actor: AuthenticatedActor, episode_id: str, request_id: str
    ) -> None:
        ep = clinical_service._episodes.get(episode_id)
        if ep is None:
            raise HTTPException(status_code=403, detail="ACCESS_DENIED_OR_NOT_FOUND")
        try:
            auth_manager.authorize_clinical_t3_access(
                request_id=request_id,
                actor=actor,
                action="WRITE",
                purpose="PATIENT_SELF_SERVICE",
                patient_id=ep.patient_id,
                assigned_clinician_id=ep.assigned_clinician_id,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail="ACCESS_DENIED_OR_NOT_FOUND") from exc

    patient_actor = authenticated(AUD_PATIENT)
    clinician_actor = authenticated(AUD_CLINICIAN, roles=CLINICIAN_ROLES, require_mfa=True)
    care_reader_actor = authenticated(AUD_PATIENT, AUD_CLINICIAN)
    sponsor_report_actor = authenticated(AUD_SPONSOR, AUD_COMMAND)
    kill_switch_actor = authenticated(AUD_COMMAND, roles=KILL_SWITCH_ROLES, require_mfa=True)
    executive_metrics_actor = authenticated(
        AUD_COMMAND, roles=EXECUTIVE_METRICS_ROLES, require_mfa=True
    )
    command_actor = authenticated(AUD_COMMAND)
    finance_actor = authenticated(
        AUD_COMMAND, roles=frozenset({"FINANCE_CONTROLLER", "EXECUTIVE_DIRECTOR"})
    )
    coordination_actor = authenticated(AUD_COMMAND, AUD_CLINICIAN)
    patient_or_clinician_actor = authenticated(AUD_PATIENT, AUD_CLINICIAN)
    any_authenticated_actor = authenticated(AUD_PATIENT, AUD_CLINICIAN, AUD_COMMAND, AUD_SPONSOR)

    # =========================================================================
    # Auth: token introspection, logout, public key, and dev-only token minting
    # =========================================================================
    @app.get("/v1/auth/jwks")
    async def get_token_jwks() -> dict[str, Any]:
        return {"keys": [token_service.public_jwk()]}

    @app.get("/v1/auth/me")
    async def get_current_identity(
        request: Request,
        actor: AuthenticatedActor = Depends(
            authenticated(AUD_PATIENT, AUD_CLINICIAN, AUD_COMMAND, AUD_SPONSOR)
        ),
    ) -> dict[str, Any]:
        claims: TokenClaims = request.state.token_claims
        return {
            "sub": claims.sub,
            "audience": claims.aud,
            "roles": list(claims.roles),
            "mfa": claims.mfa,
            "org": claims.org,
            "expires_at": claims.expires_at.isoformat(),
            "clinician_credential_active": actor.is_clinician_credential_active()
            if CLINICIAN_ROLES & set(claims.roles)
            else None,
        }

    @app.post("/v1/auth/logout", status_code=204)
    async def logout(
        request: Request,
        _actor: AuthenticatedActor = Depends(
            authenticated(AUD_PATIENT, AUD_CLINICIAN, AUD_COMMAND, AUD_SPONSOR)
        ),
    ) -> Response:
        token_service.revoke_session(request.state.token_claims.sid)
        return Response(status_code=204)

    # In-memory magic link repository (single-use tokens with 15-minute TTL)
    pending_magic_links: dict[str, dict[str, Any]] = {}

    @app.post("/v1/auth/magic-link/request")
    async def request_magic_link(
        payload: MagicLinkRequestPayload,
        request: Request,
    ) -> dict[str, Any]:
        email = payload.email.strip().lower()
        if "@" not in email or "." not in email:
            raise HTTPException(status_code=400, detail="INVALID_EMAIL_FORMAT")
        raw_token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        pending_magic_links[raw_token] = {
            "email": email,
            "expires_at": now + timedelta(minutes=15),
            "used": False,
        }
        return {
            "status": "SENT",
            "email": email,
            "expires_in_minutes": 15,
            "verification_token": raw_token if cfg.environment != "production" else None,
        }

    @app.post("/v1/auth/magic-link/verify")
    async def verify_magic_link(payload: MagicLinkVerifyPayload) -> dict[str, Any]:
        record = pending_magic_links.get(payload.token)
        now = datetime.now(timezone.utc)
        if not record or record["used"] or record["expires_at"] < now:
            raise HTTPException(status_code=401, detail="INVALID_OR_EXPIRED_MAGIC_LINK")
        record["used"] = True
        email = record["email"]
        patient_id = f"pat-{hashlib.sha256(email.encode()).hexdigest()[:12]}"
        access_token = token_service.issue(
            sub=patient_id,
            audience=AUD_PATIENT,
            roles=["PATIENT"],
            mfa=False,
            ttl=timedelta(hours=24),
        )
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "patient_id": patient_id,
            "email": email,
        }

    if cfg.dev_token_endpoint_enabled:

        @app.post("/v1/auth/dev-token", include_in_schema=False)
        async def mint_dev_token(payload: DevTokenPayload) -> dict[str, Any]:
            try:
                token = token_service.issue(
                    sub=payload.sub,
                    audience=payload.audience,
                    roles=payload.roles,
                    mfa=payload.mfa,
                    org=payload.org,
                    ttl=timedelta(minutes=payload.ttl_minutes),
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return {"access_token": token, "token_type": "Bearer"}

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
        actor: AuthenticatedActor = Depends(patient_actor),
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
                "chief_complaint_summary": ep.chief_complaint_summary,
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
        actor: AuthenticatedActor = Depends(patient_actor),
    ) -> dict[str, Any]:
        _assert_patient_owns_episode(actor, episode_id, request.state.request_id)
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
        actor: AuthenticatedActor = Depends(care_reader_actor),
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
                "jurisdiction": ep.jurisdiction,
                "chief_complaint_summary": ep.chief_complaint_summary,
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
        actor: AuthenticatedActor = Depends(patient_actor),
    ) -> dict[str, Any]:
        _assert_patient_owns_episode(actor, payload.episode_id, request.state.request_id)
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
    @app.get("/v1/encounters")
    async def list_clinician_encounters(
        state: str | None = None,
        actor: AuthenticatedActor = Depends(clinician_actor),
    ) -> list[dict[str, Any]]:
        results = []
        for enc in clinical_service._encounters.values():
            if state and enc.state != state:
                continue
            if enc.primary_clinician_id is None or enc.primary_clinician_id == actor.actor_id:
                ep = clinical_service._episodes.get(enc.episode_id)
                results.append(
                    {
                        "encounter_id": enc.encounter_id,
                        "episode_id": enc.episode_id,
                        "patient_id": enc.patient_id,
                        "state": enc.state,
                        "modality": enc.modality,
                        "funding_route": enc.funding_route,
                        "primary_clinician_id": enc.primary_clinician_id,
                        "version": enc.version,
                        "claimed_at": enc.claimed_at_iso,
                        "signed_at": enc.signed_at_iso,
                        "signed_document_hash": enc.signed_envelope.document_sha256
                        if enc.signed_envelope
                        else None,
                        "chief_complaint": ep.chief_complaint_summary if ep else None,
                        "addenda_count": len(enc.addenda),
                    }
                )
        return results

    @app.get("/v1/encounters/{encounter_id}")
    async def get_encounter_details(
        encounter_id: str,
        actor: AuthenticatedActor = Depends(clinician_actor),
    ) -> dict[str, Any]:
        if encounter_id not in clinical_service._encounters:
            raise HTTPException(status_code=404, detail="ENCOUNTER_NOT_FOUND")
        enc = clinical_service._encounters[encounter_id]
        ep = clinical_service._episodes.get(enc.episode_id)
        return {
            "encounter_id": enc.encounter_id,
            "episode_id": enc.episode_id,
            "patient_id": enc.patient_id,
            "state": enc.state,
            "modality": enc.modality,
            "funding_route": enc.funding_route,
            "primary_clinician_id": enc.primary_clinician_id,
            "version": enc.version,
            "claimed_at": enc.claimed_at_iso,
            "signed_at": enc.signed_at_iso,
            "signed_document_hash": enc.signed_envelope.document_sha256
            if enc.signed_envelope
            else None,
            "signed_clinical_note": enc.signed_clinical_note,
            "chief_complaint": ep.chief_complaint_summary if ep else None,
            "intakes": ep.intakes if ep else [],
            "addenda": enc.addenda,
        }

    @app.post("/v1/encounters/{encounter_id}/claim")
    async def claim_encounter(
        encounter_id: str,
        request: Request,
        actor: AuthenticatedActor = Depends(clinician_actor),
    ) -> dict[str, Any]:
        if encounter_id not in clinical_service._encounters:
            raise HTTPException(status_code=404, detail="ENCOUNTER_NOT_FOUND")
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
        actor: AuthenticatedActor = Depends(clinician_actor),
    ) -> dict[str, Any]:
        if encounter_id not in clinical_service._encounters:
            raise HTTPException(status_code=404, detail="ENCOUNTER_NOT_FOUND")
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
        actor: AuthenticatedActor = Depends(clinician_actor),
    ) -> dict[str, Any]:
        if encounter_id not in clinical_service._encounters:
            raise HTTPException(status_code=404, detail="ENCOUNTER_NOT_FOUND")
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
        request: Request,
        actor: AuthenticatedActor = Depends(sponsor_report_actor),
    ) -> dict[str, Any]:
        claims: TokenClaims = request.state.token_claims
        pool = ledger._pools.get(agreement_id)
        if claims.aud == AUD_SPONSOR:
            # ADR-0005: a sponsor sees only its own agreements; existence is not revealed.
            if pool is None or not claims.org or pool.sponsor_id != claims.org:
                raise HTTPException(status_code=403, detail="ACCESS_DENIED_OR_NOT_FOUND")
        else:
            if "FINANCE_CONTROLLER" not in claims.roles:
                raise HTTPException(status_code=403, detail="INSUFFICIENT_ROLE")
            if pool is None:
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
        actor: AuthenticatedActor = Depends(patient_actor),
    ) -> dict[str, Any]:
        _assert_patient_owns_episode(actor, episode_id, request.state.request_id)
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
        actor: AuthenticatedActor = Depends(kill_switch_actor),
    ) -> dict[str, Any]:
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
        actor: AuthenticatedActor = Depends(executive_metrics_actor),
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
            "operational_overview": {
                "staffed_roster_slots_count": len(clinical_service._slots),
                "encounters_queued_or_active_count": sum(
                    1
                    for e in clinical_service._encounters.values()
                    if e.state in ("TRIAGED", "IN_CONSULTATION", "BOOKED")
                ),
                "sponsor_active_pools_count": len(ledger._pools),
                "sponsor_unredeemed_liability_minor": sum(
                    p.available_to_reserve_minor + p.active_reserved_minor
                    for p in ledger._pools.values()
                ),
                "clinician_pending_payables_minor": sum(
                    p.clinician_payable_minor
                    for p in ledger._payables_by_encounter.values()
                    if p.status != "PAID"
                ),
            },
        }

    # =========================================================================
    # §4 & LWC-ACC-001 - 005: Subject & Relationship Identity
    # =========================================================================
    @app.get("/v1/identity/subjects")
    async def list_patient_subjects(
        actor: AuthenticatedActor = Depends(any_authenticated_actor),
    ) -> list[dict[str, Any]]:
        subjects = clinical_service.list_subjects_for_actor(actor)
        return [asdict(s) for s in subjects]

    @app.post("/v1/identity/subjects")
    async def create_patient_subject(
        payload: CreateSubjectPayload,
        actor: AuthenticatedActor = Depends(patient_actor),
    ) -> dict[str, Any]:
        subj = clinical_service.create_patient_subject(
            actor=actor,
            full_name=payload.full_name,
            dob_iso=payload.dob_iso,
            gender=payload.gender,
            relationship=payload.relationship,
            jurisdiction=payload.jurisdiction,
        )
        return asdict(subj)

    @app.post("/v1/identity/relationships")
    async def create_care_relationship(
        payload: CreateCareRelationshipPayload,
        actor: AuthenticatedActor = Depends(patient_actor),
    ) -> dict[str, Any]:
        rel = clinical_service.create_care_relationship(
            actor=actor,
            patient_id=payload.patient_id,
            relationship_type=payload.relationship_type,
            allowed_scopes=payload.allowed_scopes,
        )
        return asdict(rel)

    @app.post("/v1/identity/relationships/{relationship_id}/revoke")
    async def revoke_care_relationship(
        relationship_id: str,
        actor: AuthenticatedActor = Depends(patient_actor),
    ) -> dict[str, Any]:
        try:
            clinical_service.revoke_care_relationship(actor=actor, relationship_id=relationship_id)
            return {"revoked": True, "relationship_id": relationship_id}
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    # =========================================================================
    # §5 & LWC-SCR-101 - 108: Patient Longitudinal Care & Dashboard
    # =========================================================================
    @app.get("/v1/care/patients/{patient_id}/dashboard")
    async def get_patient_dashboard(
        patient_id: str,
        actor: AuthenticatedActor = Depends(patient_or_clinician_actor),
    ) -> dict[str, Any]:
        return clinical_service.get_patient_dashboard(actor=actor, patient_id=patient_id)

    @app.get("/v1/care/patients/{patient_id}/care-plans")
    async def list_patient_care_plans(
        patient_id: str,
        actor: AuthenticatedActor = Depends(patient_or_clinician_actor),
    ) -> list[dict[str, Any]]:
        plans = clinical_service.list_care_plans(patient_id=patient_id)
        return [asdict(p) for p in plans]

    @app.post("/v1/care/patients/{patient_id}/care-plans")
    async def create_patient_care_plan(
        patient_id: str,
        payload: CreateCarePlanPayload,
        actor: AuthenticatedActor = Depends(clinician_actor),
    ) -> dict[str, Any]:
        plan = clinical_service.create_or_update_care_plan(
            clinician=actor,
            patient_id=patient_id,
            episode_id=payload.episode_id,
            encounter_id=payload.encounter_id,
            programme_name=payload.programme_name,
            monitoring_instructions=payload.monitoring_instructions,
            due_at_iso=payload.due_at_iso,
            goals=payload.goals,
            actions=payload.actions,
        )
        return asdict(plan)

    @app.get("/v1/care/patients/{patient_id}/medications")
    async def list_patient_medications(
        patient_id: str,
        actor: AuthenticatedActor = Depends(patient_or_clinician_actor),
    ) -> list[dict[str, Any]]:
        meds = clinical_service.list_medications(patient_id=patient_id)
        return [asdict(m) for m in meds]

    @app.post("/v1/care/patients/{patient_id}/medications")
    async def prescribe_medication(
        patient_id: str,
        payload: PrescribeMedicationPayload,
        actor: AuthenticatedActor = Depends(clinician_actor),
    ) -> dict[str, Any]:
        med = clinical_service.prescribe_medication(
            clinician=actor,
            patient_id=patient_id,
            encounter_id=payload.encounter_id,
            medication_name=payload.medication_name,
            dosage_instructions=payload.dosage_instructions,
            frequency_per_day=payload.frequency_per_day,
            duration_days=payload.duration_days,
            clinical_indication=payload.clinical_indication,
        )
        return asdict(med)

    @app.post("/v1/care/patients/{patient_id}/medications/{medication_id}/adherence")
    async def report_medication_adherence(
        patient_id: str,
        medication_id: str,
        payload: RecordAdherencePayload,
        actor: AuthenticatedActor = Depends(patient_or_clinician_actor),
    ) -> dict[str, Any]:
        try:
            return clinical_service.report_medication_adherence(
                actor=actor,
                medication_id=medication_id,
                status=payload.status,
                notes=payload.notes,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/v1/care/patients/{patient_id}/tasks")
    async def list_patient_tasks(
        patient_id: str,
        actor: AuthenticatedActor = Depends(patient_or_clinician_actor),
    ) -> list[dict[str, Any]]:
        tasks = clinical_service.list_patient_tasks(patient_id=patient_id)
        return [asdict(t) for t in tasks]

    @app.post("/v1/care/patients/{patient_id}/tasks/{task_id}/resolve")
    async def resolve_care_task(
        patient_id: str,
        task_id: str,
        payload: ResolveCareTaskPayload,
        actor: AuthenticatedActor = Depends(patient_or_clinician_actor),
    ) -> dict[str, Any]:
        try:
            task = clinical_service.resolve_care_task(
                actor=actor,
                task_id=task_id,
                self_reported=payload.self_reported,
                notes=payload.notes,
            )
            return asdict(task)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/v1/care/patients/{patient_id}/records")
    async def list_patient_records(
        patient_id: str,
        actor: AuthenticatedActor = Depends(patient_or_clinician_actor),
    ) -> list[dict[str, Any]]:
        return clinical_service.list_patient_records(actor=actor, patient_id=patient_id)

    @app.post("/v1/care/patients/{patient_id}/observations")
    async def add_patient_observation(
        patient_id: str,
        payload: RecordObservationPayload,
        actor: AuthenticatedActor = Depends(patient_or_clinician_actor),
    ) -> dict[str, Any]:
        obs = clinical_service.add_patient_observation(
            actor=actor,
            patient_id=patient_id,
            kind=payload.kind,
            name=payload.name,
            value=payload.value,
            unit=payload.unit,
            notes=payload.notes,
            source=payload.source,
        )
        return asdict(obs)

    # =========================================================================
    # §5 & LWC-SCR-102, LWC-INT-001: Health Intelligence Companion Chat
    # =========================================================================
    @app.post("/v1/companion/chat")
    async def companion_chat(
        payload: CompanionChatPayload,
        actor: AuthenticatedActor = Depends(any_authenticated_actor),
    ) -> dict[str, Any]:
        return clinical_service.evaluate_companion_message(
            actor=actor,
            patient_id=payload.patient_id,
            message=payload.message,
            jurisdiction=payload.jurisdiction,
        )

    # =========================================================================
    # §7 & LWC-SCR-303: Network Facilities & Readiness
    # =========================================================================
    @app.get("/v1/network/facilities")
    async def list_network_facilities(
        jurisdiction: str = "NG",
        service: str | None = None,
        actor: AuthenticatedActor = Depends(any_authenticated_actor),
    ) -> list[dict[str, Any]]:
        facs = clinical_service.list_facilities(jurisdiction=jurisdiction, service=service)
        return [asdict(f) for f in facs]

    @app.post("/v1/network/facilities")
    async def register_network_facility(
        payload: FacilityRegistrationPayload,
        actor: AuthenticatedActor = Depends(command_actor),
    ) -> dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        expires_iso = (
            datetime.now(timezone.utc) + timedelta(minutes=payload.validity_minutes)
        ).isoformat()
        fac = FacilityRecord(
            facility_id=payload.facility_id,
            facility_name=payload.facility_name,
            facility_code=payload.facility_code,
            address=payload.address,
            jurisdiction=payload.jurisdiction,
            geocoordinates=payload.geocoordinates,
            services=payload.services,
            hours=payload.hours,
            contact_phone=payload.contact_phone,
            is_verified=payload.is_verified,
            readiness_state=payload.readiness_state,
            readiness_updated_at_iso=now_iso,
            readiness_expires_at_iso=expires_iso,
        )
        registered = clinical_service.register_facility(fac)
        return asdict(registered)

    @app.post("/v1/network/facilities/{facility_id}/readiness")
    async def update_facility_readiness(
        facility_id: str,
        payload: FacilityReadinessPayload,
        actor: AuthenticatedActor = Depends(command_actor),
    ) -> dict[str, Any]:
        try:
            fac = clinical_service.update_facility_readiness(
                facility_id=facility_id,
                state=payload.readiness_state,
                validity_minutes=payload.validity_minutes,
            )
            return asdict(fac)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    # =========================================================================
    # §7 & LWC-SCR-302: Care Coordination Board & Referrals
    # =========================================================================
    @app.get("/v1/coordination/board")
    async def list_coordination_board(
        actor: AuthenticatedActor = Depends(coordination_actor),
    ) -> list[dict[str, Any]]:
        tasks = clinical_service.list_coordination_board()
        return [asdict(t) for t in tasks]

    @app.post("/v1/coordination/board/{task_id}/claim")
    async def claim_coordination_task(
        task_id: str,
        actor: AuthenticatedActor = Depends(coordination_actor),
    ) -> dict[str, Any]:
        try:
            task = clinical_service.claim_coordination_task(actor=actor, task_id=task_id)
            return asdict(task)
        except CaseClaimConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/v1/coordination/board/{task_id}/resolve")
    async def resolve_coordination_task(
        task_id: str,
        payload: ResolveCoordinationTaskPayload,
        actor: AuthenticatedActor = Depends(coordination_actor),
    ) -> dict[str, Any]:
        try:
            task = clinical_service.resolve_coordination_task(
                actor=actor,
                task_id=task_id,
                disposition=payload.disposition,
            )
            return asdict(task)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/v1/referrals")
    async def list_referrals(
        actor: AuthenticatedActor = Depends(coordination_actor),
    ) -> list[dict[str, Any]]:
        return [asdict(r) for r in clinical_service._referrals.values()]

    @app.post("/v1/referrals/{referral_id}/accept")
    async def accept_referral(
        referral_id: str,
        payload: AcceptReferralPayload,
        actor: AuthenticatedActor = Depends(coordination_actor),
    ) -> dict[str, Any]:
        try:
            ref = clinical_service.accept_referral(
                referral_id=referral_id,
                receiving_facility_code=payload.receiving_facility_code,
            )
            return asdict(ref)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/v1/referrals/{referral_id}/decline")
    async def decline_referral(
        referral_id: str,
        payload: DeclineReferralPayload,
        actor: AuthenticatedActor = Depends(coordination_actor),
    ) -> dict[str, Any]:
        try:
            ref = clinical_service.decline_referral(
                referral_id=referral_id,
                decline_reason=payload.decline_reason,
            )
            return asdict(ref)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    # =========================================================================
    # §7, §10 & LWC-SCR-305: Finance Operations & Maker/Checker Reconciliation
    # =========================================================================
    @app.get("/v1/finance/exceptions")
    async def list_finance_exceptions(
        status: str | None = None,
        agreement_id: str | None = None,
        actor: AuthenticatedActor = Depends(finance_actor),
    ) -> list[dict[str, Any]]:
        return ledger.list_finance_exceptions(status=status, agreement_id=agreement_id)

    @app.post("/v1/finance/exceptions")
    async def create_finance_exception(
        payload: CreateFinanceExceptionPayload,
        actor: AuthenticatedActor = Depends(finance_actor),
    ) -> dict[str, Any]:
        return ledger.record_finance_exception(
            agreement_id=payload.agreement_id,
            encounter_id=payload.encounter_id,
            exception_type=payload.exception_type,
            amount_minor=payload.amount_minor,
            currency=payload.currency,
            reason=payload.reason,
            maker_id=actor.actor_id,
        )

    @app.post("/v1/finance/exceptions/{exception_id}/action")
    async def action_finance_exception(
        exception_id: str,
        payload: ActionFinanceExceptionPayload,
        actor: AuthenticatedActor = Depends(finance_actor),
    ) -> dict[str, Any]:
        try:
            return ledger.action_finance_exception(
                exception_id=exception_id,
                checker_id=actor.actor_id,
                action=payload.action,
                notes=payload.notes,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/v1/finance/reconciliation")
    async def get_finance_reconciliation(
        actor: AuthenticatedActor = Depends(finance_actor),
    ) -> dict[str, Any]:
        return ledger.compute_reconciliation_summary()

    # =========================================================================
    # §7 & LWC-SCR-301, LWC-MET-001 - 016: Directorate Metrics & Actions
    # =========================================================================
    @app.get("/v1/directorate/metrics")
    async def get_directorate_metrics(
        actor: AuthenticatedActor = Depends(command_actor),
    ) -> dict[str, Any]:
        return clinical_service.get_directorate_metrics()

    @app.get("/v1/directorate/actions")
    async def list_directorate_actions(
        actor: AuthenticatedActor = Depends(command_actor),
    ) -> list[dict[str, Any]]:
        actions = clinical_service.list_directorate_actions()
        return [asdict(a) for a in actions]

    @app.post("/v1/directorate/actions")
    async def create_directorate_action(
        payload: CreateDirectorateActionPayload,
        actor: AuthenticatedActor = Depends(command_actor),
    ) -> dict[str, Any]:
        action = clinical_service.create_directorate_action(
            metric_id=payload.metric_id,
            title=payload.title,
            description=payload.description,
            owner_team=payload.owner_team,
            assigned_to=payload.assigned_to,
            due_date_iso=payload.due_date_iso,
        )
        return asdict(action)

    @app.patch("/v1/directorate/actions/{action_id}")
    async def update_directorate_action(
        action_id: str,
        payload: UpdateDirectorateActionPayload,
        actor: AuthenticatedActor = Depends(command_actor),
    ) -> dict[str, Any]:
        try:
            action = clinical_service.update_directorate_action(
                action_id=action_id,
                status=payload.status,
                evidence_notes=payload.evidence_notes,
            )
            return asdict(action)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app


def _seed_non_production_fixtures(
    cfg: Settings,
    auth_manager: IdentityAndSessionManager,
    clinical_service: ClinicalOperationsService,
    ledger: FinancialLedgerEngine,
    now: datetime,
) -> None:
    """Synthetic roster clinician and sponsor pool. Never runs when environment is production."""
    default_clinician = AuthenticatedActor(
        actor_id="dr-adebayo-okonkwo",
        full_name="Dr. Adebayo Okonkwo (synthetic)",
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

    sample_subj = PatientSubjectRecord(
        patient_id="patient-001",
        account_id="patient-001",
        full_name="Sister Grace Adeleke (Demo Subject)",
        date_of_birth_iso="1988-06-15T00:00:00Z",
        gender="FEMALE",
        relationship_to_account="SELF",
        jurisdiction="NG",
    )
    clinical_service._subjects[sample_subj.patient_id] = sample_subj

    sample_ep = CareEpisodeRecord(
        episode_id="EP-NG-88412",
        patient_id="patient-001",
        acting_proxy_grant_id=None,
        care_service="GP_REMOTE",
        jurisdiction="NG",
        consent_grant_id="consent-sample-01",
        state="BOOKED",
        chief_complaint_summary="Intermittent fever and mild headache for 2 days. No breathing difficulty.",
        created_at_iso=now.isoformat(),
        intakes=[
            {
                "intake_id": "intake-ng-01",
                "revision": 1,
                "submitted_at_iso": now.isoformat(),
                "raw_statement": "Intermittent fever and mild headache for 2 days. No breathing difficulty.",
                "structured_answers": {
                    "symptom_category": "FEVER_OR_MALARIA_LIKE",
                    "duration_days": 2,
                    "patient_age_years": 34,
                    "has_chest_pain": False,
                    "has_breathing_difficulty": False,
                    "has_uncontrolled_bleeding": False,
                },
                "fired_rule_ids": ["RT-STANDARD-GP-02"],
                "outcome_type": "CLINICIAN_REVIEW",
            }
        ],
    )
    clinical_service._episodes[sample_ep.episode_id] = sample_ep

    sample_enc = EncounterRecord(
        encounter_id="ENC-NG-88412",
        episode_id=sample_ep.episode_id,
        patient_id=sample_ep.patient_id,
        appointment_id="APPT-NG-88412",
        state="OPEN",
        modality="VIDEO",
        funding_route="SPONSOR_DEFINED_SERVICES",
        entitlement_reservation_id="RES-SAMPLE-01",
        primary_clinician_id=None,
        version=1,
    )
    clinical_service._encounters[sample_enc.encounter_id] = sample_enc
