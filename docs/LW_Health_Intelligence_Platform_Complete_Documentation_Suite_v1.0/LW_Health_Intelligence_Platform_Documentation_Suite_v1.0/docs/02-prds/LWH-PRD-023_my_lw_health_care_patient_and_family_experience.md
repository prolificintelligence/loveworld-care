---
document_id: "LWH-PRD-023"
title: "My LW Health Care: patient and family experience"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Patient experience and clinical service owners"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009"]
source_refs: ["PROJECT-002", "PROJECT-003"]
directive_refs: []
---

# My LW Health Care: patient and family experience

## Purpose and service result

Make care feel attentive through a calm personal dashboard and text companion that remembers authorised context, makes the next step clear and remains accountable through follow-up. Membership of the ministry is not a prerequisite for public care access.

**Primary users:** Individuals, parents, dependants, authorised caregivers and care teams. **Accountable product/operating owner:** Patient experience and clinical service owners. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-023-R001 | Progressive account | MUST support verified personal access and optional dependant/caregiver relationships without long mandatory onboarding. | User can seek help before completing unrelated profile sections. |
| LWH-PRD-023-R002 | Today dashboard | MUST prioritise next care action, active episode, due plan/medicine/review and family subject. | An empty account receives useful start actions rather than demo records. |
| LWH-PRD-023-R003 | Conversation | MUST identify assistant versus human, preserve source context and offer direct actions. | The patient can open their care plan without navigating a chat transcript. |
| LWH-PRD-023-R004 | History and progress | MUST show patient-readable timeline, plans, medications, appointments, results and progress with provenance. | Unreviewed results and uncertain self-reports are not presented as clinical conclusions. |
| LWH-PRD-023-R005 | Family isolation | MUST isolate every subject chart, conversation, draft, reminder and sharing grant. | Switching a child profile cannot expose an adult relative record. |
| LWH-PRD-023-R006 | Reminders and routines | MUST provide controllable neutral notifications and self-reports without changing prescribed instructions. | Reminder completion is not recorded as verified clinical adherence. |
| LWH-PRD-023-R007 | Attentive handoff | MUST show request status, responsible team, next step and truthful expected update. | Delayed clinical acknowledgement creates an owned service exception. |
| LWH-PRD-023-R008 | Accessible support | MUST support keyboard/screen reader, low-bandwidth text, manual location and clear emergency access. | No compulsory video/voice or inaccessible map blocks help. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-067 | Today and family switcher | Active subject, next action, active care, plan, medicine/review and family access | Get help, open care, switch subject or update preferences | No data yields useful guidance; stale data shows last sync |
| LWH-SCR-068 | Companion and care request | Text conversation, sender/source, concise intake and offered care route | Type, inspect plan, request clinician or escalate | Unknown/urgent concern follows approved guidance; no false human review |
| LWH-SCR-069 | My health and access | Timeline, records, appointments, plans, medications, permissions and access history | Review progress, share/revoke, ask correction or arrange follow-up | Denied/expired proxy scope hides the affected records and explains next step |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

A person verifies access, selects self or an authorised dependant and gets useful immediate assistance. Only relevant questions are asked. The user can directly open the plan/history/medicines and request appropriate care. Clinical handoff retains context and visible responsibility. Follow-up and routines support continuity; the patient can correct personal context and control sharing/notifications.

## Operational responsibilities and exceptions

Patient service owners maintain support/response commitments; clinical teams own reviewed plans; privacy owners govern proxies/sharing; product owners measure burden and clarity. Voice and additional languages are deferred with documented extension points. Automated learning cannot silently convert a patient statement into a verified clinical fact.

## Offline and integration behaviour

A personal device may cache a minimum patient-approved plan/history subset with expiry and logout protection. It is not the facility local EMR. New remote requests show pending receipt until acknowledged. Urgent offline guidance uses the approved locally stored content and verified local service information when available.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-023-AT001 | New patient | Seek help without an extensive completed profile. | Relevant next actions work and unknown clinical facts remain unknown. |
| LWH-PRD-023-AT002 | Family privacy | Switch subjects and inspect chat, records and notifications. | Data and drafts are correctly isolated. |
| LWH-PRD-023-AT003 | Delayed request | Lose connectivity after submitting a care request. | Patient sees pending receipt and a safe recovery path without duplicate episode. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track unassisted task success, repeated questions, abandonment, perceived attentiveness, follow-up completion and unsafe state misunderstandings. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
