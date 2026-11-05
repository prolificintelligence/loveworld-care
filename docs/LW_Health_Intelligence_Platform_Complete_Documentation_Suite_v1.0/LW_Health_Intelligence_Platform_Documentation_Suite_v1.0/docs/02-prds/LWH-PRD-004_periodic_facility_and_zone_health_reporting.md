---
document_id: "LWH-PRD-004"
title: "Periodic facility, zone and regional health reporting"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Health information lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-SPEC-007", "LWH-SPEC-008", "LWH-OPS-002"]
source_refs: ["LWH-SRC-004", "LWH-SRC-005"]
directive_refs: ["DHS-REQ-001", "DHS-REQ-005", "DHS-REQ-006", "DHS-REQ-016"]
---

# Periodic facility, zone and regional health reporting

## Purpose and service result

Give the Directorate reliable periodic information while reducing duplicate work. Facility activity, zone/community observations and regional coordination are distinct reporting streams with compatible definitions and explicit overlap controls.

**Primary users:** Facility reporting officers, zonal/regional coordinators, reviewers and analysts. **Accountable product/operating owner:** Health information lead. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-004-R001 | Obligation calendar | MUST version expected reporting units, period, due date, indicator set and scope by effective date. | A later zone transfer does not rewrite historical completeness. |
| LWH-PRD-004-R002 | Automatic preparation | MUST prefill from authorised LW EMR/integration data with visible lineage and gaps. | An officer reviews a generated return without retyping known totals. |
| LWH-PRD-004-R003 | Multiple channels | MUST support direct forms, controlled bulk imports and authenticated interfaces. | Imported rows receive equivalent validation and evidence rules. |
| LWH-PRD-004-R004 | Missingness | MUST distinguish nil, unknown, missing, partial, late and not-applicable. | No submission cannot appear as zero illness. |
| LWH-PRD-004-R005 | Separate streams | MUST keep facility encounters, unique patients, community events and ministry population denominators distinct. | A referral appearing at two facilities does not become two unique people. |
| LWH-PRD-004-R006 | Attestation and review | MUST record submitter, source period/version and scoped verification. | Submission alone never produces a verified executive count. |
| LWH-PRD-004-R007 | Correction lineage | MUST preserve submitted versions, reasons and reviewer decisions; recompute affected aggregates. | A revised death count is traceable in old/new snapshots. |
| LWH-PRD-004-R008 | Template reconciliation | MUST reconcile the draft form catalogue with the Director supplied templates before adoption. | Every mandated field is mapped, replaced with rationale or recorded as a gap. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-010 | Reporting home | Expected returns, draft/prepared totals, due/late/partial state | Review prepared return or start manual return | Missing source or outage shows unknown and reconciliation task |
| LWH-SCR-011 | Return editor | Period, reporting unit, indicators, missingness, sources and warnings | Validate, attest, submit or revise | Field/cross-field errors link to exact sections; draft persists |
| LWH-SCR-012 | Zone/region coverage | Expected/received/verified units, community stream and exceptions | Follow up, review or escalate | Partial coverage remains visible in all roll-ups |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

A versioned obligation opens. The facility/local connector prepares eligible totals; the reporting officer checks sources and submits. Validation flags impossible or inconsistent values; the scoped reviewer verifies or returns a correction. Zonal/regional coordinators resolve coverage gaps and add separately labelled community information. The aggregate service updates a versioned leadership snapshot and links concerns to actions.

## Operational responsibilities and exceptions

Facility accountable officers own declared totals; health information reviewers own verification; coordinators own missing-unit follow-up; analysts own aggregate definitions. Proposed default is monthly attested returns with continuous event capture and weekly exception review, adjustable through adopted indicator calendars. A failed connector creates a visible source gap rather than a synthetic zero.

## Offline and integration behaviour

A facility prepares and attests a return locally. The user sees locally submitted versus centrally received/verified states. On reconnect, idempotent submission and version checks prevent duplicate totals. Reporting deadlines use recorded local period/time-zone rules; late arrival is retained accurately.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-004-AT001 | Nil and missing | Submit a nil return for one unit; leave another unsubmitted. | Coverage and zero activity remain distinguishable. |
| LWH-PRD-004-AT002 | Overlapping feeds | Load an EMR extract and an attested return for the same period. | The declared reconciliation policy prevents additive duplication. |
| LWH-PRD-004-AT003 | Historical revision | Revise a verified report after hierarchy changes. | Original scope/version remains reproducible and affected snapshots are corrected. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track expected-unit coverage, on-time submission, verification lag, correction rate and reporting effort per unit. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
