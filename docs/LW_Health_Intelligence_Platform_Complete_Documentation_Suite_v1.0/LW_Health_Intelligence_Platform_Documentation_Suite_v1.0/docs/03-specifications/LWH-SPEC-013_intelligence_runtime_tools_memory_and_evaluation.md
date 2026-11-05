---
document_id: "LWH-SPEC-013"
title: "Intelligence runtime, tools, memory and evaluation"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "AI engineering and clinical governance leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-PRD-014", "LWH-GOV-007", "LWH-SPEC-003", "LWH-SPEC-017"]
source_refs: ["LWH-SRC-028", "LWH-SRC-031"]
directive_refs: []
---

# Intelligence runtime, tools, memory and evaluation

## Runtime permission envelope

Every invocation receives actor, active subject/facility, intended purpose, clinical/administrative role, grant/privilege versions, permitted sources, allowed tools, maximum output class, model/source versions and cost/latency limits. Policy is evaluated outside the model. Retrieval follows row/field permissions. Tool execution revalidates authority and state at the authoritative service; a model-generated instruction is never a permission token.

| Class | Examples | Execution boundary |
|---|---|---|
| Read/explain | Retrieve approved plan, source-linked history or published education | Permitted data only; distinguish reported/verified/derived facts |
| Draft | Summary, note, referral text, documentation, briefing | User reviews; no signature/order/affiliation authority |
| Routine clerical | Format return, identify missing fields, organise follow-up, propose schedule | Approved tool allowlist; bounded reversible action and auditable owner |
| Approved deterministic pathway | Current low-risk support/routing and exclusions | Signed applicable protocol, complete required inputs, explicit escalation |
| Consequential clinical | Diagnosis/treatment change, prescription/order release, signing | Privileged human decision and intentional authoritative command |
| Consequential institutional/financial | Affiliation, sanction, protected disclosure, refund/funding approval | Appropriate human decision and separation of duties |

## Tool contracts

Allowed tools are typed domain operations: get_permitted_chart_summary; retrieve_current_reference; draft_note; list_owned_tasks; propose_followup; prepare_return; inspect_metric_lineage; draft_intervention; request_authorised_handover. Each declares input schema, read/write consequence, resource/purpose limits, state preconditions, idempotency, review requirement and audit. No unrestricted production SQL, shell, arbitrary URL fetch, patient export or role-grant tool is exposed to an assistant.

Retrieved documents and external text are untrusted evidence, not instructions. Strip executable content, preserve provenance and resist prompt injection. A request to override role boundaries, reveal another subject or execute a hidden consequential action is rejected by policy regardless of model wording. Source links resolve only through the user's permissions.

## Patient and institutional memory

Memory entries have subject/custodian, fact type, source record/version, observed/recorded time, reporter, verification, uncertainty, purpose, expiry/review and correction links. Patient statements, self-reported medicine use, observed measurements, clinician decisions and derived summaries remain distinct. Conflicts are displayed for qualified review. Corrections invalidate dependent summaries, embeddings and downstream recommendations where applicable. No cross-patient/family memory contamination.

Institutional memory stores approved definitions, decisions, programme lessons and task history within administrative scope. Anonymous analytics and protected clinical memories use separate indexes/permissions. Production feedback may improve evaluated versions only through approved data use, dataset preparation, review and controlled release. “Grows with the patient” means correctable continuity of context, not self-authorising clinical policy changes.

## Generation and protocol pipeline

Validate intent/scope → retrieve authorised source set → mark stale/conflicting facts → construct bounded context → generate structured draft → validate schema/citations/forbidden actions → present review or execute a permitted clerical tool → audit outcome. Unknown or unsupported content yields a clear limitation and manual/clinical route. Clinical protocol execution is a separate deterministic, versioned service; an LLM cannot alter thresholds, exclusions or escalation logic at runtime.

## Evaluation and release

Maintain synthetic/de-identified authorised test sets spanning negation, wrong subject, missing observations, conflicting medicine lists, maternal/paediatric exclusions, urgent concerns, source amendments, hallucinated citations, prompt injection, tool abuse and language limitations. Measure critical omissions, unsupported facts, wrong recommendations, source fidelity, clinician correction effort, task time and cost against no-AI baselines. A critical safety/permission failure blocks the affected use case. Model/provider upgrades rerun applicable tests and require approved scope.

## Degradation

Set bounded timeouts and spend controls per task/tenant; show actual failure. AI-off and cloud outage preserve local clinical operation, signing, worklists, core reporting and approved static information. Local inference is optional and separately qualified. Stale drafts are revalidated before consequential use. Every use case has owner, rollback, monitoring and retirement criteria.
