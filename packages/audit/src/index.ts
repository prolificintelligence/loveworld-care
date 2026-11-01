/**
 * @loveworld-care/audit
 * Tamper-evident hash-chained AuditEvent contracts, Outbox Event envelopes (§14.3),
 * and automatic T3/PHI log redaction guards (§16.5 & §22.3).
 */

import type { AccessPurpose, PlatformRole } from "@loveworld-care/authorization";
import type { DataClassificationTier } from "@loveworld-care/domain-types";

export interface TamperEvidentAuditEvent {
  readonly auditId: string;
  readonly sequenceNumber: number;
  readonly occurredAtIso: string;
  readonly requestId: string;
  readonly actorId: string;
  readonly actorRoles: readonly PlatformRole[];
  readonly purpose: AccessPurpose;
  readonly action: string;
  readonly resourceType: string;
  readonly resourceOpaqueId: string;
  readonly dataTier: DataClassificationTier;
  readonly outcome: "SUCCESS" | "DENIED" | "ERROR";
  readonly reasonCode: string;
  readonly breakGlassGrantId?: string;
  readonly previousEntryHash: string;
  readonly entryHash: string;
}

export type OutboxDomainEventType =
  | "care.episode.created.v1"
  | "care.intake.submitted.v1"
  | "care.protocol.evaluated.v1"
  | "care.appointment.booked.v1"
  | "care.encounter.claimed.v1"
  | "care.encounter.signed.v1"
  | "care.addendum.signed.v1"
  | "care.referral.authorized.v1"
  | "care.referral.status_changed.v1"
  | "finance.payment.settled.v1"
  | "finance.entitlement.reserved.v1"
  | "finance.entitlement.redeemed.v1"
  | "finance.entitlement.released.v1"
  | "finance.payable.approved.v1"
  | "security.break_glass.invoked.v1"
  | "governance.ai_kill_switch.toggled.v1";

/**
 * §14.3 Outbox-derived event envelope.
 * Deliberately excludes clinical narrative / free-text PHI.
 */
export interface OutboxEventEnvelope<TPayload = Record<string, unknown>> {
  readonly event_id: string;
  readonly event_type: OutboxDomainEventType;
  readonly occurred_at: string;
  readonly correlation_id: string;
  readonly source: "care-service" | "finance-service" | "protocol-runtime" | "identity-service";
  readonly schema_version: number;
  readonly data: TPayload;
}

const SENSITIVE_PHI_FIELD_PATTERNS: readonly RegExp[] = [
  /symptom/i,
  /diagnosis/i,
  /clinical_note/i,
  /narrative/i,
  /chief_complaint/i,
  /medication_instructions/i,
  /raw_patient_statement/i,
  /password/i,
  /secret/i,
  /token/i,
  /nin/i,
  /bvn/i,
];

/**
 * §22.3 Data protection in observability:
 * Scrubs any T2/T3 personal or clinical narrative fields before writing to general telemetry.
 */
export function redactPhiFromTelemetry<T extends Record<string, unknown>>(
  payload: T
): Record<string, unknown> {
  const sanitized: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(payload)) {
    if (SENSITIVE_PHI_FIELD_PATTERNS.some((rx) => rx.test(key))) {
      sanitized[key] = "[REDACTED_PHI_T3]";
    } else if (value && typeof value === "object" && !Array.isArray(value)) {
      sanitized[key] = redactPhiFromTelemetry(value as Record<string, unknown>);
    } else {
      sanitized[key] = value;
    }
  }
  return sanitized;
}
