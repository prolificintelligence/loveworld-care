---
document_id: "LWH-SPEC-001"
title: "Information architecture, design system and screen behaviour"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Product design and accessibility lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-DOC-000", "LWH-PRD-023", "LWH-PRD-024"]
source_refs: ["LWH-SRC-022"]
directive_refs: []
---

# Information architecture, design system and screen behaviour

## Workspace architecture

LW Health Leadership serves authorised President/Executive Minister views; LW Health Command serves Directorate operations; LW Health Coordination serves regional/zonal work; LW Health Facility Workspace serves institution/department administration and EMR; LW Care Clinical Workspace serves professional clinical work; My LW Health Care serves patients/families; LW Health Programmes serves funding/impact. One account can enter multiple authorised contexts. Home navigation contains the user's relevant tasks rather than every platform module.

Patient navigation: Today, Get help, My health, Care, Family/account. Clinical navigation: My work, Patients, Encounters/wards, Results/follow-up, Schedule. Facility navigation: Operations, Clinical services, Standards/reporting, Care finance, Administration. Region/zone navigation: Coverage, Reports/events, Readiness/referrals, Actions. Directorate navigation: Overview, Network/standards, Reporting/quality, Actions/programmes, Governance. Optional enterprise modules appear only under their own entitlement/role.

## Common screen contract

| State | Required behaviour |
|---|---|
| Loading | Preserve page title/context; show progress, no fabricated totals or empty chart normality |
| Empty | Explain what is absent and offer the next permitted action; no demonstration records in live mode |
| Partial | Identify unavailable sections/sources; preserve usable work and explicitly show incomplete coverage |
| Stale | Display last successful sync/source time, authority node and restrictions affecting consequential actions |
| Offline | Distinguish WAN-disconnected/local-operational from device isolated or local system unavailable |
| Validation error | Explain the field/rule, link focus to error, preserve valid inputs and avoid clearing the form |
| Conflict | Show current versus submitted version, preserve draft, offer review/reload; no silent overwrite |
| Denied | Explain the permitted route without leaking existence/content of protected resources |
| Service failure | Show retry/support reference and actual receipt status; never replace failure with demo success |
| Success | Name what was actually persisted/accepted; distinguish local commit, central receipt and external confirmation |

Every clinical screen has a persistent patient/subject and facility banner, clinically relevant alerts, source freshness and current responsible team. Identity confirmation happens at consequential bedside/order/record-disclosure actions. Administrative scope selectors clearly distinguish region, zone, institution and period. Subject switches reset transient search, drafts and assistant context before rendering the new subject.

## Interaction and content standards

Use a restrained navy/white/teal palette, readable sans-serif type, generous spacing and one clear primary action per task. Status uses text/icon as well as colour. Avoid dense dashboards that repeat every available metric. Patient copy describes care, ownership and next steps; algorithm/vendor names and specification IDs belong in authorised evidence views. Tables support accessible sorting, pagination and exports; map functions always have a list alternative.

Forms are progressive: prefill verified data with source/freshness, request only relevant missing facts, save drafts durably and show completion by meaningful section. Unknown is explicit. No default “no” for safety-critical questions. Clinical documents support keyboard-efficient entry, reusable templates, review of carried-forward content and intentional signing. Signing, submitting, reviewing and publishing are distinct verbs with distinct authority.

Target WCAG 2.2 AA and verify relevant criteria through automated and manual assessment. Provide semantic labels, visible unobscured focus, keyboard operation, meaningful headings, contrast, accessible error summaries and announcements, non-drag alternatives and adequate target sizes. Avoid cognitive overload and forced video. Responsive layouts cover low-cost mobile devices and shared workstation screens, with privacy-aware session locking.

## Canonical screen inventory

Module-specific fields/actions/failures are defined by the referenced PRD; this index owns screen identity and navigation placement.

| Screen | Name | Behaviour owner |
|---|---|---|
| LWH-SCR-001 | Workspace chooser | LWH-PRD-001 |
| LWH-SCR-002 | Organisation administration | LWH-PRD-001 |
| LWH-SCR-003 | Access and handover | LWH-PRD-001 |
| LWH-SCR-004 | Facility profile | LWH-PRD-002 |
| LWH-SCR-005 | Public service finder | LWH-PRD-002 |
| LWH-SCR-006 | Registry stewardship | LWH-PRD-002 |
| LWH-SCR-007 | Application and evidence | LWH-PRD-003 |
| LWH-SCR-008 | Inspection and recommendation | LWH-PRD-003 |
| LWH-SCR-009 | Directorate decision and renewal | LWH-PRD-003 |
| LWH-SCR-010 | Reporting home | LWH-PRD-004 |
| LWH-SCR-011 | Return editor | LWH-PRD-004 |
| LWH-SCR-012 | Zone/region coverage | LWH-PRD-004 |
| LWH-SCR-013 | Quick event notification | LWH-PRD-005 |
| LWH-SCR-014 | Review case | LWH-PRD-005 |
| LWH-SCR-015 | Learning and action | LWH-PRD-005 |
| LWH-SCR-016 | Quality worklist | LWH-PRD-006 |
| LWH-SCR-017 | Source comparison | LWH-PRD-006 |
| LWH-SCR-018 | Reconciliation run | LWH-PRD-006 |
| LWH-SCR-019 | Leadership overview | LWH-PRD-007 |
| LWH-SCR-020 | Directorate operations | LWH-PRD-007 |
| LWH-SCR-021 | Regional/zonal/facility cockpit | LWH-PRD-007 |
| LWH-SCR-022 | Action board | LWH-PRD-008 |
| LWH-SCR-023 | Intervention workspace | LWH-PRD-008 |
| LWH-SCR-024 | Outcome review | LWH-PRD-008 |
| LWH-SCR-025 | Clinic readiness cockpit | LWH-PRD-009 |
| LWH-SCR-026 | Referral finder and request | LWH-PRD-009 |
| LWH-SCR-027 | Handover tracker | LWH-PRD-009 |
| LWH-SCR-028 | Editorial library | LWH-PRD-010 |
| LWH-SCR-029 | Patient/public learning | LWH-PRD-010 |
| LWH-SCR-030 | Programme distribution | LWH-PRD-010 |
| LWH-SCR-031 | Care request | LWH-PRD-011 |
| LWH-SCR-032 | Consultation room | LWH-PRD-011 |
| LWH-SCR-033 | Care continuity | LWH-PRD-011 |
| LWH-SCR-034 | Sharing centre | LWH-PRD-012 |
| LWH-SCR-035 | Receiving clinical summary | LWH-PRD-012 |
| LWH-SCR-036 | Exchange reconciliation | LWH-PRD-012 |
| LWH-SCR-037 | Programme workspace | LWH-PRD-013 |
| LWH-SCR-038 | Entitlement and reconciliation | LWH-PRD-013 |
| LWH-SCR-039 | Sponsor impact | LWH-PRD-013 |
| LWH-SCR-040 | Assistant workspace | LWH-PRD-014 |
| LWH-SCR-041 | Use-case governance | LWH-PRD-014 |
| LWH-SCR-042 | Operational automation review | LWH-PRD-014 |
| LWH-SCR-043 | Registration and matching | LWH-PRD-015 |
| LWH-SCR-044 | Patient chart | LWH-PRD-015 |
| LWH-SCR-045 | Record stewardship | LWH-PRD-015 |
| LWH-SCR-046 | Arrival and triage | LWH-PRD-016 |
| LWH-SCR-047 | Encounter workbench | LWH-PRD-016 |
| LWH-SCR-048 | Care transition | LWH-PRD-016 |
| LWH-SCR-049 | Ward board | LWH-PRD-017 |
| LWH-SCR-050 | Bedside and rounds | LWH-PRD-017 |
| LWH-SCR-051 | Transfer/discharge workspace | LWH-PRD-017 |
| LWH-SCR-052 | Programme timeline | LWH-PRD-018 |
| LWH-SCR-053 | Maternal/newborn encounter | LWH-PRD-018 |
| LWH-SCR-054 | Family continuity | LWH-PRD-018 |
| LWH-SCR-055 | Orders and collection | LWH-PRD-019 |
| LWH-SCR-056 | Department workbench | LWH-PRD-019 |
| LWH-SCR-057 | Result review | LWH-PRD-019 |
| LWH-SCR-058 | Medication ordering | LWH-PRD-020 |
| LWH-SCR-059 | Dispensing and clinical stock | LWH-PRD-020 |
| LWH-SCR-060 | Medication administration record | LWH-PRD-020 |
| LWH-SCR-061 | Procedure preparation | LWH-PRD-021 |
| LWH-SCR-062 | Procedure and transfusion record | LWH-PRD-021 |
| LWH-SCR-063 | Recovery and handover | LWH-PRD-021 |
| LWH-SCR-064 | Patient account | LWH-PRD-022 |
| LWH-SCR-065 | Cashier and claims | LWH-PRD-022 |
| LWH-SCR-066 | Finance reconciliation | LWH-PRD-022 |
| LWH-SCR-067 | Today and family switcher | LWH-PRD-023 |
| LWH-SCR-068 | Companion and care request | LWH-PRD-023 |
| LWH-SCR-069 | My health and access | LWH-PRD-023 |
| LWH-SCR-070 | My work and duty coverage | LWH-PRD-024 |
| LWH-SCR-071 | Clinical workbench | LWH-PRD-024 |
| LWH-SCR-072 | Continuity and handover | LWH-PRD-024 |
| LWH-SCR-073 | Enterprise module administration | LWH-PRD-025 |
| LWH-SCR-074 | Finance and procurement workbench | LWH-PRD-025 |
| LWH-SCR-075 | People and payroll workbench | LWH-PRD-025 |


## Usability acceptance

Representative patients/caregivers, clinicians/nurses, facility officers, coordinators and executive users perform complete synthetic journeys on their actual device classes. Measure unassisted task success, repeated-entry burden, wrong-subject errors, time and interpretation of received/accepted/completed states. Proposed target is ≥90% unassisted core-task completion; any critical wrong-patient or misleading care-state defect blocks release regardless of average. Proposed study floors are 12 patient/caregiver and 6 clinical participants, supplemented by each institutional role; these are design evidence, not proof of population clinical safety.
