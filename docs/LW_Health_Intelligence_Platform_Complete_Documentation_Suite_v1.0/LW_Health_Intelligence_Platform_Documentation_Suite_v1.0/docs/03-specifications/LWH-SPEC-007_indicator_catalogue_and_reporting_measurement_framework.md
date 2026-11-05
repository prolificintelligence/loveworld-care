---
document_id: "LWH-SPEC-007"
title: "Indicator catalogue and measurement framework"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Health information and clinical measurement leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-SPEC-004", "LWH-SPEC-008", "LWH-SPEC-014"]
source_refs: ["LWH-SRC-004", "LWH-SRC-005"]
directive_refs: ["DHS-REQ-006", "DHS-REQ-007", "DHS-REQ-012"]
---

# Indicator catalogue and measurement framework

## Measurement contract

Every measure has a versioned purpose, owner, population/cohort, numerator and denominator where meaningful, event/source definition, unit, period/time zone, inclusion/exclusion rules, permitted dimensions, missingness, verification status, refresh schedule and disclosure rule. The definitions below are the project baseline; programme-specific clinical indicators require adopted definitions and source mapping. Month-end reporting is a proposed default, not a universal requirement for all signals.

| Metric | Name | Definition | Authoritative source | Interpretation / exclusions | Owner |
|---|---|---|---|---|---|
| LWH-MET-001 | Verified registry coverage | Verified active in-scope facility sites / all expected in-scope sites | Registry IDs and expected-site inventory | Site, owner category, region/zone; unknown expected coverage stated | Network lead |
| LWH-MET-002 | Active affiliation | Distinct sites with an effective active/conditional Directorate decision; report conditions separately | Affiliation decision at as-of time | Ownership/facility type; licence and readiness not implied | Standards lead |
| LWH-MET-003 | Corrective completion | Corrective actions independently accepted by due date / corrective actions due | Action due and reviewer acceptance | Criteria version/severity; overdue still included | Standards lead |
| LWH-MET-004 | Renewal timeliness | Renewals decided before prior expiry / recognitions due to expire in period | Prior decision expiry and renewal decision | Do not remove expired/nonresponding sites from denominator | Standards lead |
| LWH-MET-005 | Reporting completeness | Verified complete or explicit nil returns / expected unit-period obligations | Effective-dated obligation and return versions | Partial/unknown/missing shown separately; period hierarchy fixed | Information lead |
| LWH-MET-006 | Submission timeliness | Expected returns received by adopted deadline / expected returns due | Receipt time and deadline | Late offline arrival remains late with outage context | Information lead |
| LWH-MET-007 | Verification lag | Elapsed central receipt to verification; median/p90 and outstanding ages | Return receipt/review events | Open unverified returns reported alongside completed samples | Information lead |
| LWH-MET-008 | Correction rate | Verified returns requiring subsequent revision / verified returns in cohort | Version/correction lineage | Cause and magnitude shown; higher reporting quality may initially increase detection | Information lead |
| LWH-MET-009 | Source quality | Values passing specified reviewed checks / eligible checked values; verification coverage separately | Validation runs and check scope | No unexplained composite trust score | Data steward |
| LWH-MET-010 | Service contacts | Distinct qualifying completed encounter IDs in period | Signed clinical encounter/disposition or verified return | Not unique people; remote/facility overlap reconciled | Clinical information lead |
| LWH-MET-011 | Distinct patients served | Distinct reviewed patient links among qualifying encounters in defined cohort | Custodian-approved identity crosswalk | Unresolved links and cross-country limits disclosed | Clinical information lead |
| LWH-MET-012 | Condition-coded encounters | Qualifying encounters with specified condition/case-definition version | Source-coded diagnosis/assessment and approved inclusion rules | Separate confirmed/suspected; not population incidence | Programme clinical lead |
| LWH-MET-013 | Institutional inpatient deaths | Verified inpatient death dispositions by occurrence period | Signed source/death report under adopted definition | Community deaths, arrival-dead and unconfirmed reports separate | Quality/information lead |
| LWH-MET-014 | Institutional mortality proportion | Eligible inpatient deaths / eligible discharges including deaths in same defined cohort | Stay dispositions and approved inclusion/exclusion definition | Case mix, transfer effects and incomplete records shown; not population mortality | Clinical quality lead |
| LWH-MET-015 | Health-event review | Time to acknowledgement/review and open urgent/unverified counts | Event/task state and actual owner receipts | Reports are signals until verified; no direct incidence denominator | Quality lead |
| LWH-MET-016 | Access fulfilment | Eligible care requests receiving the suitable requested service / eligible requests | Request, service and disposition events | Withdrawn, unavailable and ineligible shown separately | Care operations |
| LWH-MET-017 | Human acknowledgement | Request accepted into covered team queue to actual clinician acknowledgement; median/p90/open overdue | Owned task/acknowledgement events | Automated acknowledgement excluded | Clinical operations |
| LWH-MET-018 | Unmet demand | Distinct eligible requests unfulfilled because suitable capacity/capability unavailable | Request/decline/availability evidence | Deduplicate repeated attempts in an episode; show service/geography | Network lead |
| LWH-MET-019 | Arrival-to-assessment | Actual arrival to first appropriate clinical assessment; distribution and overdue | Arrival/triage/assessment timestamps | Stratify adopted urgency, service and incomplete timestamps | Facility clinical lead |
| LWH-MET-020 | Continuity completion | Required follow-up/result tasks accepted complete within adopted window / tasks due | Clinical task evidence and due time | Reminder delivery and patient nonresponse not automatically completion | Clinical operations |
| LWH-MET-021 | Patient progress | Programme-specific approved follow-up measure versus usable baseline | Versioned condition/programme measure and sourced observations | Missing follow-up, selection and self-report attribution visible | Programme clinical lead |
| LWH-MET-022 | Clinical workload | Attributable clinical task minutes / available approved staffed minutes | Roster, workload/task records | Includes prep/documentation/results/handover; preserve breaks and urgent reserve | Workforce lead |
| LWH-MET-023 | Service coverage | Required service windows actually covered by privileged team / planned approved windows | Roster, privilege and operating windows | No inference from account count or optional HR employment list | Clinical operations |
| LWH-MET-024 | Readiness freshness | Active service capabilities with valid readiness / capabilities expected to operate | Capability/readiness assertions | Readiness is not accepted referral or guaranteed future availability | Network lead |
| LWH-MET-025 | Referral acceptance | Requests with actual receiving acceptance / eligible requests | Referral request and acceptance receipts | Declines/unreachable/pending separated; window and cohort explicit | Referral coordinator |
| LWH-MET-026 | Referral completion | Referrals with verified receiving outcome / referrals due for outcome | Accepted handover, receipt and outcome evidence | Acceptance and travel alone not completion | Referral coordinator |
| LWH-MET-027 | Geographic service reach | Demand areas meeting adopted serviceability definition / required demand areas | Civil geography, actual capabilities and travel/access model | Facility count alone insufficient; estimation assumptions visible | Network planning lead |
| LWH-MET-028 | Diagnostic turnaround | Order/collection/receipt/release stage durations by service | Department timestamps | Outside-reference labs and rejected specimens separated | Diagnostic lead |
| LWH-MET-029 | Critical result follow-through | Critical results with actual acknowledgement/action under policy / critical results requiring review | Approved critical flag and clinical task evidence | Delivery receipt is not clinical acknowledgement | Clinical quality lead |
| LWH-MET-030 | Medication reconciliation | Eligible transitions with completed reviewed reconciliation / transitions requiring it | Admission/transfer/discharge and medication review | Actual review evidence, not empty checkbox; missing data explicit | Medication safety lead |
| LWH-MET-031 | Medication omissions | Actual not-given/held/refused events by eligible administration opportunities | Current order schedules and MAR | Clinical appropriateness reviewed; omissions not all errors | Nursing/pharmacy leads |
| LWH-MET-032 | Clinical stockouts | Service/product periods with unavailable essential local stock under defined catalogue | Stock movements, physical verification and demand | Uncertain stock and quarantine separate; actual required products defined locally | Pharmacy lead |
| LWH-MET-033 | Occupancy | Occupied qualified bed-time / available staffed qualified bed-time | Actual local occupancy and service capacity | Closed/unqualified beds excluded with reason; reservations separate | Hospital operations |
| LWH-MET-034 | Length of stay | Actual admission to discharge duration distribution for eligible stays | Stay and disposition events | Open stays, transfers, service/case mix and incomplete timestamps visible | Hospital quality lead |
| LWH-MET-035 | Education delivery | Delivered/engaged/reviewed-understanding measures separately by approved programme | Content version and actual channel/feedback evidence | Delivery is not comprehension or health improvement | Editorial/programme lead |
| LWH-MET-036 | Intervention fulfilment | Accepted-evidence completed interventions / interventions due; outcome review separately | Owner acceptance, due, evidence and reviewer events | Unfunded/unaccepted/blocked included as exceptions | Directorate operations |
| LWH-MET-037 | Sponsored care delivery | Distinct eligible beneficiaries with qualifying delivered services; fund use and continuity separately | Programme eligibility, fulfilment and reviewed patient links | No raw clinical sponsor disclosure or double-counted included care | Programme finance |
| LWH-MET-038 | Care contribution | Approved recognised care revenue minus attributable variable costs | Finance ledger/recognition and cost allocation | Restricted funds/receipt not automatically revenue; no double-counted provider cost | Finance |
| LWH-MET-039 | Reconciliation exceptions | Unmatched/unbalanced service, receipt, claim or posting items by age/value | Ledger/provider/claim/source reconciliation | Per-currency; estimates separated from confirmed amounts | Finance |
| LWH-MET-040 | AI usefulness | Time saved and correction burden versus baseline, critical errors and cost per useful task | Governed evaluation and reviewed workflow samples | Fluency/usage not safety or efficacy | Clinical/AI leads |
| LWH-MET-041 | Experience burden | Unassisted task success, repeat-entry count, abandonment and reported attentiveness | Consented usability/product evidence | Segment patient/caregiver/clinical/institutional roles and accessibility needs | Product |
| LWH-MET-042 | Local continuity | Completed enabled clinical journeys during qualified WAN outage / tested enabled journeys | Offline scenario evidence and transaction counts | Qualification result, not proof of universal uptime | Platform/facility lead |
| LWH-MET-043 | Sync health | Oldest unacknowledged event age; accepted/duplicate/conflict/quarantine counts | Outbox/inbox and reconciliation receipts | Central receipt differs from semantic acceptance; local care not labelled failed by WAN alone | Platform/data stewards |
| LWH-MET-044 | Disclosure safety | Detected unauthorised access/disclosure and control test outcomes | Protected audit/incidents/evaluation | Absence of reports not proof of anonymity or security | Privacy/security |
| LWH-MET-045 | Country/service readiness | Scoped activations with complete adopted evidence / proposed activations | Country/facility activation dossiers | Architecture/global accounts do not imply clinical coverage | Directorate activation owner |


## Periods, comparability and coverage

Institutional snapshots bind to effective reporting obligations and the hierarchy applicable to the period. Keep occurrence period, local recording and central receipt time separately. A corrected return creates a later snapshot version and an explainable prior/current difference. Compare stable cohorts or explicitly describe region/zone/facility definition changes. Rates with zero, absent or unreliable denominators are unavailable with a reason, never zero by convenience.

Display verified completeness, late/partial/unknown units and freshness beside each relevant measure. Case/contact totals, distinct people, episodes and population incidence are different quantities. Do not calculate disease incidence from self-selected facility attendance or add community reports to encounter totals. Condition-specific progress measures require clinical ownership; there is no universal fabricated health score.

## Release and reconciliation

The health information owner approves formula/version and eligible data. Analytics records source versions, code/mapping/rule packages and output checksum. A representative sample of each released metric reconciles to source events/returns and expected unit counts. Finance separately approves recognition/cost logic. Clinical quality interprets outcomes with case mix and missingness. Suppression propagates to charts, narratives and exports.
