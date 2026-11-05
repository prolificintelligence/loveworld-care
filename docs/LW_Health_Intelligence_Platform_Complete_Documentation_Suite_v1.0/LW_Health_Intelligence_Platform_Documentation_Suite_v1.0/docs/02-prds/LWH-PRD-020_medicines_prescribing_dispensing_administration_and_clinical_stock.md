---
document_id: "LWH-PRD-020"
title: "Medicines, prescribing, dispensing, administration and stock"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Medication safety, pharmacy and nursing leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-SPEC-019", "LWH-SPEC-017"]
source_refs: ["LWH-SRC-014", "LWH-SRC-020"]
directive_refs: []
---

# Medicines, prescribing, dispensing, administration and stock

## Purpose and service result

Maintain an accurate medication chain from clinical intent to supply and actual administration, with appropriate reconciliation and traceability. Clinical stock supports care independently of optional procurement/accounting modules.

**Primary users:** Prescribers, pharmacists, dispensers, nurses, stock custodians and patients. **Accountable product/operating owner:** Medication safety, pharmacy and nursing leads. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-020-R001 | Product identity | MUST store medication code/system/version, ingredient/product, form, strength and units as distinct concepts. | Free-text display cannot silently substitute a different strength/product. |
| LWH-PRD-020-R002 | Prescribing | MUST require an authorised signed order with patient, indication/context, dose/unit, route, timing and duration/stop intent as applicable. | No template or AI draft supplies an unreviewed treatment instruction. |
| LWH-PRD-020-R003 | Safety context | MUST surface allergy status, relevant current medicines and approved checking results with source freshness. | Unknown allergies are not shown as no known allergies. |
| LWH-PRD-020-R004 | Dispensing | MUST record prescribed versus actually dispensed item, quantity, batch/expiry and permitted substitution approval. | Stock issue does not falsely prove patient ingestion. |
| LWH-PRD-020-R005 | Administration | MUST link an actual administration/omission to the current order, patient, time, actor and reason. | Retried requests cannot create a second dose record. |
| LWH-PRD-020-R006 | Reconciliation | MUST reconcile medicines at admission, transfer, review and discharge. | Discontinued/changed orders remain historically visible and update future tasks. |
| LWH-PRD-020-R007 | Clinical stock | MUST maintain local lot movements, expiry/recall/quarantine, reservations and witnessed adjustments under policy. | Duplicate sync cannot decrement stock twice. |
| LWH-PRD-020-R008 | Exceptions | MUST record hold, refusal, omission, shortage, adverse event and authorised emergency deviations without fabricating fulfilment. | A shortage creates a responsible clinical/pharmacy action. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-058 | Medication ordering | Current medicines, allergies, formulary, checks and full order intent | Draft, review, sign, hold, change or stop | Missing authority/units/applicable policy blocks release |
| LWH-SCR-059 | Dispensing and clinical stock | Order, chosen product, quantity, lots, expiry, stock and substitution | Verify, reserve, dispense, return or quarantine | Insufficient/uncertain stock remains an exception, not invented supply |
| LWH-SCR-060 | Medication administration record | Identity, due/current orders, prior administrations and omissions | Confirm administration or record reasoned omission | Duplicate, wrong subject or stale order is blocked for review |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

A clinician reconciles context and signs a complete medication order. Pharmacy verifies and dispenses the actual approved product/lot. Nursing records actual administration or a reasoned omission against the current order. Changes update future tasks while preserving past events. Discharge reconciliation produces reviewed patient instructions and continuing responsibility.

## Operational responsibilities and exceptions

Prescribers own orders; pharmacists own product verification/substitution and stock; nurses own administration records; medication-safety leads adopt checking content and incident review. Controlled medicines, paediatric calculations, infusions and high-risk double-check rules require the applicable clinical/jurisdiction package. The suite supplies data/process controls, not drug doses.

## Offline and integration behaviour

The full prescribing/dispensing/MAR/stock chain runs locally with valid local formulary and checking packages. Remote prescriptions are requests until the facility authority accepts them. Dispensing across separate disconnected facilities requires distinct allocated stock/entitlements; no shared balance is assumed. Expired safety packages require the adopted clinician/pharmacist contingency.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-020-AT001 | Dose retry | Retry an administration command after an uncertain response. | The same idempotency key returns one recorded administration. |
| LWH-PRD-020-AT002 | Changed order | Stop an order before a nurse acts from a stale view. | Server version/state check prevents unreviewed stale administration. |
| LWH-PRD-020-AT003 | Offline stock | Dispense/return/adjust local lots during WAN loss and sync twice. | Clinical history and stock reconcile exactly once with preserved provenance. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track reconciliation completion, omissions, dispensing discrepancies, stockouts, expired/recall exposure and medication incidents with review context. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
