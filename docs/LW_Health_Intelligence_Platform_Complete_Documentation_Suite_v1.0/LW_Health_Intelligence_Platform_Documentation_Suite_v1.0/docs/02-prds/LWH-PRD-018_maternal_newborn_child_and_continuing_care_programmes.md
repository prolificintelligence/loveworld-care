---
document_id: "LWH-PRD-018"
title: "Maternal, newborn, child and continuing care programmes"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Maternal/child and continuing-care clinical leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-SPEC-019", "LWH-GOV-002"]
source_refs: ["LWH-SRC-011", "LWH-SRC-012", "LWH-SRC-013", "LWH-SRC-034"]
directive_refs: []
---

# Maternal, newborn, child and continuing care programmes

## Purpose and service result

Provide connected programme records and follow-up across pregnancy, birth, postnatal care, childhood and chronic conditions. Patient-facing routines remain simple while clinicians receive the appropriate specialised clinical record.

**Primary users:** Midwives, maternal/child clinicians, general clinicians, nurses, patients and authorised caregivers. **Accountable product/operating owner:** Maternal/child and continuing-care clinical leads. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-018-R001 | Programme episodes | MUST create scoped pregnancy, newborn, child and chronic-care episodes linked to the patient chart. | An episode does not replace the longitudinal patient record. |
| LWH-PRD-018-R002 | Maternal context | MUST record relevant history, gestation/dating source, observations, assessments, plans and authorised referrals. | Uncertain dating/history remains explicitly uncertain. |
| LWH-PRD-018-R003 | Labour and birth | MUST support local approved labour/birth documentation, team, procedures, outcomes and handover. | Clinical decisions/thresholds come from a signed applicable protocol package. |
| LWH-PRD-018-R004 | Mother-infant linkage | MUST issue each infant an independent identity with relationship evidence and its own chart. | Twins are distinct patients; access does not automatically follow a family label. |
| LWH-PRD-018-R005 | Postnatal follow-up | MUST assign maternal/newborn reviews, feeding/support observations and escalation under approved scope. | Missed review creates an owned task, not just a notification. |
| LWH-PRD-018-R006 | Child growth and immunisation | MUST record measurements/units/age context, vaccine product/batch/administration and approved schedule version. | No dose schedule or growth interpretation is fabricated from incomplete inputs. |
| LWH-PRD-018-R007 | Chronic continuity | MUST track patient-agreed goals, clinical measures, medicine reconciliation, reviews and self-reported observations. | Patient-reported adherence is attributed and not presented as verified administration. |
| LWH-PRD-018-R008 | Sensitive access | MUST enforce age, representative, confidentiality and programme-specific access policies. | Parent/caregiver authority is checked against applicable current rules. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-052 | Programme timeline | Patient/episode identity, due reviews, relevant measures and care plan | Enrol, review, record visit or arrange referral | Missing clinical approval disables automated programme recommendations |
| LWH-SCR-053 | Maternal/newborn encounter | Programme-specific history, observations, labour/birth or postnatal fields and relationship links | Document, sign, link infant or hand over | Unknowns and clinical conflicts remain visible |
| LWH-SCR-054 | Family continuity | Separate family subjects, permitted plans, medicines, routines and reminders | Switch subject, complete self-report or request help | Revoked/insufficient proxy access isolates the subject data |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

A clinician enrols a suitable patient into an approved programme and creates a plan with review obligations. Visits update sourced observations, clinical decisions and follow-up. Birth creates separate infant records and appropriate relationships. Maternal/newborn and chronic-care responsibilities continue across facility and remote encounters through authorised summaries and accepted handovers.

## Operational responsibilities and exceptions

Programme leads approve templates and decision content; clinicians/midwives attest care; coordinators organise follow-up; custodians handle infant matching and caregiver authority. Standards sources inform draft structure and do not create permission to offer a service without competent staff and readiness.

## Offline and integration behaviour

Programme records, local clinical workflows, birth/newborn registration, medication/diagnostic interfaces and printing continue locally. Schedule/decision packages carry version and expiry. Unavailable or unapproved rules lead to clinician/manual care rather than guessed automated advice.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-018-AT001 | Multiple birth | Document a birth with two infants offline. | Each child has a distinct chart and correct relationship links. |
| LWH-PRD-018-AT002 | Unknown schedule | Attempt automated vaccine planning without an applicable schedule package. | No invented schedule is issued; a responsible review task appears. |
| LWH-PRD-018-AT003 | Continuity | Miss a planned maternal/chronic review and change care team. | Follow-up remains owned with accepted handover and neutral notifications. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track programme follow-up completion, missing measurements, continuity gaps, authorised vaccine-record completeness and patient-agreed progress with missingness. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
