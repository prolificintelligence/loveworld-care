---
document_id: "LWH-SPEC-012"
title: "Interoperability and controlled patient-record exchange"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Clinical interoperability and records leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-PRD-012", "LWH-SPEC-003", "LWH-SPEC-019", "LWH-SPEC-020", "LWH-ENG-007"]
source_refs: ["LWH-SRC-009", "LWH-SRC-010", "LWH-SRC-044", "LWH-SRC-045", "LWH-SRC-046"]
directive_refs: []
---

# Interoperability and controlled patient-record exchange

## Exchange baseline and version selection

Use FHIR R4 4.0.1 as the initial exchange baseline and IPS 2.0.1 as the candidate patient-summary profile, subject to each partner/country agreement. FHIR R5 exists; selecting R4 here is an interoperability decision tied to the selected IPS profile and partner capabilities. The EHR functional model's publication using R5 Requirements resources does not force the clinical wire API to R5. Profile/version negotiation is explicit, not automatic conversion.

## Resource and use-case mapping

| Use case | Candidate FHIR representation | Required LW controls |
|---|---|---|
| Patient/site/professional matching | Patient, RelatedPerson, Organization, Location, Practitioner/Role | Issuer/system identifiers, provenance, reviewed matching and privileges |
| Encounter and care responsibility | Encounter, EpisodeOfCare, CareTeam, Appointment | Local authority, accepted owner and state semantics |
| Summary and clinical documents | IPS Composition/Bundle, DocumentReference, Binary | Minimum necessary scope, signed source version and actual receipt |
| Clinical facts | Condition, AllergyIntolerance, Observation, Procedure, Immunization | Verification status, unknown/none-known, units/time and source |
| Diagnostic request/result | ServiceRequest, Specimen, DiagnosticReport, Observation, ImagingStudy | Order/accession/subject match, report version, actual review task |
| Medication chain | MedicationRequest, MedicationDispense, MedicationAdministration, MedicationStatement | Prescribed/dispensed/administered/reported distinction; complete units and source |
| Care plan/referral | CarePlan, Goal, Task, ServiceRequest | Explicit sender/receiver acceptance and pending-result responsibility |
| Authority and history | Consent, Provenance, AuditEvent | Policy enforcement outside the representation; exact purpose/recipient/validity |

These mappings are design choices and must be expressed as partner implementation profiles, terminology bindings and capability statements. A resource name alone is not a compliant interface. Required summary content, empty-section semantics and local extensions are validated against the selected profile rather than assumed from a generic JSON export.

## Exchange transaction

1. Resolve the source subject and recipient identity; review external patient links and purpose.
2. Verify valid patient/representative or other applicable authority, clinical relationship and record scope.
3. Select the minimum authorised source versions; create a source-attributed summary/document bundle.
4. Validate profile, terminology, unit, patient/reference consistency and permitted fields before transmission.
5. Encrypt/authenticate transport, bound token audience, protect attachment/image access and retain disclosure evidence.
6. Recipient confirms subject matching and package validation; acknowledge received/accepted/quarantined separately.
7. Amendments/revocations produce controlled notifications and future-access changes; retained lawful clinical copies follow policy.

Protected coded referrals may hide direct identifiers from an appropriately authorised recipient until the permitted identity-disclosure stage. The matching/linkage keys remain controlled and are not transmitted into general leadership intelligence. Clinical treatment still requires correct-patient confirmation. Truly anonymous analytics use separate transformations/disclosure review and cannot be made identifiable merely by changing a UI toggle.

## Interface qualification

Each partner has a signed data-sharing purpose, profile/version, identifier/code mapping, actual endpoints, authentication, error/retry policy, custody/retention, correction/revocation handling, availability/support and test evidence. Capability tests cover minimum summary, missing/unknown data, external identifiers, wrong patient, code/unit mismatch, preliminary/corrected results, duplicate/out-of-order messages and offline delivery. An unmatched result is quarantined, never guessed into a chart.

## Existing systems and export

Facilities may retain their EMR and provide approved aggregates plus scoped clinical exchange, or migrate under LWH-ENG-007. CSV/document adapters are allowed when properly mapped and validated; they do not pretend to provide a full real-time FHIR interface. Patient export includes a usable human-readable version and supported structured data/provenance. Export cannot bypass field permissions, small-cohort controls or clinical custody obligations.
