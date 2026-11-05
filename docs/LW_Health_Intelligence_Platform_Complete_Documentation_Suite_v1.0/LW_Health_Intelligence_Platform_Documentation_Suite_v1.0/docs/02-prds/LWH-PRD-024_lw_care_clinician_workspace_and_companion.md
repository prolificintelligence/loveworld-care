---
document_id: "LWH-PRD-024"
title: "LW Care clinician workspace and companion"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Clinical workforce and service owners"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009"]
source_refs: ["PROJECT-002", "PROJECT-003"]
directive_refs: []
---

# LW Care clinician workspace and companion

## Purpose and service result

Give clinicians a focused work tool that reduces preparation/documentation burden while preserving judgment, ownership and usable clinical context. Support duty teams, usual-care relationships and participating facility networks.

**Primary users:** Clinicians, nurses, duty coordinators, supervisors and clinical support staff. **Accountable product/operating owner:** Clinical workforce and service owners. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-024-R001 | Prioritised worklist | MUST show assigned/unclaimed work, urgency source, due obligations, service context and workload. | A clinician can identify the next accountable task without scanning unrelated dashboards. |
| LWH-PRD-024-R002 | Claim and coverage | MUST enforce one current claim owner and valid privileges/capacity for the service. | Concurrent claims do not create two independent treating owners. |
| LWH-PRD-024-R003 | Source summary | MUST prepare an editable summary with provenance, negation, contradictions and pending results. | AI cannot invent an examination or hide an important conflicting fact. |
| LWH-PRD-024-R004 | Drafting and signing | MUST support structured notes, drafts, references and intentional authenticated signing. | Accepting a draft is distinct from signing and releasing an order. |
| LWH-PRD-024-R005 | Result and follow-up | MUST organise due results, plans, recalls and patient communication with accepted handover. | A finished appointment does not close an unresolved result. |
| LWH-PRD-024-R006 | Scheduling and workload | MUST show actual commitments, leave/coverage and limits; optional HR is not required. | Time includes preparation, documentation and follow-up, not only call duration. |
| LWH-PRD-024-R007 | References | MUST retrieve current approved references with source/version and applicability. | Unsupported/expired references are visibly restricted. |
| LWH-PRD-024-R008 | Override and learning | MUST allow authorised clinical override with reason and reviewable audit; no silent model training. | Override informs evaluation without automatically changing policy. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-070 | My work and duty coverage | Prioritised encounters, results, follow-up, handovers and schedule | Claim, acknowledge, organise or request cover | No capacity/expired privileges removes new clinical availability |
| LWH-SCR-071 | Clinical workbench | Correct patient, relevant chart, editable summary, note, orders and references | Assess, document, review, prescribe within privilege or sign | Source conflict and stale draft are visible before consequential action |
| LWH-SCR-072 | Continuity and handover | Pending work, successor, patient contact and review evidence | Hand over, accept, communicate or escalate | Departing clinician remains responsible until the adopted transfer path is completed |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

A qualified clinician enters the correct workspace, reviews real workload and accepts a suitable task. The companion prepares source-linked context and drafts. The clinician assesses, edits, orders/signs under their own authority and sets follow-up. Results and referrals remain in the worklist until action or accepted handover. Supervisors can redistribute workload without erasing clinical authorship.

## Operational responsibilities and exceptions

Clinical supervisors own privileges, coverage and quality; coordinators manage operational load; clinicians own clinical decisions; AI leads monitor correction burden. Administrative or sponsor staff cannot read clinical drafts simply because they manage schedules or funding.

## Offline and integration behaviour

Local clinical worklists, charts, notes, orders, signing, results and handovers run on the facility runtime. Remote work requires actual accepted node authority. AI/reference retrieval falls back to valid local content/manual workflow, and stale drafts require revalidation before signing.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-024-AT001 | Claim race | Two clinicians claim the same local case. | One active owner succeeds and the other sees current state. |
| LWH-PRD-024-AT002 | Draft fidelity | Review a summary with negation and conflicting sources. | The summary preserves source attribution and cannot sign itself. |
| LWH-PRD-024-AT003 | Shift end | End a shift with outstanding results/referrals. | Accepted successor or accountable exception remains visible. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track total clinical minutes, overload, critical omissions, draft correction burden, unreviewed results and accepted handovers. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
