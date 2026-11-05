---
document_id: "LWH-ENG-004"
title: "Role-based UAT, Director demonstration and acceptance pack"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Programme acceptance and clinical QA leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-ENG-003", "LWH-GOV-008", "LWH-SPEC-017"]
source_refs: []
directive_refs: []
---

# Role-based UAT, Director demonstration and acceptance pack

## Acceptance scope and status

The suite defines the tests below; execution status is NOT_RUN. Acceptance covers the Director's institutional loop plus all confirmed core care workflows across the four facility types, controlled sharing, both EMR adoption routes and full local clinical continuity. Optional enterprise modules are tested for independence and, when activated, their own contracts. Countries/facilities and actual reviewers are nominated before live pilot.

| Case | Scenario | Exercise | Required pass result | Reviewer |
|---|---|---|---|---|
| LWH-UAT-001 | Mandate and naming | Explain umbrella/workspaces and all clear DHS directives | Each has an owner/document/journey; discussed/unclear points remain labelled | Directorate/product |
| LWH-UAT-002 | Hierarchy and transfer | Create regions/zones and change a facility assignment effective date | Current scope updates; historical reporting remains reproducible | Operations/QA |
| LWH-UAT-003 | Role and subject isolation | Try cross-zone, cross-patient and revoked caregiver UI/API/file/export | Unauthorised data/actions denied without leakage | Privacy/security |
| LWH-UAT-004 | Registry identity | Register one owner/two sites and duplicate candidates | Correct site/owner counts and reviewed links | Network |
| LWH-UAT-005 | Evidence and decision | Submit, inspect, recommend and decide affiliation | Only central Directorate role activates a reasoned scoped decision | Standards |
| LWH-UAT-006 | Renewal/adverse review | Expire recognition, request renewal and lodge review | No silent extension; notice/review/history and continuity retained | Standards/legal |
| LWH-UAT-007 | Directory/readiness | Search with no GPS and stale/unsuitable services | Manual search works; no false confirmed capacity | Network/product |
| LWH-UAT-008 | Expected reporting | Prepare returns before/after a zone change | Denominator follows effective obligation/hierarchy | Information |
| LWH-UAT-009 | Nil/partial/late/missing | Submit representative returns and omit one unit | Distinct states/coverage in all views | Information/QA |
| LWH-UAT-010 | Quality and overlap | Load EMR extract plus return plus duplicate event | All records accounted; no additive duplicate totals | Data |
| LWH-UAT-011 | Correction/snapshot | Revise a verified source after publication | History and affected aggregates/narratives traceable | Information |
| LWH-UAT-012 | Executive/privacy | Open President/Executive/Directorate/region/zone views and exports | Correct scope/coverage; suppression and no raw charts | Directorate/privacy |
| LWH-UAT-013 | Action outcome | Assign unfunded/unaccepted action, then fulfil/review | Ownership/resources/evidence and outcome limitations visible | Programme |
| LWH-UAT-014 | Education/policy | Publish, correct and withdraw content | Qualified review/applicability; correction reaches caches | Editorial |
| LWH-UAT-015 | Patient experience | New/returning patient opens Today, chat, plan, history and family | Low repeated entry, truthful states and correct subject isolation | Patient/product |
| LWH-UAT-016 | Account recovery | Recover identity with potential duplicate patient | Verified account recovery without destructive chart merge | Identity/custody |
| LWH-UAT-017 | Remote care | Request review, accept, consult and disconnect/recover | One owned episode; no fake clinician review or automatic billing | Clinical |
| LWH-UAT-018 | Urgent unknown | Use ambiguous critical information and disable AI/payment | Approved guidance/real escalation; no false negative or paywall | Clinical |
| LWH-UAT-019 | Chart integrity | Register provisional patient, sign and amend note | Actual source/author/version retained; no fabricated findings | Clinical/custody |
| LWH-UAT-020 | Outpatient closure | Complete encounter with pending result | Pending task stays owned despite encounter completion | Clinical |
| LWH-UAT-021 | Bed and ward | Race admissions and hand over shifts | Exclusive local occupancy and accepted responsibility | Hospital/nursing |
| LWH-UAT-022 | Diagnostics | Wrong accession, rejected specimen, final/corrected critical result | Quarantine/recollection and actual review/response retained | Diagnostics/clinical |
| LWH-UAT-023 | Medication chain | Prescribe/dispense/administer, retry and change order concurrently | Current intent, actual events and one effect; unknown allergies explicit | Pharmacy/nursing |
| LWH-UAT-024 | Clinical stock | Receive/dispense/return/quarantine and replay events | Exact local movements/balance; no duplicate effect | Pharmacy/finance |
| LWH-UAT-025 | Maternal/newborn/child | Document pregnancy, multiple birth, reviews and missing schedule | Distinct infant identities; no guessed schedule/clinical rule | Maternal/child |
| LWH-UAT-026 | Procedure/transfusion | Prepare, verify phases/unit, document actual act and hand over recovery | Privileges/authority/traceability and real handover | Procedural/blood-bank |
| LWH-UAT-027 | Sharing/referral | Coded summary, additional grant, decline/accept and outcome | Purpose/recipient match; sender retained until accepted; access history | Records/network |
| LWH-UAT-028 | Revocation/offline | Revoke while recipient disconnected then reconnect | Future online stop; bounded cached authority/lag and priority reconcile | Privacy/security |
| LWH-UAT-029 | Finance/payer | Deliver/charge/receive cash, timeout provider, adjudicate partial claim and refund | Actual states, balanced groups and independent approval | Finance |
| LWH-UAT-030 | Sponsor allowance | Reserve concurrently, cancel and use offline allocation | No overspend/double settlement; private clinical data protected | Programme/finance |
| LWH-UAT-031 | Full WAN outage | Disable WAN/cloud AI for qualified duration and execute all enabled core journeys | Complete local clinical work and truthful external dependency states | Facility/technical/clinical |
| LWH-UAT-032 | Sync/restart/fencing | Crash/retry/reorder events, restore backup and reject old authority epoch | All source evidence accounted; conflicts owned; no competing writer | Platform/data |
| LWH-UAT-033 | Existing EMR route | Qualify adapter and separately rehearse migration/cutover | Mapped identities/versions; reconciled truth; rollback preserves new care | Migration/custody |
| LWH-UAT-034 | AI boundaries | Inject malicious sources and request consequential actions | No tool/data expansion, unsupported fact or autonomous signing | Clinical/AI/security |
| LWH-UAT-035 | Optional ERP independence | Disable accounting/procurement/HR/payroll and run care | Core clinical/billing/stock/roster work continues | Facility/enterprise |
| LWH-UAT-036 | Restore/adoption/activation | Run support/incident/restore drill with actual roles and dossier | Open care/finance reconciled; trained staff and authorised scoped decision | Release owners |


## Director meeting demonstration

Use explicitly synthetic ministry units/facility/patients and role-separated accounts. Walk registration → evidence/inspection → central decision → eligible directory → prepared/manual return → verification → coverage-aware leadership view → accepted intervention/outcome review. Then show the patient/family next action, clinician workbench and a complete facility clinical chain. Disable WAN and inference to demonstrate local ward/diagnostic/medicine/discharge work, reconnect and inspect per-item reconciliation. Show one declined referral, one corrected result and one missing report so limitations are visible.

The demo is product evidence, not a live-clinical approval. Record feedback against IDs and distinguish requested scope change from discovered defect. Do not describe local role simulation or browser storage as production security/persistence.

## Release gates

G0: mandate/owners/source gaps and hierarchy understood. G1: institutional/clinical design, adopted scoped criteria/definitions and source/licence controls. G2: implemented canonical contracts, permissions, local runtime and meaningful verification. G3: integrated UAT plus actual country/service/staff readiness, privacy/clinical/finance reviews, training, support, backup/restore, funding and scoped release decision. G4: evidence-based expansion after operating review. Documentation completion is not G3.

## Decision record

Record release ID, code commit, environment, schema/migration, country/facility/service, policy/protocol/formulary/model versions, implemented requirement IDs, executed/passed/failed tests, unresolved issues, load/outage/restore/reconciliation reports, actual roster, contracts/funding, approved limitations and clinical/privacy/security/operations/finance/product decisions. A critical safety/privacy/financial blocker prevents relevant activation. Approval applies only to its stated scope/version and is reopened by material change.
