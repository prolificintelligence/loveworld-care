---
document_id: "LWH-PRD-017"
title: "Inpatient admission, nursing, transfer and discharge"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Hospital clinical and nursing directors"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-SPEC-017", "LWH-SPEC-018", "LWH-PRD-020"]
source_refs: ["LWH-SRC-008", "LWH-SRC-014"]
directive_refs: []
---

# Inpatient admission, nursing, transfer and discharge

## Purpose and service result

Run continuous inpatient care with a reliable bed/ward view, team responsibility, nursing documentation, medication administration and discharge continuity. Inpatient operation remains locally usable without WAN connectivity.

**Primary users:** Admitting clinicians, ward nurses, ward clerks, pharmacy, departments and discharge coordinators. **Accountable product/operating owner:** Hospital clinical and nursing directors. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-017-R001 | Admission and bed | MUST distinguish admission order, actual admission, bed reservation and occupancy with local concurrency control. | Two simultaneous assignments cannot occupy one exclusive bed. |
| LWH-PRD-017-R002 | Responsible team | MUST assign consultant/duty team, nursing responsibility and shift handover. | Ending a shift does not erase care ownership. |
| LWH-PRD-017-R003 | Nursing care | MUST support observations, nursing assessments, care tasks, fluid/intake-output where appropriate and escalation. | Late-entry observations retain actual observation and recorded times. |
| LWH-PRD-017-R004 | Medication administration | MUST integrate current signed orders and actual administration/omission records. | A dispensed medicine is not automatically marked administered. |
| LWH-PRD-017-R005 | Rounds and orders | MUST show current plans, results, active orders, critical acknowledgements and outstanding work. | A discontinued order cannot remain silently active on a stale task view. |
| LWH-PRD-017-R006 | Transfer | MUST record sender/receiver, ward/bed, time, care summary and accepted responsibility. | Internal or external transfer is not completed merely by requesting it. |
| LWH-PRD-017-R007 | Discharge | MUST reconcile medications, final plan, summary, pending tests, review owner and patient instructions. | A pending result survives discharge and reaches a responsible clinician. |
| LWH-PRD-017-R008 | Special dispositions | MUST handle leave, self-discharge/refusal, death and return according to approved local policy. | Clinical event, bed release, billing and statutory documentation remain separate actions. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-049 | Ward board | Beds, occupancy, responsible team, clinical task/critical result indicators | Admit, reserve, transfer or open patient | Stale data cannot silently confirm a bed reassignment |
| LWH-SCR-050 | Bedside and rounds | Identity, current plan, observations, medicines and outstanding orders | Record care, administer/omit, review or escalate | Wrong patient/version check stops the action and preserves entered work |
| LWH-SCR-051 | Transfer/discharge workspace | Accepted receiver, reconciled medicines, summary, pending results and follow-up | Confirm handover or sign discharge package | Missing acceptance/owner prevents false closure |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

An authorised clinician orders admission; the ward confirms actual receipt and bed allocation. The team records assessments, observations, nursing care, orders and medication administration locally. Shift handovers explicitly transfer tasks. A transfer/discharge plan reconciles records and responsibilities; summaries and pending-result tasks follow the patient while bed and financial states update separately.

## Operational responsibilities and exceptions

Hospital directors own approved inpatient services; duty clinicians own medical plans; nursing leads own bedside workflow and handover; discharge coordinators arrange continuity; finance owns settlement. Discharge is a clinical transition and cannot be suppressed merely because an optional accounting service is unavailable.

## Offline and integration behaviour

ADT, ward boards, clinical notes, local results, MAR, nursing tasks and discharge printing run locally. Bedside clients connect to the local server; isolated-device/LAN failure invokes the documented manual contingency. Central viewers show replication age and cannot independently overwrite bed/MAR truth.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-017-AT001 | Bed race | Assign two admissions to one exclusive bed concurrently. | Exactly one occupancy succeeds; the other receives an actionable conflict. |
| LWH-PRD-017-AT002 | Shift handover | End a shift with due medicines and an unreviewed result. | Accepted successors and unresolved tasks remain visible. |
| LWH-PRD-017-AT003 | Offline admission | Run admission through ward treatment and discharge during WAN loss. | Local care remains complete and sync reconciles with no duplicated administrations. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track occupancy, length of stay with exclusions, delayed discharge, medication omissions, unreviewed results and handover completion. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
