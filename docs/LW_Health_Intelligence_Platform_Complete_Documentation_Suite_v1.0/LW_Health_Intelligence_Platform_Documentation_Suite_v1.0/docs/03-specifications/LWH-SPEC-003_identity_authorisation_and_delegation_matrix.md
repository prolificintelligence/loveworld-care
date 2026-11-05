---
document_id: "LWH-SPEC-003"
title: "Identity, authorisation and delegation matrix"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Security and privacy architects"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-GOV-001", "LWH-SPEC-016", "LWH-SPEC-017"]
source_refs: ["LWH-SRC-009", "LWH-SRC-024"]
directive_refs: []
---

# Identity, authorisation and delegation matrix

## Policy decision

Authorise every command/query/export/attachment/event subscription at the authoritative API and data boundary. Evaluate actor status, role/grant validity, resource ownership, organisation/facility scope, subject, purpose, treatment/delegation relationship, professional privileges, jurisdiction, policy version and field sensitivity. Default deny. Cache keys include subject, actor/grant, purpose, scope and version; role changes invalidate caches.

| Role | Scope predicate | Permitted actions | Boundary |
|---|---|---|---|
| Patient | Own subject and valid grants | Read own permitted records; request care; authorise sharing; correct demographics/self-reports | Cannot sign clinician record, verify affiliation or see another adult by family label |
| Authorised caregiver | Explicit subject/field/purpose/time scope | Act for permitted dependant tasks and sharing | Relationship label alone grants no access; age/legal changes re-evaluated |
| Clinician | Privileged service/facility + treating relationship | Assess, order, sign, review results and hand over | No general cross-facility chart browse; expired privileges block new consequential acts |
| Nurse/midwife | Assigned clinical role and service privileges | Record care/observations; administer; hand over; applicable midwifery actions | Prescribing/independent assessment only where specifically privileged |
| Pharmacy/dispensing | Assigned facility medication service | Verify/dispense/substitute under policy; stock and reconciliation | No unsupported prescription changes or unrelated narrative access |
| Laboratory/radiology | Assigned diagnostic service/order | Collect, analyse, verify/release applicable results | No unrelated patient notes; validation/signing restricted by role |
| Registration/ward clerk | Assigned facility administration | Match/register demographics; operational ADT steps | No clinical signing or unrestricted confidential note access |
| Facility administrator | Own facility and delegated administration | Manage staff invitations/readiness/metadata and reporting | No clinical chart access solely by admin role |
| Reporting officer | Assigned reporting units/periods | Prepare/attest returns and source evidence | Cannot silently self-verify or edit signed clinical source |
| Zone coordinator | Assigned zone and permitted subordinate units | Coverage, community notifications, readiness, actions and permitted aggregates | No raw chart access by organisational seniority |
| Regional coordinator | Assigned region and zones | Regional support/coverage/action and permitted aggregate roll-ups | Cannot make final affiliation decision |
| Inspector | Explicit assigned case/criterion scope | Review evidence; record inspection findings | Cannot alter applicant evidence or approve own conflicts |
| Directorate standards decider | Central approved decision scope | Final reasoned affiliation, renewal and adverse decisions | No general clinical access; adopted separation/review rules apply |
| Data reviewer/analyst | Assigned source/indicator and disclosure scope | Validate/verify returns; approved analysis/snapshots | Clinical evidence only where separately justified and granted |
| Executive viewer | Explicit President/Executive Minister/Directorate view | Permitted strategic aggregates, exceptions and actions | No patient identification/key or sponsor/patient-note backdoor |
| Finance/cashier/claims | Assigned financial entity and transaction role | Charge/receipt/reconcile/claim under maker-checker controls | No unnecessary clinical narratives or self-approved adjustment |
| Sponsor manager | Contracted programme and disclosure view | Eligibility/funding administration and permitted statements/impact | No general notes, diagnoses or beneficiary re-identification |
| Optional HR/payroll/accounting | Contracted optional module and scoped duties | Employment/pay/journal tasks within segregation | No automatic clinical privilege or patient-record access |
| Technical support/service identity | Explicit short-lived task/tool scope | Health diagnostics or validated machine command | No standing human chart access; break-fix access justified/time-bounded/audited |


## Decision algorithm

1. Validate session/service identity, audience, issuer, expiry and current local/central grant context.
2. Resolve authoritative resource scope from storage, never from caller-supplied zone/patient alone.
3. Check organisation membership/delegation and independent clinical privileges where applicable.
4. Check patient/representative authority, treating relationship and purpose for clinical data/actions.
5. Apply record/field limits, confidentiality categories, separation of duties and transition guards.
6. Check offline lease, known revocation/credential expiry, local authority and policy freshness.
7. Allow the minimum action/fields; atomically write decision evidence and domain audit where required.

Patient self-report, caregiver act, clinical attestation, data verification and financial approval are distinct action types. A service account carries a restricted audience, operation set and resource envelope; assistants receive no broader rights than the requesting action allows. Attachment storage and signed/download URLs recheck subject/scope and have short validity.

## Delegation and emergency access

Delegation specifies grantor authority, recipient, actions, resources, purpose, time, delegation depth and conflict restrictions. Expiry/revocation stops future acts; accepted handover preserves open responsibilities. Emergency access is a separately adopted local policy for eligible professionals, with reason, minimum scope, expiry, alert and independent retrospective review. It does not grant global discovery or override known professional suspension automatically.

## Offline enforcement

The local identity service verifies provisioned credentials and bounded role/privilege packages without cloud introspection. Locally granted emergency/duty access follows recorded delegated authority and duration. Revocation cannot be learned from an unreachable cloud; risk is bounded by expiry, minimal replication, known-status checks and mandatory reconciliation. Clock rollback/unknown time cannot extend authority. Sensitive global role/affiliation changes remain central commands, not offline approvals.

## Negative verification

Test direct API object-ID substitution, cross-subject search, regional export, attachment URLs, event subscriptions, sponsor filtering, role simulation flags, privilege expiry, self-approval and stale offline grants. Denied errors reveal no protected content. Audit both successful and denied sensitive actions with protected operational retention. A frontend role switch is never a security control.
