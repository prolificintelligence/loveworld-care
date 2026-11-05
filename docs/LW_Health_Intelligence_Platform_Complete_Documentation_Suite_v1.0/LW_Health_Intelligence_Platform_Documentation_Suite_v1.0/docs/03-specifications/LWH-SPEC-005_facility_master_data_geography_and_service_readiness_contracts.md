---
document_id: "LWH-SPEC-005"
title: "Facility master data, geography and service readiness"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Network master-data lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-PRD-002", "LWH-PRD-003", "LWH-PRD-009", "LWH-SPEC-004"]
source_refs: ["LWH-SRC-001", "LWH-SRC-002"]
directive_refs: []
---

# Facility master data, geography and service readiness

## Canonical site record

Facility IDs identify service-delivery sites, not owners, logins or mutable names. Store operator/owner organisation, ownership category, local external registration identifiers and issuing authorities, public name/aliases, site type, legal jurisdiction, civil location codes, postal/contact details, coordinates with precision/source, accessibility, languages, service catalogue and responsible contacts. Private evidence, personal contacts and inspection dossiers are separately protected.

## Ministry and geographic relationships

Region → Zone is the required ministry spine. Optional lower levels are typed and effective-dated. Civil country/state/locality and legal processing/practice jurisdiction remain independent. Each site has a primary administrative reporting assignment per period and may serve several zones. Directorate approval records any direct/exceptional assignment. Historical reporting uses the assignment/obligation version effective for the period; current reorganisation does not rewrite it.

## Independent status axes

| Axis | States / evidence | Operational effect |
|---|---|---|
| Identity | provisional, verified, disputed, merged-linked, closed | Determines registry confidence and duplicate workflow |
| Ownership | ministry, member-owned, external; evidence and effective dates | Accurate public/administrative relationship |
| Statutory evidence | pending, checked, expired, disputed, not-applicable | Separate jurisdiction-specific legal readiness input |
| Affiliation | applicant, active, conditional, suspended, expired, rejected, withdrawn/removed | Directorate recognition scope and renewal |
| Publication | draft, eligible, published, restricted, withdrawn | Public visibility only |
| Service capability | declared, reviewed, activated, restricted, retired | What a facility is approved/equipped to provide |
| Service readiness | available, constrained, unavailable, unknown/stale | Actual current routing/capacity suitability |
| Reporting obligation | active, paused, ended, exception | Expected-period completeness denominator |

## Service readiness assertion

Every assertion specifies facility/service, eligible population, operating window/time zone, staff/privileges, essential equipment/department availability, capacity type, constraints, reporting source, observed/recorded time, expiry, verification method and accountable team. Bed availability is scoped to actual receiving capability; a nominal bed total is not a live admission acceptance. The country/facility service policy sets refresh/expiry, with shorter bounds for more variable services. Until adopted, routing cannot label a cached value confirmed.

Suitability filters need/service/population/jurisdiction, active capability and valid readiness before proximity. Offer manual location and accessible list results. Show last verified information and actual receiver contact. Confirmed routing requires acceptance by the receiving service; ambulance contact, dispatch acceptance, pickup and delivery are separate facts.

## Change and merge controls

Import with source ID and checksum; suggest candidates using multiple attributes; steward confirms site/owner distinction. A merge creates identifier crosswalks and redirects while preserving source decisions, historical reporting and records. Material service, owner, closure or location changes require review and downstream notices. A closure stops new availability and creates clinical/data-custody continuity tasks. No registry edit can delete clinical or financial history.

## Acceptance

Test one owner/two sites, two similar names/different sites, multi-country region, a zone transfer, withdrawn publication with retained affiliation, expired readiness, no GPS, unavailable specialist service and closure with active care. Public profiles must exclude private evidence/contacts and show exact recognition meaning. Counts reconcile separately for organisations, sites, services and actual patient reach.
