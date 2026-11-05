---
document_id: "LWH-ENG-002"
title: "Delivery roadmap, epics and implementation contracts"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Engineering delivery and product leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-DOC-000", "LWH-ENG-001", "LWH-ENG-003", "LWH-ENG-004"]
source_refs: []
directive_refs: []
---

# Delivery roadmap, epics and implementation contracts

## Scope and sequencing

All confirmed core workflows remain first-implementation scope. The epics below sequence dependencies; they do not defer inpatient, maternal/child, diagnostics or full local clinical operation into optional future scope. Optional accounting, procurement, HR and payroll have their own extension lane. Calendar/effort estimates follow repository audit, team capacity and facility/country selection; none is invented in this suite.

| Epic | Outcome | Coverage | Exit evidence | Dependency |
|---|---|---|---|---|
| LWH-EP-01 | Mandate, source and operating foundation | DOC/DIR/BRD/STR/GOV-001/STD plus ENG-001 audit | Validated hierarchy/source gaps, ownership and reuse decisions | None; discovery and synthetic work can begin |
| LWH-EP-02 | Shared identity, domain and UX | PRD-001; SPEC-001/003/004/005/006/009/010/011 | Scoped accounts, effective hierarchy, common contracts, accessible components | EP-01 |
| LWH-EP-03 | Institutional network loop | PRD-002/003/004/005/006 | Registration, inspection/decision, returns/events and verification | EP-02; adopted institutional policy before live decisions |
| LWH-EP-04 | Leadership and action | PRD-007/008/010; SPEC-007/008/014 | Reconciled dashboards, education and evidence-linked interventions | EP-03; approved definitions/disclosure |
| LWH-EP-05 | Local clinical foundation | PRD-015/016/024; SPEC-017/018/019 | Local identity/chart/encounter/clinical team and durable sync core | EP-02; clinical scope/content design |
| LWH-EP-06 | Full clinical departments | PRD-017/018/019/020/021; SPEC-020 | Inpatient, maternal/child, diagnostics, medicines, procedures and handover | EP-05; actual departments/privileges for activation |
| LWH-EP-07 | Connected personal/network care | PRD-009/011/012/023; SPEC-012 | Patient/family, remote care, readiness, referral and controlled exchange | EP-03/05; approved partner/purpose |
| LWH-EP-08 | Care finance and programmes | PRD-013/022; COM-001 | Patient/payer billing, entitlement, receipts, claims and reconciliation | EP-05; finance/payer terms |
| LWH-EP-09 | Bounded intelligence | PRD-014; SPEC-013; GOV-007 | Evaluated assistants with tool/data limits and AI-off continuity | EP-02 plus relevant stable workflows/source data |
| LWH-EP-10 | Country/facility qualification | SPEC-021; GOV-008; ENG-003/004/005/006/007; OPS | Actual adoption, migration, training, outage/restore and integrated UAT | Relevant EP-03 through EP-09 core scope complete |
| LWH-EP-11 | Optional enterprise extension | PRD-025; optional local/partner adapters | Accounting/procurement/HR/payroll per contracted module | Independent entitlement/rules; never prerequisite for core care |


## Ticket/build contract

Each ticket records requirement IDs, actor/subject/scope, owner, authority node, canonical entity/form/field/state/API/event references, policy prerequisites, UI states, offline behaviour, migrations, observability, acceptance and rollback. Implement a vertical slice that persists and enforces its actual authority rather than a collection of disconnected screens. Use synthetic data until the applicable live purpose is authorised. Cross-cutting safety/privacy/security review begins with design, not after implementation.

## Suggested vertical slices

First prove identity/context plus one facility registration, review and directory publication. Next prove a prepared/manual return through verification and a leadership action. In parallel prove a local patient/encounter with signed note, order, result review and follow-up. Extend that same authority model into medicines/MAR, admission/nursing/discharge, maternal/newborn and procedures. Then connect patient/remote/referral sharing, care finance and existing-EMR routes. Finally rehearse the complete local outage/reconnect and actual facility adoption. AI can be added against stable contracts without becoming a prerequisite for core work.

## Dependency and change control

Formalise the epic graph and per-feature dependencies. Source/criteria/indicator adoption precedes live institutional use; country/clinical/records/finance adoption precedes corresponding live care. Source code may implement disabled configuration and synthetic tests while adoption is pending. A late policy/schema change gets impact analysis across forms, migrations, UI, indicators, tests, training and offline nodes. Scope changes do not silently remove Director directives.

## Definition of done

A feature is done only when its required behaviour, negative permissions, state/concurrency guards, persistence/history, offline and dependency degradation, accessible UX, telemetry, meaningful tests, migration/rollback and operating instructions are evidenced. Product acceptance, clinical approval, policy adoption and deployment are separate evidence. Release completion requires the integrated UAT, actual staff/facility readiness and funded support—not just a green build.
