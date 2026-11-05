---
document_id: "LWH-PRD-012"
title: "Patient identity, record continuity and controlled exchange"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Clinical information and privacy leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-SPEC-012", "LWH-GOV-004"]
source_refs: ["LWH-SRC-009", "LWH-SRC-010", "LWH-SRC-030"]
directive_refs: ["DHS-REQ-015", "DHS-REQ-017"]
---

# Patient identity, record continuity and controlled exchange

## Purpose and service result

Let records follow the correct person through authorised care while using anonymised information for appropriate institutional intelligence. Privacy controls depend on recipient, purpose, record type and authority, not a single network-wide sharing switch.

**Primary users:** Patients/caregivers, treating teams, record custodians and exchange partners. **Accountable product/operating owner:** Clinical information and privacy leads. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-012-R001 | Identity crosswalk | MUST preserve local patient IDs, issuing facility and reviewed cross-network identity links. | A name/date similarity cannot silently merge two charts. |
| LWH-PRD-012-R002 | Disclosure lanes | MUST separate aggregate/anonymised intelligence, protected coded cases and authorised identified care records. | A coded summary never appears in a public/general facility browse list. |
| LWH-PRD-012-R003 | Grant contract | MUST record subject, recipient/team, purpose, records/fields, legal authority, validity and revocation. | Access beyond a granted purpose or record scope is denied. |
| LWH-PRD-012-R004 | Minimum clinical view | MUST use appropriate source-attributed summaries and obtain further access when required. | The receiving team can identify unknown, absent and conflicting facts. |
| LWH-PRD-012-R005 | Correct-patient check | MUST validate recipient, subject linkage and treatment context before integrating a disclosure into a clinical chart. | An authorisation token alone cannot attach records to an unmatched patient. |
| LWH-PRD-012-R006 | Provenance and correction | MUST retain authorship, source version, signature/attestation and addenda. | Receiving an amended report does not erase the prior signed version. |
| LWH-PRD-012-R007 | Revocation | MUST stop future access/disclosure and notify replicas under the adopted retention/access policy. | Revocation does not pretend already lawfully retained clinical documentation never existed. |
| LWH-PRD-012-R008 | Patient visibility | MUST provide readable access history, sharing controls and correction requests. | A patient can see recipient/purpose and contest an incorrect link. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-034 | Sharing centre | Active subject, grants, recipients, purposes, record scopes and expiry | Authorise, inspect, revoke or request correction | Unverified proxy authority blocks a grant |
| LWH-SCR-035 | Receiving clinical summary | Permitted identity/context, source facts, missingness and versions | Confirm match, accept into encounter or request more access | Conflicting identity quarantines the incoming package |
| LWH-SCR-036 | Exchange reconciliation | Matching candidates, delivery receipts, amendments and revoked grants | Resolve link, acknowledge update or investigate | Failed/partial exchange stays visible with an owner |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

A referral or care request establishes a permitted purpose. Identity matching and the required patient/representative or other lawful authority are recorded. The exchange releases the minimum permitted coded or identified package, the recipient confirms matching, and a source-attributed copy is used in care. Further data needs produce an additional scoped request. Access, correction and revocation are visible and auditable.

## Operational responsibilities and exceptions

Record custodians own matching and disclosure; clinicians confirm care context; privacy owners approve purposes and retention; patients/caregivers exercise the supported controls. Emergency access requires an adopted, audited local policy with reason, limited scope and retrospective review. Anonymous intelligence undergoes a separate disclosure-risk assessment; hiding names alone is insufficient.

## Offline and integration behaviour

Only locally held records and valid bounded grants are available. A facility cannot reveal remote records it has not received. Delayed revocation is an explicit partition limitation governed by expiry, minimum replication and audit. Reconnection prioritises access revocations and record corrections before additional bulk sharing.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-012-AT001 | Scoped exchange | Authorise one referral summary and request full chart access. | Only the permitted summary is disclosed; extra access requires its own authority. |
| LWH-PRD-012-AT002 | Wrong patient | Receive a summary with a conflicting local identity link. | Package is quarantined and not silently added to a chart. |
| LWH-PRD-012-AT003 | Revocation partition | Revoke a grant while a receiver is disconnected. | Future online access stops; offline bounds and delayed receipt are visible and audited. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track match disputes, duplicate records, disclosure failures, correction propagation, revoked-grant lag and patient sharing task success. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
