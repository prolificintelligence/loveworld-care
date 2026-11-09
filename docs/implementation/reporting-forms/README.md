# Proposed Directorate working reporting forms

Edition: **LWH-WORKING-2026.1**. Prepared 9 November 2026 at the project owner’s request. Status: **proposed for Director review and amendment**. This is a usable initial reporting design, not a representation that the Directorate, WHO or a national authority has approved it. No institutional returns or clinical counts are invented.

The live [template workspace](https://lw-health-intelligence.vercel.app/reporting-templates) includes the complete package. A currently authorised global Data Governor can prepare a form, recording actual provisional configuration authority and validity. This creates immutable indicator versions and a DRAFT template in one idempotent transaction. A different person must independently review its mapping before a governor records adoption. It can then be selected on an obligation and used for real manual or controlled CSV returns. Source preparation, independent verification, disclosure review and leadership release remain separate steps.

## Proposed reporting calendar

**Status:** PROPOSED_CONFIGURE_EXACT_OBLIGATIONS_AFTER_ADOPTION

**Frequency:** CALENDAR_MONTH

**Period:** Local month start inclusive through next local month start exclusive; officer records UTC boundaries and an actual IANA timezone for each obligation.

**Submission:** 23:59 local time on the fifth day of the following month

**Independent Review:** Target tenth day of the following month; unresolved returns remain unverified.

**Leadership Review:** Target fifteenth day; release only under the adopted disclosure policy with actual coverage and missingness.

**Exceptions:** No automatic deadlines, public-holiday extensions or emergency-response service levels are adopted. Urgent safety matters use the actual covered escalation route immediately, not the monthly return.

These deadlines and scope are design proposals, not externally mandated dates. No recurring calendar is silently created. Configure actual UTC boundaries, local IANA timezone, expected units, due time and authority on each obligation after adoption. A monthly review is not an urgent safety response service.

## Common form and interpretation contract

Each form retains actual reporting unit, half-open occurrence period, officer attestation, source method, per-measure source reference, completeness and reconciliation. Every expected measure is declared. Empty source fields never imply zero. Counts require integers; proportions retain numerator and denominator separately. Verification records the examined evidence and actual independent reviewer.

- Source counts and ratio components must be nonnegative. Subset numerators cannot exceed denominators. Zero or absent denominators produce an unavailable rate, never fabricated zero.
- VALUE, NIL, PARTIAL, UNKNOWN, MISSING and NOT_APPLICABLE remain distinct; non-applicability and unavailable values require explanation. A lack of service is not automatically a nil outcome.
- SUM applies only to disjoint reporting units and periods. RATIO_OF_SUMS recomputes from compatible components. NONE forbids arithmetic roll-up. Do not add zone/community activity to facility clinical contacts.
- Maintain source reference, reconciliation, officer attestation and independent examination evidence. Confidential cases stay in their protected workflow; no names, patient IDs or credential-bearing links in aggregate returns.
- Governors may configure provisional indicator versions and a DRAFT mapping. Independent review and explicit adoption remain required before template-bound obligations. Director changes create a new edition; existing obligations retain their old definitions and mappings.

The initial facility form deliberately captures coded-condition contacts without pretending to estimate particular disease incidence. Disease-specific definitions, code/case-definition versions and disaggregation require clinical ownership and a later reviewed edition. It does not reproduce all Nigerian NHMIS programme forms, replace statutory reporting, or claim complete maternal, immunisation, disease-surveillance or diagnostic-specialty reporting. Missing an approved clinical denominator is a reason to withhold a rate.

Manual is the initial source selector. The existing native-EMR completed-contact extractor remains available under its separately adopted exact definition; this proposal does not automatically qualify new extractors or add EMR and manual totals. No automatic interpretation of stockout, mortality or referral data as clinical quality is permitted.

## Source register and research choices

The local LWH-SPEC-007 catalogue supplies the 45 stable metric identifiers and scope cautions; LWH-SPEC-008 and the Director-vision alignment govern source verification, disclosure and accountability. The following primary sources informed this original implementation design. The detailed event cut-offs, selected metric subset and 5/10/15 calendar are engineering proposals, not quotations or claimed WHO recommendations.

- [WHO RHIS general principles (2023)](https://www.who.int/publications/i/item/9789240063938): RHIS indicator comparability, usable denominators and explicit data quality.
- [WHO community health data quality review (2023)](https://www.who.int/publications/m/item/module-4--data-quality-review-for-community-health-data): Community data verification and review at distinct organisational levels.
- [WHO routine data quality review (2019)](https://www.who.int/docs/default-source/documents/ddi/facilityanalysisguidance-integratedhealthsservices.pdf): Monthly quality review, source reconciliation and caution interpreting facility deaths.
- [Nigeria CHPRBN standing orders: NHMIS routine reporting forms (2024)](https://chprbn.gov.ng/wp-content/uploads/2024/12/CHO-Section-1-8-TEXT.pdf): Monthly register-to-summary reporting structure; national forms are contextual references, not imported mandates.
- [WHO SARA reference manual (2015)](https://www.who.int/publications/i/item/WHO-HIS-HSI-2014.5-Rev.1): Readiness evidence is a different concept from an actual delivered service or accepted referral.
- [WHO patient safety reporting guidance (2020)](https://www.who.int/publications/i/item/9789240010338): Safety reporting supports examined learning; raw incident reports do not establish population harm rates.

Research note: a surfaced FMoH-branded NHMIS page contained unrelated material and was excluded from the implemented source list. The professional council’s standing-orders publication supplies the Nigerian structural reference. No external source text is treated as executable instructions.

## Field dictionaries

### Proposed monthly facility health-service return

Code: `FACILITY-MONTHLY`. Stream: `FACILITY_ACTIVITY`. Measures: **15**.

| Metric | Measure | Formula / aggregation | Source |
|---|---|---|---|
| LWH-MET-010 | Completed service contacts | COUNT / SUM | Completed encounter register or verified equivalent |
| LWH-MET-011 | Distinct patients served within this facility | COUNT / NONE | Reviewed patient identity crosswalk and encounter register |
| LWH-MET-012 | Completed contacts with a coded clinical condition | COUNT / SUM | Signed assessment/diagnosis register, coding-system version and completed encounter register |
| LWH-MET-013 | Inpatient deaths by occurrence | COUNT / SUM | Signed inpatient disposition and death register |
| LWH-MET-014 | Institutional inpatient mortality proportion | RATIO / RATIO_OF_SUMS | Inpatient final disposition register |
| LWH-MET-016 | Care access fulfilment | RATIO / RATIO_OF_SUMS | Care request and delivered-service receipts |
| LWH-MET-018 | Unmet suitable-care requests | COUNT / SUM | Care request and capacity/decline evidence |
| LWH-MET-020 | Continuity tasks completed by deadline | RATIO / RATIO_OF_SUMS | Clinical task due-times and completion evidence |
| LWH-MET-023 | Planned service windows actually covered | RATIO / RATIO_OF_SUMS | Approved operating windows, duty roster and privilege evidence |
| LWH-MET-024 | Current readiness evidence for operating capabilities | RATIO / NONE | Capability catalogue and time-bounded readiness assertions |
| LWH-MET-025 | Referral requests receiving actual acceptance | RATIO / RATIO_OF_SUMS | Referral requests and receiving acceptance receipts |
| LWH-MET-026 | Referral outcomes verified by due date | RATIO / RATIO_OF_SUMS | Accepted handover, receiving outcome and due-date register |
| LWH-MET-029 | Critical results with required human follow-through | RATIO / RATIO_OF_SUMS | Critical flags, approved local policy and acknowledgement/action receipts |
| LWH-MET-032 | Essential product-days with confirmed stockout | COUNT / SUM | Locally approved essential-product list, stock ledger and physical checks |
| LWH-MET-033 | Staffed qualified bed occupancy | RATIO / RATIO_OF_SUMS | Timestamped occupancy and staffed-bed capacity ledger |

**LWH-MET-010: Completed service contacts**

- Count/numerator: Distinct completed encounter identifiers with an actual signed service/disposition in this period.
- Denominator: Not applicable: count, not a population rate.
- Unit: events; scale 1.
- Inclusion, exclusions and missingness: Exclude drafts, cancellations, appointments and duplicate copies. Remote contacts require actual completed care. This is not unique people; reconcile manual and EMR sources rather than adding them. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-011: Distinct patients served within this facility**

- Count/numerator: Distinct custodian-reviewed local patient links among the qualifying completed contacts.
- Denominator: Not applicable: count, not a population rate.
- Unit: people within facility only; scale 1.
- Inclusion, exclusions and missingness: Exclude unresolved links. No addition across facilities, zones or periods without reviewed identity reconciliation. Declare unresolved-link counts in the explanation. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-012: Completed contacts with a coded clinical condition**

- Count/numerator: Distinct qualifying completed encounters with at least one clinician-signed condition code from the facility's recorded coding-system/version; count each encounter once.
- Denominator: Not applicable: count, not a population rate.
- Unit: events; scale 1.
- Inclusion, exclusions and missingness: This initial profile selects any valid signed condition code and does not classify a specific disease. Suspected/confirmed status remains in the protected source. Exclude uncoded, voided and draft diagnoses. If the coding system or source is unavailable, report UNKNOWN. This is not disease incidence, prevalence, unique people or diagnostic accuracy. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-013: Inpatient deaths by occurrence**

- Count/numerator: Distinct verified inpatient death dispositions occurring in the period.
- Denominator: Not applicable: count, not a population rate.
- Unit: events; scale 1.
- Inclusion, exclusions and missingness: Exclude community deaths, unconfirmed reports, arrival-dead and duplicate notifications. Not deaths among community residents. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-014: Institutional inpatient mortality proportion**

- Count/numerator: Verified inpatient deaths among stays with final death/discharge disposition in the period.
- Denominator: All eligible final inpatient discharge dispositions including deaths in the same period.
- Unit: percent; scale 100.
- Inclusion, exclusions and missingness: Exclude transfers out without a final local discharge/death, arrival-dead and open stays from both components. Show case mix and incomplete dispositions in explanation. Not population mortality; no facility ranking from this alone. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-016: Care access fulfilment**

- Count/numerator: Eligible care requests received in this period with the suitable requested service actually delivered by the period-end cut-off.
- Denominator: All eligible care requests received in this period, including pending or unavailable services at cut-off.
- Unit: percent; scale 100.
- Inclusion, exclusions and missingness: Exclude duplicates, explicitly ineligible and withdrawn requests, declaring those counts in explanation. Automated acknowledgement is not care. Late outcomes enter a corrected version of this cohort. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-018: Unmet suitable-care requests**

- Count/numerator: Distinct eligible requests received in this period still unfulfilled at cut-off because suitable capacity or capability was unavailable.
- Denominator: Not applicable: count, not a population rate.
- Unit: events; scale 1.
- Inclusion, exclusions and missingness: Deduplicate repeated attempts within one request episode. Exclude patient withdrawal, ineligibility and requests merely awaiting review; disclose pending separately. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-020: Continuity tasks completed by deadline**

- Count/numerator: Required follow-up or result tasks due in the period with independently evidenced completion no later than their recorded deadline.
- Denominator: All required follow-up or result tasks whose recorded deadline falls in the period, including overdue and nonresponding cases.
- Unit: percent; scale 100.
- Inclusion, exclusions and missingness: Reminder delivery, message opening and patient nonresponse do not establish completion. Exclude a task only with documented cancellation authority, disclosed in explanation. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-023: Planned service windows actually covered**

- Count/numerator: Approved service windows in the period covered throughout by the required privileged team.
- Denominator: All approved planned service windows in the period, including uncovered windows.
- Unit: percent; scale 100.
- Inclusion, exclusions and missingness: Count each scheduled service window once; partial staffing is not full coverage. Account count, nominal employment and a directory listing do not demonstrate coverage. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-024: Current readiness evidence for operating capabilities**

- Count/numerator: Expected operating capabilities whose required readiness evidence is unexpired at period end.
- Denominator: All capabilities expected to operate at the period-end review, including those with absent or expired evidence.
- Unit: percent; scale 100.
- Inclusion, exclusions and missingness: An as-of measure: do not sum across months. Readiness is not licence, guaranteed future availability, accepted referral or quality certification. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-025: Referral requests receiving actual acceptance**

- Count/numerator: Eligible referral requests created in the period with recorded receiving-team acceptance by the period-end cut-off.
- Denominator: All eligible referral requests created in the period, including declined, unreachable and pending requests.
- Unit: percent; scale 100.
- Inclusion, exclusions and missingness: A sent message, directory match or transport booking is not acceptance. Exclude documented duplicates or withdrawal before review and disclose them. Late acceptance corrects the same cohort. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-026: Referral outcomes verified by due date**

- Count/numerator: Referrals due for outcome in the period with verified receiving outcome recorded by their due date.
- Denominator: All referrals whose recorded outcome deadline falls in the period, including overdue and lost-to-follow-up cases.
- Unit: percent; scale 100.
- Inclusion, exclusions and missingness: Acceptance, transport and travel are not completed care. Keep unknown, declined and pending outcomes visible; no patient-identifying narrative in returns. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-029: Critical results with required human follow-through**

- Count/numerator: Critical results with required acknowledgement and action completed by their policy-derived deadline falling in the period.
- Denominator: All critical results whose required action deadline falls in the period under the actual local critical-result policy.
- Unit: percent; scale 100.
- Inclusion, exclusions and missingness: Delivery receipt is not clinical acknowledgement. Include overdue and missing actions; if no approved flag/deadline policy exists report UNKNOWN, not zero. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-032: Essential product-days with confirmed stockout**

- Count/numerator: Distinct required essential-product and operating-day pairs during the period with verified usable stock unavailable for any required service interval.
- Denominator: Not applicable: count, not a population rate.
- Unit: events; scale 1.
- Inclusion, exclusions and missingness: One product-day once regardless of repeated attempts. Quarantined or uncertain stock is not usable; disclose uncertainty separately. Not number of patients harmed or a population rate. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-033: Staffed qualified bed occupancy**

- Count/numerator: Occupied minutes in eligible staffed qualified beds during the period.
- Denominator: Available staffed qualified bed-minutes during the same period.
- Unit: percent; scale 100.
- Inclusion, exclusions and missingness: Exclude closed/unqualified beds from both components and document closures. Reservations are not occupancy. Do not use licensed bed count as staffed capacity; unknown capacity means unavailable ratio. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

### Proposed monthly zone community-health return

Code: `ZONE-MONTHLY`. Stream: `ZONE_COMMUNITY`. Measures: **3**.

| Metric | Measure | Formula / aggregation | Source |
|---|---|---|---|
| LWH-MET-035 | Approved health education sessions delivered | COUNT / SUM | Approved education content and session delivery register |
| LWH-MET-036 | Community interventions completed by deadline | RATIO / RATIO_OF_SUMS | Intervention commitments, due dates and independent completion reviews |
| LWH-MET-027 | Required demand areas with evidenced serviceability | RATIO / NONE | Approved area inventory, access standard and serviceability assessment |

**LWH-MET-035: Approved health education sessions delivered**

- Count/numerator: Distinct approved health education sessions actually delivered in the period with content-version and delivery evidence.
- Denominator: Not applicable: count, not a population rate.
- Unit: events; scale 1.
- Inclusion, exclusions and missingness: Exclude plans, duplicate broadcasts counted as the same session and unapproved messages. Sessions are not recipients, comprehension, clinical contacts or improved health outcomes. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-036: Community interventions completed by deadline**

- Count/numerator: Accepted community interventions due in the period with evidence independently accepted complete by deadline.
- Denominator: All accepted community interventions due in the period, including blocked and overdue work.
- Unit: percent; scale 100.
- Inclusion, exclusions and missingness: A proposed, unowned or merely funded activity is not accepted completion. Exclusions and cancelled commitments require authority and remain disclosed. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-027: Required demand areas with evidenced serviceability**

- Count/numerator: Required demand areas meeting the adopted serviceability standard at period end with reviewed capability and access evidence.
- Denominator: All demand areas in the actual approved required-area inventory at period end.
- Unit: percent; scale 100.
- Inclusion, exclusions and missingness: If the inventory or access standard is absent, report UNKNOWN. Facility counts or self-selected attendance cannot establish geographic reach. Do not sum as-of percentages over periods. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

### Proposed monthly regional coordination return

Code: `REGION-MONTHLY`. Stream: `REGIONAL_COORDINATION`. Measures: **4**.

| Metric | Measure | Formula / aggregation | Source |
|---|---|---|---|
| LWH-MET-001 | Verified active registry coverage | RATIO / NONE | Expected-site inventory and verified registry records |
| LWH-MET-003 | Corrective actions completed by deadline | RATIO / RATIO_OF_SUMS | Affiliation corrective-action due dates and independent acceptance |
| LWH-MET-004 | Affiliation renewal decisions made in time | RATIO / RATIO_OF_SUMS | Prior decision expiry and actual renewal-decision timestamps |
| LWH-MET-036 | Regional interventions completed by deadline | RATIO / RATIO_OF_SUMS | Regional commitments, due dates and independent completion reviews |

**LWH-MET-001: Verified active registry coverage**

- Count/numerator: Expected in-scope sites with a verified active registry record at period end.
- Denominator: All sites in the approved expected-site inventory at period end, including sites not registered.
- Unit: percent; scale 100.
- Inclusion, exclusions and missingness: No approved expected-site inventory means UNKNOWN. Registered sites alone cannot form both components. Count facility sites, not owners; do not sum across months. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-003: Corrective actions completed by deadline**

- Count/numerator: Corrective actions due in the period with independently accepted completion no later than deadline.
- Denominator: All corrective actions due in the period, including overdue and nonresponding sites.
- Unit: percent; scale 100.
- Inclusion, exclusions and missingness: Keep severity and criteria versions in the supporting evidence. Self-attested completion and an expired obligation are not accepted corrective closure. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-004: Affiliation renewal decisions made in time**

- Count/numerator: Prior affiliation decisions expiring in the period with the renewal decision recorded before the prior expiry.
- Denominator: All prior affiliation decisions due to expire in the period, including expired and nonresponding sites.
- Unit: percent; scale 100.
- Inclusion, exclusions and missingness: Do not infer renewal from registration or a pending application; do not remove expired sites to improve the proportion. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

**LWH-MET-036: Regional interventions completed by deadline**

- Count/numerator: Accepted regional coordination interventions due in the period with independently accepted completion by deadline.
- Denominator: All accepted regional coordination interventions due in the period, including blocked and overdue work.
- Unit: percent; scale 100.
- Inclusion, exclusions and missingness: Exclude zone-delivered interventions already counted in the zone stream. Completion requires evidence and independent acceptance; funding alone is not fulfilment. Missing or unreliable sources are UNKNOWN/MISSING/PARTIAL with explanation; zero is explicit NIL only after source review. No patient identifiers in aggregate references.

## Review, replacement and retained meaning

The Director can amend the selected indicators, source rules, applicability, roles or calendar. Before submission, draft changes append a new version; all contributors are excluded from independent review. After submission/adoption, create a new edition rather than rewriting a frozen one. Withdrawal stops new template-bound obligations but preserves earlier obligation bindings, return interpretation, review evidence and historical reporting.

The source SHA-256 for the built-in proposal is the canonical JSON digest returned by the package API, not a hash of a downloaded WHO publication. Uploaded/external originals remain author-attested references; this increment does not fetch or malware-scan them.

Canonical proposal SHA-256: `32263c514fc2a069b52628018883d55814282e12a65a13a508e341f0e883ffb7`.

Director decisions requested at operating adoption: approve or replace the three form scopes; confirm responsible officers and reviewers; choose jurisdiction applicability and reporting timezone; approve calendar and follow-up ownership; confirm whether the coded-condition profile should be replaced by named clinical case definitions; adopt disclosure rules and representative source checks. Software implementation and deployment proceed independently of that review.
