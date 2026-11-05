---
document_id: "LWH-SPEC-018"
title: "Clinical record, order and team workflow contracts"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Clinical information architect"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-SPEC-017"]
source_refs: ["LWH-SRC-037", "LWH-SRC-040", "LWH-SRC-041", "LWH-SRC-042"]
directive_refs: []
---

# Clinical record, order and team workflow contracts

## Clinical context envelope

Every consequential clinical command binds actor, patient, facility/custodian, encounter/episode, service/jurisdiction, privilege, treating relationship, authority node, expected version, purpose, applicable policy and actual event time. The server resolves and checks these facts. The visible patient banner is necessary usability support but does not replace backend identity/authorisation.

## Record and teamwork contract

Draft notes preserve author and source references; assistants can prepare editable drafts. Carried-forward content is visibly attributed and reviewed. Ready-for-review is not signed. Signing requires actual intent, valid professional privilege and current record version. Signed content is immutable; addenda/corrections reference it with reason and author/time. Entered-in-error marks inappropriate clinical use while retaining protected evidence. A patient-reported statement does not become a clinician finding simply because it was copied into a summary.

Each encounter has an accountable clinical team and responsible tasks. Multiple staff can contribute scoped observations without overwriting signed content. Claim ownership, bed occupancy and current-order checks are atomic locally. Shift end, discharge, clinician absence, facility withdrawal and referral do not erase unresolved responsibilities. Handover requires eligible successor acceptance or an adopted supervised exception/escalation with a named accountable team.

## Order and execution contracts

| Object | Required data before consequential action | Execution/closure condition |
|---|---|---|
| Diagnostic/service order | Patient/encounter, requested service, question/context, priority, requester, result owner and signed version | Department accepts; actual performance/report; clinical review retained |
| Medication order | Exact product/strength reference, dose/unit, route, timing, duration/stop intent, indication, substitution rule, prescriber and applicable checks | Actual dispense/administration independent; changes affect future tasks, not past events |
| Specimen | Correct order/patient, accession/label, collector/time and receipt/condition | Rejected/recollected or accepted/analysed; no inferred collection |
| Result | Typed observations, units/absence, method/reference context, source, status and verifier | Actual release; critical acknowledgement/action and communication separately tracked |
| Procedure/transfusion | Privileged team, plan/authority, readiness, actual phase/unit checks and source evidence | Actual performed record, traceability, recovery/monitoring and accepted handover |
| Discharge/transfer | Signed clinical summary, reconciled medicines, patient instructions and pending obligation owners | Actual disposition and receiving acceptance where required; billing independent |

Medication safety and clinical urgency use approved applicable content; the platform does not create doses or thresholds from generic templates. A rule/checking outage produces a documented manual clinical route under adopted policy, not a false “no interactions” or “normal” result. Known identity/privilege failures cannot be concealed by a generic override.

## Scheduling and resources

Slots/holds/reservations and actual attendance are separate. Resource capacity includes staff/service capability and required rooms/equipment, with hold expiry and concurrency protection. Workload accounts for assessment, preparation, documentation, review and handover. Optional HR/payroll absence cannot stop clinical rosters. Remote requests are confirmed only by the schedule authority.

## Specialist and continuing care

Use a common chart/encounter/order/plan model with service-specific templates for maternal/child care, mental health, rehabilitation, dental/specialist practice and chronic programmes where activated. Sensitive note categories, consent, functional goals, multidisciplinary tasks and external referrals carry explicit access/purpose and review. Specialised clinical algorithms, scores and treatment content require a separately adopted validated package; ordinary clinical documentation remains available without inventing that content.

## Invariants and tests

No wrong-subject command; no unprivileged signing; no fabricated examination; no duplicate actual administration; no result lost at discharge; no local exclusive bed collision; no signed-note overwrite; no completed referral without accepted receiver; no clinical priority change from payment. Verify all under concurrency, stale views, missing data, WAN loss, retries and source corrections. Cross-facility partition conflicts are preserved and reviewed, not falsely prevented by an unreachable central lock.
