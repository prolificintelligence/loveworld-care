---
document_id: "LWH-SPEC-011"
title: "Events, notifications, durable jobs and integrations"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Workflow and integration architecture lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-SPEC-009", "LWH-SPEC-010", "LWH-SPEC-017"]
source_refs: []
directive_refs: []
---

# Events, notifications, durable jobs and integrations

## Event envelope and delivery

Domain mutations use a transactional outbox. Envelope fields: event_id, event_type/version, origin_node_id, epoch, monotonic node sequence, aggregate_id/type/version, custodian/facility/subject scope, occurrence/recorded times with clock context, correlation/causation, policy version, classification, dependency_refs, payload hash and authorised payload/reference. Recipient inbox deduplicates event_id and origin/epoch/sequence; identical identity/different hash is a security/integrity exception.

Transport is at-least-once; domain effects are idempotent. Receipts distinguish transport-received from applied, duplicate, conflict, quarantined and pending-dependency. Ordering is per origin/aggregate dependency, not globally by wall clock. Retry uses bounded exponential backoff/jitter and an owned dead-letter queue. Replay preserves identity and checks permissions/version rather than bypassing guards.

| Event | Type | Aggregate | Consumers / required effect | Classification / caveat |
|---|---|---|---|---|
| LWH-EVT-001 | identity.grant_changed | RoleAssignment | Revocation/expiry/assignment consumers | Restricted identity; high priority |
| LWH-EVT-002 | network.facility_verified | Facility | Registry, directory eligibility, reporting obligations | Institution metadata |
| LWH-EVT-003 | standards.application_submitted | Application | Secretariat screening and acknowledgement | Private evidence refs only |
| LWH-EVT-004 | standards.finding_recorded | Finding | Applicant response/corrective workflow | Restricted standards |
| LWH-EVT-005 | standards.decision_recorded | AffiliationDecision | Publication, renewal and conditions | Central decision source |
| LWH-EVT-006 | network.readiness_changed | ReadinessAssertion | Matching and local service dashboards | Service metadata; expiry retained |
| LWH-EVT-007 | reporting.return_submitted | ReturnVersion | Validation and central receipt | Protected aggregate/report source |
| LWH-EVT-008 | reporting.return_verified | ReturnVersion | Eligible aggregate recomputation | Verification scope/version |
| LWH-EVT-009 | reporting.return_corrected | ReturnVersion | Invalidate/recompute affected snapshots and summaries | Prior/current lineage |
| LWH-EVT-010 | quality.event_reported | HealthEvent | Covered review/urgent local escalation | Minimum context; case scope |
| LWH-EVT-011 | analytics.snapshot_released | AggregateSnapshot | Permitted leadership refresh | Disclosure-controlled output |
| LWH-EVT-012 | programme.action_assigned | Intervention | Acceptance, due escalation and resource workflow | Scoped institutional work |
| LWH-EVT-013 | programme.action_reviewed | Intervention | Completion/outcome review | Evidence refs; no causal promotion |
| LWH-EVT-014 | editorial.content_changed | ContentVersion | Publish/withdraw/correct local packages | Purpose/version/validity |
| LWH-EVT-015 | clinical.encounter_changed | Encounter | Local worklists, tasks and approved reporting | Protected clinical |
| LWH-EVT-016 | clinical.document_signed | ClinicalDocument | Immutable record index, plan/tasks and permitted exchange | Source version/attestation |
| LWH-EVT-017 | clinical.document_amended | ClinicalDocument | Invalidate summaries, notify permitted recipients | Protected correction priority |
| LWH-EVT-018 | clinical.order_released | ClinicalOrder | Performing local department acceptance | Protected order; no inferred fulfilment |
| LWH-EVT-019 | diagnostic.specimen_changed | Specimen | Department worklists and recollection | Protected patient/order linkage |
| LWH-EVT-020 | diagnostic.result_released | DiagnosticReport | Clinical review and patient communication tasks | Critical flag from adopted policy |
| LWH-EVT-021 | diagnostic.result_amended | DiagnosticReport | Reopen affected review/clinical action | Preserve old/new report |
| LWH-EVT-022 | medicines.order_changed | MedicationOrder | Pharmacy/MAR future-task refresh | Current intent and version |
| LWH-EVT-023 | medicines.dispensed | Dispense | Actual supply/stock and care finance | Not administration |
| LWH-EVT-024 | medicines.administered_or_omitted | Administration | MAR, safety review and applicable stock | Irreversible event; deduplicate |
| LWH-EVT-025 | stock.movement_recorded | StockMovement | Local inventory and optional procurement/accounting adapter | Append-only movement |
| LWH-EVT-026 | inpatient.stay_changed | AdmissionStay | Ward/bed/care transition and billing | Local authority |
| LWH-EVT-027 | clinical.procedure_recorded | ProcedureRecord | Recovery, specimens/devices and care finance | Actual performed event |
| LWH-EVT-028 | referral.state_changed | Referral | Sender/receiver work and transition tracking | Actual acceptance/receipt only |
| LWH-EVT-029 | records.grant_revoked | SharingGrant | Stop future access; priority replica update | Protected authorisation |
| LWH-EVT-030 | care.task_due | Task | Covered owner, escalation and neutral notification | No clinical text in external message |
| LWH-EVT-031 | finance.service_fulfilled | ChargeInvoiceClaim | Benefit settlement and evidence-linked charge | Finance/clinical boundary |
| LWH-EVT-032 | finance.receipt_confirmed | PaymentReceipt | Allocation, reconciliation and optional posting | Actual receipt evidence |
| LWH-EVT-033 | finance.entitlement_changed | EntitlementReservation | Reserve/settle/release and programme statement | Node allocation/ledger source |
| LWH-EVT-034 | platform.sync_outcome | NodeSyncEnvelope | Per-record reconciliation and monitoring | No raw clinical payload in logs |
| LWH-EVT-035 | activation.scope_changed | PolicyPackage | Country/facility capability restriction/activation | Signed authority/version |


## Durable work and scheduling

Jobs include reminder/notification, report opening/due checks, renewal reminders, expired readiness, unaccepted handover, critical result escalation, source correction propagation, content withdrawal, nightly reconciliation and backup/restore verification. Each job has owner, due time/time zone, retry policy, idempotency key, evidence of actual outcome and fallback. Scheduler restarts or clock changes cannot lose clinical obligations. Event replay cannot resend unlimited patient reminders or duplicate fees/stock effects.

## Notification contract

External email/SMS/push uses neutral text and a secure link by default. Distinguish queued, provider accepted, delivered where supported, failed and unknown; do not invent read state. Channel preference/consent and quiet-hour rules apply except the adopted urgent escalation policy. A failed clinically important notification creates an accountable alternative-contact task. Clinical urgency, acknowledgement and completion remain in the work system rather than inferred from delivery.

## Offline priority and integration

Local clinical events/jobs execute during WAN loss. Reconnect prioritises known access revocations, critical corrections/handovers and necessary policy updates, then clinical/reporting/finance data and large objects according to bandwidth. Dependency-aware replay cannot apply a child before its patient/order/grant reference. Large documents/images use resumable checksum-verified private transfer. Interface failure leaves an owned queue and explicit status; no remote fulfilment is manufactured.

## Acceptance

Crash between database commit and publication, duplicate/out-of-order messages, provider timeout, retried callback, expired grant, missing parent and scheduler restart must preserve all committed obligations and exactly accounted domain effects. Test messages/metrics/logs for patient data leakage. Monitor backlog age and semantic failures separately from network throughput.
