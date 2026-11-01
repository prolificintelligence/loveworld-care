/**
 * @loveworld-care/authorization
 * Server-side & client-aware RBAC + ABAC (Assignment, Purpose, Credential & Break-Glass)
 * policy engine implementing §12.4, §16.2, FR-SEC-01, AT-06, AT-07, AT-14, and AT-15.
 */

import type {
  ClinicianLifecycleState,
  DataClassificationTier,
} from "@loveworld-care/domain-types";

export type PlatformRole =
  | "PATIENT"
  | "AUTHORIZED_PROXY"
  | "CLINICIAN_GP"
  | "CLINICIAN_SPECIALIST"
  | "CARE_COORDINATOR"
  | "CLINIC_PARTNER_STAFF"
  | "CLINICAL_GOVERNANCE_LEAD"
  | "CLINICAL_OPS"
  | "SUPPORT_AGENT"
  | "FINANCE_CONTROLLER"
  | "SPONSOR_ADMIN"
  | "INSTITUTION_ADMIN"
  | "EXECUTIVE_DIRECTOR"
  | "PLATFORM_SRE";

export type AccessPurpose =
  | "PATIENT_SELF_SERVICE"
  | "GUARDIAN_PROXY_CARE"
  | "ASSIGNED_CLINICAL_CARE"
  | "BREAK_GLASS_EMERGENCY_REVIEW"
  | "CLINICAL_QUALITY_AUDIT"
  | "OPERATIONS_QUEUE_COORDINATION"
  | "NON_CLINICAL_SUPPORT"
  | "FINANCE_SETTLEMENT_RECONCILIATION"
  | "SPONSOR_AGGREGATE_REPORTING"
  | "EXECUTIVE_AGGREGATE_ANALYTICS"
  | "CROSS_PRODUCT_CONSENTED_TRANSFER";

export interface BreakGlassGrantContext {
  readonly grantId: string;
  readonly reason: string;
  readonly issuedAtIso: string;
  readonly expiresAtIso: string;
  readonly targetPatientId: string;
}

export interface ProxyAuthorityContext {
  readonly proxyGrantId: string;
  readonly patientId: string;
  readonly allowedScopes: readonly ("INTAKE" | "BOOKING" | "VIEW_SUMMARY" | "PAYMENTS")[];
  readonly validUntilIso: string;
  readonly revoked: boolean;
}

export interface ActorSecurityContext {
  readonly actorId: string;
  readonly roles: readonly PlatformRole[];
  readonly mfaVerified: boolean;
  readonly sessionLocked?: boolean;
  readonly clinicianStatus?: ClinicianLifecycleState;
  readonly credentialExpiresAtIso?: string;
  readonly activeProxyGrants?: readonly ProxyAuthorityContext[];
  readonly activeBreakGlass?: BreakGlassGrantContext;
}

export interface ResourceContext {
  readonly resourceType:
    | "CLINICAL_RECORD_T3"
    | "PROTOCOL_BUNDLE"
    | "APPOINTMENT_SLOT"
    | "QUEUE_METADATA"
    | "SUPPORT_CASE"
    | "FINANCE_LEDGER"
    | "SPONSOR_AGGREGATE_REPORT"
    | "EXECUTIVE_METRICS"
    | "CROSS_PRODUCT_HANDOFF";
  readonly dataTier: DataClassificationTier;
  readonly ownerPatientId?: string;
  readonly assignedClinicianId?: string;
  readonly sponsorId?: string;
  readonly cohortSizeK?: number;
  readonly explicitUserConsentConfirmed?: boolean;
}

export interface AuthorizationDecision {
  readonly allowed: boolean;
  readonly reasonCode:
    | "ALLOWED"
    | "DENIED_SESSION_LOCKED"
    | "DENIED_MFA_REQUIRED"
    | "DENIED_SPONSOR_NEVER_READS_CLINICAL_T3"
    | "DENIED_SUPPORT_OPS_FINANCE_NO_T3_NARRATIVE"
    | "DENIED_SRE_NO_PLAINTEXT_CLINICAL_T3"
    | "DENIED_CLINICIAN_CREDENTIAL_EXPIRED_OR_INACTIVE"
    | "DENIED_UNASSIGNED_CLINICIAN_WITHOUT_BREAK_GLASS"
    | "DENIED_PATIENT_OR_PROXY_MISMATCH"
    | "DENIED_SMALL_COHORT_SUPPRESSION_K_LT_5"
    | "DENIED_MISSING_EXPLICIT_USER_TRANSFER_CONSENT"
    | "DENIED_INSUFFICIENT_ROLE";
  readonly obligations: readonly ("AUDIT_MANDATORY" | "MASK_PHI_FIELDS" | "FLAG_SECURITY_ALERT")[];
}

const PRIVILEGED_MFA_ROLES: ReadonlySet<PlatformRole> = new Set([
  "CLINICIAN_GP",
  "CLINICIAN_SPECIALIST",
  "CARE_COORDINATOR",
  "CLINICAL_GOVERNANCE_LEAD",
  "CLINICAL_OPS",
  "FINANCE_CONTROLLER",
  "EXECUTIVE_DIRECTOR",
  "PLATFORM_SRE",
]);

export function evaluateAuthorization(
  actor: ActorSecurityContext,
  action: "READ" | "WRITE" | "CLAIM" | "SIGN" | "APPROVE" | "RESERVE" | "REDEEM",
  purpose: AccessPurpose,
  resource: ResourceContext,
  nowIso: string = new Date().toISOString()
): AuthorizationDecision {
  // AT-13: Shared-device session lock immediately blocks all resource access
  if (actor.sessionLocked) {
    return {
      allowed: false,
      reasonCode: "DENIED_SESSION_LOCKED",
      obligations: ["AUDIT_MANDATORY"],
    };
  }

  // §16.3: Privileged roles MUST have MFA verified
  const requiresMfa = actor.roles.some((r) => PRIVILEGED_MFA_ROLES.has(r));
  if (requiresMfa && !actor.mfaVerified) {
    return {
      allowed: false,
      reasonCode: "DENIED_MFA_REQUIRED",
      obligations: ["AUDIT_MANDATORY"],
    };
  }

  // AT-06 & §10.5: Sponsors and institutional buyers can NEVER access T3 clinical records
  if (
    resource.dataTier === "T3_SENSITIVE_CLINICAL" &&
    actor.roles.some((r) => r === "SPONSOR_ADMIN" || r === "INSTITUTION_ADMIN")
  ) {
    return {
      allowed: false,
      reasonCode: "DENIED_SPONSOR_NEVER_READS_CLINICAL_T3",
      obligations: ["AUDIT_MANDATORY", "FLAG_SECURITY_ALERT"],
    };
  }

  // §16.2: Infrastructure SREs do not inherit permission to read clinical plaintext
  if (
    resource.dataTier === "T3_SENSITIVE_CLINICAL" &&
    actor.roles.includes("PLATFORM_SRE") &&
    !actor.roles.includes("CLINICAL_GOVERNANCE_LEAD")
  ) {
    return {
      allowed: false,
      reasonCode: "DENIED_SRE_NO_PLAINTEXT_CLINICAL_T3",
      obligations: ["AUDIT_MANDATORY", "FLAG_SECURITY_ALERT"],
    };
  }

  // §16.2: Support, Ops, Finance, and Executive roles cannot read raw T3 clinical narratives
  if (
    resource.dataTier === "T3_SENSITIVE_CLINICAL" &&
    actor.roles.some((r) =>
      ["SUPPORT_AGENT", "CLINICAL_OPS", "FINANCE_CONTROLLER", "EXECUTIVE_DIRECTOR"].includes(r)
    ) &&
    !actor.roles.some((r) =>
      ["CLINICIAN_GP", "CLINICIAN_SPECIALIST", "CLINICAL_GOVERNANCE_LEAD"].includes(r)
    )
  ) {
    return {
      allowed: false,
      reasonCode: "DENIED_SUPPORT_OPS_FINANCE_NO_T3_NARRATIVE",
      obligations: ["AUDIT_MANDATORY", "MASK_PHI_FIELDS"],
    };
  }

  // AT-14 & §10.5: Small-cohort k>=5 suppression on Sponsor aggregate reports
  if (resource.resourceType === "SPONSOR_AGGREGATE_REPORT") {
    if (
      !actor.roles.some((r) =>
        ["SPONSOR_ADMIN", "INSTITUTION_ADMIN", "FINANCE_CONTROLLER", "EXECUTIVE_DIRECTOR"].includes(r)
      )
    ) {
      return {
        allowed: false,
        reasonCode: "DENIED_INSUFFICIENT_ROLE",
        obligations: ["AUDIT_MANDATORY"],
      };
    }
    if (typeof resource.cohortSizeK === "number" && resource.cohortSizeK > 0 && resource.cohortSizeK < 5) {
      return {
        allowed: false,
        reasonCode: "DENIED_SMALL_COHORT_SUPPRESSION_K_LT_5",
        obligations: ["AUDIT_MANDATORY"],
      };
    }
    return {
      allowed: true,
      reasonCode: "ALLOWED",
      obligations: ["AUDIT_MANDATORY"],
    };
  }

  // AT-15 & §12.4: Cross-product scan handoff requires explicit user action & consent
  if (resource.resourceType === "CROSS_PRODUCT_HANDOFF") {
    if (!resource.explicitUserConsentConfirmed || purpose !== "CROSS_PRODUCT_CONSENTED_TRANSFER") {
      return {
        allowed: false,
        reasonCode: "DENIED_MISSING_EXPLICIT_USER_TRANSFER_CONSENT",
        obligations: ["AUDIT_MANDATORY", "FLAG_SECURITY_ALERT"],
      };
    }
  }

  // Clinical T3 Access Rules
  if (resource.resourceType === "CLINICAL_RECORD_T3") {
    const isClinician = actor.roles.some(
      (r) => r === "CLINICIAN_GP" || r === "CLINICIAN_SPECIALIST"
    );

    if (isClinician) {
      // AT-07 & §8.1: Active verified credential and non-expired licence required
      const credentialValid =
        actor.clinicianStatus === "APPROVED_ACTIVE" &&
        (!actor.credentialExpiresAtIso || actor.credentialExpiresAtIso > nowIso);

      if (!credentialValid) {
        return {
          allowed: false,
          reasonCode: "DENIED_CLINICIAN_CREDENTIAL_EXPIRED_OR_INACTIVE",
          obligations: ["AUDIT_MANDATORY", "FLAG_SECURITY_ALERT"],
        };
      }

      // Assigned clinician OR active Break-Glass grant
      const isAssigned =
        Boolean(resource.assignedClinicianId) && resource.assignedClinicianId === actor.actorId;
      const hasValidBreakGlass =
        purpose === "BREAK_GLASS_EMERGENCY_REVIEW" &&
        actor.activeBreakGlass !== undefined &&
        actor.activeBreakGlass.targetPatientId === resource.ownerPatientId &&
        actor.activeBreakGlass.expiresAtIso > nowIso;

      // Claiming an unassigned case is permitted if clinician is active
      if (action === "CLAIM" && !resource.assignedClinicianId) {
        return {
          allowed: true,
          reasonCode: "ALLOWED",
          obligations: ["AUDIT_MANDATORY"],
        };
      }

      if (!isAssigned && !hasValidBreakGlass) {
        return {
          allowed: false,
          reasonCode: "DENIED_UNASSIGNED_CLINICIAN_WITHOUT_BREAK_GLASS",
          obligations: ["AUDIT_MANDATORY", "FLAG_SECURITY_ALERT"],
        };
      }

      return {
        allowed: true,
        reasonCode: "ALLOWED",
        obligations: ["AUDIT_MANDATORY"],
      };
    }

    // Clinical Governance Lead for quality audit (read-only)
    if (
      actor.roles.includes("CLINICAL_GOVERNANCE_LEAD") &&
      action === "READ" &&
      purpose === "CLINICAL_QUALITY_AUDIT"
    ) {
      return {
        allowed: true,
        reasonCode: "ALLOWED",
        obligations: ["AUDIT_MANDATORY"],
      };
    }

    // Patient or Verified Proxy Authority
    if (actor.roles.includes("PATIENT") && resource.ownerPatientId === actor.actorId) {
      if (action === "SIGN" || action === "CLAIM") {
        return {
          allowed: false,
          reasonCode: "DENIED_INSUFFICIENT_ROLE",
          obligations: ["AUDIT_MANDATORY"],
        };
      }
      return {
        allowed: true,
        reasonCode: "ALLOWED",
        obligations: ["AUDIT_MANDATORY"],
      };
    }

    if (actor.roles.includes("AUTHORIZED_PROXY") && resource.ownerPatientId) {
      const matchingProxy = actor.activeProxyGrants?.find(
        (g) =>
          g.patientId === resource.ownerPatientId &&
          !g.revoked &&
          g.validUntilIso > nowIso
      );
      if (matchingProxy && (action === "READ" || action === "WRITE")) {
        return {
          allowed: true,
          reasonCode: "ALLOWED",
          obligations: ["AUDIT_MANDATORY"],
        };
      }
    }

    return {
      allowed: false,
      reasonCode: "DENIED_PATIENT_OR_PROXY_MISMATCH",
      obligations: ["AUDIT_MANDATORY", "FLAG_SECURITY_ALERT"],
    };
  }

  return {
    allowed: true,
    reasonCode: "ALLOWED",
    obligations: ["AUDIT_MANDATORY"],
  };
}
