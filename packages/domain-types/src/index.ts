/**
 * @loveworld-care/domain-types
 * Authoritative domain state machines, data classification tiers, currency minor-unit
 * primitives, and lifecycle transition invariants (§6.3, §7.2, §8.1, §10.3, §13.1, §17).
 */

export type ProductModuleId =
  | "DOCTOR_NOW"
  | "HEALTH_NAVIGATOR"
  | "SPONSOR_CARE"
  | "CARE_COMMAND"
  | "CARE_CONTINUITY"
  | "CLINIC_CONNECT"
  | "SPECIALIST_BRIDGE"
  | "HEALTH_INTELLIGENCE_HANDOFF";

export type DataClassificationTier =
  | "T0_PUBLIC"
  | "T1_ORGANISATION_ONLY"
  | "T2_PERSONAL"
  | "T3_SENSITIVE_CLINICAL"
  | "T4_RESTRICTED_CONTROLS";

export type CurrencyCode = "NGN" | "ESP" | "USD";

export type EconomicEntityBook =
  | "LOVEWORLD_CARE_OPERATOR"
  | "PROLIFIC_INTELLIGENCE";

export interface MoneyMinor {
  /** Integral minor units (e.g. kobo for NGN, minor units for ESP Espees, cents for USD). Never floating-point. */
  readonly amountMinor: number;
  readonly currency: CurrencyCode;
}

export function assertValidMoneyMinor(money: MoneyMinor): void {
  if (!Number.isSafeInteger(money.amountMinor)) {
    throw new Error(
      `Invalid non-integer money amount: ${money.amountMinor} for ${money.currency}`
    );
  }
}

export function addMoneyMinor(a: MoneyMinor, b: MoneyMinor): MoneyMinor {
  assertValidMoneyMinor(a);
  assertValidMoneyMinor(b);
  if (a.currency !== b.currency) {
    throw new Error(`Currency mismatch: cannot add ${a.currency} and ${b.currency}`);
  }
  return {
    amountMinor: a.amountMinor + b.amountMinor,
    currency: a.currency,
  };
}

export function subtractMoneyMinor(a: MoneyMinor, b: MoneyMinor): MoneyMinor {
  assertValidMoneyMinor(a);
  assertValidMoneyMinor(b);
  if (a.currency !== b.currency) {
    throw new Error(`Currency mismatch: cannot subtract ${b.currency} from ${a.currency}`);
  }
  return {
    amountMinor: a.amountMinor - b.amountMinor,
    currency: a.currency,
  };
}

export function formatMoneyMinor(money: MoneyMinor): string {
  assertValidMoneyMinor(money);
  const major = (money.amountMinor / 100).toLocaleString("en-NG", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  switch (money.currency) {
    case "NGN":
      return `₦${major}`;
    case "ESP":
      return `${major} ESP`;
    case "USD":
      return `$${major}`;
  }
}

// =============================================================================
// §6.3 Core Lifecycle State Machines & Transition Graphs
// =============================================================================

export type CareEpisodeState =
  | "DRAFT"
  | "SUBMITTED"
  | "ACTIVE"
  | "FOLLOW_UP"
  | "REFERRED"
  | "CLOSED"
  | "WITHDRAWN"
  | "EXPIRED"
  | "CANCELLED";

export const CARE_EPISODE_TRANSITIONS: Readonly<
  Record<CareEpisodeState, readonly CareEpisodeState[]>
> = {
  DRAFT: ["SUBMITTED", "WITHDRAWN", "EXPIRED", "CANCELLED"],
  SUBMITTED: ["ACTIVE", "REFERRED", "WITHDRAWN", "EXPIRED", "CANCELLED"],
  ACTIVE: ["FOLLOW_UP", "REFERRED", "CLOSED", "CANCELLED"],
  FOLLOW_UP: ["ACTIVE", "REFERRED", "CLOSED", "EXPIRED"],
  REFERRED: ["ACTIVE", "FOLLOW_UP", "CLOSED"],
  CLOSED: [],
  WITHDRAWN: [],
  EXPIRED: [],
  CANCELLED: [],
};

export type AppointmentState =
  | "REQUESTED"
  | "OFFERED"
  | "BOOKED"
  | "CHECKED_IN"
  | "FULFILLED"
  | "NO_SHOW"
  | "CANCELLED"
  | "EXPIRED";

export const APPOINTMENT_TRANSITIONS: Readonly<
  Record<AppointmentState, readonly AppointmentState[]>
> = {
  REQUESTED: ["OFFERED", "BOOKED", "CANCELLED", "EXPIRED"],
  OFFERED: ["BOOKED", "CANCELLED", "EXPIRED"],
  BOOKED: ["CHECKED_IN", "NO_SHOW", "CANCELLED", "EXPIRED"],
  CHECKED_IN: ["FULFILLED", "CANCELLED"],
  FULFILLED: [],
  NO_SHOW: [],
  CANCELLED: [],
  EXPIRED: [],
};

export type EncounterState =
  | "OPEN"
  | "IN_PROGRESS"
  | "DOCUMENTATION_PENDING"
  | "SIGNED"
  | "CLOSED"
  | "ABORTED";

export const ENCOUNTER_TRANSITIONS: Readonly<
  Record<EncounterState, readonly EncounterState[]>
> = {
  OPEN: ["IN_PROGRESS", "ABORTED"],
  IN_PROGRESS: ["DOCUMENTATION_PENDING", "SIGNED", "ABORTED"],
  DOCUMENTATION_PENDING: ["SIGNED", "ABORTED"],
  SIGNED: ["CLOSED"],
  CLOSED: [],
  ABORTED: [],
};

export type ConsultationModality =
  | "VIDEO"
  | "AUDIO_FALLBACK"
  | "ASYNC_CLINICAL_MESSAGING"
  | "CLINIC_TO_CLINICIAN_TELECONSULT";

export type ReferralState =
  | "DRAFT"
  | "AUTHORIZED"
  | "SENT"
  | "RECEIVED"
  | "ACCEPTED"
  | "DECLINED"
  | "COMPLETED"
  | "CLOSED";

export const REFERRAL_TRANSITIONS: Readonly<
  Record<ReferralState, readonly ReferralState[]>
> = {
  DRAFT: ["AUTHORIZED", "CLOSED"],
  AUTHORIZED: ["SENT", "CLOSED"],
  SENT: ["RECEIVED", "DECLINED", "CLOSED"],
  RECEIVED: ["ACCEPTED", "DECLINED"],
  ACCEPTED: ["COMPLETED", "CLOSED"],
  DECLINED: ["CLOSED"],
  COMPLETED: ["CLOSED"],
  CLOSED: [],
};

// =============================================================================
// §7.2 Health Navigator Protocol Lifecycle & Workflow Outcomes
// =============================================================================

export type ProtocolBundleState =
  | "DRAFT"
  | "CLINICAL_REVIEW"
  | "APPROVED"
  | "ACTIVE"
  | "SUSPENDED"
  | "RETIRED";

export const PROTOCOL_BUNDLE_TRANSITIONS: Readonly<
  Record<ProtocolBundleState, readonly ProtocolBundleState[]>
> = {
  DRAFT: ["CLINICAL_REVIEW", "RETIRED"],
  CLINICAL_REVIEW: ["DRAFT", "APPROVED", "RETIRED"],
  APPROVED: ["ACTIVE", "SUSPENDED", "RETIRED"],
  ACTIVE: ["SUSPENDED", "RETIRED"],
  SUSPENDED: ["ACTIVE", "RETIRED"],
  RETIRED: [],
};

export type ProtocolOutcomeType =
  | "EMERGENCY_GUIDANCE"
  | "URGENT_PROFESSIONAL_ASSESSMENT"
  | "CLINICIAN_REVIEW"
  | "ROUTINE_CARE_NAVIGATION"
  | "GENERAL_INFORMATION_WITH_SAFETY_NET"
  | "OUT_OF_SCOPE"
  | "INSUFFICIENT_INFORMATION"
  | "PROTOCOL_UNAVAILABLE";

// =============================================================================
// §8.1 Clinician Credential & Onboarding Lifecycle
// =============================================================================

export type ClinicianLifecycleState =
  | "APPLIED"
  | "LICENCE_CHECK_PENDING"
  | "VERIFIED"
  | "TRAINING_PENDING"
  | "APPROVED_ACTIVE"
  | "SUSPENDED"
  | "INACTIVE";

export const CLINICIAN_LIFECYCLE_TRANSITIONS: Readonly<
  Record<ClinicianLifecycleState, readonly ClinicianLifecycleState[]>
> = {
  APPLIED: ["LICENCE_CHECK_PENDING", "INACTIVE"],
  LICENCE_CHECK_PENDING: ["VERIFIED", "SUSPENDED", "INACTIVE"],
  VERIFIED: ["TRAINING_PENDING", "APPROVED_ACTIVE", "SUSPENDED"],
  TRAINING_PENDING: ["APPROVED_ACTIVE", "SUSPENDED", "INACTIVE"],
  APPROVED_ACTIVE: ["SUSPENDED", "INACTIVE"],
  SUSPENDED: ["LICENCE_CHECK_PENDING", "APPROVED_ACTIVE", "INACTIVE"],
  INACTIVE: ["LICENCE_CHECK_PENDING"],
};

// =============================================================================
// §10.3 SponsorCare Entitlement State Machine
// =============================================================================

export type EntitlementState =
  | "AVAILABLE"
  | "RESERVED"
  | "REDEEMED"
  | "RELEASED"
  | "EXPIRED"
  | "SUSPENDED"
  | "REVERSED";

export const ENTITLEMENT_TRANSITIONS: Readonly<
  Record<EntitlementState, readonly EntitlementState[]>
> = {
  AVAILABLE: ["RESERVED", "EXPIRED", "SUSPENDED"],
  RESERVED: ["REDEEMED", "RELEASED", "SUSPENDED", "EXPIRED"],
  RELEASED: ["AVAILABLE", "EXPIRED"],
  SUSPENDED: ["RESERVED", "AVAILABLE", "EXPIRED"],
  REDEEMED: ["REVERSED"],
  REVERSED: [],
  EXPIRED: [],
};

export type FundingRouteType =
  | "SELF_PAY"
  | "SPONSOR_DEFINED_SERVICES"
  | "INSTITUTIONAL_ACCESS_CONTRACT"
  | "ESPEES_WALLET_DIRECT";

export type PaymentGatewayProvider =
  | "PAYSTACK"
  | "FLUTTERWAVE"
  | "ESPEES_WALLET";

export function canTransition<S extends string>(
  transitionMap: Readonly<Record<S, readonly S[]>>,
  fromState: S,
  toState: S
): boolean {
  return transitionMap[fromState]?.includes(toState) ?? false;
}

export function assertValidTransition<S extends string>(
  entityName: string,
  transitionMap: Readonly<Record<S, readonly S[]>>,
  fromState: S,
  toState: S
): void {
  if (!canTransition(transitionMap, fromState, toState)) {
    throw new Error(
      `Invalid ${entityName} state transition from '${fromState}' to '${toState}'`
    );
  }
}

// =============================================================================
// §17.2 Unit Economics & Encounter Margin Calculation
// =============================================================================

export interface EncounterUnitEconomicsInput {
  readonly encounterId: string;
  readonly payerCohort: FundingRouteType;
  readonly currency: CurrencyCode;
  readonly settledRevenueMinor: number;
  readonly clinicianDirectCostMinor: number;
  readonly paymentProcessingFeeMinor: number;
  readonly communicationsRtcModelCostMinor: number;
  readonly variableSupportCostMinor: number;
  readonly refundQualityReserveMinor: number;
}

export interface EncounterUnitEconomicsResult extends EncounterUnitEconomicsInput {
  readonly totalVariableCostMinor: number;
  readonly contributionMarginMinor: number;
  readonly contributionMarginRatioBps: number;
  readonly isStructurallyPositive: boolean;
}

export function computeEncounterUnitEconomics(
  input: EncounterUnitEconomicsInput
): EncounterUnitEconomicsResult {
  const totalVariableCostMinor =
    input.clinicianDirectCostMinor +
    input.paymentProcessingFeeMinor +
    input.communicationsRtcModelCostMinor +
    input.variableSupportCostMinor +
    input.refundQualityReserveMinor;

  const contributionMarginMinor = input.settledRevenueMinor - totalVariableCostMinor;
  const contributionMarginRatioBps =
    input.settledRevenueMinor > 0
      ? Math.round((contributionMarginMinor * 10000) / input.settledRevenueMinor)
      : 0;

  return {
    ...input,
    totalVariableCostMinor,
    contributionMarginMinor,
    contributionMarginRatioBps,
    isStructurallyPositive: contributionMarginMinor > 0,
  };
}

// =============================================================================
// §4 & §5 Longitudinal Care, Subjects, Care Plans & Coordination
// =============================================================================

export interface PatientSubject {
  readonly patient_id: string;
  readonly account_id: string;
  readonly full_name: string;
  readonly date_of_birth_iso: string;
  readonly gender: string;
  readonly relationship_to_account: "SELF" | "CHILD" | "SPOUSE" | "PARENT" | "DEPENDENT" | string;
  readonly jurisdiction: string;
  readonly created_at_iso: string;
}

export interface CareRelationship {
  readonly relationship_id: string;
  readonly account_id: string;
  readonly patient_id: string;
  readonly relationship_type: "SELF" | "GUARDIAN" | "ADULT_PROXY" | string;
  readonly allowed_scopes: readonly string[];
  readonly revoked: boolean;
}

export interface CareContinuityPlan {
  readonly plan_id: string;
  readonly episode_id: string;
  readonly encounter_id: string;
  readonly patient_id: string;
  readonly owning_clinician_id: string;
  readonly programme_name: string;
  readonly monitoring_instructions: string;
  readonly due_at_iso: string;
  readonly status: "ACTIVE" | "COMPLETED" | "ESCALATED";
  readonly goals: readonly string[];
  readonly actions: readonly string[];
}

export interface MedicationAdherenceReport {
  readonly report_id: string;
  readonly status: "TAKEN" | "SKIPPED" | "ISSUE";
  readonly reported_by_actor_id: string;
  readonly reported_at_iso: string;
  readonly notes?: string | null;
}

export interface MedicationInstruction {
  readonly medication_id: string;
  readonly patient_id: string;
  readonly encounter_id: string;
  readonly prescriber_clinician_id: string;
  readonly prescriber_clinician_name: string;
  readonly medication_name: string;
  readonly dosage_instructions: string;
  readonly frequency_per_day: number;
  readonly duration_days: number;
  readonly clinical_indication: string;
  readonly status: "ACTIVE" | "COMPLETED" | "DISCONTINUED";
  readonly prescribed_at_iso: string;
  readonly adherence_reports: readonly MedicationAdherenceReport[];
}

export interface CareTask {
  readonly task_id: string;
  readonly patient_id: string;
  readonly episode_id?: string | null;
  readonly encounter_id?: string | null;
  readonly assigned_to: "PATIENT" | "CLINICIAN" | "COORDINATOR";
  readonly task_type:
    | "MEDICATION_REMINDER"
    | "CHECK_IN"
    | "RESULT_REVIEW"
    | "FOLLOW_UP"
    | "REFERRAL_FOLLOW_UP"
    | "CLINICAL_REVIEW";
  readonly title: string;
  readonly description: string;
  readonly due_at_iso: string;
  readonly status: "OPEN" | "IN_PROGRESS" | "RESOLVED" | "VERIFIED_CLOSED" | "CANCELLED" | "ESCALATED";
  readonly self_reported_completion: boolean;
  readonly resolved_at_iso?: string | null;
  readonly created_at_iso: string;
}

export interface ClinicalObservation {
  readonly observation_id: string;
  readonly patient_id: string;
  readonly kind: "SYMPTOM" | "VITAL" | "LAB_RESULT" | "DOCUMENT";
  readonly name: string;
  readonly value: string;
  readonly unit?: string | null;
  readonly observed_at_iso: string;
  readonly recorded_at_iso: string;
  readonly source: "PATIENT_REPORTED" | "CLINICIAN_ENTERED" | "LAB_UPLOAD";
  readonly verification_status: "UNVERIFIED" | "DRAFT" | "VERIFIED";
  readonly notes?: string | null;
}

export interface NetworkFacility {
  readonly facility_id: string;
  readonly facility_name: string;
  readonly facility_code: string;
  readonly address: string;
  readonly jurisdiction: string;
  readonly geocoordinates: { readonly lat: number; readonly lng: number };
  readonly services: readonly string[];
  readonly hours: string;
  readonly contact_phone: string;
  readonly is_verified: boolean;
  readonly readiness_state: "CONFIRMED_AVAILABLE" | "STALE" | "UNAVAILABLE";
  readonly readiness_updated_at_iso: string;
  readonly readiness_expires_at_iso: string;
}

export interface CoordinationTask {
  readonly task_id: string;
  readonly episode_id: string;
  readonly patient_id: string;
  readonly work_state:
    | "AWAITING_ASSIGNMENT"
    | "AWAITING_PATIENT"
    | "CALLBACK_DUE"
    | "REFERRAL_PENDING"
    | "RESULT_OVERDUE"
    | "SERVICE_EXCEPTION";
  readonly urgency: "ROUTINE" | "URGENT" | "EMERGENCY";
  readonly due_at_iso: string;
  readonly owner_team: string;
  readonly claimed_by?: string | null;
  readonly communication_status: string;
  readonly next_action: string;
  readonly created_at_iso: string;
}

export interface DirectorateAction {
  readonly action_id: string;
  readonly metric_id: string;
  readonly title: string;
  readonly description: string;
  readonly owner_team: string;
  readonly assigned_to: string;
  readonly due_date_iso: string;
  readonly status: "OPEN" | "IN_PROGRESS" | "RESOLVED";
  readonly evidence_notes: string;
  readonly created_at_iso: string;
}

export interface DirectorateMetric {
  readonly id: string;
  readonly name: string;
  readonly value: number;
  readonly unit: string;
  readonly definition: string;
  readonly denominator: string;
  readonly reporting_period: string;
  readonly refresh_time_iso: string;
  readonly source: string;
  readonly completeness: string;
}

export interface FinanceException {
  readonly exception_id: string;
  readonly agreement_id?: string | null;
  readonly encounter_id?: string | null;
  readonly exception_type: string;
  readonly amount_minor: number;
  readonly currency: string;
  readonly reason: string;
  readonly maker_id: string;
  readonly checker_id?: string | null;
  readonly status: "PENDING_REVIEW" | "APPROVED" | "REJECTED" | "REMEDIATED";
  readonly action_notes?: string | null;
  readonly created_at_iso: string;
  readonly resolved_at_iso?: string | null;
}

export interface ReconciliationSummary {
  readonly summary_id: string;
  readonly as_of_iso: string;
  readonly total_sponsor_cash_received_minor: number;
  readonly total_reserved_minor: number;
  readonly total_redeemed_minor: number;
  readonly total_available_liability_minor: number;
  readonly total_clinician_payables_minor: number;
  readonly total_clinician_paid_minor: number;
  readonly unresolved_exceptions_count: number;
  readonly double_entry_balanced: boolean;
}
