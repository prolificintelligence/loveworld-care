---
document_id: "LWH-PRD-007"
title: "Leadership dashboards and institutional intelligence"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Directorate intelligence owner"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-SPEC-007", "LWH-SPEC-014"]
source_refs: []
directive_refs: ["DHS-REQ-007", "DHS-REQ-012", "DHS-REQ-017"]
---

# Leadership dashboards and institutional intelligence

## Purpose and service result

Give each leadership level a concise, decision-relevant view of network health, service delivery, standards and action. Every displayed measure includes enough context to interpret its reliability.

**Primary users:** President authorised viewers, Executive Minister, Directorate, regional/zonal leads and facility leadership. **Accountable product/operating owner:** Directorate intelligence owner. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-007-R001 | Role views | MUST provide distinct leadership, Directorate operational, region, zone and facility defaults. | A senior strategic view is concise; operational users can reach their tasks. |
| LWH-PRD-007-R002 | Measurement contract | MUST display period, unit, denominator, coverage, freshness and definition access. | A rate with unreliable population denominator is withheld or labelled appropriately. |
| LWH-PRD-007-R003 | Verified and provisional | MUST visibly separate verified snapshots, provisional operational signals and forecasts. | A model narrative cannot elevate unverified reports. |
| LWH-PRD-007-R004 | Disclosure | MUST apply purpose/scoped views, small-cell and differencing protections to UI, API and exports. | A CSV cannot bypass a suppressed cell. |
| LWH-PRD-007-R005 | Actionability | MUST link a concern to source evidence, an authorised action and its accountable owner. | A leadership decision can be followed through to reviewed outcome. |
| LWH-PRD-007-R006 | Historical comparison | MUST show hierarchy/definition changes and comparable cohorts. | A region split does not create a false unexplained improvement. |
| LWH-PRD-007-R007 | Unknown states | MUST distinguish zero, missing, stale and unavailable. | Backend failure cannot show a clean zero-demand dashboard. |
| LWH-PRD-007-R008 | Narrative assistance | MUST source-link AI summaries and retain deterministic numeric reconciliation. | Unsupported causal or clinical claims are withheld for review. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-019 | Leadership overview | Network coverage, standards, care access, major exceptions and intervention progress | Select period/scope, inspect definitions or request briefing | Low coverage is prominent; charts do not imply population representativeness |
| LWH-SCR-020 | Directorate operations | Returns, affiliation/renewals, workload, readiness, quality and funding exceptions | Open scoped worklists, assign action or review evidence | Permission denial keeps aggregates visible only where allowed |
| LWH-SCR-021 | Regional/zonal/facility cockpit | Own-unit trends, reporting obligations, readiness, outstanding actions | Follow up units, correct data or accept intervention | Stale data retains last successful timestamp and clear limitations |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

An authorised leader opens a scoped overview, checks period/coverage, explores an exception and views permitted evidence. A decision creates an intervention with owner, resources and review date. Operational owners accept and execute; leadership sees completion evidence and subsequent measures with causal limitations. Corrected source data revises the snapshot transparently.

## Operational responsibilities and exceptions

Information owners maintain definitions and release snapshots; coordinators resolve missingness; programme owners act on findings. President/Executive Minister access is explicitly authorised and aggregate-first. Financial impact, clinical quality and utilisation are shown separately rather than combined into an unexplained score.

## Offline and integration behaviour

A cached approved snapshot is read-only and timestamped. Local facility operational dashboards continue from local clinical data. Cross-network freshness cannot advance until actual ingestion/review completes; offline action drafts are queued for authorised acceptance.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-007-AT001 | Hierarchical scope | Open the same period as facility, zone, region and Directorate users. | Values reconcile to authorised scope and expected-unit coverage. |
| LWH-PRD-007-AT002 | Disclosure export | Attempt small-cell drill-down and repeated filtered exports. | Equivalent protections apply through every delivery channel. |
| LWH-PRD-007-AT003 | Source outage | Break a reporting source and refresh the dashboard. | Unknown/stale state replaces successful-looking zeros. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track decision-to-action completion, metric reconciliation, reporting coverage, stale snapshots, useful briefing task success and disclosure exceptions. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
