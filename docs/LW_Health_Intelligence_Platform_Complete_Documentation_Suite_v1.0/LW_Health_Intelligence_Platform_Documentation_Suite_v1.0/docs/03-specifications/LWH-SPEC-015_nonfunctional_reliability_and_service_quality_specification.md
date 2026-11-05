---
document_id: "LWH-SPEC-015"
title: "Reliability, performance and service-quality specification"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Platform reliability and service operations leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-SPEC-017", "LWH-ENG-003", "LWH-OPS-005"]
source_refs: ["LWH-SRC-022", "LWH-SRC-027"]
directive_refs: []
---

# Reliability, performance and service-quality specification

## Qualification objectives

The following are proposed engineering qualification targets, not existing SLAs or clinical response promises. Actual facility class, capacity, recovery and support obligations are adopted before pilot activation. Clinical response windows require clinical operations/staffing decisions and are not inferred from API latency.

| Area | Proposed requirement / test | Evidence and limitation |
|---|---|---|
| Local chart/worklist | p95 ≤2 seconds at adopted facility load over qualified LAN | Measure cold/warm and large charts, not only empty fixtures |
| Local clinical mutation | p95 ≤1 second for ordinary structured commit excluding large upload | Ack only after durable transaction/audit/outbox; observed slow tail reported |
| Central ordinary tasks | p95 ≤3 seconds for bounded queries at adopted load | External/long-running work gets truthful async state |
| Load profiles | Qualify small clinic and inpatient/diagnostic facility profiles from actual staff/throughput | No global capacity claim from one laptop benchmark |
| WAN loss | All enabled core local clinical journeys complete during proposed 72-hour qualification partition | Actual supported duration/configuration adopted; dependencies and package validity tested |
| Crash durability | No acknowledged transaction loss on process restart with qualified storage | Site/hardware loss is a different recovery case |
| Duplicate delivery | No duplicate domain effect in defined retry/replay suite | Idempotency and ledger/stock/administration invariants |
| Sync recovery | Every queued event accounted as applied/duplicate/conflict/quarantine/pending | Backlog drains within adopted workload/bandwidth recovery budget |
| Local hardware recovery | Proposed ≤15-minute recovery for qualified redundant inpatient profile | Manual clinical continuity begins immediately; no unsupported HA claim |
| Backup/restore | Encrypted database/files/keys/policy restore and reconciliation drill | RPO/RTO selected by facility risk/cost; unreplicated site-loss exposure disclosed |
| Availability | Proposed 99.9% monthly central service target; local clinical target separately risk-assessed | WAN outage does not equal local care outage; scheduled work counted transparently |
| Accessibility | Applicable WCAG 2.2 AA criteria assessed manually/automatically | Keyboard, screen reader, mobile, zoom and cognitive load tested |
| Low bandwidth | Text/core tasks usable without large imagery/video; resumable uploads | Test actual device/network classes and reconnect behaviour |
| Time and locale | Store offset/UTC/source; local reporting periods, DST and date-only facts preserved | Clock skew/rollback and future/late entries tested |
| Portability | Export records, source versions, grants, audit and code mappings in usable documented formats | No silent loss of signed/addendum/financial history |

## Dependency and failure classes

WAN loss leaves the facility LAN runtime operational. Device isolation, local authentication failure, database/storage failure, LAN outage, power failure, ransomware and whole-site loss each have separate detection and runbooks. External AI, remote records, reference laboratories, payer/card settlement, ambulance dispatch and remote referral acceptance cannot be guaranteed by a local database. Show actual pending/unavailable states and continue locally feasible care under approved contingency.

## Capacity and recovery design

Measure registered/active charts, concurrent users, department devices, write rate, peak reporting load, documents/images, retention growth, sync backlog and downtime workload. Size local compute/storage, UPS, backup media and redundancy accordingly. Reserve capacity for urgent work and reconciliation. A backup is not successful until a clean restore validates keys, files, referential integrity, open obligations and financial/stock totals.

During a WAN partition, a later catastrophic site loss can lose unreplicated data unless an independent reachable protected copy exists. Do not promise zero offsite RPO under that condition. Adopt and disclose the facility's physical redundancy/backup strategy and clinical paper/recovery plan. Fencing prevents competing local primaries; disaster failover must preserve write-authority epochs.

## Monitoring and acceptance

Track local/central health independently: latency, errors, storage, backups, clock, certificate/package expiry, outbox age, semantic conflicts and overdue clinical tasks. Alert an accountable team; avoid leaking clinical details into general telemetry. Qualify complete journeys under realistic load, crash/restart, power/LAN/WAN loss, retries and restore. Unresolved wrong-patient, unsafe state, financial/stock integrity or lost-care defects block the affected release.
