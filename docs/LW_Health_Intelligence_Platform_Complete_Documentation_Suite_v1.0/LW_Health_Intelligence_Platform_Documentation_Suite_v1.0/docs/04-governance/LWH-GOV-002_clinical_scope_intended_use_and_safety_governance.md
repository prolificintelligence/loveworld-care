---
document_id: "LWH-GOV-002"
title: "Clinical intended use, scope and safety governance"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Authorised clinical governance lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-SPEC-018", "LWH-SPEC-019", "LWH-SPEC-021", "LWH-ENG-004"]
source_refs: ["LWH-SRC-007", "LWH-SRC-014", "LWH-SRC-050"]
directive_refs: []
---

# Clinical intended use, scope and safety governance

## Intended use and authority

LW Health Intelligence supports institutional operations and clinical documentation/care workflows. LW Care provides approved remote and facility care functions; clinical professionals retain responsibility for consequential assessment, prescribing, orders, procedures and signed records. Each medical software function has an intended-use record, target user/population/setting, clinical claim, required inputs, limitations, failure alternatives and applicable regulatory assessment. Administrative analytics, documentation assistance and clinical decision functions are assessed separately.

The comprehensive first-implementation scope includes all confirmed facility types and core workflows. Actual service activation depends on competent staff, privileges, equipment, adopted local clinical content and readiness. Global design does not authorise worldwide medical practice. IMDRF clinical-evaluation guidance is a reference for intended-use evidence, not a substitute for applicable national requirements or certification.

## Safety management and hazard baseline

| Hazard | Required controls | Accountable role | Verification reference |
|---|---|---|---|
| LWH-HAZ-001 — Wrong patient/infant or caregiver | Independent identity confirmation, reviewed links, subject isolation; provisional pathway | Registration/custody/clinical | PRD-012/015/018/023 matching and family cases |
| LWH-HAZ-002 — Missed urgent condition | Approved routing/triage, explicit unknowns, covered escalation and non-AI fallback | Clinical duty lead | PRD-011/016; urgent and ambiguous input cases |
| LWH-HAZ-003 — Unowned pending result/follow-up | Durable task, acknowledged review, accepted handover and escalation | Clinical operations | PRD-017/019/024 discharge/shift cases |
| LWH-HAZ-004 — Wrong/stale medication or duplicate dose | Current order/version, product/unit checks, idempotent MAR, reconciliation | Medication/nursing leads | PRD-020 stale-order/retry/offline cases |
| LWH-HAZ-005 — Wrong specimen/result/unit | Patient/order/accession match, unit mapping, department verification, amendment | Diagnostic lead | PRD-019 mismatch and corrected-result cases |
| LWH-HAZ-006 — Unsafe procedure/transfusion | Privileges/readiness/authority, team phases, component/recipient traceability and recovery | Procedural/blood-bank lead | PRD-021 readiness, mismatch and offline cases |
| LWH-HAZ-007 — False referral/ambulance acceptance | Actual receiving/dispatch acknowledgement, sender ownership and alternatives | Network clinical lead | PRD-009 decline/unreachable cases |
| LWH-HAZ-008 — Clinical conflict after partition | Single authority, append-only evidence, version checks and qualified reconciliation | Facility clinical/data leads | SPEC-017 conflict/replay cases |
| LWH-HAZ-009 — Data disclosure or false anonymity | Purpose/field controls, separated datasets, disclosure assessment and protected codes | Privacy owner | SPEC-003/014 access/export/differencing cases |
| LWH-HAZ-010 — AI unsupported clinical authority | Bounded tools, signed protocols, human consequential decisions and AI-off | Clinical/AI owners | PRD-014 injection/source fidelity/AI-off cases |
| LWH-HAZ-011 — Financial status distorts care | Independent urgency/state, actual settlement, transparent funding alternatives | Clinical/finance leads | PRD-013/022 emergency and payment cases |
| LWH-HAZ-012 — Device/power/LAN/site failure | Qualified local infrastructure, manual continuity, backup/restore and open-care reconciliation | Facility/platform leads | SPEC-015/017; OPS-005/006 drills |
| LWH-HAZ-013 — Expired capability/credential/reference | Activation/privilege/package validity and known restrictions | Clinical governance | Country/facility expiry and outage tests |
| LWH-HAZ-014 — Misleading leadership inference | Coverage/definitions, no false incidence/causality, versioned corrections | Information owner | PRD-007; SPEC-007/014 reconciliation cases |


For each hazard record cause, hazardous situation, potential harm, severity/likelihood rationale, control implementation, test evidence, residual risk, accepting authority and monitoring. This table initiates the log; implementation-specific hazards and actual residual-risk decisions are added during design/testing. No risk is declared accepted because a generic disclaimer exists.

## Clinical content and overrides

Every protocol, triage rule, dose calculator, diagnostic threshold, vaccine schedule and reference package has qualified author/reviewer, evidence/version, jurisdiction/population, exclusions, missing-input behaviour, escalation, effective/expiry and validation. Unapproved clinical parameters remain inactive. Unfamiliar clinical content is not filled with AI-generated plausible rules. Authorised overrides record reason, source/current facts and review; they cannot silently bypass identity, professional authority or known restrictions. Manual clinician-led care is available under adopted contingency when automated assistance is unavailable.

## Evidence and release

Clinical review evaluates workflow usability, wrong-patient protection, source fidelity, orders/medicines, results/follow-up, maternal/child and procedural scope, offline continuity and safe degradation. Required evidence includes representative test cases, incident drills, qualified user training, actual service readiness and approved country package. Synthetic tests are labelled; no patient trial or safety claim is inferred from a demo.

## Stop and resume

Contain affected capabilities on suspected serious harm, wrong-patient disclosure, dangerous unsupported guidance, unprivileged signing, lost urgent work or integrity failure. Preserve local clinical/manual alternatives and affected patient responsibilities. Clinical, privacy, technical and operational leads investigate and reconcile open care. Resume only after correction, applicable regression evidence and authorised scope review. Review outcomes, near misses and reporting burden continuously; absence of incident reports is not proof of safety.
