---
document_id: "LWH-PRD-005"
title: "Health events, safety reporting and review"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Clinical quality and health information leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009"]
source_refs: ["LWH-SRC-007"]
directive_refs: ["DHS-REQ-005", "DHS-REQ-006", "DHS-REQ-012"]
---

# Health events, safety reporting and review

## Purpose and service result

Capture occurrences early enough for action while separating a reported signal from a verified event. Support both community health notifications and clinical safety learning with purpose-specific confidentiality.

**Primary users:** Facility staff, zonal coordinators, quality reviewers, clinical duty teams and intervention owners. **Accountable product/operating owner:** Clinical quality and health information leads. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-005-R001 | Event categories | MUST version event types, reporting source, occurrence time, location precision and review owner. | A death notification is not automatically a certified cause of death. |
| LWH-PRD-005-R002 | Minimum capture | MUST allow a concise initial notification and subsequent structured completion. | Reporter can preserve an urgent signal without completing an unnecessary long form. |
| LWH-PRD-005-R003 | Review state | MUST distinguish signal, under-review, verified, duplicate, unsubstantiated and closed. | Executive views do not relabel every report as a confirmed disease case. |
| LWH-PRD-005-R004 | Urgency ownership | MUST route time-sensitive work to an actually covered team with acknowledgement/escalation. | No owner/coverage creates an explicit operational exception. |
| LWH-PRD-005-R005 | Privacy purpose | MUST minimise identifiable details and restrict case-level clinical safety review. | A general coordinator cannot retrieve confidential incident narratives. |
| LWH-PRD-005-R006 | Learning | MUST record contributing factors, corrective actions and reviewed learning separately from individual blame. | An incident review yields an accepted action and follow-up. |
| LWH-PRD-005-R007 | Duplicates | MUST relate reports of the same occurrence across community/facility channels without erasing sources. | Multiple notifications can resolve to one reviewed event. |
| LWH-PRD-005-R008 | Statutory interface | MUST preserve jurisdiction-specific external reporting obligations and receipts where adopted. | A ministry notification is not presented as completed government reporting. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-013 | Quick event notification | Category, occurrence, source, minimum context, immediate concern | Submit and see responsible team | Urgent clinical need shows local response route; no fabricated acknowledgement |
| LWH-SCR-014 | Review case | Source reports, evidence, confidentiality, verification and related events | Assign, corroborate, classify, deduplicate or refer | Insufficient evidence stays under review with an owner |
| LWH-SCR-015 | Learning and action | Findings, improvement actions, due dates and outcome checks | Accept action, review evidence, close/reopen | Message delivery alone cannot close an unresolved event |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

A staff member or coordinator records a signal. The duty reviewer acknowledges, checks scope/urgency, links duplicates and verifies what can be established. Required clinical/authority notifications are separately tracked. Findings create intervention or quality tasks. Closure records the disposition and outstanding related obligations; anonymised learning can be published after review.

## Operational responsibilities and exceptions

Clinical duty teams handle immediate patient risk; health information reviewers establish reporting classification; quality leads run learning review; privacy staff handle exposure incidents. Incident counts reflect reporting behaviour and cannot be treated as population incidence without an appropriate case/denominator method.

## Offline and integration behaviour

Local capture and local clinical escalation remain operational. Remote notification is queued with transmission state. Telephone/manual escalation can be recorded with actual recipient/time, and is not inferred from a queued message. Cross-site deduplication occurs after reconnection.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-005-AT001 | Unverified signal | Submit a suspected occurrence with limited evidence. | It is visible as a signal, scoped to the right reviewers. |
| LWH-PRD-005-AT002 | Duplicate notification | Submit linked zone and facility notifications. | One reviewed occurrence retains both sources without inflated counts. |
| LWH-PRD-005-AT003 | Disconnected urgency | Report an urgent event offline. | Local care/escalation proceeds; remote delivery remains honestly pending. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track acknowledgement/review delay, unowned urgent events, duplicate resolution, completed corrective actions and recurrent hazards. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
