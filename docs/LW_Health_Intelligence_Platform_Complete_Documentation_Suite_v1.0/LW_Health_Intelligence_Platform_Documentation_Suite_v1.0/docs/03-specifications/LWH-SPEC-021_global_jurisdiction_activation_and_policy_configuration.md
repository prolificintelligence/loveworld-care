---
document_id: "LWH-SPEC-021"
title: "Global jurisdiction activation and policy configuration"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Country activation and platform policy leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-GOV-008", "LWH-GOV-003", "LWH-SPEC-017", "LWH-ENG-004"]
source_refs: ["PROJECT-003"]
directive_refs: []
---

# Global jurisdiction activation and policy configuration

## Global design and local activation

Pilot countries are deliberately unselected. The platform models global institutional participation, cross-country ministry units and jurisdiction-specific clinical/data/financial operation. No country, licence regime, currency, statutory report or tax schedule is silently hard-coded as the universal default. A facility service resolves the adopted country/operator package plus more restrictive facility/service scope.

## Configuration catalogue

| Parameter | Key | Required adopted content / default | Owner |
|---|---|---|---|
| LWH-CFG-001 | clinical_enabled | false until country/service approval | Directorate/country clinical owner |
| LWH-CFG-002 | operator_and_custodian_entities | Named accountable legal/clinical/data/finance entities | Directorate/legal |
| LWH-CFG-003 | ministry_hierarchy_import | Validated Region → Zone roster and effective dates | Directorate operations |
| LWH-CFG-004 | practice_and_professional_rules | Profession/registration/privilege/service boundaries | Clinical/legal |
| LWH-CFG-005 | supported_populations_services | Facility capability and explicit exclusions | Clinical director |
| LWH-CFG-006 | data_processing_locations | Approved production, backup, support, exchange and AI locations | Privacy/security |
| LWH-CFG-007 | processing_and_sharing_authority | Purpose/lawful basis, consent/representative and emergency-access rules | Privacy/legal/clinical |
| LWH-CFG-008 | retention_and_rights | Record-class retention, holds, access/correction/complaint timelines | Records/privacy |
| LWH-CFG-009 | clinical_content_packages | Protocols, formulary, schedules, scores/calculators and review/expiry | Clinical governance |
| LWH-CFG-010 | diagnostic_and_medicine_catalogues | Mapped codes/units, reference/critical rules and product terms | Diagnostic/pharmacy leads |
| LWH-CFG-011 | affiliation_criteria_calendar | Criteria, inspection, conditions, renewal/notice/review terms | Directorate standards |
| LWH-CFG-012 | reporting_obligations | Forms, indicators, period/timezone, deadline and expected units | Health information lead |
| LWH-CFG-013 | service_response_and_escalation | Actual staffed coverage, response commitments and tested contacts | Clinical operations |
| LWH-CFG-014 | disclosure_controls | Permitted dimensions/cohorts/exports, suppression and review | Privacy/information |
| LWH-CFG-015 | financial_and_payer_rules | Currency/scale, approved tariff, taxes, claims and adjustment limits | Finance/legal |
| LWH-CFG-016 | offline_identity_and_authority | Local issuance, lease/expiry, revocation and clock policy | Clinical/security |
| LWH-CFG-017 | recovery_capacity_targets | Actual load, outage tolerance, RPO/RTO, support and backups | Facility/platform owners |
| LWH-CFG-018 | partner_profiles | Approved identifiers, interfaces, data agreements and conformance | Interoperability/custody |
| LWH-CFG-019 | optional_enterprise_rules | Contracted modules, accounting/employment/payroll local rules | Enterprise/finance/legal |
| LWH-CFG-020 | activation_evidence | Tests, training, readiness, funding, reviews and scoped release decision | Programme release owners |


## Policy package schema and resolution

Each package carries ID, semantic version, type, issuer/approvers, jurisdiction/operator/facility/service applicability, effective/expiry, source references/licences, configuration values, dependencies, hash/signature, supersession and rollback. Resolve country/operator → service → facility restrictions explicitly; document which values can narrow or override. Ministry administrative hierarchy cannot override legal/practice limits. Conflicts fail with an actionable review requirement rather than choose the most permissive rule.

Example safe deployment state:

```json
{"package_id":"synthetic-unactivated-profile","version":"1.0.0","clinical_enabled":false,"pilot_country":null,"approved_services":[],"approved_processing_locations":[],"activation_status":"DESIGN_ONLY"}
```

The example is configuration structure, not an approved country package. Clinical enabling requires the complete adopted evidence set; a developer changing a boolean cannot authorise service. Package compatibility and migrations are validated before rollout. Local packages preserve historical rules necessary to interpret existing records.

## Adoption workflow

The Directorate nominates a country/operator owner; qualified reviewers assess practice/software regulation, privacy/processing, records/consent, clinical service, finance and contracts. Facilities validate capabilities, professional privileges, departments, local runtime and support. The release board reviews exact evidence/version and authorises only the stated country/service/facility cohort. Registration and public metadata activation are distinct from clinical activation.

## Updating and stopping

Monitor changed source standards/law, expired credentials/content, new partner/data location and service incidents. Material changes reopen the affected review and tests. Restrictions reach nodes with priority; disconnected nodes follow bounded cached authority and known local restrictions. Preserve safe local care/manual alternatives and open obligations while containing an affected capability. Resumption requires reviewed evidence, not a green infrastructure signal alone.
