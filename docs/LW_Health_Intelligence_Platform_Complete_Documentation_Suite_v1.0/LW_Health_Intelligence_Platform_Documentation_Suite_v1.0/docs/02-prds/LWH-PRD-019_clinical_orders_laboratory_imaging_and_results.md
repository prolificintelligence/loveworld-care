---
document_id: "LWH-PRD-019"
title: "Clinical orders, laboratory, imaging and results"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Diagnostic services and clinical information leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-SPEC-020"]
source_refs: ["LWH-SRC-009", "LWH-SRC-017", "LWH-SRC-018", "LWH-SRC-020"]
directive_refs: []
---

# Clinical orders, laboratory, imaging and results

## Purpose and service result

Close the loop from a clinical question to a reviewed result and patient follow-up. Diagnostic centres can operate their own local workflow or integrate existing laboratory/radiology systems without losing identity, order or version integrity.

**Primary users:** Ordering clinicians, phlebotomy/laboratory teams, imaging staff, reporting specialists and result reviewers. **Accountable product/operating owner:** Diagnostic services and clinical information leads. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-019-R001 | Order authority | MUST record patient/encounter, requester, service, clinical context, priority and authorisation before release. | An unsigned/unprivileged request cannot become an active order. |
| LWH-PRD-019-R002 | Specimen chain | MUST separate requested test, specimen collection, accession, receipt, rejection and analysis. | Wrong/unlabelled specimens follow a documented rejection/recollection path. |
| LWH-PRD-019-R003 | Result structure | MUST preserve value or coded/text result, units, reference context, method, status, author and source. | A numeric result without required unit/mapping enters review. |
| LWH-PRD-019-R004 | Verification | MUST distinguish preliminary, final, corrected, cancelled and entered-in-error results. | A corrected report retains the earlier report and notifies affected reviewers. |
| LWH-PRD-019-R005 | Critical follow-up | MUST create an owned critical-result task under an approved laboratory/clinical policy and record acknowledgement. | Message delivery is not clinician acknowledgement or patient contact. |
| LWH-PRD-019-R006 | Imaging | MUST link image study/accession, report and authorised image access; protect image metadata. | A study URL cannot bypass patient/recipient authorisation. |
| LWH-PRD-019-R007 | External ingestion | MUST quarantine unmapped identities/codes and uncertain OCR until reviewed. | A scanned external report is not presented as a verified structured fact. |
| LWH-PRD-019-R008 | Closure | MUST track review, clinical response and patient communication obligations. | A final report cannot disappear from the review worklist after discharge. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-055 | Orders and collection | Clinical question, service, patient, priority, specimen/status and instructions | Order, collect, receive, reject or cancel | Mismatch blocks the affected transition and creates reconciliation |
| LWH-SCR-056 | Department workbench | Accession/worklist, result entry, instrument input, verification and report versions | Analyse, verify, sign, amend or release | Unmapped values and failed interfaces stay visible |
| LWH-SCR-057 | Result review | Current/prior results, critical flags, responsible reviewer and patient communication | Acknowledge, act, refer or arrange review | Absent reviewer triggers accepted handover/escalation |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

A clinician signs an order. The department accepts and performs the correct local collection/study workflow. Qualified staff verify and release the report, preserving source and units. The responsible clinician acknowledges and records the clinical response and communication. Amendments reopen the affected obligations. External systems pass through identity/mapping validation and reconciliation.

## Operational responsibilities and exceptions

Department leads own test catalogue, quality controls and result verification; treating teams own clinical response; interface stewards resolve unmatched messages; duty leads cover critical work. Reference ranges/critical limits come from adopted local laboratory policy, not generic AI inference.

## Offline and integration behaviour

Local orders, specimen labels/accessions, departmental worklists, locally connected instruments/PACS, verification, critical-result tasks and printing continue. External reference laboratories remain pending until an actual result arrives. Store-and-forward image/document transfer preserves checksums and receipt state.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-019-AT001 | Identity mismatch | Receive an external result with an unmatched patient/accession. | It is quarantined and assigned for reconciliation. |
| LWH-PRD-019-AT002 | Amended critical result | Correct a previously final clinically significant result. | Prior report remains and review/communication obligations reopen. |
| LWH-PRD-019-AT003 | Offline department | Order, collect, verify and review a local diagnostic test without WAN. | The complete local chain persists and later syncs without duplicate reports. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track turnaround by stage, rejected specimens, unmatched orders/results, amended reports and unacknowledged critical results. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
