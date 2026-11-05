---
document_id: "LWH-ENG-003"
title: "Quality strategy and verification specifications"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "QA lead with clinical, privacy and finance reviewers"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-GOV-002", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-ENG-004"]
source_refs: []
directive_refs: []
---

# Quality strategy and verification specifications

## Test model

Requirements, hazards, forms/fields, state transitions, permissions, APIs/events and operational journeys are traced to tests. Use unit tests for nontrivial deterministic rules; schema/contract tests for interfaces; domain/concurrency tests for consequential invariants; integration tests for real adapters/transactions; UI/accessibility tests for journeys; and qualified operational drills for outage/recovery/adoption. Do not treat screenshot success as evidence of clinical or financial correctness.

## Mandatory test families

| Family | Required coverage |
|---|---|
| Identity/access | Actor versus subject, family/revocation, role scope, professional expiry, self-approval, direct APIs/files/exports |
| Institutional | Duplicate sites/owners, criteria/evidence, central decision, renewal/appeal, publication/readiness separation |
| Reporting | Expected units, nil/missing/partial/late, historical hierarchy, overlap/dedup, correction and reproducible snapshots |
| Clinical integrity | Correct patient, source/unknowns, notes/addenda, orders, result review, accepted handover and pending care |
| Medicines/diagnostics | Units/mappings, specimen/accession, amended/critical results, current orders, MAR retry and clinical stock |
| Inpatient/maternal/procedure | Bed races, shift handover, discharge follow-up, infant identities, applicable consent/privileges and traceability |
| Finance | Balanced groups, entitlements, callbacks, actual settlement, claims, partial payments, refunds and optional GL independence |
| Offline | Complete core local journeys, auth/package validity, cloud/AI unavailable, crash/restart, replay/conflict/dependency and restore |
| AI | Source fidelity/negation, unsupported facts, cross-subject/injection/tools, human authority and AI-off |
| Experience | All UI states, keyboard/screen reader, low bandwidth, progressive forms, truthful status and support |
| Operations | Real roster/readiness, escalation, training, support, local backup/restore and affected-care reconciliation |

## Data and environments

Synthetic fixtures use clearly fictitious people/units and no copied real patient information. Clinical vignettes are reviewed by qualified staff and do not encode invented treatment rules. Test country/service packages are explicitly synthetic. Real data use requires a separately authorised purpose/environment. Separate demo, automated-test, staging, pilot and live secrets/tenants; production must never fall back to fixtures.

## Concurrency and fault injection

Exercise simultaneous case claims, bed allocation, entitlement reserve and order change/administration. Crash after commit before response/outbox publish, lose acknowledgements, duplicate/reorder messages, skew clocks, expire/revoke grants, corrupt/miss objects and restart schedulers. Assert every committed clinical/financial fact is accounted for, with no duplicate doses/stock/ledger and no lost result/follow-up. A failed dependency cannot become a successful empty result.

## Evidence and defect rules

Record exact code/environment/configuration/content/model versions, test input/scenario, expected/actual result, source evidence, reviewer and limitations. All supplied PRD/UAT cases are NOT_RUN until executed. Clinical, privacy/security and ledger/stock integrity blockers cannot be waived by ordinary product acceptance. Retest affected paths after changes; avoid redundant broad testing without a changed risk. Qualified owners accept residual risks explicitly.

## Documentation checks versus implementation tests

The delivered suite is checked for IDs, paths, references, schema compilation/examples and catalogue coverage. Those checks do not execute the platform. Implementation readiness requires actual contract/domain/E2E/operational evidence against the release candidate. Keep this distinction visible in reports and meeting demonstrations.
