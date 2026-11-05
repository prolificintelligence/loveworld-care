---
document_id: "LWH-PRD-011"
title: "LW Care service integration and remote care"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Clinical service product owner"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-PRD-023", "LWH-PRD-024"]
source_refs: ["PROJECT-002", "PROJECT-003"]
directive_refs: ["DHS-REQ-011"]
---

# LW Care service integration and remote care

## Purpose and service result

Connect immediate personal assistance, staffed remote care and facility services into one owned care episode. LW Care is a capability inside LW Health Intelligence Platform, sharing identity and network services while protecting clinical records.

**Primary users:** Patients, duty clinicians, coordinators, facilities and care programme teams. **Accountable product/operating owner:** Clinical service product owner. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-011-R001 | One episode | MUST preserve episode identity across conversation, review, appointment, consultation, referral and follow-up. | Patient does not repeat an intake when a clinician accepts the case. |
| LWH-PRD-011-R002 | Truthful assistance | MUST label automated assistance and distinguish received, clinician-acknowledged and assessed. | AI greeting never implies a clinician has reviewed the patient. |
| LWH-PRD-011-R003 | Clinical routing | MUST use approved low-risk protocols and emergency escalation independently of payment/AI availability. | Unknown critical information cannot default to a reassuring negative. |
| LWH-PRD-011-R004 | Covered service | MUST match by privileges, jurisdiction, capacity, continuity and service hours. | Unavailable coverage gives a truthful next step and owner. |
| LWH-PRD-011-R005 | Consult recovery | MUST preserve draft and episode during call/network failure, with alternative review/reschedule. | Disconnected video does not sign, complete or bill care automatically. |
| LWH-PRD-011-R006 | Clinical completion | MUST require an authorised signed assessment and owned follow-up/results. | An unresolved result survives consultation completion. |
| LWH-PRD-011-R007 | Facility link | MUST exchange a permitted referral/summary and await receiving acceptance. | A facility appointment is not confirmed from a sent request alone. |
| LWH-PRD-011-R008 | Care finance | MUST separate clinical urgency, entitlement, price acceptance, payment and settlement. | Urgent guidance works without login or settled payment. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-031 | Care request | Active subject, concern, approved assistance, offered services and response state | Start help, provide concise context or request clinician | No capacity shows alternatives and clear service hours |
| LWH-SCR-032 | Consultation room | Verified participants, connection state, relevant summary and shared plan | Join, reconnect, change modality or receive next steps | Call failure retains care ownership and evidence |
| LWH-SCR-033 | Care continuity | Signed plan, medications, referrals, pending results and next review | Complete tasks, ask clarification or arrange follow-up | Overdue clinical obligations create owned work |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

A patient describes a need and receives immediate bounded help. Approved routing offers self-support, clinician review or urgent local escalation. A qualified clinician accepts, reviews source context and completes the appropriate consultation. The signed plan creates owned tasks and any referral. The patient sees the next step and actual review state until obligations are resolved or accepted by another team.

## Operational responsibilities and exceptions

The clinical operator supplies duty coverage, response commitments and safe alternatives. Coordinators arrange suitable network services. Clinicians sign consequential decisions and acknowledge results. Product owners monitor repeated data entry, unowned care and misleading states. Text and dashboard are core; voice and additional languages remain separately validated extensions.

## Offline and integration behaviour

In-facility care continues locally. A disconnected patient device can read a deliberately limited cached plan but cannot promise remote clinician receipt. Cloud calls and external messages show their actual availability. Reconnecting resumes the same episode, deduplicates submissions and reconciles pending tasks.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-011-AT001 | Care handoff | Move a patient request from assistant to clinician to facility. | Context, owner and status persist without duplicate intake. |
| LWH-PRD-011-AT002 | Call loss | Disconnect during a consultation. | Draft survives; no false completion or automatic charge. |
| LWH-PRD-011-AT003 | AI unavailable | Disable inference and request urgent assistance. | Approved guidance/escalation and staffed worklists remain usable. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Measure human acknowledgement, unmet demand, repeated-information burden, continuity completion and patient task success. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
