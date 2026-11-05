---
document_id: "LWH-PRD-003"
title: "Affiliation, inspection, renewal and noncompliance"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Directorate standards lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-GOV-005", "LWH-OPS-003"]
source_refs: ["LWH-SRC-002", "LWH-SRC-006"]
directive_refs: ["DHS-REQ-003", "DHS-REQ-013", "DHS-REQ-014", "DHS-REQ-018"]
---

# Affiliation, inspection, renewal and noncompliance

## Purpose and service result

Make recognition meaningful through published criteria, evidence, independent review and improvement. Final affiliation decisions belong centrally to the Directorate; payment, AI scoring and facility self-declaration do not make a facility recognised.

**Primary users:** Applicants, inspectors, standards reviewers, Directorate decision-makers and appeal reviewers. **Accountable product/operating owner:** Directorate standards lead. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-003-R001 | Applicable criteria | MUST select a versioned criterion set by facility type, services and jurisdiction. | An application retains the criteria used for its decision. |
| LWH-PRD-003-R002 | Evidence provenance | MUST retain original evidence, issuer/source, expiry and verification outcomes. | Reviewer comments never overwrite applicant documents. |
| LWH-PRD-003-R003 | Inspection independence | MUST assign competent inspectors, record conflicts and distinguish observed from self-reported findings. | Conflicted assessors cannot silently approve their own findings. |
| LWH-PRD-003-R004 | Corrective work | MUST give findings, response rights, corrective actions, deadlines and evidence of resolution. | A submitted correction awaits review rather than auto-closing. |
| LWH-PRD-003-R005 | Central decision | MUST restrict approve/conditional/reject/renew/suspend/remove decisions to authorised Directorate roles. | A region reviewer can recommend but cannot activate affiliation. |
| LWH-PRD-003-R006 | Recognition meaning | MUST show exact scope, conditions, effective/expiry dates and separate statutory status. | The public badge cannot imply government accreditation. |
| LWH-PRD-003-R007 | Renewal | MUST schedule reassessment under an adopted calendar and prevent silent expiry extension. | A proposed renewal retains prior decision and current expiry. |
| LWH-PRD-003-R008 | Review and continuity | MUST preserve notices, reasons, response, review/appeal and reinstatement; transfer active care responsibilities. | Suspension does not delete clinical/financial/inspection history. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-007 | Application and evidence | Criteria checklist, source documents, declarations and progress | Save, submit, respond to findings | Incomplete evidence identifies exact gaps and preserves draft |
| LWH-SCR-008 | Inspection and recommendation | Assigned visits, observations, evidence, conflicts and corrective plan | Record finding, request correction, recommend decision | Unverified evidence remains visibly unverified |
| LWH-SCR-009 | Directorate decision and renewal | Review dossier, criteria version, conditions, prior decisions and notices | Approve, condition, reject, renew or impose adopted restriction | Unauthorised/self-conflicted decision is blocked; review path retained |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

An applicant submits a scoped application. Secretariat screens identity/evidence, an inspector records observations, the applicant responds and an independent reviewer recommends a disposition. The Directorate records a reasoned final decision. Eligible publication updates, conditions create owned tasks and expiry creates renewal work. An adverse decision provides notice and review without erasing history.

## Operational responsibilities and exceptions

The standards lead maintains criteria and assessor competence; secretariat coordinates visits; inspectors attest observations; Directorate decides; an appropriately independent reviewer handles challenges. Renewal fees, if later approved, are financially reconciled and do not substitute for evidence. WHO-derived self-assessment tools are used within their stated purpose, not relabelled as official accreditation.

## Offline and integration behaviour

Applicants and inspectors can capture locally and queue evidence with integrity metadata. A central affiliation decision requires the authoritative Directorate service; offline capture cannot create recognition. Facility clinical continuity uses the last accepted status plus any known local protective restrictions.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-003-AT001 | Decision authority | Submit a complete inspected case through a regional reviewer. | Only the central authorised Directorate decision activates affiliation. |
| LWH-PRD-003-AT002 | Expiry and appeal | Expire affiliation and lodge a review request. | Status, publication and review history remain distinct and auditable. |
| LWH-PRD-003-AT003 | Offline inspection | Record findings without WAN and reconnect. | Original evidence and inspector attribution arrive once; no premature approval. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track review turnaround, overdue corrections, renewal coverage, recurrent findings and verified improvement; do not reward approval volume alone. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
