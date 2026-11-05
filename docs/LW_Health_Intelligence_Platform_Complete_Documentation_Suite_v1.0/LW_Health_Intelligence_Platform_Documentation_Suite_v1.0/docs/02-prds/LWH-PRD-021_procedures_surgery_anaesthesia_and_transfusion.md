---
document_id: "LWH-PRD-021"
title: "Procedures, surgery, anaesthesia and transfusion"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Facility procedural services and clinical safety leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-GOV-002", "LWH-SPEC-019"]
source_refs: ["LWH-SRC-015", "LWH-SRC-014"]
directive_refs: []
---

# Procedures, surgery, anaesthesia and transfusion

## Purpose and service result

Provide an accountable clinical record for procedures and high-risk treatment, including preparation, consent, team checks, anaesthesia/recovery and transfusion traceability. Enable these capabilities only at appropriately privileged and ready facilities.

**Primary users:** Procedural clinicians, surgeons, anaesthesia teams, nurses, blood-bank staff and receiving ward teams. **Accountable product/operating owner:** Facility procedural services and clinical safety leads. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-021-R001 | Clinical plan | MUST link procedure indication, patient, encounter, responsible team, site/context and approved privileges. | A facility without the service capability cannot publish the procedure as available. |
| LWH-PRD-021-R002 | Consent and preparation | MUST record applicable consent/authority, pre-assessment, required investigations and readiness checks. | A checklist does not substitute for the clinician assessment or valid authority. |
| LWH-PRD-021-R003 | Safety phases | MUST support team verification before anaesthesia/procedure, before incision/intervention and before leaving the room as applicable. | Each required phase records actual participants, findings and exceptions. |
| LWH-PRD-021-R004 | Procedure record | MUST capture actual procedure, times, findings, specimens, implants/devices, complications and operator attestation. | Planned procedure is not automatically recorded as performed. |
| LWH-PRD-021-R005 | Anaesthesia and recovery | MUST support the approved local anaesthesia record, monitoring, medicines and recovery handover. | Required intra-procedure documentation remains locally usable offline. |
| LWH-PRD-021-R006 | Transfusion chain | MUST link clinical order, specimen/crossmatch evidence, identified component/unit, checks, issue, actual transfusion and reaction monitoring. | AI cannot certify compatibility or substitute the blood-bank authorisation. |
| LWH-PRD-021-R007 | Traceability | MUST retain component/implant identifiers, stock/disposition and recall links. | A recalled item can be traced to actual recipient records within authorised scope. |
| LWH-PRD-021-R008 | Handover | MUST transfer postoperative/procedure obligations, analgesia/order plans, pending specimens/results and complications to an accepted team. | Recovery departure cannot orphan follow-up. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-061 | Procedure preparation | Plan, privileges, patient/site confirmation, consent, investigations and readiness | Schedule, assess, confirm team or hold with reason | Missing required evidence produces an owned hold/exception |
| LWH-SCR-062 | Procedure and transfusion record | Actual safety checks, operative/anaesthesia data, specimens, devices and units | Record, attest, monitor, react or stop under clinical authority | Mismatch/unknown evidence stops automatic confirmation and triggers local clinical review |
| LWH-SCR-063 | Recovery and handover | Current condition, orders, complications, pending results and recipient | Accept handover, arrange review or escalate | Unaccepted responsibility stays with originating team |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

A privileged team plans the procedure, verifies authority/readiness and documents preparation. Team safety phases occur and are attested at the actual point of care. The procedure, anaesthesia or transfusion record captures what occurred. Recovery and ward teams explicitly accept responsibility, and specimens/results/reviews remain tracked. Deviations and adverse events enter clinical quality review.

## Operational responsibilities and exceptions

Service directors own privileges/equipment; clinical teams own assessments and actual care; blood-bank staff own compatibility evidence and unit release; nursing/recovery teams own monitoring and handover. Source-informed checklist structure is locally reviewed and licensing/attribution checked before reproduction or adaptation. No clinical scoring, dose or compatibility algorithm is invented here.

## Offline and integration behaviour

Preparation, clinical documentation, safety phases, local blood-bank/stock interfaces, monitoring capture and handover run locally. External blood supply, remote advice or reference results remain explicitly unavailable/pending. Power/device failure invokes procedural contingency independently of WAN status.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-021-AT001 | Unperformed plan | Cancel a scheduled procedure. | No performed procedure, used implant or transfused component is fabricated. |
| LWH-PRD-021-AT002 | Unit mismatch | Present a blood component inconsistent with the recorded authorised chain. | No automated confirmation; local clinical/blood-bank review is required. |
| LWH-PRD-021-AT003 | Offline procedure | Record a complete procedure and postoperative handover during WAN outage. | Local documentation and responsibility remain intact and sync preserves original attestations. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track safety-phase completion, procedural cancellations, specimen/result follow-through, traceability gaps, adverse events and accepted recovery handovers. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
