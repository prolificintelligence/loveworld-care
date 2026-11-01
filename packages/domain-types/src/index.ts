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
