---
document_id: "LWH-PRD-022"
title: "Patient billing, payments, claims and care finance"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Facility and programme finance lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-COM-001", "LWH-SPEC-010"]
source_refs: ["PROJECT-003"]
directive_refs: []
---

# Patient billing, payments, claims and care finance

## Purpose and service result

Account accurately for care delivered, patient/payer obligations and receipts while keeping clinical workflow independent of optional enterprise accounting. Display charges and support routes clearly without changing clinical urgency.

**Primary users:** Billing officers, cashiers, payer/sponsor teams, patients, clinicians and reconciliation staff. **Accountable product/operating owner:** Facility and programme finance lead. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-022-R001 | Price book | MUST version service, payer contract, currency, tax/discount applicability and effective dates. | A charge uses the approved price applicable to its actual service event. |
| LWH-PRD-022-R002 | Charge evidence | MUST link charges to delivered/authorised billable service evidence and reversal reasons. | Booking or failed consultation cannot automatically become earned service revenue. |
| LWH-PRD-022-R003 | Invoice and receipt | MUST separate invoice, payment intent, received cash/confirmed provider receipt, allocation and refund. | A pending external payment is never labelled settled. |
| LWH-PRD-022-R004 | Ledger integrity | MUST use append-only balanced transaction groups, currency minor-unit amounts and immutable source keys. | Duplicate callbacks or sync cannot duplicate financial effects. |
| LWH-PRD-022-R005 | Payer split | MUST support patient, sponsor and institutional responsibility with prior authorisation/claim state where applicable. | Benefit exhaustion cannot silently charge an unconsenting patient. |
| LWH-PRD-022-R006 | Claims lifecycle | MUST preserve submitted version, acknowledgement, rejection, adjudication, remittance and appeals. | Claim submission does not imply payer approval or payment. |
| LWH-PRD-022-R007 | Controls | MUST require reasoned independent approval for refunds, write-offs and sensitive adjustments. | Maker cannot approve their own transaction outside an adopted exception. |
| LWH-PRD-022-R008 | Optional accounting | MUST export/reconcile journals to optional general ledger without making it a care prerequisite. | Accounting outage queues postings while clinical and care billing work continues. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-064 | Patient account | Services, charges, payer split, invoices, pending/received payments and support | Review estimate, invoice or explain funding options | Unapproved price/coverage remains unresolved and visible |
| LWH-SCR-065 | Cashier and claims | Cash/provider receipts, allocations, claim versions and remittances | Record receipt, submit claim or request adjustment | External timeout remains pending; no guessed settlement |
| LWH-SCR-066 | Finance reconciliation | Source services, ledger groups, provider settlements and accounting acknowledgements | Match, investigate, reverse or approve independently | Unexplained differences block financial close, not urgent care |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

Approved service evidence generates a versioned charge, the payer split is established and an invoice/claim is issued. Cash or actual provider confirmation records receipt; finance allocates and reconciles it. Denied claims, cancellations and refunds use explicit authorised workflows. Optional accounting receives balanced, idempotent postings and acknowledges them separately.

## Operational responsibilities and exceptions

Finance adopts tariffs, payer rules and approval limits; clinicians attest actual care; cashiers record receipts; independent reviewers approve sensitive changes; reconciliation staff close differences. Payment credentials use approved provider channels; raw card secrets are not stored in the EMR. Jurisdiction-specific tax/insurance rules belong to the country/payer package.

## Offline and integration behaviour

Local tariffs, charge capture, cash receipts, invoices, adjustments under local authority and printing continue. External card/bank/payer authorisation or settlement remains pending until verified. Offline sponsor spending uses preallocated allowances. The node namespaces receipt IDs and exports append-only journals after reconnect.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-022-AT001 | Duplicate callback | Replay a successful payment event and its sync message. | One receipt/allocation effect is recorded. |
| LWH-PRD-022-AT002 | Partial payer | Adjudicate part of a claim with a remaining patient balance. | Each obligation and actual remittance remains explicit. |
| LWH-PRD-022-AT003 | Offline cash | Deliver and bill care, receive cash and later sync. | Local receipt and balanced ledger survive; central accounting receives one reconciled posting. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track service-to-charge reconciliation, cash/settlement differences, rejected claims, debtor ageing, refunds and contribution per delivered care service. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
