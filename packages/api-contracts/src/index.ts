/**
 * @loveworld-care/api-contracts
 * Versioned /v1 REST API request/response DTOs and typed client for all 4 PWAs
 * (§14.1–14.5, covering DoctorNow, Health Navigator, SponsorCare, Care Command,
 * CareContinuity, ClinicConnect, SpecialistBridge, and Health Intelligence handoff).
 */

import type {
  AppointmentState,
  CareContinuityPlan,
  CareEpisodeState,
  CareRelationship,
  CareTask,
  ClinicalObservation,
  ConsultationModality,
  CoordinationTask,
  CurrencyCode,
  DirectorateAction,
  DirectorateMetric,
  EncounterState,
  EntitlementState,
  FinanceException,
  FundingRouteType,
  MedicationInstruction,
  NetworkFacility,
  PatientSubject,
  PaymentGatewayProvider,
  ProtocolBundleState,
  ProtocolOutcomeType,
  ReconciliationSummary,
  ReferralState,
} from "@loveworld-care/domain-types";

export type {
  AppointmentState,
  CareContinuityPlan,
  CareEpisodeState,
  CareRelationship,
  CareTask,
  ClinicalObservation,
  ConsultationModality,
  CoordinationTask,
  CurrencyCode,
  DirectorateAction,
  DirectorateMetric,
  EncounterState,
  EntitlementState,
  FinanceException,
  FundingRouteType,
  MedicationInstruction,
  NetworkFacility,
  PatientSubject,
  PaymentGatewayProvider,
  ProtocolBundleState,
  ProtocolOutcomeType,
  ReconciliationSummary,
  ReferralState,
};

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
  readonly eligible_population_count?: number;
  readonly beneficiaries_served_count?: number;
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
// Longitudinal Care, Coordination, Facilities, Companion & Governance DTOs
// =============================================================================

export interface CreateSubjectRequest {
  readonly full_name: string;
  readonly dob_iso: string;
  readonly gender?: string;
  readonly relationship?: string;
  readonly jurisdiction?: string;
}

export interface CreateCareRelationshipRequest {
  readonly patient_id: string;
  readonly relationship_type?: string;
  readonly allowed_scopes?: readonly string[];
}

export interface CreateCarePlanRequest {
  readonly episode_id: string;
  readonly encounter_id: string;
  readonly programme_name: string;
  readonly monitoring_instructions: string;
  readonly due_at_iso: string;
  readonly goals?: readonly string[];
  readonly actions?: readonly string[];
}

export interface PrescribeMedicationRequest {
  readonly encounter_id: string;
  readonly medication_name: string;
  readonly dosage_instructions: string;
  readonly frequency_per_day?: number;
  readonly duration_days?: number;
  readonly clinical_indication?: string;
}

export interface RecordAdherenceRequest {
  readonly status: "TAKEN" | "SKIPPED" | "ISSUE";
  readonly notes?: string | null;
}

export interface CreateCareTaskRequest {
  readonly episode_id?: string | null;
  readonly encounter_id?: string | null;
  readonly assigned_to?: "PATIENT" | "CLINICIAN" | "COORDINATOR";
  readonly task_type?:
    | "MEDICATION_REMINDER"
    | "CHECK_IN"
    | "RESULT_REVIEW"
    | "FOLLOW_UP"
    | "REFERRAL_FOLLOW_UP"
    | "CLINICAL_REVIEW";
  readonly title: string;
  readonly description?: string;
  readonly due_at_iso: string;
}

export interface ResolveCareTaskRequest {
  readonly self_reported?: boolean;
  readonly notes?: string | null;
}

export interface RecordObservationRequest {
  readonly kind: "SYMPTOM" | "VITAL" | "LAB_RESULT" | "DOCUMENT";
  readonly name: string;
  readonly value: string;
  readonly unit?: string | null;
  readonly notes?: string | null;
  readonly source?: "PATIENT_REPORTED" | "CLINICIAN_ENTERED" | "LAB_UPLOAD";
}

export interface CompanionChatRequest {
  readonly patient_id?: string | null;
  readonly message: string;
  readonly jurisdiction?: string;
}

export interface CompanionChatResponse {
  readonly intent: string;
  readonly emergency: boolean;
  readonly reply: string;
  readonly emergency_contacts?: readonly {
    readonly region: string;
    readonly label: string;
    readonly phone: string;
  }[];
  readonly suggested_actions?: readonly string[];
  readonly provenance: {
    readonly source: string;
    readonly protocol_id: string;
    readonly timestamp: string;
    readonly disclaimer: string;
  };
}

export interface PatientDashboardResponse {
  readonly patient_id: string;
  readonly subject: {
    readonly patient_id: string;
    readonly full_name: string;
    readonly relationship: string;
    readonly jurisdiction: string;
  };
  readonly active_episodes: readonly {
    readonly episode_id: string;
    readonly state: string;
    readonly care_service: string;
    readonly chief_complaint?: string;
    readonly assigned_clinician_id?: string | null;
    readonly active_protocol_outcome?: string | null;
    readonly created_at: string;
  }[];
  readonly active_appointments: readonly {
    readonly encounter_id: string;
    readonly episode_id: string;
    readonly modality: string;
    readonly state: string;
    readonly clinician_name: string;
    readonly specialty: string;
    readonly starts_at: string | null;
  }[];
  readonly due_tasks: readonly {
    readonly task_id: string;
    readonly task_type: string;
    readonly title: string;
    readonly description: string;
    readonly due_at: string;
    readonly status: string;
    readonly self_reported: boolean;
  }[];
  readonly active_medications: readonly {
    readonly medication_id: string;
    readonly medication_name: string;
    readonly dosage_instructions: string;
    readonly frequency_per_day: number;
    readonly duration_days: number;
    readonly clinical_indication: string;
    readonly status: string;
    readonly prescribed_at: string;
    readonly adherence_count: number;
  }[];
  readonly active_care_plans: readonly {
    readonly plan_id: string;
    readonly programme_name: string;
    readonly monitoring_instructions: string;
    readonly due_at: string;
    readonly status: string;
    readonly goals: readonly string[];
    readonly actions: readonly string[];
  }[];
  readonly recent_observations: readonly {
    readonly observation_id: string;
    readonly kind: string;
    readonly name: string;
    readonly value: string;
    readonly unit?: string | null;
    readonly observed_at: string;
    readonly source: string;
    readonly verification_status: string;
  }[];
  readonly next_action: {
    readonly type: string;
    readonly label: string;
    readonly details: string;
    readonly link: string;
  } | null;
  readonly last_sync_time: string;
}

export interface ResolveCoordinationTaskRequest {
  readonly disposition: string;
}

export interface AcceptReferralRequest {
  readonly receiving_facility_code: string;
}

export interface DeclineReferralRequest {
  readonly decline_reason: string;
}

export interface FacilityRegistrationRequest {
  readonly facility_id: string;
  readonly facility_name: string;
  readonly facility_code: string;
  readonly address: string;
  readonly jurisdiction?: string;
  readonly geocoordinates?: { readonly lat: number; readonly lng: number };
  readonly services?: readonly string[];
  readonly hours?: string;
  readonly contact_phone?: string;
  readonly is_verified?: boolean;
  readonly readiness_state?: "CONFIRMED_AVAILABLE" | "STALE" | "UNAVAILABLE";
  readonly validity_minutes?: number;
}

export interface FacilityReadinessRequest {
  readonly readiness_state: "CONFIRMED_AVAILABLE" | "STALE" | "UNAVAILABLE";
  readonly validity_minutes?: number;
}

export interface CreateFinanceExceptionRequest {
  readonly agreement_id?: string | null;
  readonly encounter_id?: string | null;
  readonly exception_type: string;
  readonly amount_minor: number;
  readonly currency?: string;
  readonly reason: string;
}

export interface ActionFinanceExceptionRequest {
  readonly action: "APPROVE" | "REJECT" | "REMEDIATE";
  readonly notes: string;
}

export interface CreateDirectorateActionRequest {
  readonly metric_id: string;
  readonly title: string;
  readonly description: string;
  readonly owner_team: string;
  readonly assigned_to: string;
  readonly due_date_iso: string;
}

export interface UpdateDirectorateActionRequest {
  readonly status: "OPEN" | "IN_PROGRESS" | "RESOLVED";
  readonly evidence_notes?: string;
}

export interface DirectorateMetricsResponse {
  readonly reporting_period: string;
  readonly refresh_time_iso: string;
  readonly metrics: readonly DirectorateMetric[];
  readonly action_items_count: number;
  readonly free_text_phi_included: false;
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

  // Identity & Subjects
  listSubjects() {
    return this.request<readonly PatientSubject[]>("GET", "/v1/identity/subjects");
  }

  createSubject(payload: CreateSubjectRequest) {
    return this.request<PatientSubject>("POST", "/v1/identity/subjects", payload);
  }

  createCareRelationship(payload: CreateCareRelationshipRequest) {
    return this.request<CareRelationship>("POST", "/v1/identity/relationships", payload);
  }

  revokeCareRelationship(relationshipId: string) {
    return this.request<{ revoked: boolean; relationship_id: string }>(
      "POST",
      `/v1/identity/relationships/${encodeURIComponent(relationshipId)}/revoke`
    );
  }

  // Patient Longitudinal Care
  getPatientDashboard(patientId: string) {
    return this.request<PatientDashboardResponse>(
      "GET",
      `/v1/care/patients/${encodeURIComponent(patientId)}/dashboard`
    );
  }

  listCarePlans(patientId: string) {
    return this.request<readonly CareContinuityPlan[]>(
      "GET",
      `/v1/care/patients/${encodeURIComponent(patientId)}/care-plans`
    );
  }

  createCarePlan(patientId: string, payload: CreateCarePlanRequest) {
    return this.request<CareContinuityPlan>(
      "POST",
      `/v1/care/patients/${encodeURIComponent(patientId)}/care-plans`,
      payload
    );
  }

  listMedications(patientId: string) {
    return this.request<readonly MedicationInstruction[]>(
      "GET",
      `/v1/care/patients/${encodeURIComponent(patientId)}/medications`
    );
  }

  prescribeMedication(patientId: string, payload: PrescribeMedicationRequest) {
    return this.request<MedicationInstruction>(
      "POST",
      `/v1/care/patients/${encodeURIComponent(patientId)}/medications`,
      payload
    );
  }

  reportMedicationAdherence(
    patientId: string,
    medicationId: string,
    payload: RecordAdherenceRequest
  ) {
    return this.request<Record<string, unknown>>(
      "POST",
      `/v1/care/patients/${encodeURIComponent(patientId)}/medications/${encodeURIComponent(
        medicationId
      )}/adherence`,
      payload
    );
  }

  listTasks(patientId: string) {
    return this.request<readonly CareTask[]>(
      "GET",
      `/v1/care/patients/${encodeURIComponent(patientId)}/tasks`
    );
  }

  resolveTask(patientId: string, taskId: string, payload: ResolveCareTaskRequest) {
    return this.request<CareTask>(
      "POST",
      `/v1/care/patients/${encodeURIComponent(patientId)}/tasks/${encodeURIComponent(
        taskId
      )}/resolve`,
      payload
    );
  }

  listRecords(patientId: string) {
    return this.request<readonly Record<string, unknown>[]>(
      "GET",
      `/v1/care/patients/${encodeURIComponent(patientId)}/records`
    );
  }

  addObservation(patientId: string, payload: RecordObservationRequest) {
    return this.request<ClinicalObservation>(
      "POST",
      `/v1/care/patients/${encodeURIComponent(patientId)}/observations`,
      payload
    );
  }

  // Health Intelligence Companion
  companionChat(payload: CompanionChatRequest) {
    return this.request<CompanionChatResponse>("POST", "/v1/companion/chat", payload);
  }

  // Network Facilities & Readiness
  listFacilities(jurisdiction = "NG", service?: string) {
    const s = service ? `&service=${encodeURIComponent(service)}` : "";
    return this.request<readonly NetworkFacility[]>(
      "GET",
      `/v1/network/facilities?jurisdiction=${encodeURIComponent(jurisdiction)}${s}`
    );
  }

  registerFacility(payload: FacilityRegistrationRequest) {
    return this.request<NetworkFacility>("POST", "/v1/network/facilities", payload);
  }

  updateFacilityReadiness(facilityId: string, payload: FacilityReadinessRequest) {
    return this.request<NetworkFacility>(
      "POST",
      `/v1/network/facilities/${encodeURIComponent(facilityId)}/readiness`,
      payload
    );
  }

  // Coordination Board & Referrals
  listCoordinationBoard() {
    return this.request<readonly CoordinationTask[]>("GET", "/v1/coordination/board");
  }

  claimCoordinationTask(taskId: string) {
    return this.request<CoordinationTask>(
      "POST",
      `/v1/coordination/board/${encodeURIComponent(taskId)}/claim`
    );
  }

  resolveCoordinationTask(taskId: string, payload: ResolveCoordinationTaskRequest) {
    return this.request<CoordinationTask>(
      "POST",
      `/v1/coordination/board/${encodeURIComponent(taskId)}/resolve`,
      payload
    );
  }

  listReferrals() {
    return this.request<readonly Record<string, unknown>[]>("GET", "/v1/referrals");
  }

  acceptReferral(referralId: string, payload: AcceptReferralRequest) {
    return this.request<Record<string, unknown>>(
      "POST",
      `/v1/referrals/${encodeURIComponent(referralId)}/accept`,
      payload
    );
  }

  declineReferral(referralId: string, payload: DeclineReferralRequest) {
    return this.request<Record<string, unknown>>(
      "POST",
      `/v1/referrals/${encodeURIComponent(referralId)}/decline`,
      payload
    );
  }

  // Finance Operations
  listFinanceExceptions(status?: string, agreementId?: string) {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (agreementId) params.set("agreement_id", agreementId);
    const q = params.toString() ? `?${params.toString()}` : "";
    return this.request<readonly FinanceException[]>("GET", `/v1/finance/exceptions${q}`);
  }

  createFinanceException(payload: CreateFinanceExceptionRequest) {
    return this.request<FinanceException>("POST", "/v1/finance/exceptions", payload);
  }

  actionFinanceException(exceptionId: string, payload: ActionFinanceExceptionRequest) {
    return this.request<FinanceException>(
      "POST",
      `/v1/finance/exceptions/${encodeURIComponent(exceptionId)}/action`,
      payload
    );
  }

  getFinanceReconciliation() {
    return this.request<ReconciliationSummary>("GET", "/v1/finance/reconciliation");
  }

  // Directorate Governance & Metrics
  getDirectorateMetrics() {
    return this.request<DirectorateMetricsResponse>("GET", "/v1/directorate/metrics");
  }

  listDirectorateActions() {
    return this.request<readonly DirectorateAction[]>("GET", "/v1/directorate/actions");
  }

  createDirectorateAction(payload: CreateDirectorateActionRequest) {
    return this.request<DirectorateAction>("POST", "/v1/directorate/actions", payload);
  }

  updateDirectorateAction(actionId: string, payload: UpdateDirectorateActionRequest) {
    return this.request<DirectorateAction>(
      "PATCH",
      `/v1/directorate/actions/${encodeURIComponent(actionId)}`,
      payload
    );
  }
}
