---
document_id: "LWH-PRD-006"
title: "Data validation, verification and stewardship"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Health information stewardship lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009"]
source_refs: ["LWH-SRC-005"]
directive_refs: ["DHS-REQ-006", "DHS-REQ-012"]
---

# Data validation, verification and stewardship

## Purpose and service result

Turn submitted data into trustworthy information through visible checks, source review and reversible corrections. Automated validation assists reviewers without certifying the underlying clinical truth.

**Primary users:** Data stewards, facility officers, regional reviewers, analysts and integration operators. **Accountable product/operating owner:** Health information stewardship lead. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-006-R001 | Validation layers | MUST apply schema, code/unit, temporal, arithmetic, cross-field and historical consistency checks. | A count cannot be negative or exceed its applicable total without a defined exception. |
| LWH-PRD-006-R002 | Severity | MUST distinguish blocking errors, review warnings and informational findings. | A warning override requires a reason and reviewer attribution. |
| LWH-PRD-006-R003 | Source verification | MUST record evidence examined, method, scope and verifier. | Verified means the named check was performed, not universal accuracy. |
| LWH-PRD-006-R004 | Stewardship queue | MUST assign duplicate, unmapped-code, missing-source and conflicting-data cases. | A failed import cannot silently drop invalid rows. |
| LWH-PRD-006-R005 | Corrections | MUST preserve raw source, corrected value, reason, author and downstream impact. | An analyst cannot edit a signed source note through a dashboard. |
| LWH-PRD-006-R006 | Reproducibility | MUST version rules, source extracts and aggregation runs. | A historical snapshot can be reproduced with its original definitions. |
| LWH-PRD-006-R007 | Quality visibility | MUST expose completeness, timeliness, verification coverage and limitations next to measures. | A high headline count does not hide poor source coverage. |
| LWH-PRD-006-R008 | Feedback | MUST return actionable findings to the responsible unit and track resolution. | Repeated data-quality failures produce training/improvement work. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-016 | Quality worklist | Blocking/warning cases by source, unit, period and owner | Claim, assign or inspect | Unavailable source has retry and accountable owner |
| LWH-SCR-017 | Source comparison | Raw and interpreted fields, provenance, checks and differences | Verify, request correction or approve explained override | Signed clinical content is read-only here |
| LWH-SCR-018 | Reconciliation run | Input versions, rule version, matched/unmatched/duplicate totals | Publish reviewed result or rerun after correction | Failed run leaves previous snapshot with stale status |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

An ingestion/return creates a validation run. Blocking issues return to the originator; warning cases enter a scoped reviewer queue. A reviewer compares permitted evidence, records a finding and requests or accepts a correction. The revised source creates a new run; only eligible verified values feed the relevant aggregate. Affected actions and dashboards receive correction notices.

## Operational responsibilities and exceptions

Data stewards own mappings and duplicate review; originators correct their source; information leads approve indicator/rule versions; clinical custodians amend clinical records. Repeated overrides are sampled independently. Imported third-party data retains external provenance and confidence.

## Offline and integration behaviour

Local validation uses the pinned rule/code package. Central/cross-unit checks resume after reconnect. No offline node can certify unseen external data; later findings create review tasks without rewriting signed clinical facts.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-006-AT001 | Invalid batch | Import rows with invalid units and one valid row. | Row-level outcomes and reconciliation totals account for every input. |
| LWH-PRD-006-AT002 | Late correction | Correct a previously verified value. | Original version remains and impacted aggregates are regenerated. |
| LWH-PRD-006-AT003 | Rule change | Run an extract under two rule versions. | Differences are explainable and old evidence remains reproducible. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track blocking errors, warning overrides, unmapped codes, source verification coverage and unresolved reconciliation age. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
