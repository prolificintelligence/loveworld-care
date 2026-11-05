---
document_id: "LWH-SPEC-006"
title: "Form catalogue, field dictionary and executable capture schemas"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Clinical information, standards and reporting leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-SPEC-004", "LWH-SPEC-009", "LWH-SPEC-018", "LWH-SPEC-019"]
source_refs: ["LWH-SRC-001", "LWH-SRC-002", "LWH-SRC-003", "LWH-SRC-004", "LWH-SRC-005", "LWH-SRC-007", "LWH-SRC-010", "LWH-SRC-011", "LWH-SRC-012", "LWH-SRC-013", "LWH-SRC-015", "LWH-SRC-032", "LWH-SRC-034", "LWH-SRC-036", "LWH-SRC-037", "LWH-SRC-038", "LWH-SRC-039", "LWH-SRC-040", "LWH-SRC-041", "LWH-SRC-042", "LWH-SRC-043", "LWH-SRC-044", "LWH-SRC-045", "LWH-SRC-047", "LWH-SRC-048", "LWH-SRC-049"]
directive_refs: ["DHS-REQ-016"]
---

# Form catalogue, field dictionary and executable capture schemas

## Form engine and adoption

This catalogue supplies project-designed capture forms, stable field references and executable JSON Schema 2020-12 contracts. Source references identify the domain supporting curation; they do not claim copied item wording, complete WHO instruments or organisational endorsement. Existing Directorate templates have not been supplied. Reconcile each original field to these definitions, document additions/retirements and obtain the responsible owner's adoption before production reporting/standards use. Legacy prototype FRM-001…007 map respectively to LWH-FRM-001…007 without changing their meanings.

These are capture schemas, not substitutes for clinical policy, professional judgement, server permissions or state-transition validation. A submitted capture can record an explicit unknown; a later consequential action such as releasing a medication order or accepting a clinical handover must satisfy the stricter runtime clinical/authority rules. No clinical threshold, dose, vaccine schedule or local legal consent rule is supplied by a plausible default.

## Common field and UI contract

The envelope carries form ID/version, draft/submitted stage, authoritative node, authenticated actor, facility/unit and applicable patient/encounter. Server-owned identity/recorded timestamps are derived and checked against the session; they are not trusted because a client sent them. Source references and version accompany imported/prepared answers. Protected uploads are referenced by private IDs, verified content/checksum, source and applicable expiry.

Presence in the tables means required for the submitted capture stage; optional/conditional fields become mandatory at their specific clinical/state guard. Every typed value can explicitly declare unknown, not-assessed, unavailable, declined or not-applicable with an explanation. These absence states never become numerical zero or a negative clinical fact. Some identity/authority fields cannot remain absent for the target action; the action validator blocks or uses a documented provisional pathway. Known-none allergy is an explicit clinical state rather than missing data.

Repeated observations store code, typed value or absence, unit, effective time, method, reference context and source. Exact medication quantities use decimal strings plus coded units. Money uses integer minor units, currency and currency scale. Periods preserve time zone. Cross-field chronology, totals, unit applicability, safety checks, authorisation and record version are validated server-side and reported against these stable field references.

The UI prepopulates known facts, exposes source/freshness and asks only relevant questions. Show sections progressively, save drafts durably and preserve valid inputs after an error. Signing/publishing is a separate intentional workflow. Clinical records remain patient scoped; institutional event forms avoid names and store sensitive details only through an authorised separate link.

## Form and field definitions

### LWH-FRM-001 — Facility application

**Owner:** Registry steward. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-001.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-001.F001 | site_name | text | submitted | Current public site name; aliases retained | LWH-SRC-001 |
| LWH-FRM-001.F002 | operator_org_id | ref | submitted | Verified owner/operator organisation | LWH-SRC-001 |
| LWH-FRM-001.F003 | ownership_category | ownership | submitted | Ministry/member-owned/external labels are independent of affiliation | LWH-SRC-001 |
| LWH-FRM-001.F004 | jurisdiction_profile | text | submitted | Legal/geographic profile; never infer from zone | LWH-SRC-001 |
| LWH-FRM-001.F005 | location | location | submitted | Civil codes, coordinates/source/precision; manual address allowed | LWH-SRC-001 |
| LWH-FRM-001.F006 | services | concepts | submitted | Declared service catalogue, not confirmed readiness | LWH-SRC-001 |
| LWH-FRM-001.F007 | contacts | contacts | submitted | Public versus private purpose flags | LWH-SRC-001 |
| LWH-FRM-001.F008 | evidence_refs | refs | conditional/optional | Private verified uploads; retain source/expiry | LWH-SRC-001 |

**Cross-field/transition rule:** Resolve duplicate site/operator before publication; require declaration and applicable evidence before submission acceptance.

### LWH-FRM-002 — Service readiness review

**Owner:** Network clinical lead. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-002.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-002.F001 | service | concept | submitted | Exact service/population scope | LWH-SRC-002 |
| LWH-FRM-002.F002 | readiness | readiness | submitted | Available/constrained/unavailable/unknown | LWH-SRC-002 |
| LWH-FRM-002.F003 | observed_at | datetime | submitted | Actual assessment time | LWH-SRC-002 |
| LWH-FRM-002.F004 | valid_until | datetime | submitted | Adopted service-specific expiry | LWH-SRC-002 |
| LWH-FRM-002.F005 | staff_privilege_refs | refs | submitted | Applicable staffed/privileged team | LWH-SRC-002 |
| LWH-FRM-002.F006 | equipment_constraints | text | conditional/optional | Observed capability/constraint evidence | LWH-SRC-002 |
| LWH-FRM-002.F007 | capacity | count | conditional/optional | Defined capacity unit; not referral acceptance | LWH-SRC-002 |
| LWH-FRM-002.F008 | review_evidence | refs | conditional/optional | Self-report versus checked evidence | LWH-SRC-002 |

**Cross-field/transition rule:** Expiry must follow observation; unknown/stale readiness cannot confirm new routing.

### LWH-FRM-003 — Facility periodic return

**Owner:** Facility accountable officer. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-003.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-003.F001 | obligation_id | ref | submitted | Expected reporting unit/period record | LWH-SRC-004 |
| LWH-FRM-003.F002 | template_version | text | submitted | Adopted form/indicator version | LWH-SRC-004 |
| LWH-FRM-003.F003 | period | period | submitted | Local period with timezone | LWH-SRC-004 |
| LWH-FRM-003.F004 | indicator_values | indicator_values | submitted | Counts/rates with source, unit and missingness | LWH-SRC-004 |
| LWH-FRM-003.F005 | source_refs | refs | submitted | Extract/register/version references | LWH-SRC-004 |
| LWH-FRM-003.F006 | limitations | text | conditional/optional | Coverage and data gaps | LWH-SRC-004 |
| LWH-FRM-003.F007 | attestation | text | submitted | Submitter declaration; separate from reviewer verification | LWH-SRC-004 |

**Cross-field/transition rule:** Exactly one current submitted version per obligation; prior versions remain; nil/partial/late are explicit states.

### LWH-FRM-004 — Zone coordination return

**Owner:** Zone health coordinator. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-004.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-004.F001 | zone_id | ref | submitted | Validated ministry zone | LWH-SRC-004 |
| LWH-FRM-004.F002 | period | period | submitted | Defined reporting period | LWH-SRC-004 |
| LWH-FRM-004.F003 | expected_unit_refs | refs | submitted | Obligation-based coverage | LWH-SRC-004 |
| LWH-FRM-004.F004 | community_events | indicator_values | conditional/optional | Distinct community notification stream | LWH-SRC-004 |
| LWH-FRM-004.F005 | source_refs | refs | submitted | Traceable sources with overlap assessment | LWH-SRC-004 |
| LWH-FRM-004.F006 | coordination_gaps | text | conditional/optional | Readiness, reporting or referral gaps | LWH-SRC-004 |
| LWH-FRM-004.F007 | action_refs | refs | conditional/optional | Owned follow-through | LWH-SRC-004 |

**Cross-field/transition rule:** Do not sum community reports and facility activity as unique people or population incidence.

### LWH-FRM-005 — Health event notification

**Owner:** Event review duty lead. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-005.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-005.F001 | event_type | concept | submitted | Versioned occurrence/safety category | LWH-SRC-007 |
| LWH-FRM-005.F002 | occurred_at | datetime | submitted | Occurrence or explicitly uncertain time | LWH-SRC-007 |
| LWH-FRM-005.F003 | location | location | conditional/optional | Minimum necessary precision | LWH-SRC-007 |
| LWH-FRM-005.F004 | source_context | text | submitted | Reporter/source and what is known | LWH-SRC-007 |
| LWH-FRM-005.F005 | review_state | review_state | submitted | Signal versus corroborated disposition | LWH-SRC-007 |
| LWH-FRM-005.F006 | urgency_context | text | conditional/optional | Concern for clinical duty assessment | LWH-SRC-007 |
| LWH-FRM-005.F007 | related_report_refs | refs | conditional/optional | Possible duplicate reports | LWH-SRC-007 |
| LWH-FRM-005.F008 | owner_team_id | ref | submitted | Actual accountable review queue | LWH-SRC-007 |

**Cross-field/transition rule:** Anonymous institutional notification excludes patient names; restricted clinical context is a separately authorised linked record.

### LWH-FRM-006 — Intervention and action plan

**Owner:** Programme owner. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-006.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-006.F001 | trigger_refs | refs | submitted | Evidence or decision supporting action | PROJECT-003 |
| LWH-FRM-006.F002 | intended_result | text | submitted | Specific service/health improvement purpose | PROJECT-003 |
| LWH-FRM-006.F003 | scope_refs | refs | submitted | Affected region/zone/facility/programme | PROJECT-003 |
| LWH-FRM-006.F004 | owner_team_id | ref | submitted | Accepted delivery owner tracked separately | PROJECT-003 |
| LWH-FRM-006.F005 | resources | text | submitted | Budget/people/dependencies; unknowns explicit | PROJECT-003 |
| LWH-FRM-006.F006 | due_at | datetime | submitted | Adopted commitment | PROJECT-003 |
| LWH-FRM-006.F007 | review_at | datetime | submitted | Outcome review distinct from completion | PROJECT-003 |
| LWH-FRM-006.F008 | completion_evidence | refs | conditional/optional | Reviewer acceptance required | PROJECT-003 |

**Cross-field/transition rule:** Assigned is not accepted; notification delivery does not prove fulfilment.

### LWH-FRM-007 — Central affiliation decision

**Owner:** Directorate standards decider. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-007.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-007.F001 | application_id | ref | submitted | Original application and submitted version | PROJECT-003 |
| LWH-FRM-007.F002 | criteria_version | text | submitted | Applicable adopted criteria | PROJECT-003 |
| LWH-FRM-007.F003 | evidence_refs | refs | submitted | Reviewed inspection/evidence dossier | PROJECT-003 |
| LWH-FRM-007.F004 | decision | decision | submitted | Approve/conditional/reject/suspend/remove/renew | PROJECT-003 |
| LWH-FRM-007.F005 | reason | text | submitted | Reasoned determination | PROJECT-003 |
| LWH-FRM-007.F006 | conditions | text | conditional/optional | Scope, corrective work and review | PROJECT-003 |
| LWH-FRM-007.F007 | effective_at | datetime | submitted | Decision start | PROJECT-003 |
| LWH-FRM-007.F008 | expires_at | datetime | conditional/optional | Required for time-limited recognition | PROJECT-003 |

**Cross-field/transition rule:** Only central authorised Directorate role can commit; retain notice and review route. Legacy prototype FRM-007 is an alias.

### LWH-FRM-008 — Inspection record

**Owner:** Standards inspector. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-008.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-008.F001 | application_id | ref | submitted | Inspected case | LWH-SRC-003 |
| LWH-FRM-008.F002 | scope | text | submitted | Services/criteria and visit scope | LWH-SRC-003 |
| LWH-FRM-008.F003 | inspector_id | ref | submitted | Assigned competent actor | LWH-SRC-003 |
| LWH-FRM-008.F004 | conflict_declaration | text | submitted | Independence or approved mitigation | LWH-SRC-003 |
| LWH-FRM-008.F005 | method | text | submitted | Interview/observation/record review as applicable | LWH-SRC-003 |
| LWH-FRM-008.F006 | findings | findings | submitted | Criterion, evidence, observation and severity-policy reference | LWH-SRC-003 |
| LWH-FRM-008.F007 | visit_period | period | submitted | Actual visit dates | LWH-SRC-003 |
| LWH-FRM-008.F008 | applicant_response | text | conditional/optional | Preserve separately from assessor conclusion | LWH-SRC-003 |

**Cross-field/transition rule:** Project inspection criteria are adapted/approved independently; do not label an IPC self-assessment as an official audit.

### LWH-FRM-009 — Renewal application

**Owner:** Facility accountable officer. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-009.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-009.F001 | affiliation_decision_id | ref | submitted | Current recognition version | PROJECT-003 |
| LWH-FRM-009.F002 | changes | text | submitted | Changed owner/site/services or explicit none | PROJECT-003 |
| LWH-FRM-009.F003 | updated_evidence | refs | submitted | Required current evidence | PROJECT-003 |
| LWH-FRM-009.F004 | criteria_version | text | submitted | Renewal assessment version | PROJECT-003 |
| LWH-FRM-009.F005 | open_findings | refs | conditional/optional | Unresolved conditions | PROJECT-003 |
| LWH-FRM-009.F006 | continuity_plan | text | conditional/optional | Active care/records continuity where restricted | PROJECT-003 |

**Cross-field/transition rule:** Submission does not extend expiry or create recognition automatically.

### LWH-FRM-010 — Corrective action and response

**Owner:** Finding owner/reviewer. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-010.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-010.F001 | finding_id | ref | submitted | Source finding | PROJECT-003 |
| LWH-FRM-010.F002 | required_action | text | submitted | Agreed correction | PROJECT-003 |
| LWH-FRM-010.F003 | owner_team_id | ref | submitted | Responsible delivery owner | PROJECT-003 |
| LWH-FRM-010.F004 | due_at | datetime | submitted | Adopted deadline | PROJECT-003 |
| LWH-FRM-010.F005 | response | text | conditional/optional | Applicant explanation | PROJECT-003 |
| LWH-FRM-010.F006 | evidence_refs | refs | conditional/optional | Actual resolution proof | PROJECT-003 |
| LWH-FRM-010.F007 | review_result | text | conditional/optional | Independent review and reason | PROJECT-003 |

**Cross-field/transition rule:** Completion submission remains unverified until the permitted reviewer accepts evidence.

### LWH-FRM-011 — Noncompliance decision and review

**Owner:** Directorate standards decider. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-011.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-011.F001 | source_decision_id | ref | submitted | Decision/finding under review | PROJECT-003 |
| LWH-FRM-011.F002 | notice_refs | refs | submitted | Notice and response opportunity | PROJECT-003 |
| LWH-FRM-011.F003 | risk_context | text | submitted | Evidence and proportionality | PROJECT-003 |
| LWH-FRM-011.F004 | proposed_restriction | text | submitted | Scope/duration/authority | PROJECT-003 |
| LWH-FRM-011.F005 | response | text | conditional/optional | Facility response preserved | PROJECT-003 |
| LWH-FRM-011.F006 | review_owner_id | ref | submitted | Independent review role | PROJECT-003 |
| LWH-FRM-011.F007 | continuity_actions | refs | conditional/optional | Patient/records/referral obligations | PROJECT-003 |

**Cross-field/transition rule:** No automated sanction from a score; preserve appeal/reinstatement history.

### LWH-FRM-012 — Data verification and correction

**Owner:** Health information reviewer. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-012.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-012.F001 | source_version_id | ref | submitted | Exact return/import version | LWH-SRC-005 |
| LWH-FRM-012.F002 | rule_version | text | submitted | Validation rules applied | LWH-SRC-005 |
| LWH-FRM-012.F003 | checks | findings | submitted | Method/evidence/findings | LWH-SRC-005 |
| LWH-FRM-012.F004 | disposition | review_state | submitted | Verify/return/dispute/duplicate as applicable | LWH-SRC-005 |
| LWH-FRM-012.F005 | override_reason | text | conditional/optional | Required for explained warning override | LWH-SRC-005 |
| LWH-FRM-012.F006 | correction_refs | refs | conditional/optional | Revised source and linked reason | LWH-SRC-005 |
| LWH-FRM-012.F007 | affected_snapshots | refs | conditional/optional | Recomputation/notice scope | LWH-SRC-005 |

**Cross-field/transition rule:** Reviewer cannot edit signed source clinical records; corrections follow custody workflow.

### LWH-FRM-013 — Education/content approval

**Owner:** Clinical editorial lead. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-013.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-013.F001 | content_type | concept | submitted | Clinical/policy/faith/rights purpose | LWH-SRC-032 |
| LWH-FRM-013.F002 | audience | text | submitted | Intended reader and eligibility | LWH-SRC-032 |
| LWH-FRM-013.F003 | source_refs | refs | submitted | Verified source/version | LWH-SRC-032 |
| LWH-FRM-013.F004 | author_id | ref | submitted | Accountable author | LWH-SRC-032 |
| LWH-FRM-013.F005 | reviewer_id | ref | submitted | Qualified reviewer | LWH-SRC-032 |
| LWH-FRM-013.F006 | jurisdiction_language | text | submitted | Applicability and translation version | LWH-SRC-032 |
| LWH-FRM-013.F007 | valid_period | period | submitted | Publication/review/expiry interval | LWH-SRC-032 |
| LWH-FRM-013.F008 | correction_plan | text | conditional/optional | Affected recipient/cache handling | LWH-SRC-032 |

**Cross-field/transition rule:** Clinical and ministry policy approval roles are distinct; unclear recorded wording is not a publication source.

### LWH-FRM-014 — Programme outcome review

**Owner:** Intervention reviewer. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-014.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-014.F001 | intervention_id | ref | submitted | Action under review | PROJECT-003 |
| LWH-FRM-014.F002 | baseline_refs | refs | submitted | Measure/cohort/period | PROJECT-003 |
| LWH-FRM-014.F003 | completion_evidence | refs | submitted | Actual activity evidence | PROJECT-003 |
| LWH-FRM-014.F004 | followup_refs | refs | submitted | Comparable later measures | PROJECT-003 |
| LWH-FRM-014.F005 | coverage_changes | text | submitted | Missingness/comparability | PROJECT-003 |
| LWH-FRM-014.F006 | limitations | text | submitted | Causality and selection limits | PROJECT-003 |
| LWH-FRM-014.F007 | decision | text | submitted | Close/reopen/continue with rationale | PROJECT-003 |

**Cross-field/transition rule:** Activity completion and observed outcome are separate; causal impact requires suitable evaluation.

### LWH-FRM-015 — Clinic/service activation

**Owner:** Clinical network lead. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-015.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-015.F001 | facility_service_id | ref | submitted | Service/capability being activated | LWH-SRC-002 |
| LWH-FRM-015.F002 | population_scope | text | submitted | Approved care scope/exclusions | LWH-SRC-002 |
| LWH-FRM-015.F003 | privilege_refs | refs | submitted | Credentialed/privileged team | LWH-SRC-002 |
| LWH-FRM-015.F004 | readiness_refs | refs | submitted | Verified essential readiness | LWH-SRC-002 |
| LWH-FRM-015.F005 | operating_hours | text | submitted | Time zone and duty coverage | LWH-SRC-002 |
| LWH-FRM-015.F006 | escalation_routes | text | submitted | Tested local contacts/owners | LWH-SRC-002 |
| LWH-FRM-015.F007 | receiving_partners | refs | conditional/optional | Verified referral pathway agreements | LWH-SRC-002 |

**Cross-field/transition rule:** Activation requires an adopted country package and actual staffed readiness; directory creation is insufficient.

### LWH-FRM-016 — Referral and accepted handover

**Owner:** Referring/receiving clinical teams. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-016.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-016.F001 | source_encounter_id | ref | submitted | Correct clinical context | LWH-SRC-010 |
| LWH-FRM-016.F002 | need | text | submitted | Reason and required capability | LWH-SRC-010 |
| LWH-FRM-016.F003 | receiver_service_id | ref | submitted | Suitable receiving service | LWH-SRC-010 |
| LWH-FRM-016.F004 | sharing_grant_id | ref | submitted | Minimum authorised summary scope | LWH-SRC-010 |
| LWH-FRM-016.F005 | acceptance | handover | conditional/optional | Actual recipient/time and conditions | LWH-SRC-010 |
| LWH-FRM-016.F006 | transport_context | text | conditional/optional | Real feasibility/arrangements | LWH-SRC-010 |
| LWH-FRM-016.F007 | outcome | text | conditional/optional | Receipt/clinical outcome and continuing owner | LWH-SRC-010 |
| LWH-FRM-016.F008 | pending_task_refs | refs | conditional/optional | Results/medicines/follow-up to retain | LWH-SRC-010 |

**Cross-field/transition rule:** Request, acceptance, departure, receipt and outcome remain separate; sender retains accountability until accepted transfer.

### LWH-FRM-017 — Record-sharing authority

**Owner:** Patient/representative and record custodian. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-017.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-017.F001 | recipient_refs | refs | submitted | Named team/facility/recipient; no universal public browse | LWH-SRC-044 |
| LWH-FRM-017.F002 | purpose | concept | submitted | Approved purpose | LWH-SRC-044 |
| LWH-FRM-017.F003 | record_scope | refs | submitted | Permitted records/fields | LWH-SRC-044 |
| LWH-FRM-017.F004 | authority_type | concept | submitted | Patient/representative or other applicable authority | LWH-SRC-044 |
| LWH-FRM-017.F005 | authority_evidence | refs | submitted | Evidence/consent version | LWH-SRC-044 |
| LWH-FRM-017.F006 | valid_until | datetime | submitted | Bounded access | LWH-SRC-044 |
| LWH-FRM-017.F007 | revocation_context | text | conditional/optional | Future-access stop and retained-copy obligations | LWH-SRC-044 |

**Cross-field/transition rule:** Grant is purpose/recipient scoped; coded data stays protected; revocation is not destructive historical erasure.

### LWH-FRM-018 — Organisation and delegated role setup

**Owner:** Identity steward. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-018.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-018.F001 | organisation_id | ref | submitted | Validated unit/operator | PROJECT-003 |
| LWH-FRM-018.F002 | parent_id | ref | conditional/optional | Typed ministry relationship; no forced country level | PROJECT-003 |
| LWH-FRM-018.F003 | relationship_type | text | submitted | Region/zone/optional unit type | PROJECT-003 |
| LWH-FRM-018.F004 | actor_id | ref | submitted | Verified invitee/member | PROJECT-003 |
| LWH-FRM-018.F005 | role | text | submitted | Permitted role | PROJECT-003 |
| LWH-FRM-018.F006 | resource_scope | refs | submitted | Explicit facilities/units/resources | PROJECT-003 |
| LWH-FRM-018.F007 | valid_period | period | submitted | Start/end and acting assignment | PROJECT-003 |
| LWH-FRM-018.F008 | grantor_id | ref | submitted | Authorised grantor/delegation depth | PROJECT-003 |

**Cross-field/transition rule:** Reject hierarchy cycles, incompatible grants and delegation outside grantor authority.

### LWH-FRM-019 — Rights request or complaint

**Owner:** Privacy/complaints owner. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-019.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-019.F001 | requester_authority | text | submitted | Verified right to act; minimum evidence | LWH-SRC-032 |
| LWH-FRM-019.F002 | request_type | concept | submitted | Access/correction/sharing/complaint/other | LWH-SRC-032 |
| LWH-FRM-019.F003 | record_refs | refs | conditional/optional | Only necessary case scope | LWH-SRC-032 |
| LWH-FRM-019.F004 | request | text | submitted | Concern and desired response | LWH-SRC-032 |
| LWH-FRM-019.F005 | owner_team_id | ref | submitted | Accountable queue | LWH-SRC-032 |
| LWH-FRM-019.F006 | disposition | text | conditional/optional | Reasoned resolution and review route | LWH-SRC-032 |

**Cross-field/transition rule:** Jurisdiction response obligations apply; do not expose a record while verifying authority.

### LWH-FRM-020 — Programme funding agreement schedule

**Owner:** Programme finance lead. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-020.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-020.F001 | party_refs | refs | submitted | Operator, funder and delivery responsibilities | PROJECT-003 |
| LWH-FRM-020.F002 | services | concepts | submitted | Covered approved services | PROJECT-003 |
| LWH-FRM-020.F003 | eligibility | text | submitted | Cohort rules | PROJECT-003 |
| LWH-FRM-020.F004 | funding | money | submitted | Currency/minor-unit amount; no invented commitment | PROJECT-003 |
| LWH-FRM-020.F005 | restrictions | text | submitted | Permitted use, reservation and release | PROJECT-003 |
| LWH-FRM-020.F006 | reporting_terms | text | submitted | Permitted impact/financial reporting | PROJECT-003 |
| LWH-FRM-020.F007 | reconciliation_terms | text | submitted | Evidence, refunds and independent approval | PROJECT-003 |

**Cross-field/transition rule:** Funding receipt, restricted balances, service fulfilment and recognised revenue are distinct.

### LWH-FRM-021 — Patient registration and matching

**Owner:** Registration/record custodian. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-021.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-021.F001 | identifiers | identifiers | submitted | Issuing systems/local IDs or provisional status | LWH-SRC-036 |
| LWH-FRM-021.F002 | name | text | conditional/optional | Known name; unknown stays explicit | LWH-SRC-036 |
| LWH-FRM-021.F003 | birth_date | date | conditional/optional | Known/estimated with source; no inferred date | LWH-SRC-036 |
| LWH-FRM-021.F004 | contacts | contacts | conditional/optional | Patient and permitted contact purpose | LWH-SRC-036 |
| LWH-FRM-021.F005 | demographic_context | text | conditional/optional | Relevant sex/gender/other context; purpose limited | LWH-SRC-036 |
| LWH-FRM-021.F006 | match_evidence | text | conditional/optional | Reviewed links and identity confirmation | LWH-SRC-036 |

**Cross-field/transition rule:** Generate a provisional patient ID before care if necessary; no silent automatic chart merge.

### LWH-FRM-022 — Representative/caregiver authority

**Owner:** Record custodian. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-022.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-022.F001 | actor_id | ref | submitted | Verified person acting | LWH-SRC-044 |
| LWH-FRM-022.F002 | relationship | concept | submitted | Family relationship does not itself establish authority | LWH-SRC-044 |
| LWH-FRM-022.F003 | authority_type | concept | submitted | Applicable legal/patient authority | LWH-SRC-044 |
| LWH-FRM-022.F004 | evidence_refs | refs | submitted | Verified evidence | LWH-SRC-044 |
| LWH-FRM-022.F005 | allowed_actions | texts | submitted | Action-specific grant | LWH-SRC-044 |
| LWH-FRM-022.F006 | valid_period | period | submitted | Expiry/reassessment including age transitions | LWH-SRC-044 |

**Cross-field/transition rule:** Subject/actor remain separate; authority can differ by record category and action.

### LWH-FRM-023 — Encounter intake and assessment

**Owner:** Treating clinician. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-023.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-023.F001 | encounter_kind | concept | submitted | Walk-in/booked/remote/referred/emergency | LWH-SRC-037 |
| LWH-FRM-023.F002 | concern | text | submitted | Patient-reported complaint/source | LWH-SRC-037 |
| LWH-FRM-023.F003 | history | text | conditional/optional | Relevant findings with provenance | LWH-SRC-037 |
| LWH-FRM-023.F004 | examination | text | conditional/optional | Actual examined findings only | LWH-SRC-037 |
| LWH-FRM-023.F005 | assessment | concepts | conditional/optional | Clinician assessment and verification status | LWH-SRC-037 |
| LWH-FRM-023.F006 | plan | text | conditional/optional | Reviewed clinical plan | LWH-SRC-037 |
| LWH-FRM-023.F007 | disposition | concept | conditional/optional | Home/admit/refer/observe/other | LWH-SRC-037 |
| LWH-FRM-023.F008 | responsible_team_id | ref | submitted | Current clinical owner | LWH-SRC-037 |

**Cross-field/transition rule:** Signing/disposition requires current privilege, appropriate assessment and owned pending obligations.

### LWH-FRM-024 — Triage and observations

**Owner:** Privileged triage/clinical staff. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-024.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-024.F001 | measurements | observations | conditional/optional | Typed values, units, effective time and method | LWH-SRC-038 |
| LWH-FRM-024.F002 | clinical_context | text | submitted | Observed concerns and relevant unknowns | LWH-SRC-038 |
| LWH-FRM-024.F003 | triage_policy_version | text | submitted | Approved setting/population policy | LWH-SRC-038 |
| LWH-FRM-024.F004 | urgency_assessment | concept | submitted | Attributed human/approved rule decision | LWH-SRC-038 |
| LWH-FRM-024.F005 | assessor_id | ref | submitted | Competent assigned actor | LWH-SRC-038 |
| LWH-FRM-024.F006 | escalation | handover | conditional/optional | Actual accepted urgent route | LWH-SRC-038 |

**Cross-field/transition rule:** Facility triage tools are not automatically valid for unsupervised remote triage; no guessed clinical thresholds.

### LWH-FRM-025 — Clinical document and addendum

**Owner:** Clinical author/custodian. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-025.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-025.F001 | document_type | concept | submitted | Note/summary/addendum/correction | LWH-SRC-045 |
| LWH-FRM-025.F002 | content | text | submitted | Actual authored narrative or structured references | LWH-SRC-045 |
| LWH-FRM-025.F003 | source_refs | refs | conditional/optional | Reviewed source material | LWH-SRC-045 |
| LWH-FRM-025.F004 | attestation_context | text | conditional/optional | Intentional signer/privilege check occurs in command | LWH-SRC-045 |
| LWH-FRM-025.F005 | amends_version_id | ref | conditional/optional | Required for addendum/correction | LWH-SRC-045 |
| LWH-FRM-025.F006 | reason | text | conditional/optional | Required for amendment/error designation | LWH-SRC-045 |

**Cross-field/transition rule:** Signed content is immutable; correction preserves original and invalidates derived summaries as needed.

### LWH-FRM-026 — Problem, allergy and medication reconciliation

**Owner:** Treating clinical team. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-026.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-026.F001 | problems | concepts | conditional/optional | Status/certainty/source captured in linked records | LWH-SRC-039 |
| LWH-FRM-026.F002 | allergy_status | allergy_status | submitted | Unknown/none-known/known/not-assessed are distinct | LWH-SRC-039 |
| LWH-FRM-026.F003 | allergies | allergies | conditional/optional | Agent, reaction, certainty and source | LWH-SRC-039 |
| LWH-FRM-026.F004 | medicine_refs | refs | conditional/optional | Current reported/ordered/dispensed/administered distinctions | LWH-SRC-039 |
| LWH-FRM-026.F005 | reconciliation_findings | text | submitted | Actual review, conflicts and missingness | LWH-SRC-039 |
| LWH-FRM-026.F006 | review_owner_id | ref | submitted | Responsible clinician/pharmacist | LWH-SRC-039 |

**Cross-field/transition rule:** No allergy rows does not mean no allergies; clinical list changes require authorised review.

### LWH-FRM-027 — Clinical diagnostic/service order

**Owner:** Ordering clinician. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-027.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-027.F001 | order_kind | concept | submitted | Diagnostic/procedure/referral/other | LWH-SRC-037 |
| LWH-FRM-027.F002 | requested_service | concept | submitted | Catalogue service with version | LWH-SRC-037 |
| LWH-FRM-027.F003 | clinical_question | text | submitted | Reason and relevant context | LWH-SRC-037 |
| LWH-FRM-027.F004 | priority | concept | submitted | Approved clinical priority | LWH-SRC-037 |
| LWH-FRM-027.F005 | specimen_requirements | text | conditional/optional | Applicable local department instructions | LWH-SRC-037 |
| LWH-FRM-027.F006 | requester_id | ref | submitted | Privileged requester | LWH-SRC-037 |
| LWH-FRM-027.F007 | review_owner_id | ref | submitted | Result/fulfilment owner | LWH-SRC-037 |

**Cross-field/transition rule:** Order release checks privilege and signed version; cancellation after performance preserves actual execution.

### LWH-FRM-028 — Specimen collection and receipt

**Owner:** Diagnostic department. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-028.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-028.F001 | order_id | ref | submitted | Accepted order | LWH-SRC-043 |
| LWH-FRM-028.F002 | accession | text | submitted | Local/site-qualified identifier | LWH-SRC-043 |
| LWH-FRM-028.F003 | specimen_type | concept | submitted | Catalogue requirement | LWH-SRC-043 |
| LWH-FRM-028.F004 | collected_at | datetime | conditional/optional | Actual collection time | LWH-SRC-043 |
| LWH-FRM-028.F005 | collector_id | ref | conditional/optional | Actual performer | LWH-SRC-043 |
| LWH-FRM-028.F006 | received_at | datetime | conditional/optional | Actual receipt | LWH-SRC-043 |
| LWH-FRM-028.F007 | condition_or_rejection | text | conditional/optional | Observed condition and reason; recollection task | LWH-SRC-043 |

**Cross-field/transition rule:** Identity/label/order match is checked at collection and receipt; missing facts do not become completed stages.

### LWH-FRM-029 — Diagnostic result and amendment

**Owner:** Diagnostic verifier. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-029.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-029.F001 | order_refs | refs | submitted | Applicable orders/accessions | LWH-SRC-042 |
| LWH-FRM-029.F002 | results | observations | submitted | Value/code/text with unit, method, absence and reference context | LWH-SRC-042 |
| LWH-FRM-029.F003 | report_status | report_status | submitted | Preliminary/final/corrected/cancelled/error | LWH-SRC-042 |
| LWH-FRM-029.F004 | verifier_id | ref | conditional/optional | Required for authorised release | LWH-SRC-042 |
| LWH-FRM-029.F005 | amends_version_id | ref | conditional/optional | Required for correction | LWH-SRC-042 |
| LWH-FRM-029.F006 | critical_review | handover | conditional/optional | Adopted trigger, actual acknowledgement and response | LWH-SRC-042 |
| LWH-FRM-029.F007 | source_document_refs | refs | conditional/optional | External report/OCR provenance | LWH-SRC-042 |

**Cross-field/transition rule:** Final/corrected report requires authorised verifier; critical review remains a separate clinical obligation.

### LWH-FRM-030 — Medication order

**Owner:** Privileged prescriber. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-030.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-030.F001 | medication | concept | submitted | Approved code/product/form/strength reference | LWH-SRC-040 |
| LWH-FRM-030.F002 | dose | quantity | submitted | Exact decimal and unit; no default dose | LWH-SRC-040 |
| LWH-FRM-030.F003 | route | concept | submitted | Explicit route | LWH-SRC-040 |
| LWH-FRM-030.F004 | timing | text | submitted | Complete structured timing intent per clinical package | LWH-SRC-040 |
| LWH-FRM-030.F005 | duration_or_stop | text | submitted | Applicable end/review instruction | LWH-SRC-040 |
| LWH-FRM-030.F006 | indication | text | submitted | Clinical purpose | LWH-SRC-040 |
| LWH-FRM-030.F007 | dispense_quantity | quantity | conditional/optional | Exact quantity and unit | LWH-SRC-040 |
| LWH-FRM-030.F008 | substitution_policy | text | submitted | Explicit allowed/forbidden/clinical-review rule | LWH-SRC-040 |

**Cross-field/transition rule:** No order release with absent dose/route/timing or missing required safety review; all values remain prescriber decisions.

### LWH-FRM-031 — Medication dispensing

**Owner:** Pharmacy/dispensing staff. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-031.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-031.F001 | order_version_id | ref | submitted | Current authorised intent | LWH-SRC-047 |
| LWH-FRM-031.F002 | actual_product | concept | submitted | Actual dispensed product/strength | LWH-SRC-047 |
| LWH-FRM-031.F003 | quantity | quantity | submitted | Actual quantity/unit | LWH-SRC-047 |
| LWH-FRM-031.F004 | lot_refs | refs | submitted | Batch/expiry traceability | LWH-SRC-047 |
| LWH-FRM-031.F005 | dispensed_at | datetime | submitted | Actual event time | LWH-SRC-047 |
| LWH-FRM-031.F006 | substitution_authority | text | conditional/optional | Required if item differs | LWH-SRC-047 |
| LWH-FRM-031.F007 | counselling_context | text | conditional/optional | Instructions provided and responsible staff | LWH-SRC-047 |

**Cross-field/transition rule:** Actual supply creates stock movement; it does not prove administration or adherence.

### LWH-FRM-032 — Medication administration or omission

**Owner:** Privileged nursing/clinical staff. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-032.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-032.F001 | order_version_id | ref | submitted | Rechecked current order | LWH-SRC-041 |
| LWH-FRM-032.F002 | administration_status | admin_status | submitted | Given/not-given/held/refused/error | LWH-SRC-041 |
| LWH-FRM-032.F003 | actual_product | concept | conditional/optional | Required for a given dose | LWH-SRC-041 |
| LWH-FRM-032.F004 | actual_dose | quantity | conditional/optional | Required for a given dose | LWH-SRC-041 |
| LWH-FRM-032.F005 | performed_at | datetime | submitted | Actual event time; late entry explicit | LWH-SRC-041 |
| LWH-FRM-032.F006 | performer_id | ref | submitted | Actual competent actor | LWH-SRC-041 |
| LWH-FRM-032.F007 | reason | text | conditional/optional | Required for omission/deviation | LWH-SRC-041 |
| LWH-FRM-032.F008 | second_check_ref | ref | conditional/optional | Where required by approved high-risk policy | LWH-SRC-041 |

**Cross-field/transition rule:** Given requires actual product/dose; reason required for not-given/held/refused; retry is idempotent.

### LWH-FRM-033 — Clinical stock movement

**Owner:** Clinical stock custodian. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-033.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-033.F001 | product | concept | submitted | Product/form/strength/unit | PROJECT-003 |
| LWH-FRM-033.F002 | lot_id | ref | submitted | Batch/expiry/location | PROJECT-003 |
| LWH-FRM-033.F003 | movement_type | stock_move | submitted | Receipt/issue/return/quarantine/adjustment/reversal | PROJECT-003 |
| LWH-FRM-033.F004 | quantity | quantity | submitted | Exact signed movement under direction rules | PROJECT-003 |
| LWH-FRM-033.F005 | source_event_id | ref | submitted | Unique clinical/receiving event | PROJECT-003 |
| LWH-FRM-033.F006 | reason | text | conditional/optional | Required for adjustment/quarantine | PROJECT-003 |
| LWH-FRM-033.F007 | approval_ref | ref | conditional/optional | Applicable independent authorisation | PROJECT-003 |

**Cross-field/transition rule:** No duplicate stock effects; unconfirmed physical stock is not invented; optional procurement is not required.

### LWH-FRM-034 — Admission and bed assignment

**Owner:** Admitting/ward team. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-034.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-034.F001 | admission_order_id | ref | submitted | Authorised admission intent | LWH-SRC-037 |
| LWH-FRM-034.F002 | stay_id | ref | submitted | Locally authoritative stay | LWH-SRC-037 |
| LWH-FRM-034.F003 | ward_id | ref | submitted | Suitable service | LWH-SRC-037 |
| LWH-FRM-034.F004 | bed_id | ref | conditional/optional | Actual accepted bed or explicit awaiting status | LWH-SRC-037 |
| LWH-FRM-034.F005 | responsible_team_id | ref | submitted | Accepted clinical team | LWH-SRC-037 |
| LWH-FRM-034.F006 | admitted_at | datetime | conditional/optional | Actual receipt/admission time | LWH-SRC-037 |
| LWH-FRM-034.F007 | handover | handover | conditional/optional | Sender/receiver and outstanding work | LWH-SRC-037 |

**Cross-field/transition rule:** One active exclusive occupancy per bed; actual admission distinct from reservation/order.

### LWH-FRM-035 — Nursing assessment and care

**Owner:** Assigned nursing team. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-035.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-035.F001 | care_type | concept | submitted | Assessment/observation/task/intake-output/other | LWH-SRC-038 |
| LWH-FRM-035.F002 | observations | observations | conditional/optional | Typed actual measurements | LWH-SRC-038 |
| LWH-FRM-035.F003 | care_performed | text | submitted | Actual work, exceptions or refusal | LWH-SRC-038 |
| LWH-FRM-035.F004 | performed_at | datetime | submitted | Actual time | LWH-SRC-038 |
| LWH-FRM-035.F005 | performer_id | ref | submitted | Assigned actor | LWH-SRC-038 |
| LWH-FRM-035.F006 | escalation | handover | conditional/optional | Concern, recipient and acknowledgement | LWH-SRC-038 |
| LWH-FRM-035.F007 | plan_task_refs | refs | conditional/optional | Care-plan/MAR/tasks; do not duplicate dose events | LWH-SRC-038 |

**Cross-field/transition rule:** Planned care and actual care are separate; omissions and late entries remain attributed.

### LWH-FRM-036 — Transfer and discharge package

**Owner:** Clinical discharge/handover team. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-036.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-036.F001 | transition_type | concept | submitted | Ward/facility transfer, discharge, leave, death/other | LWH-SRC-010 |
| LWH-FRM-036.F002 | clinical_summary | text | submitted | Signed relevant findings and course | LWH-SRC-010 |
| LWH-FRM-036.F003 | medicine_reconciliation_refs | refs | submitted | Reviewed continuing/stopped instructions | LWH-SRC-010 |
| LWH-FRM-036.F004 | pending_order_task_refs | refs | conditional/optional | Results and follow-up remain owned | LWH-SRC-010 |
| LWH-FRM-036.F005 | receiving_handover | handover | conditional/optional | Required for transfer | LWH-SRC-010 |
| LWH-FRM-036.F006 | patient_instructions | text | submitted | Reviewed usable instructions | LWH-SRC-010 |
| LWH-FRM-036.F007 | followup_plan_ref | ref | submitted | Responsible team and review path | LWH-SRC-010 |

**Cross-field/transition rule:** Pending result cannot disappear at discharge; financial settlement and clinical disposition remain separate.

### LWH-FRM-037 — Maternal antenatal review

**Owner:** Maternal clinical lead. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-037.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-037.F001 | pregnancy_episode_id | ref | submitted | Correct maternal episode | LWH-SRC-011 |
| LWH-FRM-037.F002 | dating_context | text | submitted | Gestation/date estimate and source | LWH-SRC-011 |
| LWH-FRM-037.F003 | relevant_history | text | conditional/optional | Reviewed maternal history | LWH-SRC-011 |
| LWH-FRM-037.F004 | observations | observations | conditional/optional | Actual clinical measures | LWH-SRC-011 |
| LWH-FRM-037.F005 | assessment_plan | text | submitted | Clinician decisions under applicable protocol | LWH-SRC-011 |
| LWH-FRM-037.F006 | investigation_refs | refs | conditional/optional | Orders/results | LWH-SRC-011 |
| LWH-FRM-037.F007 | followup_ref | ref | submitted | Accepted review/referral responsibility | LWH-SRC-011 |

**Cross-field/transition rule:** Source-informed draft structure; no generated clinical schedule, dose or risk threshold.

### LWH-FRM-038 — Birth and newborn record

**Owner:** Birth team and record custodian. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-038.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-038.F001 | pregnancy_episode_id | ref | submitted | Maternal context | LWH-SRC-034 |
| LWH-FRM-038.F002 | actual_birth_at | datetime | submitted | Actual/uncertain recorded time context | LWH-SRC-034 |
| LWH-FRM-038.F003 | birth_context | text | submitted | Actual clinical course/outcome | LWH-SRC-034 |
| LWH-FRM-038.F004 | infant_patient_refs | refs | submitted | Independent ID per infant | LWH-SRC-034 |
| LWH-FRM-038.F005 | relationship_evidence | text | submitted | Mother/infant matching and verification | LWH-SRC-034 |
| LWH-FRM-038.F006 | team_refs | refs | submitted | Actual responsible/attesting team | LWH-SRC-034 |
| LWH-FRM-038.F007 | handover | handover | submitted | Maternal and infant continuing care | LWH-SRC-034 |

**Cross-field/transition rule:** Multiple births cannot share a patient ID; maternal/newborn consent and access scopes remain distinct.

### LWH-FRM-039 — Postnatal review

**Owner:** Maternal/newborn clinical team. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-039.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-039.F001 | programme_episode_id | ref | submitted | Maternal or newborn episode | LWH-SRC-012 |
| LWH-FRM-039.F002 | clinical_context | text | submitted | Relevant symptoms/concerns and source | LWH-SRC-012 |
| LWH-FRM-039.F003 | observations | observations | conditional/optional | Actual measurements | LWH-SRC-012 |
| LWH-FRM-039.F004 | feeding_support_context | text | conditional/optional | Applicable reviewed support | LWH-SRC-012 |
| LWH-FRM-039.F005 | assessment_plan | text | submitted | Responsible clinician decision | LWH-SRC-012 |
| LWH-FRM-039.F006 | followup_ref | ref | submitted | Review/escalation and accepted owner | LWH-SRC-012 |

**Cross-field/transition rule:** Separate maternal/newborn subjects; service-specific clinical content requires adopted package.

### LWH-FRM-040 — Child growth and immunisation

**Owner:** Child-health clinical team. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-040.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-040.F001 | measurement_context | observations | conditional/optional | Age/source and actual measurements/units | LWH-SRC-013 |
| LWH-FRM-040.F002 | immunisation_product | concept | conditional/optional | Actual vaccine product when administered | LWH-SRC-013 |
| LWH-FRM-040.F003 | batch_expiry | text | conditional/optional | Required traceability for administration | LWH-SRC-013 |
| LWH-FRM-040.F004 | administered_at | datetime | conditional/optional | Actual administration event | LWH-SRC-013 |
| LWH-FRM-040.F005 | schedule_version | text | conditional/optional | Required for generated recommendation | LWH-SRC-013 |
| LWH-FRM-040.F006 | clinical_review | text | submitted | Actual decision and relevant unknowns | LWH-SRC-013 |
| LWH-FRM-040.F007 | followup_ref | ref | submitted | Owned next review | LWH-SRC-013 |

**Cross-field/transition rule:** No dose schedule or growth interpretation without valid applicable content; caregiver authority checked.

### LWH-FRM-041 — Procedure and safety phases

**Owner:** Procedural clinical team. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-041.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-041.F001 | procedure_order_id | ref | submitted | Planned intervention and privileged team | LWH-SRC-015 |
| LWH-FRM-041.F002 | consent_ref | ref | submitted | Applicable informed consent/authority | LWH-SRC-015 |
| LWH-FRM-041.F003 | safety_phases | findings | submitted | Actual applicable checks, participants and exceptions | LWH-SRC-015 |
| LWH-FRM-041.F004 | performed_procedure | concept | conditional/optional | Only after actual performance | LWH-SRC-015 |
| LWH-FRM-041.F005 | findings_complications | text | conditional/optional | Actual operative/procedural findings | LWH-SRC-015 |
| LWH-FRM-041.F006 | specimen_device_refs | refs | conditional/optional | Traceability | LWH-SRC-015 |
| LWH-FRM-041.F007 | recovery_handover | handover | conditional/optional | Required before transfer of responsibility | LWH-SRC-015 |

**Cross-field/transition rule:** Planned is not performed; source checklist reuse requires licensing/attribution review and local adaptation.

### LWH-FRM-042 — Anaesthesia and recovery record

**Owner:** Privileged anaesthesia team. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-042.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-042.F001 | procedure_ref | ref | submitted | Correct procedure/encounter | PROJECT-003 |
| LWH-FRM-042.F002 | preassessment | text | submitted | Actual assessment and plan | PROJECT-003 |
| LWH-FRM-042.F003 | monitoring | observations | conditional/optional | Actual time-series observations | PROJECT-003 |
| LWH-FRM-042.F004 | medication_event_refs | refs | conditional/optional | Link signed orders/actual administrations | PROJECT-003 |
| LWH-FRM-042.F005 | clinical_events | text | conditional/optional | Actual course, complications and interventions | PROJECT-003 |
| LWH-FRM-042.F006 | recovery_handover | handover | conditional/optional | Actual accepted receiver and status | PROJECT-003 |

**Cross-field/transition rule:** Local service-specific template is clinically adopted; no automated anaesthetic dosing guidance.

### LWH-FRM-043 — Transfusion and component traceability

**Owner:** Blood-bank and clinical team. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-043.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-043.F001 | clinical_order_id | ref | submitted | Authorised clinical need | PROJECT-003 |
| LWH-FRM-043.F002 | specimen_crossmatch_refs | refs | submitted | Qualified laboratory compatibility evidence | PROJECT-003 |
| LWH-FRM-043.F003 | component_unit_id | text | submitted | Actual blood component/unit | PROJECT-003 |
| LWH-FRM-043.F004 | verification_checks | findings | submitted | Identity/unit/expiry and applicable human checks | PROJECT-003 |
| LWH-FRM-043.F005 | actual_period | period | conditional/optional | Actual start/end | PROJECT-003 |
| LWH-FRM-043.F006 | monitoring_reaction | text | conditional/optional | Actual observations/reaction and response | PROJECT-003 |
| LWH-FRM-043.F007 | handover | handover | conditional/optional | Continuing clinical owner | PROJECT-003 |

**Cross-field/transition rule:** Compatibility is not inferred by AI; authorised local blood-bank evidence and clinical protocol govern release.

### LWH-FRM-044 — Care charge, invoice and payer split

**Owner:** Care finance team. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-044.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-044.F001 | service_evidence_refs | refs | submitted | Actual billable service | PROJECT-003 |
| LWH-FRM-044.F002 | tariff_version | text | submitted | Approved price/contract | PROJECT-003 |
| LWH-FRM-044.F003 | line_amounts | money_lines | submitted | Integer minor units/currency | PROJECT-003 |
| LWH-FRM-044.F004 | payer_responsibilities | text | submitted | Patient/sponsor/other split and authority | PROJECT-003 |
| LWH-FRM-044.F005 | invoice_state | text | submitted | Draft/issued/adjusted/settled as applicable | PROJECT-003 |
| LWH-FRM-044.F006 | adjustment_reason | text | conditional/optional | Approval and reversal linkage | PROJECT-003 |

**Cross-field/transition rule:** Invoice does not prove payment; clinical urgency is independent of balance.

### LWH-FRM-045 — Payment receipt and claim reconciliation

**Owner:** Finance reconciliation team. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-045.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-045.F001 | source_transaction_id | text | submitted | Provider/cash/claim namespace plus unique key | PROJECT-003 |
| LWH-FRM-045.F002 | amount | money | submitted | Actual or explicitly pending amount state | PROJECT-003 |
| LWH-FRM-045.F003 | receipt_or_claim_state | text | submitted | Intent/receipt/claim approval/remittance distinct | PROJECT-003 |
| LWH-FRM-045.F004 | source_evidence | refs | submitted | Actual provider/cash/adjudication evidence | PROJECT-003 |
| LWH-FRM-045.F005 | allocation_refs | refs | conditional/optional | Invoice/benefit allocations | PROJECT-003 |
| LWH-FRM-045.F006 | approval_reason | text | conditional/optional | Sensitive adjustment authorisation | PROJECT-003 |

**Cross-field/transition rule:** No settled status from a timeout or unverified callback; balanced effects and maker-checker apply.

### LWH-FRM-046 — Downtime and sync reconciliation

**Owner:** Facility duty and technical leads. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-046.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-046.F001 | node_id | ref | submitted | Actual authority node and epoch | PROJECT-003 |
| LWH-FRM-046.F002 | outage_period | period | submitted | WAN/LAN/power/device fault context | PROJECT-003 |
| LWH-FRM-046.F003 | affected_services | concepts | submitted | Actual limitations | PROJECT-003 |
| LWH-FRM-046.F004 | local_continuity_evidence | refs | submitted | Clinical transactions/backup/manual log | PROJECT-003 |
| LWH-FRM-046.F005 | sync_outcomes | text | conditional/optional | Accepted/duplicate/conflict/rejected/dependency counts | PROJECT-003 |
| LWH-FRM-046.F006 | open_exception_refs | refs | conditional/optional | Owned reconciliation tasks | PROJECT-003 |
| LWH-FRM-046.F007 | recovery_signoff | text | conditional/optional | Clinical/data/finance/technical review | PROJECT-003 |

**Cross-field/transition rule:** Local recovery is distinct from completed clinical/financial reconciliation; no blanket replay-success claim.

### LWH-FRM-047 — Country and service activation dossier

**Owner:** Directorate country activation owner. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-047.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-047.F001 | country_profile_id | text | submitted | Unselected until actual adoption | PROJECT-003 |
| LWH-FRM-047.F002 | operator_entities | refs | submitted | Clinical/data/finance responsibility | PROJECT-003 |
| LWH-FRM-047.F003 | legal_privacy_reviews | refs | submitted | Applicable obligations, transfers, retention, rights | PROJECT-003 |
| LWH-FRM-047.F004 | service_privilege_packages | refs | submitted | Actual clinical scope and professional authority | PROJECT-003 |
| LWH-FRM-047.F005 | hosting_processing | text | submitted | Approved data/AI/backup locations | PROJECT-003 |
| LWH-FRM-047.F006 | readiness_test_refs | refs | submitted | Evidence including offline workflow and restore | PROJECT-003 |
| LWH-FRM-047.F007 | activation_decision | text | conditional/optional | Authorised scoped decision/version | PROJECT-003 |

**Cross-field/transition rule:** Global architecture does not activate an unreviewed country; no default pilot location is assumed.

### LWH-FRM-048 — Optional enterprise activation and transactions

**Owner:** Enterprise module owner. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-048.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-048.F001 | module | erp_module | submitted | Accounting/procurement/HR/payroll | PROJECT-003 |
| LWH-FRM-048.F002 | contract_ref | ref | submitted | Optional entitlement and responsibilities | PROJECT-003 |
| LWH-FRM-048.F003 | country_rule_version | text | submitted | Approved relevant rules | PROJECT-003 |
| LWH-FRM-048.F004 | approval_matrix | text | submitted | Segregated roles/limits | PROJECT-003 |
| LWH-FRM-048.F005 | transaction_refs | refs | conditional/optional | Journals/orders/employment/pay-run | PROJECT-003 |
| LWH-FRM-048.F006 | reconciliation | text | conditional/optional | Source/posted/paid evidence | PROJECT-003 |

**Cross-field/transition rule:** Core care operates with this module disabled; no invented payroll/tax rules.

### LWH-FRM-049 — Care plan and follow-up

**Owner:** Clinical and patient continuity team. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-049.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-049.F001 | episode_id | ref | submitted | Longitudinal care purpose | LWH-SRC-048 |
| LWH-FRM-049.F002 | goals | text | submitted | Patient-agreed/clinician-reviewed goals | LWH-SRC-048 |
| LWH-FRM-049.F003 | clinical_instructions | text | submitted | Approved signed plan or order references | LWH-SRC-048 |
| LWH-FRM-049.F004 | task_refs | refs | submitted | Responsible owner, due/review, accepted handover | LWH-SRC-048 |
| LWH-FRM-049.F005 | patient_preferences | text | conditional/optional | Reminder/routine choices distinct from prescription | LWH-SRC-048 |
| LWH-FRM-049.F006 | review_context | text | conditional/optional | Actual progress, self-report attribution and revision | LWH-SRC-048 |

**Cross-field/transition rule:** Plan revisions update future tasks safely; reminders/self-reports do not rewrite clinical instructions.

### LWH-FRM-050 — Clinical coverage and workload

**Owner:** Clinical workforce lead. **Privacy:** institutional/restricted according to purpose. **Schema:** `contracts/forms/LWH-FRM-050.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-050.F001 | team_id | ref | submitted | Actual service team | PROJECT-003 |
| LWH-FRM-050.F002 | service_scope | concepts | submitted | Privileges and populations | PROJECT-003 |
| LWH-FRM-050.F003 | coverage_period | period | submitted | Local staffed hours/timezone | PROJECT-003 |
| LWH-FRM-050.F004 | staff_refs | refs | submitted | Credentialed assigned staff | PROJECT-003 |
| LWH-FRM-050.F005 | capacity_context | text | submitted | Preparation/care/documentation/follow-up workload | PROJECT-003 |
| LWH-FRM-050.F006 | handover_refs | refs | conditional/optional | Accepted transfer of open obligations | PROJECT-003 |

**Cross-field/transition rule:** Optional HR is not required; unstaffed services cannot promise clinical response.

### LWH-FRM-051 — Treatment consent, refusal and supported decision

**Owner:** Treating clinician and records owner. **Privacy:** protected clinical. **Schema:** `contracts/forms/LWH-FRM-051.schema.json`.

| Field reference | Key | Type | Capture presence | Validation / purpose | Reference domain |
|---|---|---|---|---|---|
| LWH-FRM-051.F001 | intervention_scope | text | submitted | Specific proposed care and explanation | LWH-SRC-044 |
| LWH-FRM-051.F002 | decision_capacity_context | text | submitted | Patient/representative authority and support | LWH-SRC-044 |
| LWH-FRM-051.F003 | decision | text | submitted | Consent/refusal/withdrawal/other applicable authority | LWH-SRC-044 |
| LWH-FRM-051.F004 | information_provided | text | submitted | Relevant explanation and questions addressed | LWH-SRC-044 |
| LWH-FRM-051.F005 | authority_evidence | refs | conditional/optional | Representative/emergency/legal evidence as applicable | LWH-SRC-044 |
| LWH-FRM-051.F006 | witness_context | text | conditional/optional | Required where local policy applies | LWH-SRC-044 |
| LWH-FRM-051.F007 | valid_period | period | conditional/optional | Scope/expiry/review | LWH-SRC-044 |

**Cross-field/transition rule:** Treatment consent is distinct from record-sharing consent, app terms and marketing preferences.

## Machine contracts and verification

`contracts/forms/common.schema.json` defines shared scalar/structured types. Each form's schema uses stable urn references to those types. `contracts/form_field_manifest.json` supplies the same field metadata for agents/renderers. A schema loader must register all referenced IDs and enforce format checking. Unknown keys are rejected; version changes require explicit compatibility mapping.

The delivered contracts can be loaded and structurally validated. Schema compilation and positive/negative synthetic capture checks are reported in VALIDATION_REPORT.md. This proves structural consistency only. Country/clinical policy checks, permissions, concurrent writes, signatures, chronology and clinically meaningful validation require implementation tests and qualified review. Published variants preserve field IDs when meaning is unchanged; a changed meaning gets a new field/schema version and source-to-target migration.

## Additional executable presence constraints

Submitted administration capture explicitly requires product/dose fields for a given event and a reason for not-given/held/refused. Submitted final/corrected diagnostic capture requires verifier context, and corrected capture requires the amended version reference. Capture may preserve an explicit unknown for retrospective reconciliation; a consequential release/administration still rejects missing required actual values or authority under the clinical state rules. This distinction preserves evidence without inventing a clinical fact.
