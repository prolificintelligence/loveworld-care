/**
 * @loveworld-care/api-contracts
 * Versioned /v1 REST API request/response DTOs and typed client for all 4 PWAs
 * (§14.1–14.5, covering DoctorNow, Health Navigator, SponsorCare, Care Command,
 * CareContinuity, ClinicConnect, SpecialistBridge, and Health Intelligence handoff).
 */

import type {
  AppointmentState,
  CareEpisodeState,
  ConsultationModality,
  CurrencyCode,
  EncounterState,
  EntitlementState,
  FundingRouteType,
  PaymentGatewayProvider,
  ProtocolBundleState,
  ProtocolOutcomeType,
  ReferralState,
} from "@loveworld-care/domain-types";

export interface ApiErrorEnvelope {
  readonly error_code: string;
  readonly message: string;
  readonly request_id: string;
  readonly details?: Record<string, unknown>;
}

// =============================================================================
// 1. Care Episodes, Intake & Health Navigator Protocol Evaluation (§6, §7, §14.2)
// =============================================================================

export interface CreateCareEpisodeRequest {
  readonly patient_id: string;
  readonly acting_proxy_grant_id?: string;
  readonly jurisdiction: string;
  readonly care_service:
    | "GP_REMOTE"
    | "SPECIALIST_BRIDGE"
    | "CLINIC_CONNECT_ESCALATION"
    | "CARE_CONTINUITY_FOLLOWUP";
  readonly consent_grant_id: string;
  readonly request_source: "PATIENT_PWA" | "CLINIC_CONNECT_PWA" | "CARE_COORDINATOR";
  readonly chief_complaint_summary: string;
}

export interface CareEpisodeResponse {
  readonly episode_id: string;
  readonly patient_id: string;
  readonly state: CareEpisodeState;
  readonly care_service: string;
  readonly jurisdiction: string;
  readonly chief_complaint_summary?: string;
  readonly assigned_clinician_id: string | null;
  readonly active_protocol_outcome: ProtocolOutcomeType | null;
  readonly created_at: string;
  readonly request_id: string;
  /** §14.2: Never contains autonomous clinical advice. */
  readonly clinical_advice: null;
}

export interface SubmitIntakeAnswersRequest {
  readonly structured_answers: Record<string, string | number | boolean | string[]>;
  readonly raw_patient_statement: string;
  readonly language_code: string;
  readonly request_ai_draft_extraction: boolean;
}

export interface IntakeEvaluationResponse {
  readonly intake_id: string;
  readonly protocol_run_id: string;
  readonly protocol_bundle_id: string;
  readonly protocol_version: string;
  readonly protocol_document_hash: string;
  readonly input_revision: number;
  readonly outcome_type: ProtocolOutcomeType;
  readonly hard_stop_triggered: boolean;
  readonly fired_rule_ids: readonly string[];
  readonly unresolved_fields: readonly string[];
  readonly approved_content_id: string;
  readonly safety_net_guidance_text: string;
  readonly emergency_contacts: readonly {
    readonly region: string;
    readonly label: string;
    readonly phone: string;
  }[];
  readonly ai_draft_summary_for_clinician?: {
    readonly watermark: "UNSIGNED / FOR CLINICIAN REVIEW ONLY";
    readonly model_id: string;
    readonly extracted_fields: Record<string, unknown>;
    readonly draft_narrative: string;
    readonly model_made_decision: false;
  } | null;
  readonly clinician_acknowledged: boolean;
  readonly model_made_decision: false;
}

// =============================================================================
// 2. Provider Roster, Availability & Atomic Appointment Booking (§6.3, §8.1, §10)
// =============================================================================

export interface StaffedSlotDTO {
  readonly slot_id: string;
  readonly clinician_id: string;
  readonly clinician_display_name: string;
  readonly specialty: string;
  readonly mdcn_verified: boolean;
  readonly jurisdiction: string;
  readonly starts_at: string;
  readonly ends_at: string;
  readonly supported_modalities: readonly ConsultationModality[];
  readonly fee_minor: number;
  readonly currency: CurrencyCode;
}

export interface CreateAppointmentBookingRequest {
  readonly episode_id: string;
  readonly slot_id: string;
  readonly modality: ConsultationModality;
  readonly funding_route: FundingRouteType;
  readonly payment_provider?: PaymentGatewayProvider;
  readonly sponsor_agreement_id?: string;
  readonly institution_agreement_id?: string;
}

export interface AppointmentBookingResponse {
  readonly appointment_id: string;
  readonly episode_id: string;
  readonly slot_id: string;
  readonly state: AppointmentState;
  readonly modality: ConsultationModality;
  readonly funding_route: FundingRouteType;
  readonly entitlement_reservation_id: string | null;
  readonly payment_checkout_url: string | null;
  readonly payment_reference: string | null;
  readonly fee_minor: number;
  readonly currency: CurrencyCode;
}

// =============================================================================
// 3. Clinician Atomic Claim, RTC Session, Signing & Addenda (§6.4, §8.2, §13.4)
// =============================================================================

export interface EncounterSummaryDTO {
  readonly encounter_id: string;
  readonly episode_id: string;
  readonly patient_id: string;
  readonly state: EncounterState;
  readonly modality: ConsultationModality;
  readonly funding_route: FundingRouteType;
  readonly primary_clinician_id: string | null;
  readonly version: number;
  readonly claimed_at: string | null;
  readonly signed_at: string | null;
  readonly signed_document_hash: string | null;
  readonly chief_complaint: string | null;
  readonly addenda_count: number;
}

export interface EncounterDetailDTO {
  readonly encounter_id: string;
  readonly episode_id: string;
  readonly patient_id: string;
  readonly state: EncounterState;
  readonly modality: ConsultationModality;
  readonly funding_route: FundingRouteType;
  readonly primary_clinician_id: string | null;
  readonly version: number;
  readonly claimed_at: string | null;
  readonly signed_at: string | null;
  readonly signed_document_hash: string | null;
  readonly signed_clinical_note: Record<string, unknown> | null;
  readonly chief_complaint: string | null;
  readonly intakes: readonly Record<string, unknown>[];
  readonly addenda: readonly {
    readonly addendum_id: string;
    readonly amendment_reason: string;
    readonly addendum_text: string;
    readonly document_sha256: string;
    readonly signed_at_iso: string;
  }[];
}

export interface ClaimEncounterResponse {
  readonly encounter_id: string;
  readonly episode_id: string;
  readonly state: EncounterState;
  readonly primary_clinician_id: string;
  readonly version: number;
  readonly claimed_at: string;
  readonly rtc_room_token: string | null;
  readonly rtc_server_url: string | null;
}

export interface SignEncounterRequest {
  readonly expected_version: number;
  readonly remote_suitability_accepted: boolean;
  readonly remote_decline_reason?: string;
  readonly modality_used: ConsultationModality;
  readonly modality_limitations_noted: string;
  readonly history_and_findings: string;
  readonly clinical_assessment: string;
  readonly management_plan: string;
  readonly safety_net_instructions: string;
  readonly mfa_step_up_code: string;
  readonly prescriptions?: readonly {
    readonly medication_name: string;
    readonly dosage_instructions: string;
    readonly duration_days: number;
    readonly clinical_indication: string;
  }[];
  readonly referral?: {
    readonly receiving_facility_code: string;
    readonly receiving_facility_name: string;
    readonly specialty_code: string;
    readonly priority: "routine" | "urgent" | "asap" | "stat";
    readonly clinical_reason: string;
    readonly investigations_attached: readonly string[];
  };
  readonly follow_up_plan?: {
    readonly care_continuity_programme: string;
    readonly due_in_days: number;
    readonly monitoring_instructions: string;
  };
}

export interface SignedEncounterResponse {
  readonly encounter_id: string;
  readonly state: "SIGNED";
  readonly version: number;
  readonly signed_at: string;
  readonly signed_document_hash: string;
  readonly signature_ed25519_base64: string;
  readonly settlement_triggered: boolean;
  readonly referral_id: string | null;
  readonly follow_up_task_id: string | null;
  readonly fhir_bundle_id: string;
}

export interface CreateClinicalAddendumRequest {
  readonly original_signed_document_hash: string;
  readonly amendment_reason: string;
  readonly addendum_text: string;
  readonly mfa_step_up_code: string;
}

// =============================================================================
// 4. SponsorCare, Multi-Currency Double-Entry Ledger & Unit Economics (§10, §17)
// =============================================================================

export interface SponsorPoolSummaryDTO {
  readonly agreement_id: string;
  readonly sponsor_name: string;
  readonly funding_type: FundingRouteType;
  readonly currency: CurrencyCode;
  readonly committed_unfunded_minor: number;
  readonly funded_cash_received_minor: number;
  readonly active_reserved_minor: number;
  readonly redeemed_settled_minor: number;
  readonly available_to_reserve_minor: number;
  readonly eligible_beneficiary_count: number;
  readonly completed_encounters_count: number;
  readonly k_anonymity_suppressed: boolean;
}

export interface MakerCheckerActionRequest {
  readonly exception_id: string;
  readonly action: "APPROVE_RELEASE" | "APPROVE_REFUND" | "APPROVE_PAYOUT" | "REJECT";
  readonly checker_notes: string;
  readonly mfa_code: string;
}

// =============================================================================
// 5. Cross-Product Health Intelligence Consent-Gated Handoff (§12.4 & AT-15)
// =============================================================================

export interface HealthIntelligenceHandoffRequest {
  readonly patient_id: string;
  readonly source_scan_id: string;
  readonly product_name: string;
  readonly extracted_ingredients: readonly string[];
  readonly patient_question: string;
  readonly explicit_user_consent_confirmed: boolean;
  readonly consent_timestamp_iso: string;
}

export interface EmergencyGuidanceResponse {
  readonly jurisdiction: string;
  readonly requires_payment: boolean;
  readonly requires_ai_inference: boolean;
  readonly ambulance_dispatch_claimed: boolean;
  readonly emergency_notice: string;
  readonly emergency_contacts: readonly {
    readonly region: string;
    readonly label: string;
    readonly phone: string;
  }[];
}

export interface AuthMeResponse {
  readonly sub: string;
  readonly audience: string;
  readonly roles: readonly string[];
  readonly mfa: boolean;
  readonly org?: string | null;
  readonly expires_at: string;
  readonly clinician_credential_active?: boolean | null;
}

export interface DevTokenRequest {
  readonly sub: string;
  readonly audience: "lwc:patient" | "lwc:clinician" | "lwc:command" | "lwc:sponsor";
  readonly roles: readonly string[];
  readonly mfa?: boolean;
  readonly org?: string;
  readonly ttl_minutes?: number;
}

export interface DevTokenResponse {
  readonly access_token: string;
  readonly token_type: string;
}

export interface ExecutiveMetricsResponse {
  readonly north_star_signed_encounters_count: number;
  readonly ai_kill_switch_enabled: boolean;
  readonly unit_economics_baseline_ngn_minor: {
    readonly settled_price_minor: number;
    readonly clinician_compensation_minor: number;
    readonly contribution_margin_minor: number;
    readonly contribution_margin_pct: number;
  };
  readonly base_scenario_break_even_encounters_per_month: number;
  readonly free_text_phi_included: false;
  readonly operational_overview?: {
    readonly staffed_roster_slots_count: number;
    readonly encounters_queued_or_active_count: number;
    readonly sponsor_active_pools_count: number;
    readonly sponsor_unredeemed_liability_minor: number;
    readonly clinician_pending_payables_minor: number;
  };
}

// =============================================================================
// Typed /v1 Client Wrapper
// =============================================================================

export class LoveWorldCareApiClient {
  constructor(
    private readonly baseUrl: string,
    private readonly getHeaders: () => Record<string, string> = () => ({})
  ) {}

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
    idempotencyKey?: string
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...this.getHeaders(),
    };
    if (idempotencyKey) {
      headers["Idempotency-Key"] = idempotencyKey;
    }

    const res = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      cache: "no-store",
    });

    if (!res.ok) {
      const errBody = (await res.json().catch(() => ({
        error_code: "HTTP_ERROR",
        message: res.statusText,
        request_id: "unknown",
      }))) as ApiErrorEnvelope;
      throw new Error(`[${errBody.error_code || res.status}] ${errBody.message || res.statusText}`);
    }

    return (await res.json()) as T;
  }

  getEmergencyGuidance(jurisdiction = "NG") {
    return this.request<EmergencyGuidanceResponse>(
      "GET",
      `/v1/emergency/guidance?jurisdiction=${encodeURIComponent(jurisdiction)}`
    );
  }

  getAuthMe() {
    return this.request<AuthMeResponse>("GET", "/v1/auth/me");
  }

  requestMagicLink(email: string, redirectUrl?: string) {
    return this.request<{
      status: string;
      email: string;
      expires_in_minutes: number;
      verification_token?: string;
    }>("POST", "/v1/auth/magic-link/request", { email, redirect_url: redirectUrl });
  }

  verifyMagicLink(token: string) {
    return this.request<{
      access_token: string;
      token_type: string;
      patient_id: string;
      email: string;
    }>("POST", "/v1/auth/magic-link/verify", { token });
  }

  mintDevToken(payload: DevTokenRequest) {
    return this.request<DevTokenResponse>("POST", "/v1/auth/dev-token", payload);
  }

  logout() {
    return this.request<void>("POST", "/v1/auth/logout");
  }

  createEpisode(payload: CreateCareEpisodeRequest, idempotencyKey?: string) {
    return this.request<CareEpisodeResponse>(
      "POST",
      "/v1/care/episodes",
      payload,
      idempotencyKey
    );
  }

  getCareEpisode(episodeId: string) {
    return this.request<CareEpisodeResponse>(
      "GET",
      `/v1/care/episodes/${encodeURIComponent(episodeId)}`
    );
  }

  submitIntake(
    episodeId: string,
    payload: SubmitIntakeAnswersRequest,
    idempotencyKey?: string
  ) {
    return this.request<IntakeEvaluationResponse>(
      "POST",
      `/v1/care/episodes/${encodeURIComponent(episodeId)}/intakes`,
      payload,
      idempotencyKey
    );
  }

  listStaffedSlots(jurisdiction = "NG", specialty = "GP") {
    return this.request<readonly StaffedSlotDTO[]>(
      "GET",
      `/v1/clinicians/slots?jurisdiction=${encodeURIComponent(
        jurisdiction
      )}&specialty=${encodeURIComponent(specialty)}`
    );
  }

  bookAppointment(payload: CreateAppointmentBookingRequest, idempotencyKey: string) {
    return this.request<AppointmentBookingResponse>(
      "POST",
      "/v1/appointments",
      payload,
      idempotencyKey
    );
  }

  listEncounters(state?: string) {
    const q = state ? `?state=${encodeURIComponent(state)}` : "";
    return this.request<readonly EncounterSummaryDTO[]>(
      "GET",
      `/v1/encounters${q}`
    );
  }

  getEncounter(encounterId: string) {
    return this.request<EncounterDetailDTO>(
      "GET",
      `/v1/encounters/${encodeURIComponent(encounterId)}`
    );
  }

  claimEncounter(encounterId: string, idempotencyKey?: string) {
    return this.request<ClaimEncounterResponse>(
      "POST",
      `/v1/encounters/${encodeURIComponent(encounterId)}/claim`,
      {},
      idempotencyKey
    );
  }

  signEncounter(
    encounterId: string,
    payload: SignEncounterRequest,
    idempotencyKey?: string
  ) {
    return this.request<SignedEncounterResponse>(
      "POST",
      `/v1/encounters/${encodeURIComponent(encounterId)}/sign`,
      payload,
      idempotencyKey
    );
  }

  createAddendum(
    encounterId: string,
    payload: CreateClinicalAddendumRequest,
    idempotencyKey?: string
  ) {
    return this.request<Record<string, unknown>>(
      "POST",
      `/v1/encounters/${encodeURIComponent(encounterId)}/addenda`,
      payload,
      idempotencyKey
    );
  }

  getSponsorPoolReport(agreementId: string) {
    return this.request<SponsorPoolSummaryDTO>(
      "GET",
      `/v1/sponsor/pools/${encodeURIComponent(agreementId)}/report`
    );
  }

  toggleAiKillSwitch(enabled: boolean, reason: string) {
    return this.request<{ ai_kill_switch_enabled: boolean; deterministic_care_pathway_operational: boolean }>(
      "POST",
      "/v1/governance/ai-kill-switch",
      { enabled, reason }
    );
  }

  getExecutiveMetrics() {
    return this.request<ExecutiveMetricsResponse>("GET", "/v1/executive/metrics");
  }

  transferIntelligenceHandoff(
    episodeId: string,
    payload: HealthIntelligenceHandoffRequest
  ) {
    return this.request<Record<string, unknown>>(
      "POST",
      `/v1/care/episodes/${encodeURIComponent(episodeId)}/intelligence-handoff`,
      payload
    );
  }
}
