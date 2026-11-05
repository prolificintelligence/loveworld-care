---
document_id: "LWH-SPEC-009"
title: "State transitions and business-rule catalogue"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Domain architecture and operations leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-SPEC-003", "LWH-SPEC-010", "LWH-SPEC-011", "LWH-SPEC-017"]
source_refs: []
directive_refs: []
---

# State transitions and business-rule catalogue

## Transition contract

Every transition accepts actor, subject/resource, authority node, purpose, expected version, idempotency key, requested action and evidence. Validate permissions, current state, policy/configuration version and required data; atomically persist revision, audit, task/ledger effects and outbox. Return the new version and actual local/central/external acknowledgement state. A rejected command preserves the user's draft and produces no partial domain effects unless the specified compensation is recorded.

| State family | States / paths | Actor and guards | Effects / exceptions |
|---|---|---|---|
| LWH-STM-001 — Account/grant | INVITED → VERIFIED/ACTIVE → SUSPENDED/REVOKED/EXPIRED | Identity authority; actor verification, grantor authority and validity | Revocation queues to nodes; handover open work; preserve author history |
| LWH-STM-002 — Application | DRAFT → SUBMITTED → SCREENING → EVIDENCE_REVIEW → INSPECTION → RECOMMENDED → DECIDED; CORRECTION_REQUIRED/WITHDRAWN | Applicant submits; reviewers/inspectors attest; Directorate alone decides | Versioned dossier; original evidence immutable; no fee/AI approval |
| LWH-STM-003 — Affiliation | APPLICANT → ACTIVE/CONDITIONAL/REJECTED → RENEWAL_DUE → RENEWED/EXPIRED; SUSPENDED/REMOVED/REINSTATED | Central Directorate, adopted criteria, notices and review authority | Conditions/expiry and publication updated separately; retain continuity/history |
| LWH-STM-004 — Publication | DRAFT → ELIGIBLE → PUBLISHED → RESTRICTED/WITHDRAWN | Registry/publication authority; eligible fields and current decision evidence | Public projection only; withdrawal does not delete source records |
| LWH-STM-005 — Readiness | UNKNOWN → AVAILABLE/CONSTRAINED/UNAVAILABLE → STALE | Local authorised service team; observed time, scope and valid_until | Expiry changes matching; no remote acceptance inferred |
| LWH-STM-006 — Return | DRAFT → SUBMITTED → VALIDATING → VERIFIED; RETURNED_FOR_CORRECTION → REVISED → VALIDATING; WITHDRAWN | Originator submits; independent scoped reviewer verifies | Immutable versions; completeness/timeliness are separate attributes; recompute snapshots |
| LWH-STM-007 — Event review | SIGNAL → ACKNOWLEDGED → UNDER_REVIEW → VERIFIED/UNSUBSTANTIATED/DUPLICATE → CLOSED | Covered duty reviewer; evidence and classification rule | Urgent local escalation; related actions remain independently owned |
| LWH-STM-008 — Intervention/task | PROPOSED → ASSIGNED → ACCEPTED → IN_PROGRESS/BLOCKED → EVIDENCE_SUBMITTED → REVIEWED_COMPLETE; REOPENED/CANCELLED | Resource/owner authority; completion reviewer and required evidence | Unaccepted/overdue work remains on exception board; delivery not completion |
| LWH-STM-009 — Content | DRAFT → IN_REVIEW → APPROVED → PUBLISHED → REVIEW_DUE/EXPIRED/WITHDRAWN; CORRECTED | Qualified clinical/editorial/policy approval and applicability | Versioned cache withdrawal/correction; expired rules do not execute |
| LWH-STM-010 — Care episode | OPEN → ROUTED → OWNED → ACTIVE_CARE → FOLLOWUP_PENDING → RESOLVED/TRANSFERRED; CANCELLED | Clinical owner, approved scope and accepted successor where transferred | Underlying tasks/results persist; chat ending not clinical resolution |
| LWH-STM-011 — Encounter | PLANNED/ARRIVED → TRIAGED → ASSIGNED → ACKNOWLEDGED → IN_PROGRESS → COMPLETED; CANCELLED/TRANSFERRED | Local care authority; valid clinician privilege and signed disposition | Pending obligations assigned before completion; payment independent |
| LWH-STM-012 — Clinical document | DRAFT → READY_FOR_REVIEW → SIGNED → ADDENDUM/CORRECTION; ENTERED_IN_ERROR | Actual author/privileged signer, expected version and intent | Signed version immutable; derived summaries invalidated; correction never erases history |
| LWH-STM-013 — Appointment | REQUESTED → HELD → CONFIRMED → ARRIVED → FULFILLED; EXPIRED/CANCELLED/NO_SHOW | Schedule authority; slot/resource capacity; accepted service | Hold expires safely; retry cannot overbook; external request not confirmation |
| LWH-STM-014 — Clinical order | DRAFT → SIGNED → RELEASED → ACCEPTED → IN_PROGRESS → FULFILLED; REJECTED/CANCELLED/ON_HOLD | Privileged requester and performing department; valid policy/current version | Cancel after performance records actual execution; tasks/results retain owners |
| LWH-STM-015 — Specimen | REQUESTED → COLLECTED → RECEIVED → ACCEPTED/REJECTED → ANALYSED → DISPOSED/RETAINED | Competent collector/department; identity, label, source and actual times | Recollection/exception task; no inferred collection from order |
| LWH-STM-016 — Diagnostic report | DRAFT/PRELIMINARY → VERIFIED → FINAL → CORRECTED; CANCELLED/ENTERED_IN_ERROR | Department verifier and source evidence; units/status/match validated | Critical review tasks and amendments propagate; final does not mean clinically reviewed |
| LWH-STM-017 — Medication order | DRAFT → SIGNED/ACTIVE → ON_HOLD/RESUMED → COMPLETED/STOPPED; CANCELLED/ENTERED_IN_ERROR | Privileged prescriber; complete dose/route/timing and applicable checks | Changes create new intent/version; past administration preserved |
| LWH-STM-018 — Dispense | REQUESTED → VERIFIED → RESERVED → DISPENSED; PARTIAL/RETURNED/CANCELLED | Pharmacy authority; actual product/quantity/lot and substitution approval | Stock effect once; dispense is not administration |
| LWH-STM-019 — Administration | DUE → GIVEN/NOT_GIVEN/HELD/REFUSED; ENTERED_IN_ERROR via correction | Current order, correct patient, competent actor and actual event/omission reason | Idempotent event; no last-write-wins or deletion of actual event |
| LWH-STM-020 — Stay/bed | ADMISSION_ORDERED → AWAITING_RECEIPT → ADMITTED → TRANSFER_PENDING/IN_WARD → DISCHARGED/OTHER_DISPOSITION | Local ward authority; actual receiving team, occupancy and disposition | Unique active exclusive bed; pending results/follow-up survive discharge |
| LWH-STM-021 — Procedure | PLANNED → PREASSESSED → AUTHORISED_READY → IN_PROGRESS → RECOVERY → HANDED_OVER/COMPLETED; HELD/CANCELLED | Privileged team; consent/authority, readiness and actual safety phases | Actual performed/specimen/device record; recovery owner; no inferred performance |
| LWH-STM-022 — Transfusion | ORDERED → LAB_AUTHORISED → UNIT_VERIFIED → STARTED → COMPLETED/STOPPED; REACTION_REVIEW | Clinical/blood-bank/nursing roles; matching/component and approved checks | Unit/recipient traceability, actual monitoring/reaction and clinical response |
| LWH-STM-023 — Referral | DRAFT → REQUESTED → ACKNOWLEDGED → ACCEPTED/DECLINED → DEPARTED → RECEIVED → OUTCOME_RECORDED → CLOSED | Sender/receiver clinical authority, permitted summary and actual acceptance | Decline/unreachable retains sender; outstanding tasks explicitly transferred |
| LWH-STM-024 — Sharing grant | REQUESTED → AUTHORISED → ACTIVE → EXPIRED/REVOKED/RESTRICTED | Valid patient/representative/other authority; recipient/purpose/scope | Future access stops; retained clinical copies follow policy; offline lag recorded |
| LWH-STM-025 — Entitlement | AVAILABLE → RESERVED → FULFILLED/SETTLED; RELEASED/EXPIRED/REVERSED | Finance/allocation authority; service evidence and balance constraint | Atomic no-overspend; offline allowance allocated to one node |
| LWH-STM-026 — Invoice/payment | DRAFT → ISSUED → PART_PAID/PAID; ADJUSTED/VOIDED; payment INTENT → PENDING → CONFIRMED/FAILED → REFUNDED | Care finance/provider/cash evidence; maker-checker for adjustments | Balanced immutable ledger effects; pending never settled |
| LWH-STM-027 — Payer claim | DRAFT → SUBMITTED → ACKNOWLEDGED → ADJUDICATED/REJECTED → REMITTED/UNDER_REVIEW | Payer contract/receipt authority; exact claim version | Submission, approval and cash receipt distinct; appeal trail preserved |
| LWH-STM-028 — Sync item | LOCAL_COMMITTED → QUEUED → SENT → RECEIVED → APPLIED/DUPLICATE/CONFLICT/QUARANTINED/PENDING_DEPENDENCY | Authenticated node/epoch/sequence; hash, ownership, version and dependencies | Per-item semantic receipt; failures owned; no blanket batch success |
| LWH-STM-029 — Country/service activation | DRAFT → REVIEWED → EVIDENCE_READY → AUTHORISED → ACTIVE → RESTRICTED/PAUSED/RETIRED | Named Directorate/country clinical/privacy/technical/finance owners | No global clinical coverage from design; updates can require re-review |
| LWH-STM-030 — Optional ERP transaction | DRAFT → REVIEWED → APPROVED → POSTED/PAYMENT_REQUESTED → RECONCILED; REVERSED | Module/country rules and segregation of duties | Core care independent; external payment/filing requires actual confirmation |


## Independent axes

Affiliation, licence evidence, publication, service capability, readiness and reporting obligation remain independent. Clinical encounter, episode, document, order, task, referral and financial state also remain independent. Combined screen labels are projections and cannot replace those underlying facts. Return completeness (nil/partial/complete/unknown) and timeliness (on-time/late) are attributes rather than mutually exclusive workflow states.

## Concurrency and irreversibility

Use expected-version checks for mutable aggregates, unique claim/occupancy constraints and idempotency for retried operations. Signed notes, actual administrations, performed procedures, source reports and ledger entries are append-only facts with attributed correction/reversal. A new version cannot erase an already observed act. Conflicting clinical changes enter a qualified review task. Last-write-wins is prohibited for these consequential records.

## Deadlines, escalation and cancellation

Deadlines are versioned configuration with time zone and staffed coverage. At breach, create an accountable escalation and truthful user update; do not close work simply to improve a metric. Cancellation checks performed work, reserved capacity/funds, pending results and patient communication. Withdrawal/closure triggers accepted handover and records custody; it does not delete history. Known restrictions apply immediately at the node that knows them; offline propagation and authority expiry follow LWH-SPEC-017.

## Verification

For each state family test every allowed transition plus wrong role, wrong subject, expired policy/privilege, wrong version, duplicate request, missing evidence, reversed event order and outage. Side effects must be exactly accounted for even when delivery is at-least-once. Acceptance cases reside in each PRD and the integrated UAT pack; the delivered catalogue is a design contract, not a claim those tests passed.
