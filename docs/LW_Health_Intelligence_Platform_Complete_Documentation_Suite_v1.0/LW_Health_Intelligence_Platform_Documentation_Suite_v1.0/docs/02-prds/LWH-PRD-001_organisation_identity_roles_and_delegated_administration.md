---
document_id: "LWH-PRD-001"
title: "Organisation identity, roles and delegated administration"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Identity and Directorate operations lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009"]
source_refs: []
directive_refs: ["DHS-REQ-010", "DHS-REQ-011"]
---

# Organisation identity, roles and delegated administration

## Purpose and service result

Give every participant an accountable identity and the correct working context. The ministry reporting spine is Region → Zone, with optional lower units and separate geography. A person can hold several valid roles without acquiring unrelated patient access.

**Primary users:** Directorate administrators, regional/zonal coordinators, facility administrators, patients and staff. **Accountable product/operating owner:** Identity and Directorate operations lead. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-001-R001 | Separate actor and subject | MUST separate login account, patient, caregiver, professional, organisation member and payer identifiers. | Switch a dependent profile without changing the authenticated actor. |
| LWH-PRD-001-R002 | Effective hierarchy | MUST store typed parent/reporting relationships with start/end dates and reject cycles. | A historical return retains its original reporting scope after a zone transfer. |
| LWH-PRD-001-R003 | Scoped grants | MUST bind roles to resource scope, validity, grantor and delegation depth; default deny. | A zone officer cannot read another zone through API/export. |
| LWH-PRD-001-R004 | Multiple contexts | MUST show an explicit context selector and clear drafts/cache when subject changes. | A clinician who is also a patient sees separated workspaces. |
| LWH-PRD-001-R005 | Privileged identity | MUST require strong authentication for professional, reviewer, finance and administrative actions. | An ordinary patient session cannot elevate itself. |
| LWH-PRD-001-R006 | Delegation | MUST record acting assignments, expiry, conflicts and accepted handover of open work. | An expired acting officer loses new decisions but historical authorship remains. |
| LWH-PRD-001-R007 | Offboarding | MUST revoke grants/sessions, reassign work and queue node revocation updates. | An offline node reports its permission freshness and receives revocation on reconnect. |
| LWH-PRD-001-R008 | Recovery | MUST support verified account recovery without silently merging patients or bypassing professional credential checks. | Changed email preserves correct subject linkage and access history. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-001 | Workspace chooser | Valid roles, subjects, facility and scope; last used context | Enter an authorised workspace | No memberships: guided request; revoked role: denied explanation |
| LWH-SCR-002 | Organisation administration | Region/zone tree, relationship dates, people and delegated roles | Invite, assign, expire or transfer | Cycle/version conflict: preserve draft and explain affected units |
| LWH-SCR-003 | Access and handover | Grant history, open obligations, acting appointments | Revoke, accept handover, review access | Absent recipient: retain accountable queue and escalate |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

An administrator creates/imports a validated region and zone, assigns a coordinator, verifies a facility administrator and issues a scoped invitation. The invitee authenticates, accepts the role, enters the correct workspace and completes a task. A transfer closes the previous assignment with an effective date and moves open responsibilities through an accepted handover.

## Operational responsibilities and exceptions

Identity stewards resolve duplicate accounts; record custodians resolve patient matching. These are separate case queues. Inviter and reviewer conflicts are logged. Membership alone never grants treatment, affiliation approval or payroll access. Support staff see account diagnostics with limited personal information.

## Offline and integration behaviour

Facility staff authenticate against a provisioned local authority and valid cached grants. Local supervision can issue only approved offline grants. Regional hierarchy changes remain queued administrative proposals until central acceptance. Cross-facility/global account recovery requiring online verification remains pending.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-001-AT001 | Scoped onboarding | Invite a zone coordinator and facility administrator. | Each sees only the assigned resources and role actions. |
| LWH-PRD-001-AT002 | Wrong context | Open another patient/facility identifier through API. | Request is denied with no record content leaked. |
| LWH-PRD-001-AT003 | Offline departure | Revoke a professional centrally during a facility partition. | Node applies bounded offline policy, displays freshness and reconciles access on reconnect. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track invitation completion, wrong-context incidents, expired assignments, unaccepted handovers and access-review completion. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
