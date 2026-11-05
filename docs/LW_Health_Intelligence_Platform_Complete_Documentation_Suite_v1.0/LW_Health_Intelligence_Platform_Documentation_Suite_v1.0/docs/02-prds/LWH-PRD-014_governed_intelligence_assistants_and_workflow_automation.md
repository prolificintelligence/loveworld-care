---
document_id: "LWH-PRD-014"
title: "Governed assistants and workflow automation"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "AI product and clinical governance leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-SPEC-013", "LWH-GOV-007"]
source_refs: ["LWH-SRC-028", "LWH-SRC-031"]
directive_refs: []
---

# Governed assistants and workflow automation

## Purpose and service result

Reduce administrative burden and support continuity through bounded intelligence. Separate clerical automation, clinical drafts, approved protocol execution and institutional decisions so each retains the appropriate authority.

**Primary users:** Patients, clinicians, data reviewers, coordinators and Directorate analysts. **Accountable product/operating owner:** AI product and clinical governance leads. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-014-R001 | Use-case registry | MUST version intended use, user, data scope, tools, owner, review class and evaluation. | An unregistered assistant cannot call privileged production tools. |
| LWH-PRD-014-R002 | Bounded retrieval | MUST supply only authorised subject/facility/purpose context with source references. | Prompt injection cannot request another patient or payroll dataset. |
| LWH-PRD-014-R003 | Clinical review | MUST require clinician review for consequential assessment, orders, prescribing, signing and treatment changes. | AI drafts cannot directly execute those commands. |
| LWH-PRD-014-R004 | Institutional authority | MUST retain human review for affiliation, sanctions, protected disclosures and funding approvals. | A model score cannot activate recognition or release funds. |
| LWH-PRD-014-R005 | Approved protocols | MUST execute only current, signed, applicable protocol rules with exclusions and escalation. | Unknown safety inputs never default to a safe classification. |
| LWH-PRD-014-R006 | Memory correction | MUST distinguish patient report, observed fact, clinician decision and derived summary with lineage. | Correcting a source invalidates dependent memories/summaries. |
| LWH-PRD-014-R007 | Evaluation and cost | MUST compare usefulness, errors, latency, staff correction burden and cost against a baseline. | A fluent answer with unsupported facts fails evaluation. |
| LWH-PRD-014-R008 | AI-off continuity | MUST preserve core institutional and clinical workflows without inference. | Cloud/model outage cannot prevent local care, signing or reporting. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-040 | Assistant workspace | Purpose, active subject/scope, sources, draft and uncertainty | Ask, inspect evidence, edit, accept or reject | Unavailable/unsupported output gives manual workflow |
| LWH-SCR-041 | Use-case governance | Versions, permitted tools, evaluations, incidents and cost | Review, approve bounded use, restrict or retire | Failed evaluation keeps the capability inactive |
| LWH-SCR-042 | Operational automation review | Proposed clerical tasks, confidence, owners and audit | Approve permitted batch, correct or stop | Irreversible actions stay under the relevant human authority |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

A user requests help in an authorised context. Policy grants a bounded data/tool envelope; retrieval prepares source evidence; the assistant drafts or performs a permitted low-consequence task. The responsible user reviews consequential output and executes the authoritative action. Feedback is retained with provenance for evaluation, without uncontrolled production learning.

## Operational responsibilities and exceptions

Clinical owners approve intended use and thresholds; data/standards owners approve institutional assistants; security controls tools; AI leads maintain evaluations; finance monitors cost. AI does not infer protected diagnoses for leadership narratives or silently train on patient records.

## Offline and integration behaviour

Locally deployed inference is optional and independently qualified. The mandatory offline clinical runtime provides deterministic/manual workflows using valid local reference packages. External model requests queue only when purpose/retention policy allows; otherwise they fail explicitly. Reconnection does not automatically execute stale clinical drafts.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-014-AT001 | Injection | Place malicious instructions in an uploaded source document. | Tool/data scope cannot expand and the attempt is recorded. |
| LWH-PRD-014-AT002 | Source correction | Correct a fact used in a patient summary. | Dependent summary is invalidated and requires refresh/review. |
| LWH-PRD-014-AT003 | AI-off | Disable every model endpoint during clinic operation. | Core care and institutional tasks continue. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track critical omissions, invented facts/citations, clinician correction burden, time saved, cost per useful task and authorised-tool violations. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
