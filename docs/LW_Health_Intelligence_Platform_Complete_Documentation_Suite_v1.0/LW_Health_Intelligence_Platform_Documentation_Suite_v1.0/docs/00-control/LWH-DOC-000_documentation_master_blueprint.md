---
document_id: "LWH-DOC-000"
title: "Documentation master and product baseline"
version: "2.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Programme product owner"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: []
source_refs: ["PROJECT-001", "PROJECT-002", "PROJECT-003"]
directive_refs: []
---

# Documentation master and product baseline

## Purpose and authority

This suite is the authored design baseline for **LW Health Intelligence Platform**, prepared after the interactive requirements session on 5 November 2026. It replaces the earlier outline's Care-led product framing. **LW Care** is the connected care-delivery capability. **My LW Health Care** is the working patient application name. Stable LWH document IDs are preserved so earlier references remain usable.

The Director's institutional mission governs the programme: know the network; establish meaningful affiliation and standards; receive reliable facility and zone information; provide appropriate leadership intelligence; support education, community access and referrals; and turn concerns into owned, reviewed action. The comprehensive EMR strengthens those outcomes and the clinical service. Affiliated facilities can report through integration or direct returns while retaining their own EMR.

## Baseline decisions

| Reference | Subject | Confirmed product direction |
|---|---|---|
| LWH-DEC-101 | Platform name | LW Health Intelligence Platform; LW Care is a feature/capability within it. |
| LWH-DEC-102 | Patient experience | My LW Health Care is the working patient app name; dashboard plus text conversation; voice/languages are later extensions. |
| LWH-DEC-103 | Ministry hierarchy | Region → Zone is the required reporting spine; lower levels are optional and configurable. |
| LWH-DEC-104 | Affiliation authority | The Directorate centrally makes final affiliation decisions after evidence review and inspection. |
| LWH-DEC-105 | Facility clinical scope | Comprehensive facility EMR belongs in the first implementation scope. |
| LWH-DEC-106 | Facility types | Community/primary clinics, inpatient hospitals, maternal/child facilities and specialist/diagnostic centres are supported. |
| LWH-DEC-107 | Existing systems | Adoption can retain an existing EMR with integration or migrate to the LW EMR, facility by facility. |
| LWH-DEC-108 | Sharing | Anonymised intelligence and protected coded/identified clinical sharing coexist according to recipient, purpose and authorisation. |
| LWH-DEC-109 | International rollout | Design the global architecture now; pilot countries will be selected later. |
| LWH-DEC-110 | Facility operations | All core patient-care workflows are included. Full accounting, procurement, HR and payroll are optional. |
| LWH-DEC-111 | Funding | Directorate funding for the core platform is the leading proposal, with revenue from care and optional services. No amount is approved. |
| LWH-DEC-112 | Offline continuity | Facilities continue all core clinical operations locally during WAN outages and synchronise later. |
| LWH-DEC-113 | Personal accounts | One personal account; optional dependant profiles and explicitly authorised caregivers; public access with a clear LoveWorld identity. |
| LWH-DEC-114 | Clinical assistance | AI prepares summaries, documentation, references, follow-up, referrals and workload support; clinicians retain consequential clinical authority and overrides. |
| LWH-DEC-115 | Continuity priorities | General personal/family/maternal health, chronic-condition support and medication/follow-up support. |
| LWH-DEC-116 | Care experience | Immediate bounded assistance, appropriate escalation, truthful updates, low repeated data entry and continuing ownership of unresolved care. |


These are product decisions confirmed by the project lead. They are separate from country operating authorisations, approved clinical protocols, binding prices and statutory authority.

## What this suite supplies

The controlled documents include programme/business requirements; 25 module PRDs; 21 shared specifications; governance policies; engineering, testing and release plans; operational procedures; and commercial/partner frameworks. The PRDs contain required behaviour and observable acceptance cases. Shared specifications define screen, field, permission, state, API, event, measurement and offline contracts. Optional enterprise modules have explicit interfaces and activation boundaries.

Use README.md as the index. Use LWH-DIR-001 for directive interpretation, LWH-GOV-001 for responsibility, LWH-SPEC-006 for form fields, LWH-SPEC-009 for states and LWH-SPEC-017 for local clinical continuity. Implementation agents use AGENTS.md and the machine-readable manifest. A requirement is not satisfied merely because its label appears in a screen.

## Completion and remaining authority

This is a complete documentation baseline for the defined product scope, not evidence that code has been built, integrations passed, clinical software certified or a live service authorised. Institution-specific values still requiring adoption are recorded as bounded decisions with an accountable role and activation effect. They are not replaced with invented names, clinical thresholds or approved prices. A country activation package resolves applicable law, service scope, privileges, data location, retention and clinical policy before that country's live activation.

The first implementation scope includes all confirmed core workflows. Engineering may deliver dependent increments, but cannot silently redefine inpatient, maternity, diagnostics or offline operation as future optional scope. A facility activates only the services it is staffed and equipped to provide. Full accounting, procurement, HR and payroll are optional.

## Change and approval

Version 1.0.0 establishes the design baseline. Product approves scope; the Directorate approves institutional policy; clinical, privacy, finance and technical owners approve their own operating decisions. Changes identify affected requirement IDs, schema/data migrations, training, tests and rollback. Preserve historical documents and IDs. The supplied validation report concerns document integrity only; all implementation acceptance cases start NOT_RUN.

## Supersession and Care baseline crosswalk

This master is document version 2.0.0, superseding the earlier LWH-DOC-000 outline version 1.0.0 within documentation suite version 1.0.0. Newly authored individual documents begin at 1.0.0. Preserve external LWC IDs as source references; the mappings below identify their new canonical owners.

| Preserved Care intent / source family | New canonical owner | Refinement |
|---|---|---|
| LWC-VIS-001/002; Directorate intelligence | LWH-STR-001; LWH-PRD-007/008 | Director-first parent platform with Care inside it |
| LWC-VIS-003/004; INT/PRT | LWH-PRD-011/014; LWH-SPEC-013; LWH-GOV-002/007 | Immediate bounded help, clinically approved pathways and human authority |
| LWC-VIS-005/006; MEM; care plans | LWH-PRD-018/023; LWH-SPEC-019; LWH-GOV-004 | Correctable longitudinal context and programme continuity |
| LWC-VIS-007/008; clinician SCR/JRN | LWH-PRD-016/024; LWH-SPEC-018 | Duty/usual-care/network teams, focused work and accepted handover |
| LWC-VIS-009; NET/referral STM | LWH-PRD-002/009/012; LWH-SPEC-005/012 | Location/capability/readiness and actual receiving acceptance |
| LWC-VIS-010/011; ACC/ACL | LWH-PRD-001/012/023; LWH-SPEC-003 | Public account with subject-separated family/representative permissions |
| LWC-VIS-012; ECO/financial STM | LWH-PRD-013/022; LWH-COM-001 | Directorate-funded core proposal plus approved care/optional service revenue |
| LWC-VIS-013; patient SCR | LWH-PRD-023; LWH-SPEC-001 | Dashboard plus text; voice/languages later |
| LWC-VIS-014; GAT/DEL/AT | LWH-GOV-008; LWH-ENG-002/003/004 | Global architecture; countries later; qualified controlled activation |
| LWC-DAT/API/EVT; security/consent controls | LWH-SPEC-003/004/009…021; LWH-GOV-003/004 | Canonical contracts, protection and full local clinical runtime |
| Earlier Nigeria-first and limited facility scope | LWH-DEC-105/106/109/112; LWH-PRD-015…022 | Explicitly superseded by comprehensive EMR/all facility types/global design/offline clinical operation |
