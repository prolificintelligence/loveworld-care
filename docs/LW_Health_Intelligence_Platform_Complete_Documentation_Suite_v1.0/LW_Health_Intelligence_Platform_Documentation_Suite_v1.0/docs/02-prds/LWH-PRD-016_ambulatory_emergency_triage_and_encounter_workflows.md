---
document_id: "LWH-PRD-016"
title: "Ambulatory, emergency triage and encounter workflows"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Facility clinical operations lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-SPEC-018", "LWH-OPS-006"]
source_refs: ["LWH-SRC-016", "LWH-SRC-035"]
directive_refs: []
---

# Ambulatory, emergency triage and encounter workflows

## Purpose and service result

Support scheduled, walk-in and urgent care from arrival through assessment and follow-up. Clinical priority and truthful ownership replace opaque waiting, while approved assistance reduces avoidable delays.

**Primary users:** Reception, triage staff, nurses, clinicians, patients and duty coordinators. **Accountable product/operating owner:** Facility clinical operations lead. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-016-R001 | Arrival paths | MUST support booked, walk-in, referred and emergency arrivals with correct patient matching. | An urgent arrival can bypass nonessential administrative completion. |
| LWH-PRD-016-R002 | Triage governance | MUST record observations, source, urgency assessment and assessor under an approved local triage policy. | AI cannot independently certify a low-risk clinical disposition. |
| LWH-PRD-016-R003 | Queue ownership | MUST distinguish arrival, triage, assigned, acknowledged and assessment; capacity is explicit. | Patients/staff see who owns unacknowledged work. |
| LWH-PRD-016-R004 | Structured encounter | MUST support complaint/history, examination, assessment, problems, plan, orders and follow-up with unknowns. | No examination is auto-filled from a conversational summary. |
| LWH-PRD-016-R005 | Privilege checks | MUST check clinician/service/jurisdiction authority at consequential actions. | An expired/unprivileged user cannot sign or prescribe. |
| LWH-PRD-016-R006 | Parallel teamwork | MUST allow role-scoped observations and tasks while protecting signed content and current orders. | Concurrent edits create conflict/review rather than lost clinical facts. |
| LWH-PRD-016-R007 | Disposition | MUST support home plan, observation, admission, referral and emergency transfer with owned obligations. | Encounter completion cannot orphan a pending result. |
| LWH-PRD-016-R008 | Continuity | MUST create clear patient instructions, reminders and responsible review tasks. | A delivered reminder alone does not close clinical follow-up. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-046 | Arrival and triage | Matched patient, arrival reason, observations, urgency and available team | Register arrival, triage or escalate | Uncertain urgency remains reviewable; emergency route is accessible |
| LWH-SCR-047 | Encounter workbench | Longitudinal context, note, assessments, orders, tasks and draft assistance | Document, order, sign or arrange disposition | Conflicts preserve work; no fabricated normal findings |
| LWH-SCR-048 | Care transition | Plan, pending results, referral/admission and patient instructions | Confirm handoff, print/share plan or arrange review | Unaccepted transfer leaves originating accountability |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

A patient arrives through the appropriate path, receives a locally approved triage assessment and is allocated to a qualified team. The clinician reviews context, records findings, orders required work and evaluates results. A signed disposition creates an admission, referral or home plan; pending obligations retain named owners and the patient sees the next step.

## Operational responsibilities and exceptions

Duty coordinators maintain real capacity and escalation routes; triage staff attest urgency; treating clinicians decide clinical disposition. Locally approved response commitments drive overdue alerts. Unknown history or absent measurements remain explicit and do not become default normality.

## Offline and integration behaviour

All local arrival, triage, clinical assessment, local orders, notes, disposition, billing capture and printing continue on the facility LAN. Remote consultation and external referrals show actual dependency status. AI absence never prevents a clinician completing the encounter.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-016-AT001 | Urgent arrival | Register and triage an urgent patient with incomplete demographics. | Essential clinical assessment proceeds with provisional identity and owner. |
| LWH-PRD-016-AT002 | Unowned result | Attempt to complete an encounter with a pending review obligation. | The obligation remains assigned or explicitly handed over. |
| LWH-PRD-016-AT003 | WAN outage | Complete an ambulatory encounter including local diagnostics and discharge plan. | Clinical transactions persist locally and later synchronise once. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track arrival-to-assessment, unacknowledged work, unsafe delays, incomplete handoffs, follow-up completion and patient/clinician effort. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
