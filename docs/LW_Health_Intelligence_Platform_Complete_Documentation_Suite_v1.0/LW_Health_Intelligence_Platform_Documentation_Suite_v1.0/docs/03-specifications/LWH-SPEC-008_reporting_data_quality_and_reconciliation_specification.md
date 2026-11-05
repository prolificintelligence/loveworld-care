---
document_id: "LWH-SPEC-008"
title: "Reporting, data quality and reconciliation rules"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Health information systems lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-PRD-004", "LWH-PRD-006", "LWH-SPEC-007", "LWH-SPEC-017"]
source_refs: ["LWH-SRC-004", "LWH-SRC-005"]
directive_refs: []
---

# Reporting, data quality and reconciliation rules

## Reporting architecture

Sources are LW EMR-derived extracts, approved existing-EMR adapters, facility manual/bulk returns and zone/community notifications. They share an adopted indicator dictionary but do not become additive streams by default. A facility/period/indicator authority rule chooses declared source, derived source or a reconciled result. Source versions and discrepancy decisions remain visible. Clinical data extraction uses only the minimum fields necessary for approved reporting.

## Ingestion and review algorithm

1. Authenticate source/node and reporting scope; resolve obligation/template/period and hierarchy version.
2. Validate format/schema, required presence/absence reasons, code versions, units and allowed dimensions.
3. Apply logical checks: nonnegative counts, defined subtotal/total relationships, valid chronology and denominator compatibility.
4. Check expected unit/period uniqueness and duplicate origin events/import batches. Retain a complete input ledger, including rejected/quarantined records.
5. Apply temporal/outlier/consistency warnings under versioned rules; a statistical outlier is not automatically a false value or clinical outbreak.
6. Route blocking errors to originators; warnings to accountable reviewers; retain reasoned overrides and evidence examined.
7. Verify the specified source checks; record reviewer/method/scope and publish only eligible status to the appropriate analytic lane.
8. A correction creates a new source version, invalidates affected projections and recomputes snapshots with notification to relevant owners.

## Calendar and obligation rules

Proposed routine operating baseline: monthly attested facility/zone returns, continuously captured events and weekly operational exception review. Indicator-specific urgency and external statutory calendars override only through adopted configuration. Each obligation fixes expected unit, applicable indicators, local period/time zone, due time, authority and effective hierarchy. Ended facilities/changed assignments are handled through effective-date rules; simply filtering today's active facilities cannot reproduce past completeness.

Nil is an explicit attested absence of qualifying activity; missing is no eligible return; partial is incomplete content/coverage; unknown is an unanswered/uncertain fact; late is a time attribute. A verified partial report remains partial. Data unavailable because an API failed cannot be transformed into a nil return. Community deaths, inpatient deaths, arrival-dead events, clinician-confirmed diagnoses and unverified notifications retain distinct definitions.

## Reconciliation contracts

| Boundary | Required match and accounting | Exception owner |
|---|---|---|
| EMR extract → facility return | Facility/period/indicator/definition; included/excluded events and adjustment reasons | Facility information officer |
| Facility → zone/community | Distinct source stream; reviewed event/identity links where lawful; no simple total addition | Zone reviewer |
| Existing EMR → LW | Patient/order/source ID, code/unit mapping, source status and version | Interface steward |
| Local → cell/control plane | Origin/epoch/sequence, event/entity version, hash and semantic outcome | Sync/data steward |
| Return → dashboard | Source versions, rule/formula, scope/period/denominator and coverage | Analyst/information owner |
| Service → finance | Fulfilment, charge, entitlement, receipt, payer settlement and optional posting | Finance reconciler |

Each batch reports input, accepted, duplicate, blocked, quarantined, pending-dependency and failed counts, with conservation of every source record. Record-level exceptions have owners/age/retry limits. Replaying a corrected batch references the previous batch and does not double-count previously accepted records. No silent row dropping.

## Stewardship and acceptance

Stewards maintain code mappings, identity links and rules with review/versioning. Reviewers cannot amend signed source clinical records through reporting interfaces. A source correction is requested from its custodian. Test nil/missing/partial/late, changed hierarchy, overlapping extracts/returns, inconsistent units, duplicate events, late amendments and failed sources. Reconcile each snapshot to its exact input versions and reproduce historical results before releasing a metric.
