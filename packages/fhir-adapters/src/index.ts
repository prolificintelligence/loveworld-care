/**
 * @loveworld-care/fhir-adapters
 * Profiled HL7 FHIR R4 interoperability adapters (§13.5 & FR-INTG-01) with explicit
 * origin, transformation provenance, Nigeria National Digital Health Architecture
 * identifier namespaces, and verifiable referral Bundle export.
 */

import type {
  AppointmentState,
  ConsultationModality,
  EncounterState,
  ReferralState,
} from "@loveworld-care/domain-types";

export const LW_FHIR_SYSTEM_NAMESPACES = {
  PATIENT_ID: "https://care.loveworld.org/fhir/sid/patient-id",
  PRACTITIONER_ID: "https://care.loveworld.org/fhir/sid/practitioner-id",
  MDCN_LICENCE: "https://mdcn.gov.ng/fhir/sid/licence-number",
  ENCOUNTER_ID: "https://care.loveworld.org/fhir/sid/encounter-id",
  DOCUMENT_SHA256: "https://care.loveworld.org/fhir/sid/document-sha256",
  REFERRAL_ID: "https://care.loveworld.org/fhir/sid/referral-id",
} as const;

export interface FhirMetaProvenance {
  readonly versionId: string;
  readonly lastUpdated: string;
  readonly source: string;
  readonly profile: readonly string[];
  readonly tag: readonly {
    readonly system: string;
    readonly code: string;
    readonly display: string;
  }[];
}

export interface FhirR4Resource {
  readonly resourceType:
    | "Bundle"
    | "Patient"
    | "Practitioner"
    | "Organization"
    | "Appointment"
    | "Encounter"
    | "Observation"
    | "Condition"
    | "MedicationRequest"
    | "ServiceRequest"
    | "CarePlan"
    | "Consent"
    | "DocumentReference"
    | "Provenance";
  readonly id: string;
  readonly meta: FhirMetaProvenance;
  readonly [key: string]: unknown;
}

export interface CanonicalSignedEncounterExportInput {
  readonly encounterId: string;
  readonly patientOpaqueId: string;
  readonly clinicianId: string;
  readonly clinicianMdcnLicence: string;
  readonly encounterState: EncounterState;
  readonly modality: ConsultationModality;
  readonly startedAtIso: string;
  readonly endedAtIso: string;
  readonly signedAtIso: string;
  readonly signedDocumentHash: string;
  readonly signatureEd25519Base64: string;
  readonly chiefComplaintCode?: string;
  readonly assessmentSummary: string;
  readonly planSummary: string;
  readonly referral?: {
    readonly referralId: string;
    readonly state: ReferralState;
    readonly receivingFacilityCode: string;
    readonly receivingFacilityName: string;
    readonly specialtyCode: string;
    readonly clinicalReason: string;
    readonly priority: "routine" | "urgent" | "asap" | "stat";
  };
}

export function mapEncounterStateToFhirStatus(
  state: EncounterState
): "planned" | "in-progress" | "finished" | "cancelled" {
  switch (state) {
    case "OPEN":
      return "planned";
    case "IN_PROGRESS":
    case "DOCUMENTATION_PENDING":
      return "in-progress";
    case "SIGNED":
    case "CLOSED":
      return "finished";
    case "ABORTED":
      return "cancelled";
  }
}

export function mapAppointmentStateToFhirStatus(
  state: AppointmentState
): "proposed" | "pending" | "booked" | "arrived" | "fulfilled" | "cancelled" | "noshow" {
  switch (state) {
    case "REQUESTED":
      return "proposed";
    case "OFFERED":
      return "pending";
    case "BOOKED":
      return "booked";
    case "CHECKED_IN":
      return "arrived";
    case "FULFILLED":
      return "fulfilled";
    case "NO_SHOW":
      return "noshow";
    case "CANCELLED":
    case "EXPIRED":
      return "cancelled";
  }
}

/**
 * Generates a signed, provenance-tagged FHIR R4 Bundle for an encounter & referral handoff (§13.5).
 * Explicitly marks whether a referral is only SENT vs ACCEPTED so receiving facilities or
 * patients never misinterpret a sent referral as an accepted appointment.
 */
export function buildSignedEncounterFhirBundle(
  input: CanonicalSignedEncounterExportInput
): FhirR4Resource {
  const entries: { fullUrl: string; resource: FhirR4Resource }[] = [];

  const encounterResource: FhirR4Resource = {
    resourceType: "Encounter",
    id: input.encounterId,
    meta: {
      versionId: "1",
      lastUpdated: input.signedAtIso,
      source: "urn:loveworld-care:care-service",
      profile: ["http://hl7.org/fhir/StructureDefinition/Encounter"],
      tag: [
        {
          system: LW_FHIR_SYSTEM_NAMESPACES.DOCUMENT_SHA256,
          code: input.signedDocumentHash,
          display: "Clinician Signed Immutable Record Hash",
        },
      ],
    },
    status: mapEncounterStateToFhirStatus(input.encounterState),
    class: {
      system: "http://terminology.hl7.org/CodeSystem/v3-ActCode",
      code: "VR",
      display: `Virtual (${input.modality})`,
    },
    subject: {
      reference: `Patient/${input.patientOpaqueId}`,
      identifier: {
        system: LW_FHIR_SYSTEM_NAMESPACES.PATIENT_ID,
        value: input.patientOpaqueId,
      },
    },
    participant: [
      {
        individual: {
          reference: `Practitioner/${input.clinicianId}`,
          identifier: {
            system: LW_FHIR_SYSTEM_NAMESPACES.MDCN_LICENCE,
            value: input.clinicianMdcnLicence,
          },
        },
      },
    ],
    period: {
      start: input.startedAtIso,
      end: input.endedAtIso,
    },
  };

  entries.push({
    fullUrl: `urn:uuid:${input.encounterId}`,
    resource: encounterResource,
  });

  if (input.referral) {
    const serviceRequestResource: FhirR4Resource = {
      resourceType: "ServiceRequest",
      id: input.referral.referralId,
      meta: {
        versionId: "1",
        lastUpdated: input.signedAtIso,
        source: "urn:loveworld-care:care-service",
        profile: ["http://hl7.org/fhir/StructureDefinition/ServiceRequest"],
        tag: [
          {
            system: "https://care.loveworld.org/fhir/CodeSystem/referral-acceptance-state",
            code: input.referral.state,
            display:
              input.referral.state === "ACCEPTED"
                ? "Accepted by Receiving Facility"
                : "Pending Facility Acceptance (Not a Confirmed Facility Booking)",
          },
        ],
      },
      status: input.referral.state === "CLOSED" ? "completed" : "active",
      intent: "order",
      priority: input.referral.priority,
      subject: { reference: `Patient/${input.patientOpaqueId}` },
      encounter: { reference: `Encounter/${input.encounterId}` },
      requester: { reference: `Practitioner/${input.clinicianId}` },
      performer: [
        {
          identifier: {
            system: "https://care.loveworld.org/fhir/sid/facility-code",
            value: input.referral.receivingFacilityCode,
          },
          display: input.referral.receivingFacilityName,
        },
      ],
      reasonCode: [{ text: input.referral.clinicalReason }],
    };

    entries.push({
      fullUrl: `urn:uuid:${input.referral.referralId}`,
      resource: serviceRequestResource,
    });
  }

  const provenanceResource: FhirR4Resource = {
    resourceType: "Provenance",
    id: `prov-${input.encounterId}`,
    meta: {
      versionId: "1",
      lastUpdated: input.signedAtIso,
      source: "urn:loveworld-care:care-service",
      profile: ["http://hl7.org/fhir/StructureDefinition/Provenance"],
      tag: [],
    },
    target: [{ reference: `Encounter/${input.encounterId}` }],
    recorded: input.signedAtIso,
    agent: [
      {
        type: {
          coding: [
            {
              system: "http://terminology.hl7.org/CodeSystem/provenance-participant-type",
              code: "signer",
            },
          ],
        },
        who: { reference: `Practitioner/${input.clinicianId}` },
      },
    ],
    signature: [
      {
        type: [
          {
            system: "urn:iso-astm:E1762-95:2013",
            code: "1.2.840.10065.1.12.1.1",
            display: "Author's Signature",
          },
        ],
        when: input.signedAtIso,
        who: { reference: `Practitioner/${input.clinicianId}` },
        sigFormat: "application/ed25519",
        data: input.signatureEd25519Base64,
      },
    ],
  };

  entries.push({
    fullUrl: `urn:uuid:prov-${input.encounterId}`,
    resource: provenanceResource,
  });

  return {
    resourceType: "Bundle",
    id: `bundle-${input.encounterId}`,
    meta: {
      versionId: "1",
      lastUpdated: input.signedAtIso,
      source: "urn:loveworld-care:care-service",
      profile: ["http://hl7.org/fhir/StructureDefinition/Bundle"],
      tag: [],
    },
    type: "collection",
    timestamp: input.signedAtIso,
    entry: entries,
  };
}
