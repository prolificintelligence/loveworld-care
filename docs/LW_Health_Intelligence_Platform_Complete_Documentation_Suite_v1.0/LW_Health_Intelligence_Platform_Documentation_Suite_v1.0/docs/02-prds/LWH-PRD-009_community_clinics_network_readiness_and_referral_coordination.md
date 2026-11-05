---
document_id: "LWH-PRD-009"
title: "Community clinics, readiness and referral coordination"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Network clinical operations lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-SPEC-005", "LWH-OPS-004"]
source_refs: ["LWH-SRC-002", "LWH-SRC-016"]
directive_refs: ["DHS-REQ-004", "DHS-REQ-009", "DHS-REQ-019"]
---

# Community clinics, readiness and referral coordination

## Purpose and service result

Connect people to feasible services through community clinics and specialised receiving centres. Capability, current readiness, proximity and operational acceptance govern routing; a directory entry alone is insufficient.

**Primary users:** Patients, local clinic staff, coordinators, referring clinicians and receiving teams. **Accountable product/operating owner:** Network clinical operations lead. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-009-R001 | Clinic scope | MUST declare approved services/populations, staff, equipment, hours and referral routes per clinic. | An unstaffed clinic cannot appear operational. |
| LWH-PRD-009-R002 | Readiness assertions | MUST time-bound readiness by service and source, including temporary constraints. | A closed maternity service is excluded despite an active facility listing. |
| LWH-PRD-009-R003 | Suitable matching | MUST consider clinical need, capability, location, access and readiness before travel distance. | A nearby unsuitable centre is not ranked as an appropriate destination. |
| LWH-PRD-009-R004 | Referral states | MUST distinguish request, acknowledgement, acceptance, departure, receipt and outcome. | Sending a request does not prove the receiving facility accepted. |
| LWH-PRD-009-R005 | Safe handover | MUST include authorised summary, owner, transport/communication needs and outstanding results. | A receiving team explicitly accepts its responsibility. |
| LWH-PRD-009-R006 | Unavailability | MUST preserve originating ownership on decline/unreachable service and offer owned alternatives. | The patient is not left with a failed transfer and no responsible team. |
| LWH-PRD-009-R007 | Emergency channels | MUST show only verified local response contacts and actual dispatch/acceptance receipts. | No universal ambulance coverage is implied. |
| LWH-PRD-009-R008 | Closed loop | MUST record receiving outcome, follow-up, feedback and unresolved obligations. | Referral closure cannot discard a pending critical result. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-025 | Clinic readiness cockpit | Staff/services, operating status, constraints and verification age | Update local readiness or request support | Expired evidence removes confirmed availability |
| LWH-SCR-026 | Referral finder and request | Need, suitable facilities, location, contact and permitted summary | Contact, request, choose alternative or coordinate transport | No suitable destination creates an escalation with retained owner |
| LWH-SCR-027 | Handover tracker | Request/acceptance, journey, recipient, documents and outcome | Accept, confirm receipt, return outcome or escalate | Network loss preserves truthful pending status |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

A clinician identifies a need beyond local capability, selects a suitable verified receiver and sends a permitted summary. The receiver assesses availability and accepts or declines. The sender coordinates safe transfer, records departure and verifies receipt. The receiving team returns outcome/follow-up responsibilities; the originating team reconciles outstanding work before closure.

## Operational responsibilities and exceptions

Clinic directors maintain scope; duty teams own patient care; network coordinators confirm receiving/transport arrangements; receiving teams own accepted work. Service expansion requires evidence, not just creating another facility record. Emergency response commitments are location-specific and staffed.

## Offline and integration behaviour

Local assessment, stabilisation documentation and referral preparation continue. External acceptance requires actual communication, including recorded telephone acceptance where policy allows. Queued network requests remain unconfirmed. Local duty teams use the adopted contingency when no remote contact is possible.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-009-AT001 | Unavailable receiver | Request referral to a centre that declines. | Originating team retains ownership and receives alternatives/escalation. |
| LWH-PRD-009-AT002 | Accepted transfer | Complete request through receiving outcome. | Each handoff has actual actor/time and outstanding tasks remain owned. |
| LWH-PRD-009-AT003 | Offline referral | Prepare a referral without WAN and record a verified phone acceptance. | Local documentation works; digital transmission and actual acceptance are separately recorded. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track unmet demand, readiness freshness, acceptance/receipt delay, completion and lost handovers. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
