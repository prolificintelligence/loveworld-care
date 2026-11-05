---
document_id: "LWH-PRD-013"
title: "Sponsored programmes, entitlements and funding"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Programme finance and care access leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-SPEC-010", "LWH-COM-001"]
source_refs: ["PROJECT-002"]
directive_refs: []
---

# Sponsored programmes, entitlements and funding

## Purpose and service result

Translate approved programme funding into dependable care access, with clear eligibility and financial accountability. Sponsors receive useful programme evidence without general access to patient charts.

**Primary users:** Sponsor managers, programme administrators, finance staff, patients and authorised care teams. **Accountable product/operating owner:** Programme finance and care access leads. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-013-R001 | Programme definition | MUST version eligibility, covered services, limits, periods, fund restrictions and accountable operator. | A benefit cannot be offered outside its approved terms. |
| LWH-PRD-013-R002 | Subject and payer | MUST separate patient, beneficiary, sponsor, payer and contracting institution. | A sponsor account does not become a patient caregiver. |
| LWH-PRD-013-R003 | Reservations | MUST reserve entitlements atomically with idempotency and expiry/release rules. | Concurrent requests cannot spend the same balance twice. |
| LWH-PRD-013-R004 | Fulfilment evidence | MUST settle benefits against actual qualifying service evidence. | A booked or cancelled service is not automatically a consumed benefit. |
| LWH-PRD-013-R005 | Adjustments | MUST use reasoned maker-checker adjustments, reversals and reconciliation. | An operator cannot approve their own balance correction. |
| LWH-PRD-013-R006 | Disclosure | MUST report permitted aggregate impact and financial usage with small-cohort protections. | Sponsor export cannot reveal clinical notes through beneficiary identifiers. |
| LWH-PRD-013-R007 | Financial classification | MUST distinguish cash received, restricted funds, payable liabilities and earned service revenue. | Funding receipt is not automatically recognised as service revenue. |
| LWH-PRD-013-R008 | Urgency independence | MUST keep urgent clinical guidance and priority independent of entitlement balance. | An exhausted benefit presents a funding route without changing clinical urgency. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-037 | Programme workspace | Contract, eligible services, funding, covered cohort and restrictions | Create approved programme or request funding change | Unapproved terms remain a draft |
| LWH-SCR-038 | Entitlement and reconciliation | Reservations, fulfilments, releases, ledger entries and exceptions | Reconcile, propose adjustment or approve independently | Unbalanced/unmatched transactions enter a visible exception queue |
| LWH-SCR-039 | Sponsor impact | Permitted coverage, delivery, continuity and funding measures | Review period, export protected statement or fund approved services | Suppressed/unknown measures remain suppressed in exports |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

An approved programme is funded and eligibility established. A care request checks and reserves the appropriate benefit. The service is actually delivered or cancelled, producing settlement or release. Finance reconciles receipts, obligations and provider amounts. Sponsors receive permitted statements and impact measures; clinical teams retain follow-up responsibility.

## Operational responsibilities and exceptions

Finance owns fund custody/recognition and reconciliation; programme staff own eligibility; clinical teams attest actual care; privacy owners approve sponsor disclosure. Custodial escrow, insurance or financing claims require separate classification/authorisation and are not inferred from a pool screen.

## Offline and integration behaviour

Offline spending requires preallocated facility-specific signed benefit allowances with expiry and limits. Without such an allowance, eligibility/payment remains pending and care follows the approved clinical/funding contingency. Reconnection reconciles reservations and settlements idempotently; the same balance is never concurrently allocated to multiple nodes.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-013-AT001 | Concurrent use | Reserve the last benefit concurrently at two clients. | Only valid allocated capacity is spendable; no negative entitlement. |
| LWH-PRD-013-AT002 | Cancelled care | Cancel after reservation but before fulfilment. | Reservation releases under policy; no false impact or revenue. |
| LWH-PRD-013-AT003 | Sponsor access | Request patient notes through programme API/export. | Clinical content is denied and aggregate protections persist. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track beneficiaries actually served, unused/expired reservations, cost per delivered service, unmet funded demand, reconciliation exceptions and approved contribution. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
