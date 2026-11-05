---
document_id: "LWH-PRD-010"
title: "Health education, approved policy and rights communication"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Clinical editorial and Directorate policy lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009"]
source_refs: ["LWH-SRC-032"]
directive_refs: ["DHS-REQ-008"]
---

# Health education, approved policy and rights communication

## Purpose and service result

Provide trustworthy education and clear approved policy through the channels people use, linked to actionable support. Preserve the ministry identity while distinguishing faith content, clinical guidance and patient rights.

**Primary users:** Clinical editors, policy owners, regional/zonal distributors, patients and the public. **Accountable product/operating owner:** Clinical editorial and Directorate policy lead. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-010-R001 | Content provenance | MUST store author, reviewer, sources, purpose, audience, jurisdiction, language and version. | A clinical article has an accountable qualified reviewer. |
| LWH-PRD-010-R002 | Approval and expiry | MUST separate drafting, review, approval, publication, review-due, withdrawal and correction. | Unapproved/withdrawn clinical content cannot be served as current guidance. |
| LWH-PRD-010-R003 | Policy accuracy | MUST use separately approved ministry wording rather than infer restrictions from unclear audio. | Unresolved transcript phrases are absent from live treatment instructions. |
| LWH-PRD-010-R004 | Accessible delivery | MUST support concise text, readable documents and contextual links without compulsory long onboarding. | Patient can read the relevant explanation from the care-plan task. |
| LWH-PRD-010-R005 | Targeted distribution | MUST use consented preferences and permitted audience segments without exposing diagnoses in notifications. | A lock-screen message contains a neutral prompt. |
| LWH-PRD-010-R006 | Linked support | MUST link content to appropriate care/referral/contact paths and explain its purpose. | Education does not silently replace needed clinical review. |
| LWH-PRD-010-R007 | Correction propagation | MUST identify affected versions/audiences and distribute meaningful corrections. | An offline cache marks expired content and receives withdrawal on reconnect. |
| LWH-PRD-010-R008 | Feedback and effect | MUST separate delivery, engagement, understanding and health outcomes. | A delivered campaign is not reported as proven behaviour change. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-028 | Editorial library | Source, content type, audience, reviewers and due/expiry dates | Draft, review, approve, correct or withdraw | Missing reviewer/applicability blocks clinical publication |
| LWH-SCR-029 | Patient/public learning | Relevant approved education, rights and service access | Read, save, ask for help or change preferences | Expired material shows status and current alternatives |
| LWH-SCR-030 | Programme distribution | Audience scope, delivery channels, corrections and feedback | Schedule, distribute or review effect | Failed delivery retains retry and support path |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

A policy/clinical owner identifies a need, an editor prepares sourced content, the correct reviewer approves an applicable version and distribution targets permitted audiences. Patients can move directly to support. Feedback informs revision; withdrawals/corrections reach caches and affected recipients with an auditable trail.

## Operational responsibilities and exceptions

Editorial owners manage source quality and clinical review; ministry policy owners approve institutional wording; coordinators distribute; service teams receive help requests. Language rollout is separate from text-first release and requires clinical translation/usability review.

## Offline and integration behaviour

Approved content packages are locally readable with validity and source dates. Expired decision-support content is not executed. Local care teams can provide documented clinical explanation; publishing new central policy waits for the proper authority.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-010-AT001 | Approval | Try to publish unreviewed clinical content. | Publication is blocked with missing review requirements. |
| LWH-PRD-010-AT002 | Correction | Withdraw a published item with local cached copies. | Caches update on reconnect; active views show version/validity. |
| LWH-PRD-010-AT003 | Private notification | Send programme reminders to an authorised audience. | External messages reveal no clinical detail by default. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track current reviewed content, correction reach, support requests, accessibility task success and programme-specific outcomes with limitations. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
