---
document_id: "LWH-SPEC-010"
title: "API commands, queries and error contracts"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "API and domain architecture lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-SPEC-003", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-SPEC-017"]
source_refs: ["LWH-SRC-024", "LWH-SRC-025", "LWH-SRC-049", "LWH-SRC-051"]
directive_refs: []
---

# API commands, queries and error contracts

## Transport and authority contract

APIs are versioned, authenticated and purpose/resource scoped. `contracts/openapi.capture.json` defines the reference capture endpoints and their form schemas. Capture is distinct from consequential release/sign/approve commands. Country/partner FHIR interfaces have separate capability statements and profiles. Local and cell gateways enforce the same domain rules and route to the named authority; a cloud replica cannot independently sign a facility-origin clinical record during a partition.

Mutation headers: `Authorization`, `Idempotency-Key`, `If-Match` for existing-version mutation, and trace/correlation ID. Resolve actor/facility/patient authority from trusted session and storage. Ignore or reject forged server-owned metadata. Idempotency is scoped to authenticated principal/node, operation and resource; persist request hash and original result. Same key/different content yields conflict. Strong entity version comparison prevents lost updates. A timeout is an unknown result to query/retry using the same operation key, not permission to create a new clinical/financial event.

## Capture endpoints

| Operation | Method/path | Purpose | Request capture schema | Authorised role | Authority |
|---|---|---|---|---|---|
| LWH-API-001 | POST /v1/facilities | Facility registration | LWH-FRM-001 | Registry scope | Central registry or accepted queued proposal |
| LWH-API-002 | POST /v1/facilities/{id}/readiness | Readiness assertion | LWH-FRM-002 | Local service authority | Facility |
| LWH-API-003 | POST /v1/obligations/{id}/returns | Facility return submission | LWH-FRM-003 | Reporting officer/obligation | Facility origin; central receipt/review separate |
| LWH-API-004 | POST /v1/zones/{id}/returns | Zone return | LWH-FRM-004 | Zone coordinator | Institutional reporting authority |
| LWH-API-005 | POST /v1/health-events | Occurrence notification | LWH-FRM-005 | Covered reporting/clinical purpose | Origin node; reviewed centrally/locally by scope |
| LWH-API-006 | POST /v1/interventions | Action proposal/assignment | LWH-FRM-006 | Programme authority | Programme workflow |
| LWH-API-007 | POST /v1/applications/{id}/decisions | Final affiliation decision | LWH-FRM-007 | Directorate central decider | Central only |
| LWH-API-008 | POST /v1/applications/{id}/inspections | Inspection evidence | LWH-FRM-008 | Assigned competent inspector | Case authority; offline capture allowed |
| LWH-API-009 | POST /v1/affiliations/{id}/renewals | Renewal application | LWH-FRM-009 | Facility accountable officer | Central case service |
| LWH-API-010 | POST /v1/findings/{id}/responses | Corrective response | LWH-FRM-010 | Finding owner/reviewer | Case authority |
| LWH-API-011 | POST /v1/affiliations/{id}/restrictions | Adverse decision/review | LWH-FRM-011 | Directorate adopted authority | Central only |
| LWH-API-012 | POST /v1/returns/{id}/review | Verification/correction review | LWH-FRM-012 | Scoped independent data reviewer | Reporting authority |
| LWH-API-013 | POST /v1/content-versions | Editorial approval workflow | LWH-FRM-013 | Qualified author/reviewer/policy role | Content authority |
| LWH-API-014 | POST /v1/interventions/{id}/reviews | Outcome review | LWH-FRM-014 | Programme reviewer | Programme authority |
| LWH-API-015 | POST /v1/facility-services/{id}/activations | Service activation | LWH-FRM-015 | Clinical/network activation authority | Adopted service/country scope |
| LWH-API-016 | POST /v1/referrals | Referral request/handover | LWH-FRM-016 | Sender/receiver clinical authority | Sender origin and explicit receiver acceptance |
| LWH-API-017 | POST /v1/sharing-grants | Record-sharing authority | LWH-FRM-017 | Patient/representative/custodian | Protected exchange authority |
| LWH-API-018 | POST /v1/organisation-role-assignments | Role/delegation change | LWH-FRM-018 | Authorised grantor | Identity authority |
| LWH-API-019 | POST /v1/rights-requests | Privacy/complaint request | LWH-FRM-019 | Verified requester and scoped handler | Privacy/custody authority |
| LWH-API-020 | POST /v1/programmes | Funding/benefit programme | LWH-FRM-020 | Programme finance | Programme authority |
| LWH-API-021 | POST /v1/patients | Patient registration | LWH-FRM-021 | Facility registration | Facility |
| LWH-API-022 | POST /v1/patients/{id}/representative-grants | Caregiver authority | LWH-FRM-022 | Custodian/valid representative | Custody/identity authority |
| LWH-API-023 | POST /v1/encounters | Encounter assessment | LWH-FRM-023 | Assigned clinical team | Facility |
| LWH-API-024 | POST /v1/encounters/{id}/observations | Triage/observations | LWH-FRM-024 | Privileged clinical staff | Facility |
| LWH-API-025 | POST /v1/encounters/{id}/documents | Clinical note/addendum | LWH-FRM-025 | Clinical author/custodian | Facility |
| LWH-API-026 | POST /v1/patients/{id}/reconciliations | Clinical list reconciliation | LWH-FRM-026 | Treating clinician/pharmacist | Facility |
| LWH-API-027 | POST /v1/clinical-orders | Non-medication order | LWH-FRM-027 | Privileged requester | Facility |
| LWH-API-028 | POST /v1/specimens | Specimen chain | LWH-FRM-028 | Diagnostic department | Facility/department |
| LWH-API-029 | POST /v1/diagnostic-reports | Diagnostic result | LWH-FRM-029 | Competent verifier | Facility/department |
| LWH-API-030 | POST /v1/medication-orders | Medication intent | LWH-FRM-030 | Privileged prescriber | Facility |
| LWH-API-031 | POST /v1/dispenses | Actual medicine supply | LWH-FRM-031 | Pharmacy/dispensing | Facility |
| LWH-API-032 | POST /v1/administrations | Actual dose/omission | LWH-FRM-032 | Privileged care staff | Facility |
| LWH-API-033 | POST /v1/clinical-stock-movements | Stock movement | LWH-FRM-033 | Stock custody/approval | Facility |
| LWH-API-034 | POST /v1/admissions | Admission/occupancy | LWH-FRM-034 | Admitting/receiving team | Facility |
| LWH-API-035 | POST /v1/nursing-records | Nursing assessment/care | LWH-FRM-035 | Assigned nursing team | Facility |
| LWH-API-036 | POST /v1/care-transitions | Transfer/discharge | LWH-FRM-036 | Clinical/receiving team | Facility |
| LWH-API-037 | POST /v1/maternal-reviews | ANC care capture | LWH-FRM-037 | Privileged maternal team | Facility |
| LWH-API-038 | POST /v1/birth-records | Birth/newborn capture | LWH-FRM-038 | Birth team/custodian | Facility |
| LWH-API-039 | POST /v1/postnatal-reviews | PNC capture | LWH-FRM-039 | Maternal/newborn team | Facility |
| LWH-API-040 | POST /v1/child-health-reviews | Growth/immunisation capture | LWH-FRM-040 | Child health team | Facility |
| LWH-API-041 | POST /v1/procedure-records | Procedure phases/record | LWH-FRM-041 | Privileged procedural team | Facility |
| LWH-API-042 | POST /v1/anaesthesia-records | Anaesthesia/recovery | LWH-FRM-042 | Privileged anaesthesia team | Facility |
| LWH-API-043 | POST /v1/transfusion-records | Component/recipient chain | LWH-FRM-043 | Blood-bank/clinical/nursing | Facility |
| LWH-API-044 | POST /v1/care-invoices | Care charge/invoice | LWH-FRM-044 | Care finance | Facility/programme finance |
| LWH-API-045 | POST /v1/payment-receipts | Cash/provider receipt | LWH-FRM-045 | Cashier/provider verifier | Finance authority |
| LWH-API-046 | POST /v1/claims/{id}/reconciliations | Claim adjudication/remittance | LWH-FRM-045 | Claims/finance reviewer | Finance/payer evidence |
| LWH-API-047 | POST /v1/node-reconciliations | Outage/sync resolution | LWH-FRM-046 | Duty/data/technical lead | Origin and accepting nodes |
| LWH-API-048 | POST /v1/country-activations | Country activation dossier | LWH-FRM-047 | Directorate country owners | Central adopted approval |
| LWH-API-049 | POST /v1/enterprise/{module}/transactions | Optional ERP transaction | LWH-FRM-048 | Contracted module/role | Optional module authority |
| LWH-API-050 | POST /v1/care-plans | Plan/follow-up | LWH-FRM-049 | Clinical plan owner | Facility/care cell |
| LWH-API-051 | POST /v1/coverage-rosters | Staffed clinical coverage | LWH-FRM-050 | Clinical workforce authority | Service/facility |
| LWH-API-052 | POST /v1/treatment-consents | Treatment consent/refusal | LWH-FRM-051 | Valid subject/clinical/custody authority | Facility/custody |


## Consequential command catalogue

POST `/v1/commands/{command_name}` carries resource ID, expected version, idempotency key, reason/evidence where required and explicit signing/decision intent. `command_name` is one of the following registered operations; unknown commands fail. Implementations may expose equivalent resource-specific routes only with the same command identity, schema and guards.

| Command | Resource | Required guards / evidence | Committed result |
|---|---|---|---|
| clinical_document.sign | ClinicalDocument | Privileged signer; expected draft version; signing intent and necessary review | SIGNED; immutable revision, audit and outbox |
| clinical_order.release | ClinicalOrder | Signed current intent; privileges; applicable required fields/checks | RELEASED; actual performing department still accepts |
| medication_order.stop | MedicationOrder | Privileged prescriber; current version; reason and future-task review | STOPPED; past administrations preserved |
| referral.accept | Referral | Actual receiving service; suitable readiness; permitted summary; capacity | ACCEPTED with recipient/time/conditions |
| referral.confirm_receipt | Referral | Actual receiving clinical team and subject match | RECEIVED; care handover evidence |
| task.accept_handover | Task | Eligible successor; task/subject scope; actual acceptance | New accepted owner; previous authorship retained |
| result.acknowledge | DiagnosticReport | Responsible privileged reviewer; current report version | Actual acknowledgement; clinical response task separately required |
| sharing_grant.revoke | SharingGrant | Valid patient/representative/custody authority and reason | Future access stopped; revocation event prioritised |
| return.verify | ReturnVersion | Independent scoped verifier; checks/evidence; expected source version | VERIFIED within recorded scope; snapshot eligibility updated |
| affiliation.decide | Application | Central authorised Directorate; adopted criteria/evidence; reason | Reasoned decision; independent publication/readiness changes |
| entitlement.reserve | EntitlementAllocation | Authorised service; unspent allocation; correct beneficiary; expected balance | Atomic RESERVED; no overspend |
| entitlement.settle | EntitlementReservation | Actual qualifying fulfilment and approved amount | SETTLED once; ledger effects balanced |
| finance.reverse | LedgerGroup | Reason, original group and independent approval | New balanced reversal; original unchanged |
| encounter.complete | Encounter | Signed disposition and assigned/accepted outstanding obligations | COMPLETED encounter; episode/tasks may remain open |
| stay.discharge | AdmissionStay | Clinical authority, reconciled plan/medicines, pending-results owner | Actual discharge; bed and finance effects separately recorded |


The authority derives signer/approver identity, checks current policy/privileges/state and commits record history, audit, task/ledger effects and outbox atomically. Signatures attest actual identity/intent; cryptography cannot establish that a clinical assertion is true. Central affiliation commands are online central decisions even when inspection capture occurred offline.

## Query and exchange behaviour

GET resource/list queries derive scope before filtering/counting. Lists support opaque scope-bound cursors, stable ordering, bounded page size (proposed maximum 100), explicit as-of/source freshness and completeness. Patient search requires a permitted purpose and sufficient matching context; it is not a public network directory. Directory queries filter service/population/location/readiness and expose public fields only. Dashboard queries require measure/version/period/scope; exports receive equivalent disclosure controls. Attachments/images use authorised private streams or short-lived scoped access, never a permanent public URL.

Partner exchange uses the adopted FHIR R4/IPS profile, identity crosswalk, consent/purpose and receipt contract in LWH-SPEC-012. Bulk ingestion has per-row outcomes and batch conservation. Webhooks authenticate the provider, timestamp/replay window and event identity, then verify consequential external state where required. Never mark a payment/claim/referral fulfilled merely because an HTTP request was accepted.

## Receipt and error examples

```json
{"operation_id":"synthetic-operation","resource_id":"synthetic-resource","version":4,"execution_state":"LOCAL_COMMITTED","authority_node":"synthetic-facility-node","central_replication":"PENDING","external_confirmation":"NOT_APPLICABLE","audit_ref":"synthetic-audit"}
```

```json
{"error":{"code":"VERSION_CONFLICT","message":"This record changed. Review the current version before continuing.","current_version":5,"retryable":false,"field_errors":[],"correlation_id":"synthetic-trace"}}
```

Codes: AUTH_REQUIRED; ACCESS_DENIED; NOT_FOUND_OR_NOT_PERMITTED; VALIDATION_FAILED (field/rule references); VERSION_CONFLICT; INVALID_TRANSITION; IDEMPOTENCY_KEY_REUSE; AUTHORITY_UNAVAILABLE; POLICY_NOT_ACTIVE; PRIVILEGE_EXPIRED; DEPENDENCY_PENDING; EXTERNAL_STATUS_UNKNOWN; RATE_LIMITED. Use 401/403/404 according to the non-disclosure policy, 409 for state/key conflicts, 412 for failed version precondition, 422 for valid-format domain errors, 429 with bounded retry guidance and 503 for unavailable required authority. Errors preserve drafts and do not include patient details or secrets.

## Verification and implementation handoff

The supplied OpenAPI reference covers capture. Implementers must map each consequential command/query to a typed domain DTO, canonical entity/field IDs and the exact state/permission rules above; a capture success is insufficient. Contract tests include forged metadata, wrong subject/tenant, privilege expiry, invalid units, duplicate request/callback, response loss, remote-authority partition and forbidden export. No endpoint returns demo fixtures when a real dependency fails.

## Supplemental typed command and query contracts

`contracts/command_schemas.json` supplies executable JSON capture/intent schemas for all 15 registered consequential commands. The server still derives actor/privileges, validates actual clinical/financial evidence, checks expected state/version and enforces the guards in this document. A syntactically valid command is not authorisation. `contracts/query_catalogue.json` identifies 15 bounded query families and their scope/freshness contracts. No command creates a clinical signature merely from caller-supplied signer metadata.
