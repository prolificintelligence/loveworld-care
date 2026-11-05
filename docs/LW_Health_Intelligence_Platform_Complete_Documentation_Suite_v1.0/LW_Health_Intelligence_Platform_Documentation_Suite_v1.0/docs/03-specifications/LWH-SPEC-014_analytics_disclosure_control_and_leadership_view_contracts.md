---
document_id: "LWH-SPEC-014"
title: "Analytics, disclosure and leadership view contracts"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Analytics and privacy leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-PRD-007", "LWH-SPEC-007", "LWH-SPEC-008", "LWH-GOV-003"]
source_refs: ["LWH-SRC-005", "LWH-SRC-030"]
directive_refs: []
---

# Analytics, disclosure and leadership view contracts

## Analytic lanes and datasets

Operational clinical views use locally authoritative records and clinical permissions. Institutional reporting uses permitted facility/zone data and verified returns. Leadership views use disclosure-controlled aggregates. Protected case/referral review is a separate purpose-limited application and cannot be reached through a general dashboard drill-down. Coded patient identifiers and identity crosswalks never form part of anonymous leadership datasets.

## Role-specific view contract

| View | Default decision deck | Permitted drill-down |
|---|---|---|
| President authorised view | Network reach/standards, major service/health exceptions, intervention progress and resource decisions | Reviewed strategic aggregates and approved programme evidence |
| Executive Minister | Programme delivery, cross-region gaps, resource needs and follow-through | Permitted region/programme summaries and owned actions |
| Directorate | Affiliation/renewals, reporting quality, access/continuity, workforce/readiness/referrals, sponsored delivery and economics | Scoped operational worklists; confidential case access only by separate role/purpose |
| Region | Assigned-zone coverage, support needs, readiness and actions | Own authorised units and permitted aggregate details |
| Zone | Facility/community reporting, clinic/referral readiness and accepted local work | Own reporting/evidence/tasks within confidentiality controls |
| Facility | Clinical operations, own standards/reporting, workload and care finance | Own permitted records according to clinical/administrative role |
| Sponsor | Funding, qualifying services, permitted beneficiary/impact measures | Contracted financial detail and protected aggregates, not clinical notes |

Each tile has metric ID/version, period/time zone, scope/hierarchy version, numerator/denominator or count definition, verified/provisional status, coverage, refresh and interpretation. Dashboard defaults are concise, with selectable deeper workspaces. Narrative generation references these exact measures and cannot independently invent numbers or causal claims.

## Disclosure control

Assess direct identifiers, quasi-identifiers, rare events, fine geography, exact dates, combinations and repeated/differencing queries. Adopt minimum cohort and dimension rules by dataset/purpose; apply primary and complementary suppression where needed, plus export/query limits and reviewed narrative handling. Until a disclosure rule is approved, suppress potentially identifying fine-grained outputs rather than assume a universally safe threshold. No `k ≥ 5` anonymity guarantee or differential-privacy claim is made.

If formal differential privacy is later adopted, specify privacy unit, mechanism, epsilon/delta, sensitivity, contribution bounds, composition/query budget and utility/privacy evaluation. Rounding or hiding names is not that mechanism. Patient-level research access requires a separately approved purpose, agreement and disclosure assessment.

## Freshness, correction and release

Store immutable aggregate snapshots with source versions, transformation/rule/formula versions, scope/obligation/hierarchy and disclosure policy. Local operational/provisional signals are visibly distinct from verified institutional measures. Corrections regenerate affected snapshots and flag prior exports/narratives for review where appropriate. Backend failure displays unavailable; last-good snapshots show age rather than a green zero. Comparisons use consistent cohorts or explain scope/definition changes.

## Acceptance

Reconcile selected dashboard values to exact sources and expected obligations; test zero/missing/partial/late, region reorganisation, duplicate feeds and late amendment. Attempt the same disclosure through charts, tables, APIs, downloads, narratives, repeated filters and scheduler emails. Test each role with wrong scope and direct object access. Analytics acceptance includes decision usefulness and coverage clarity, not attractive charts alone.
