---
document_id: "LWH-OPS-006"
title: "Facility clinical operation, downtime and synchronisation"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Facility clinical director and local technical lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-SPEC-017", "LWH-SPEC-018", "LWH-SPEC-020", "LWH-ENG-004"]
source_refs: []
directive_refs: []
---

# Facility clinical operation, downtime and synchronisation

## Purpose, trigger and staffing

Use for ordinary local care and transition into/out of WAN outage. All enabled core clinical workflows continue on the qualified facility runtime; external dependencies retain honest status.

The accountable owner is **Facility clinical director and local technical lead**. Assign named primary/deputy contacts and staffed coverage at activation. An absence does not remove open responsibility; the adopted handover/escalation remains explicit. Operate only within the applicable country/facility policy, professional privileges and purpose-scoped access.

## Procedure

| Step | Responsible role | Action and decision | Evidence / handoff |
|---|---|---|---|
| LWH-OPS-006-S001 | Duty/local technical leads | Confirm local server, LAN/power, storage, identity/grants, reference packages, departments and backups. | Daily readiness and actual limitations |
| LWH-OPS-006-S002 | Registration/clinical team | Match/register patients, triage/assess and document/sign with patient/privilege checks. | Local chart/encounter and actual owner |
| LWH-OPS-006-S003 | Departments/nursing/pharmacy | Continue orders, local results, wards/MAR, clinical stock and service-specific maternal/procedural work. | Actual events, critical acknowledgements and handovers |
| LWH-OPS-006-S004 | Duty coordinator | On WAN loss announce local-operational state; identify remote data/communication/payment limits. | Outage context and tested alternate contact/manual route |
| LWH-OPS-006-S005 | Clinical/finance teams | Complete locally feasible care, discharge/print and care billing/cash records; retain pending external actions. | No fake remote acceptance, settlement or result |
| LWH-OPS-006-S006 | Local technical service | Preserve durable DB/audit/outbox, monitor capacity/clock/expiry and protect independent backups. | Local commit receipts and health evidence |
| LWH-OPS-006-S007 | Sync/information stewards | On reconnect authenticate authority/epoch, prioritise revocations/corrections and apply dependency-aware replay. | Per-event applied/duplicate/conflict/quarantine outcomes |
| LWH-OPS-006-S008 | Clinical/pharmacy/custody/finance reviewers | Resolve qualified conflicts and reconcile open care, stock, benefits, receipts and reports. | Named decisions, retained actual history and corrected projections |
| LWH-OPS-006-S009 | Facility service owner | Review completion with all affected owners and record residual limitations. | Recovery sign-off; no incident closure from transport success alone |

## Exceptions and continuity

An isolated bedside device cannot independently become a competing MAR writer. Use adopted paper/manual contingency for LAN/power failure, then attribute late entries with actual event times and review duplicate/omitted work. Known professional restrictions apply; a local supervisor cannot invent a licence. Expired automated content falls back to adopted clinician-led manual care, not fabricated decision support. External record/recipient states remain pending until real evidence.

## Records, supervision and review

Retain downtime log, authority/epoch, credential/policy versions, locally committed events, manual forms, actual communication evidence, sync receipts and review decisions. Protect paper and backup media. Incoming source conflicts are evidence to reconcile, not data to overwrite by timestamp.

Preserve actual event and recorded times, actor, source/version, decision, authority and successor acceptance. External delivery does not prove review or fulfilment. Signed/history/ledger records are corrected by addendum/reversal rather than silent overwrite. Patient information is shared only through the permitted purpose and channel; general support/notifications use neutral minimum context.

## Readiness and acceptance

With WAN/cloud AI off, complete outpatient, inpatient, maternal/newborn, diagnostic, medicine, procedure, discharge and care-finance chains. Restart local services, reconnect with duplicates/conflicts and verify every obligation and financial/stock effect. Actual facility users and departments sign qualification evidence.

Train actual roles and deputies through a complete synthetic successful and failed journey. Record observed effort, missed handoffs, source gaps and downtime recovery. Review recurrent exceptions and update the relevant policy/forms/training through controlled change. A runbook is not operationally ready until named staff can execute it with the actual configured contacts and systems.
