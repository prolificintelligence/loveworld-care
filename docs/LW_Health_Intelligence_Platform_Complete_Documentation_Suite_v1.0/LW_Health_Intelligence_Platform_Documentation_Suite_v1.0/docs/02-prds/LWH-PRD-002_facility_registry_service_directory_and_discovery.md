---
document_id: "LWH-PRD-002"
title: "Facility registry, service directory and discovery"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Network registry lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009"]
source_refs: ["LWH-SRC-001", "LWH-SRC-002"]
directive_refs: ["DHS-REQ-001", "DHS-REQ-002", "DHS-REQ-004"]
---

# Facility registry, service directory and discovery

## Purpose and service result

Create one reliable record per facility site, with accurate ownership, affiliation and services. People should find suitable care without interpreting an administrative registry or assuming a listing guarantees current capacity.

**Primary users:** Facility administrators, registry stewards, patients, coordinators and referral teams. **Accountable product/operating owner:** Network registry lead. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-002-R001 | Stable site identity | MUST distinguish operating organisation, physical/virtual service site and external registry identifiers. | One owner with two hospitals produces two sites, not duplicate owners. |
| LWH-PRD-002-R002 | Ownership categories | MUST separately label ministry-owned, member-owned and external ownership/relationship. | A member-owned hospital is never published as ministry-owned. |
| LWH-PRD-002-R003 | Separate status axes | MUST store affiliation, statutory evidence, publication, service capability and live readiness independently. | Expired readiness does not erase historical affiliation. |
| LWH-PRD-002-R004 | Duplicate stewardship | MUST suggest duplicates and require reviewed link/merge with preserved identifiers and audit. | A later import does not create a second count of the same site. |
| LWH-PRD-002-R005 | Scoped publication | MUST publish only approved public fields with current eligibility and verification dates. | Evidence documents and private staff contacts remain private. |
| LWH-PRD-002-R006 | Suitable search | MUST filter service/population suitability before proximity; allow manual location and list access. | No GPS still allows a usable search and accessible results. |
| LWH-PRD-002-R007 | Truthful availability | MUST distinguish listed hours, capability, readiness and confirmed acceptance. | An emergency contact is labelled as contact information, not dispatch. |
| LWH-PRD-002-R008 | Change lifecycle | MUST review material changes and propagate closures/restrictions to directory and routing. | Withdrawn site disappears from new recommendations while history remains. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-004 | Facility profile | Identity, owner, location precision, contacts, services, verification and status | Register, correct or request publication | Duplicate candidate opens stewardship rather than silently replacing |
| LWH-SCR-005 | Public service finder | Service need, location, hours, accessibility, verified status | Search, compare, contact or request referral | No suitable service gives clear alternatives and last-verified context |
| LWH-SCR-006 | Registry stewardship | Unverified changes, duplicate cases and public/private preview | Verify, link, publish or suspend listing | Permission/version conflict leaves prior public version in place |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

A facility administrator registers a site and operator, supplies location/services and ownership evidence. A steward resolves duplicates and verifies metadata. Affiliation review runs separately. An eligible profile is published; a patient searches by need/location, views accurate limitations and initiates contact/referral. The receiving service separately confirms acceptance.

## Operational responsibilities and exceptions

Registry stewards own identity/publication; standards staff own recognition; facility leads own capability declarations; clinical operations verify readiness. Correction requests are acknowledged and assigned. Country/address code mappings never force ministry hierarchy into geographic order.

## Offline and integration behaviour

The local directory cache shows source/version and freshness. New cross-network availability is unknown during disconnection. Local staff can update their own readiness at the local authority; central publication changes are queued and reconciled. No cached listing confirms a remote bed.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-002-AT001 | Two sites | Register two sites owned by one institution. | Directory and reports count sites and owners correctly. |
| LWH-PRD-002-AT002 | Sensitive evidence | Fetch a public profile and its attachments. | Only eligible public information is returned. |
| LWH-PRD-002-AT003 | Stale service | Search when a service readiness assertion has expired. | No confirmed routing is offered from stale readiness. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track verified site coverage, duplicates, stale profiles, search task success and unsuitable-referral rate. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
