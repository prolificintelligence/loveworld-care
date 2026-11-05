---
document_id: "LWH-SPEC-002"
title: "End-to-end user journeys and service blueprints"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Service design and operations lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-SPEC-001", "LWH-SPEC-009", "LWH-ENG-004"]
source_refs: []
directive_refs: []
---

# End-to-end user journeys and service blueprints

## Journey contract

Every journey names trigger, active subject/scope, actors, authoritative system, handoff evidence, success/failed completion, elapsed-time commitment and owner. Each arrow below is a responsibility handoff, not merely navigation. The originating owner remains responsible until the defined recipient accepts. Actual service windows and clinical response values are adopted country/facility parameters rather than invented global promises.

| Journey | Result | Actors | Required successful path | Exception/continuity path | Accountable role |
|---|---|---|---|---|---|
| LWH-JRN-001 | Facility registration to public discovery | Facility admin → registry steward → inspector/reviewer → Directorate → directory user | Register owner/site; resolve duplicate; submit evidence; inspect; recommend; centrally decide; publish eligible services; user contacts/refers. | Incomplete evidence returns to applicant; declined case retains reasons/review; publication and recognition are separate. | Network/standards lead |
| LWH-JRN-002 | Renewal, correction and adverse review | Secretariat → facility → inspector → Directorate → independent review | Open renewal from expiry calendar; collect changes; inspect applicable criteria; decide; notify; correct/review; update publication. | Known protective restriction can be applied under policy; expiry is never silently extended; active care handover remains owned. | Standards lead |
| LWH-JRN-003 | Facility return to leadership action | Facility/local adapter → reporting officer → verifier → analyst → programme owner | Prepare period totals; check source; attest; validate; verify; publish snapshot with coverage; create accepted intervention; review result. | Nil/partial/missing/late remain distinct; failed connector produces a gap; corrections regenerate snapshots. | Health information lead |
| LWH-JRN-004 | Community event to reviewed action | Community/zone reporter → reviewer → duty/quality team → intervention owner | Capture minimal signal; assign urgency/owner; corroborate; deduplicate; classify; fulfil required notifications; act; review/close. | Unconfirmed signal is not incidence; unreachable urgent owner escalates to real local coverage. | Quality/information leads |
| LWH-JRN-005 | Executive briefing to verified intervention | Authorised leader → information owner → programme lead → delivery owner → reviewer | Check scope/coverage; inspect permitted evidence; decide resources; assign; accept; execute; submit proof; review outcome/limitations. | Unfunded/unaccepted/overdue work stays visible; completion is distinct from impact. | Directorate operations |
| LWH-JRN-006 | Education/policy to help | Editor → qualified reviewer → policy owner → coordinator → patient/service team | Curate source; label purpose/applicability; review; publish; distribute permitted content; receive help requests; correct/review. | Unclear recorded policy phrases remain unresolved; expired content is withdrawn; delivery is not comprehension. | Clinical editorial lead |
| LWH-JRN-007 | New personal/family account | Person → identity service → patient/representative → care team | Verify account; establish self; add dependant only with appropriate authority; select subject; progressively capture needed facts; seek help. | Identity recovery does not merge charts; proxy refusal/revocation isolates data. | Identity/privacy owners |
| LWH-JRN-008 | Immediate help to remote clinical care | Patient → assistant/rules → duty coordinator → clinician → follow-up team | Describe need; receive bounded assistance; escalate if applicable; request staffed review; clinician accepts; assesses; signs plan; owns follow-up. | No capacity or failed call remains an owned episode with truthful status and alternatives. | Clinical operator |
| LWH-JRN-009 | Outpatient visit to continuing care | Reception → triage → clinician → departments → clinician → patient/coordinator | Match/register; triage; allocate; assess; order; perform diagnostics/dispense; review; sign disposition; arrange plan and pending results. | Urgent patient can use provisional identity; unknowns remain unknown; optional ERP absence cannot stop care. | Facility clinical lead |
| LWH-JRN-010 | Inpatient admission to discharge | Admitting clinician → ward/nursing → pharmacy/diagnostics → discharge team → receiving follow-up | Order/admit; allocate bed; accept team; document rounds/care/MAR; hand over shifts; reconcile medicines; sign summary; preserve result/review owners. | Bed collision and stale orders are blocked; pending result survives discharge. | Hospital/nursing directors |
| LWH-JRN-011 | Diagnostic order to reviewed result | Requester → collector → department → verifier → treating clinician → patient | Sign order; identify/label; collect/receive; analyse; verify/release; acknowledge; record clinical response; communicate; close obligations. | Rejection, amendment, critical review and external unmatched result have explicit owned paths. | Diagnostic lead |
| LWH-JRN-012 | Medication intent to actual administration | Prescriber → pharmacist → nurse/patient → review team | Reconcile; sign complete order; verify product/stock; dispense; confirm current order/patient; administer or record omission; monitor/review. | No duplicate dose on retry; substitution/shortage/hold/refusal recorded; no AI-generated treatment authority. | Medication safety lead |
| LWH-JRN-013 | Pregnancy/birth to maternal/newborn continuity | Maternal team → birth team → infant record custodian → postnatal/family team | Enrol; record care; use approved labour workflow; attest actual birth; identify each infant; link relationships; schedule separate maternal/newborn reviews. | Uncertain dating and multiple births remain distinct; caregiver grants follow applicable rules. | Maternal/child lead |
| LWH-JRN-014 | Procedure/transfusion to recovery | Privileged team → preparation/check team → procedure/blood-bank → recovery/ward | Plan and authorise; assess/consent; verify phases/unit; perform and document; monitor; trace specimens/devices; accept recovery handover. | Mismatch/failed readiness creates local clinical hold/exception; planned work never becomes performed by default. | Procedural service lead |
| LWH-JRN-015 | Referral and controlled record sharing | Sender → patient/authority → exchange custodian → receiver → follow-up owner | Establish need/purpose; match; grant minimum access; send protected summary; receiver accepts; coordinate transfer; confirm receipt/outcome; reconcile tasks. | Declined/unreachable receiver leaves sender owner; additional access requires authority; no public patient browse. | Network/record custodians |
| LWH-JRN-016 | Care billing and sponsored fulfilment | Clinical service → billing → patient/payer/benefit → cashier/provider → finance | Generate evidence-linked charge; reserve benefit; invoice/claim; receive actual payment/remittance; settle/release; reconcile; optionally post GL. | Timeout remains pending; no double spending; refund/reversal retains original; urgency stays clinical. | Finance lead |
| LWH-JRN-017 | Existing EMR integration or migration | Facility owner → integration/custody team → clinical users → reconciler | Select route; map identity/data/contracts; qualify interfaces or migrate; reconcile clinical/finance truth; rehearse cutover; activate; monitor. | No blind dual writer; unresolved identities quarantined; rollback preserves post-cutover clinical work. | Migration lead |
| LWH-JRN-018 | Full clinical work during WAN loss | Facility duty/local IT → all departments → sync service → reconciliation stewards | Detect partition; retain local authority/auth/reference packages; complete all enabled clinical workflows; commit locally; reconnect; prioritise revocation/corrections; replay/deduplicate/review conflicts. | External acceptance/payment/AI remains actual pending/unavailable; LAN/power failure uses separate contingency. | Facility operator/platform lead |
| LWH-JRN-019 | Patient correction and access withdrawal | Patient/representative → privacy/custodian → clinical owner → exchange partners | Verify request authority; locate data/grants; assess; correct/addend/restrict; notify affected systems; show outcome and review route. | Historical lawful records are not destructively deleted; unresolved identity disputes stay visible. | Privacy/records owner |
| LWH-JRN-020 | Staff departure or service closure | Supervisor → incoming team → identity/network → custodians | Stop new allocation; identify open care/reports/referrals; secure accepted successors; revoke grants; update readiness/directory; retain historical records. | Work cannot vanish on account disable or affiliation removal; unaccepted obligations escalate. | Service/network owner |


## Service blueprint layers

Frontstage: user sees current status, next action, responsible team and expected update under an adopted commitment. Backstage: authority checks, record persistence, rule validation, durable jobs, source verification and accepted handovers. Support: staffing, facility readiness, finance, privacy/custody, technical continuity and escalation contacts. Evidence: local/central receipts, signed decisions, reviews, reconciliation and user communication.

## Cross-journey safeguards

The active patient and actor are distinct in every journey. Remote and facility episodes can join through explicit identity/authority links. Clinical, referral, financial, affiliation, publication and reporting states remain independent. A clinically completed encounter can still have pending result review; a recognised facility may have unavailable services; an approved claim can still be unpaid. Templates reuse known facts with provenance and freshness. Device/role changes preserve drafts only within authorised context.

## Validation procedure

Design and operational owners walk every journey using synthetic data and role-separated accounts. Each handoff verifies sender, recipient, permitted data, actual acceptance and failure owner. Repeat with missing information, unavailable service, wrong subject, a departed staff member, late source correction and WAN loss. Record elapsed work, repeated questions, user comprehension, clinical/financial discrepancies and unresolved dependencies. A visually successful path does not pass if its operational responsibility is missing.
