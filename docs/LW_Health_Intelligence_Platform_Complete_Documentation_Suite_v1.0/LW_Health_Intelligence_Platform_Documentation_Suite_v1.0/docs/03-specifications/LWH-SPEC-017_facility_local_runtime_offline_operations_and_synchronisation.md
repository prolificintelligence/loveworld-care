---
document_id: "LWH-SPEC-017"
title: "Facility local runtime, full offline care and synchronisation"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Facility runtime architect and clinical operator"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-ARC-001", "LWH-SPEC-003", "LWH-SPEC-009", "LWH-SPEC-011", "LWH-SPEC-015", "LWH-OPS-006"]
source_refs: ["PROJECT-003", "LWH-SRC-025", "LWH-SRC-026", "LWH-SRC-027"]
directive_refs: []
---

# Facility local runtime, full offline care and synchronisation

## Mandatory offline scope

LWH-DEC-112 requires all enabled core clinical operations to continue locally during WAN/internet outage. This is a facility runtime requirement, not a browser-cache feature. The qualified facility package includes local API/domain services, relational database, identity/permission verification, protected documents, active chart data, local terminology/forms/rule packages, work queues, print services, required department/device adapters, audit/outbox, monitoring and backup/recovery. Local users reach it through the facility LAN using stable protected origins.

| Workflow | Locally operational capability | Boundary / honest dependency status |
|---|---|---|
| Registration/chart | Search local charts; issue provisional/site-qualified IDs; update attributed demographics; print | Unseen remote history stays unavailable; central identity links await reviewed matching |
| Triage/encounter | Record observations, assess, assign, document, order, sign and disposition locally | Cloud AI/video/external advice cannot be assumed available |
| Admission/ward | Admit, allocate local bed, record rounds/nursing/MAR and hand over shifts | Other-site bed acceptance must be actually obtained |
| Diagnostics | Local order, label, collect, accession, instrument/local department result, verify and review | External reference laboratory remains pending; imported results require match |
| Imaging | Locally qualified acquisition/archive/view/report and authorised local access | Remote archive/studies inaccessible unless valid authorised local replicas exist |
| Medication | Local formulary, prescribing, verification, dispensing, administration/omission and reconciliation | Unavailable/expired checking service uses adopted manual clinical process; no invented safety result |
| Clinical stock | Lot/expiry/quarantine and actual movements with local balance | No concurrent spend of remote stock or unallocated shared benefits |
| Maternal/child | Programme records, labour/birth/newborn IDs, local reviews/immunisation and follow-up | Automated schedules/clinical rules require current applicable local package |
| Procedure/anaesthesia/transfusion | Actual checks, consent/authority, local records/monitoring, units/devices and recovery handover | External supply/consultation unavailable remains explicit; local equipment/power readiness required |
| Referral/sharing | Prepare permitted package; record actual phone/manual acceptance and local handover | Queued request is not receiving acceptance or completed electronic disclosure |
| Discharge/follow-up | Reconcile plan/medicines; sign and print; retain responsible pending-result tasks | External message delivery/appointment acceptance stays pending |
| Care finance | Local approved tariff, charge/invoice, cash receipt, allocations and controlled adjustments | Bank/card/payer settlement requires actual confirmation; offline benefit allocation must be prebounded |
| Reporting | Prepare/attest local return; run local validation and record events | Central receipt/verification and cross-unit dedup occur later |
| Optional ERP | Core care remains independent; optional local ERP only if separately qualified | Bank payment/statutory filings/supplier confirmations remain actual external dependencies |


“All core operations” refers to the enabled facility's actual local clinical workflows. It does not make unreachable external organisations, remote data, card networks, cloud AI or equipment operational. Qualification records each department and dependency. A newly arriving patient can be treated under a provisional local identity without pretending remote records are present.

## Write authority and partition model

One node/epoch is authoritative for each clinical/financial aggregate. Normally the facility runtime owns facility encounters, orders, results, administrations, local beds and stock. Remote users submit commands to that authority; if unreachable, the request is pending and cannot be presented as a committed clinical change. Other facilities can create their own encounters with attributed source facts and later reconcile the authorised identity/continuity links. A global patient identity does not create one unrestricted multiwriter clinical document.

Central services remain authoritative for central affiliation decisions and shared global control. Inspection/report drafts can be captured offline; recognition cannot be granted by a disconnected facility. Country/custodian policies determine permitted replication locations and data minimisation. The cloud holds authorised replicas/projections, not an uncoordinated competing writer for the same facility record.

## Local commit protocol

Validate identity/grant/privilege, patient context, current aggregate version, state and applicable policy. In one transaction write the current domain result, immutable revision, related clinical tasks/stock/ledger effects where transactionally owned, protected audit and outbox event. Acknowledge LOCAL_COMMITTED only after qualified durable storage commit. The response includes authority, version and replication state. Uploads use private staged objects, checksums and transactional references; a missing object cannot be labelled a complete signed package.

Client retries reuse operation identity. Unique constraints prevent duplicate administrations, receipts, stock movements and claim effects. Expected versions prevent silent concurrent edits. The local runtime continues during WAN loss; a bedside device isolated from that runtime uses a separate documented contingency, not an independent unsupervised dose writer.

## Authentication and valid reference packages

Provision staff and bounded role/privilege packages before disconnection. Local authentication supports strong local factors/verifiers and service certificates without online email/introspection. Known suspensions/expiry apply; clock rollback never extends validity. A delegated local authority can issue only adopted, time-bounded duty/emergency grants with reason/evidence and review. It cannot manufacture professional registration or unrestricted network privileges.

Reference packages include approved schema/form versions, service policies, terminology/formulary, clinical protocols/schedules, trust keys and user-facing guidance, with hash/signature, issuer, applicability, effective/expiry and rollback. Package updates are atomic and preserve old versions needed to interpret records. Expired automated guidance is disabled; competent clinicians use the adopted manual clinical process and document decisions rather than receive a fabricated check. Qualification tests policy/credential expiry within an outage, not only a well-provisioned happy path.

## Synchronisation protocol

1. Authenticate both nodes and establish permitted custodian/subject/data scope, authority epochs and package capabilities.
2. Exchange receipt/high-water metadata and known urgent revocations/corrections without leaking unrelated records.
3. Transfer outbox envelopes with origin/epoch/sequence, event/entity version, dependencies and integrity metadata. Large objects transfer resumably with verified hashes.
4. Receiver records the envelope durably, deduplicates and validates authority, schema, grant context, references and expected domain version.
5. Apply eligible effects once, or return DUPLICATE, CONFLICT, QUARANTINED, REJECTED_WITH_REASON or PENDING_DEPENDENCY. Retain raw source evidence safely for review.
6. Sender stores per-item semantic receipts. Transport success is not semantic application. Every batch input is accounted for; unresolved items have owners/retry/review.
7. Recompute permitted reporting/projections from accepted source versions; reconcile finance/stock/clinical obligations before declaring recovery complete.

Priority is risk-aware: known access revocations and critical corrections/handovers first, then necessary clinical/reporting/finance records and bulk objects, while respecting dependencies. Sequence receipt may advance while an explicitly tracked item is quarantined; compaction must preserve the raw evidence, receipt history and outstanding review. An identical event ID with a different hash is an integrity incident. No blanket last-write-wins for clinical or financial records.

## Conflict policy

| Conflict | Required handling | Accountable reviewer |
|---|---|---|
| Demographics/self-report | Preserve both source versions; proposed value cannot overwrite verified clinical fact; custodian reviews | Record custodian |
| Signed notes/addenda | Append source attestation and correction lineage; never replace signed text | Clinical records owner |
| Order change/stop versus execution | Retain actual chronology and both sources; flag stale/conflicting execution for urgent clinical reconciliation | Duty clinician/medication lead |
| Medication administrations/stock | Idempotency and source event uniqueness; conflicting actual events remain evidence, not last-write-wins | Nursing/pharmacy leads |
| Bed/stay | Enforce local occupancy atomically; cross-facility overlaps are detected/reviewed rather than claiming global partition-proof uniqueness | Ward/clinical information lead |
| Result correction | Preserve old/new report, source status and verifier; reopen review/communication | Diagnostic/treating leads |
| Role/grant revocation | Known restriction applied immediately; reconcile acts under prior valid bounded offline authority with reasoned review | Privacy/clinical governance |
| Finance/entitlement | Balanced append-only effects, node-specific allocation, duplicate proof and reversal rather than overwrite | Finance reconciler |
| Facility/report/hierarchy | Effective-date and version reconciliation; no silent rewriting of earlier reporting scope | Network/information steward |


Late-arriving evidence of actual care is preserved even when its authority is disputed. It may remain restricted/quarantined and require clinical governance review rather than being discarded or silently promoted into current verified truth. Source occurred/recorded times and clock uncertainty remain visible. A reviewer documents current clinical interpretation and follow-up; a technical synchroniser cannot decide medicine conflicts.

## Recovery, fencing and site loss

WAN, LAN, power, storage, identity, malware and site-loss events are separate. Provide qualified UPS, encrypted backups, capacity monitoring and facility-appropriate redundancy. Failover must fence the old writer before promoting a new authority epoch. Restoring a backup never reuses a sequence/epoch in a way that overwrites newer events. A disconnected old node returning after replacement is quarantined/reconciled, not allowed to resume competing writes.

Proposed qualification uses a 72-hour WAN outage at adopted facility load, process restart, department operations, expiry/role changes and full reconnection. Actual outage tolerance/RPO/RTO is adopted by facility class. No zero offsite RPO is promised for a partition plus total site loss without an independent reachable protected copy. Manual recovery reconstructs actual care and outstanding obligations with attribution; it does not invent missing clinical acts.

## Acceptance matrix

Pass complete outpatient, inpatient, maternity/newborn, diagnostic, medicine, procedure, billing and discharge journeys with WAN disabled and cloud AI off. Verify local persistence after restart; no duplicate doses/receipts/stock after retry/replay; accepted handovers; correct local/cached-remote freshness; certificate/credential expiry handling; conflict queues and per-item accounting. Reconnect with duplicate/out-of-order events and late corrections. Clinical, data, finance and technical owners review the reconciled result before incident closure.
