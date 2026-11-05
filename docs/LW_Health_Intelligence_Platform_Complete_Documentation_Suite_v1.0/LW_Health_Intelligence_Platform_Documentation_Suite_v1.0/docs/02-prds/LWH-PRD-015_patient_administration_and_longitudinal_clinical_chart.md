---
document_id: "LWH-PRD-015"
title: "Patient administration and longitudinal clinical chart"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Facility clinical information lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-SPEC-018", "LWH-GOV-004"]
source_refs: ["LWH-SRC-008", "LWH-SRC-009"]
directive_refs: ["DHS-REQ-015"]
---

# Patient administration and longitudinal clinical chart

## Purpose and service result

Provide a trustworthy person-centred chart that is usable at first contact and throughout repeated care. Administrative registration stays concise while clinical context, provenance and patient identity remain dependable.

**Primary users:** Registration staff, record custodians, clinicians, nurses and patients. **Accountable product/operating owner:** Facility clinical information lead. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-015-R001 | Progressive registration | MUST capture the minimum viable identity/contact and expand only for care or legal need. | Emergency/unknown patients can receive provisional IDs without fabricated demographics. |
| LWH-PRD-015-R002 | Local identifiers | MUST issue collision-resistant site-qualified identifiers and preserve external identifier systems. | Offline registration does not depend on central sequence allocation. |
| LWH-PRD-015-R003 | Identity safeguards | MUST support patient/representative confirmation and context-appropriate independent identifiers. | A bed number alone is not treated as permanent patient identity. |
| LWH-PRD-015-R004 | Longitudinal facts | MUST separate history, problems, allergies, medicines, observations, procedures and plans with source/status. | Unknown allergy status differs from no known allergies and from no recorded data. |
| LWH-PRD-015-R005 | Sensitive attributes | MUST distinguish recorded sex/gender and relevant physiological/clinical context where needed. | Missing attributes are not inferred from name or ministry role. |
| LWH-PRD-015-R006 | Duplicate resolution | MUST require reviewed matching/merge and preserve reversible source crosswalks. | Conflicting charts cannot be destructively merged by a similarity score. |
| LWH-PRD-015-R007 | Documentation integrity | MUST support drafts, attestation, signed versions, addenda and entered-in-error correction. | An amendment preserves the original signed statement. |
| LWH-PRD-015-R008 | Patient continuity | MUST link encounters, episodes, dependants/caregivers, access grants and pending obligations without conflating them. | An adult dependant profile does not give another family member blanket access. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-043 | Registration and matching | Name/known identifiers, contact, provisional status and match candidates | Search, register, confirm or refer duplicate review | Emergency registration remains usable; uncertain match stays unresolved |
| LWH-SCR-044 | Patient chart | Identity banner, timeline, problem/allergy/medication lists, results and plans | Open encounter, review fact, amend or request sharing | Stale/conflicting source facts are visible with provenance |
| LWH-SCR-045 | Record stewardship | Duplicates, amendments, disclosure/correction requests and chart links | Review, approve link or preserve separate records | Insufficient evidence blocks destructive merge |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

A receptionist searches existing local identifiers before registration, verifies the person or creates a provisional record and opens the correct service encounter. Clinicians review longitudinal context, document new findings and sign. Source-attributed records remain available across visits. External links or duplicate disputes enter stewardship; patients can request correction and authorised sharing.

## Operational responsibilities and exceptions

Registration staff maintain demographics; clinicians own clinical attestations; custodians resolve links and record corrections. A patient may have no app account. A payer/contact/next-of-kin is not automatically an authorised representative. Clinical records survive facility affiliation withdrawal under the approved custody plan.

## Offline and integration behaviour

Registration, matching against local records, chart review, documentation and printing operate on the local runtime. Central matching waits for synchronisation. Provisional IDs remain valid and are linked through reviewed crosswalks rather than replaced destructively.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-015-AT001 | Unknown patient | Register an unidentified emergency patient offline. | A provisional chart is usable and can later be reconciled safely. |
| LWH-PRD-015-AT002 | Allergy semantics | Open charts with unknown, none-known and confirmed allergy states. | Each is distinct and medication checks use the right state. |
| LWH-PRD-015-AT003 | Amendment | Correct a signed note and merge candidate identity. | Original attestation remains; link requires reviewed evidence. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track duplicate creation, wrong-patient events, provisional resolution, chart completeness and repeated registration burden. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
