# Implementation review and recommended next phases

Review date: **8 November 2026**, Africa/Lagos. This is a delivery assessment and proposed implementation sequence. It preserves the authored baseline and the project lead's decisions to defer offline installation and avoid Playwright installation. No application implementation, migration or deployment was performed during this review.

## Subsequent scope decision

The project lead clarified that offline care remains core and that only deployments outside the existing cloud stack must be deferred. Facility-local installation and additional worker/scanner hosts are therefore deferred. Cloud-compatible engineering continues in the recommended sequence. The historical review findings below describe the pre-Phase-4A runtime; subsequent delivery is recorded in [the controls release](2026-11-08-control-release.md) and [cloud recovery/reconciliation release](2026-11-08-cloud-recovery-release.md).

## Subsequent scope decision

The project lead clarified that offline care remains core and that only deployments outside the existing cloud stack must be deferred. Facility-local installation and additional worker/scanner hosts are therefore deferred. Cloud-compatible engineering continues in the recommended sequence. The historical review findings below describe the pre-Phase-4A runtime; subsequent delivery is recorded in [the controls release](2026-11-08-control-release.md) and [cloud recovery/reconciliation release](2026-11-08-cloud-recovery-release.md).

## Recommendation

**Start Phase 4A: shared production controls and activation readiness.** Complete the controls on which every further clinical, patient and financial workflow relies. Follow with Phase 4B to close the remaining institutional lifecycle and approved-information gaps. Clinical completion can progress alongside Phase 4B once the relevant shared controls are available.

Keep the programme directed toward the full documented platform. Patient/family care, full clinical departments, existing-EMR integration and migration, care finance, governed assistance, and full facility-local offline care remain core scope. The current cloud releases are substantial deployed increments; full-suite acceptance is still outstanding. Accounting, procurement, HR and payroll remain a separately scoped optional extension.

## Baseline and review method

Reviewed the [documentation index](../LW_Health_Intelligence_Platform_Documentation_Index.md), suite manifest/reading routes and control decisions, all 200 granular requirements, acceptance catalogue, delivery roadmap, relevant shared/governance/operating contracts, existing progress/release records, deployed application sources and test coverage structure. Source inspection focused on identity, activation, storage, scheduling, clinical contracts, reporting, permissions and production packaging. This is not an independent penetration test, clinical validation or exhaustive line-by-line security audit.

All **78 controlled document SHA-256 hashes match** the manifest. The suite describes **25 PRDs, 21 specifications, 51 forms, 355 tagged fields, 75 screens, 20 journeys, 45 measures and 111 acceptance specifications**. These are authored scope counts, not counts of implemented or accepted features. The original 200 requirement records remain NOT_ASSESSED/NOT_RUN; the original 111 acceptance cases remain NOT_RUN. Executed engineering tests are separate evidence.

The supporting files are:

- [200-requirement phase allocation](2026-11-08-next-phase-requirements.csv): every original requirement ID is allocated once to its primary review/completion phase, with its original verification expectation. Existing work is to be verified and its gaps closed, rather than rebuilt indiscriminately. Assignment is not a completion assertion, estimate or claim that 200 requirements are missing.
- [78-document integrity inventory](2026-11-08-controlled-document-review-inventory.csv): exact source paths and matched baseline hashes.
- [Existing overall progress matrix](2026-11-05-platform-progress.md): coverage across all 25 PRDs and 21 specifications.

The proposed phase labels below continue implementation releases 1-3. They do not rename the canonical LWH-EP epic IDs in LWH-ENG-002. Cross-cutting specifications, operational work and final qualification supplement the PRD requirement allocations in the CSV.

## Work delivered and evidence

| Increment | Verified delivered scope | Material boundary |
|---|---|---|
| 1. Institutional foundation | Persistent MFA identity and scoped grants; facility/operator registration; evidence/inspection/central affiliation decisions; public directory controls; real configured cloud integrations | Full recovery/delegation, effective hierarchy stewardship, renewal/adverse review, scanned evidence and readiness operations remain incomplete |
| 2. Cloud EMR | Encrypted charts, encounters, signing/addenda/corrections, consent/sharing, diagnostics, medicines/MAR/stock, beds/stays, programmes, procedures/transfusion, referrals, appointments, reviewed identity links, tariffs/invoices/cash ledger | Breadth of workflows exists; complete specialty data, coverage/capacity, exception variants, payer/finance and external interfaces remain partial; cloud access is required |
| 3. Directorate reporting | Frozen obligations/metric versions, explicit missingness, controlled imports, actual completed-encounter extraction, independent verification, protected safety review, disclosure-controlled snapshots, accepted actions/handovers and overdue exceptions | One automatic EMR extractor; broader source mappings, institutional adoption, stewardship at scale, portfolio/learning and real-time delivery remain outstanding |

The progress matrix contains **20 partial PRDs**, **3 not delivered** (010 education/policy, 013 sponsored programmes, 023 patient/family), **1 infrastructure-only** (014 governed assistants), and **1 deferred/optional** (025 ERP). These categories do not support a defensible percentage-complete figure.

The tested runtime is commit `173d60adce9eda255fb8dbef1c35fde14f3a59ff`; current reviewed repository HEAD is `b46e6d3d3a81cfc814b89e0484459d746eed9261` (release evidence and verification diagnostics). The [runtime CI](https://github.com/prolificintelligence/loveworld-care/actions/runs/42421116592) recorded **116 passing tests**, web checks and secrets scan. The [current HEAD CI](https://github.com/prolificintelligence/loveworld-care/actions/runs/42421937528) is also successful for Python, web and secrets scan. No broad functional suite was rerun for this documentation review.

During this review, live verification again confirmed both production deployments READY, matching source hashes for **29 API and 13 frontend files**, actual schema **3**, reporting READY, no-store API responses, denied unauthenticated clinical/reporting access, and HTTP 200 for /, /care, /directorate, /activate and /directory. Existing release evidence also records actual isolated Neon concurrency, immutable-history, revocation and restart checks, plus post-migration clinical note/bed/stock protection checks. See [exact release evidence](2026-11-07-directorate-release.md).

A current metadata-only production read at **2026-11-07T23:04:22Z (8 November in Africa/Lagos)** found zero adopted reporting definitions, obligations, returns, disclosure policies, cohorts/snapshots, event categories, duty windows, safety cases and actions. It also confirmed immutable protections on **28 history tables** and the signed clinical record trigger for UPDATE/DELETE. The new reporting module is installed; real configuration/adoption and operating acceptance remain outstanding. No protected record contents were read for that check.

These checks establish the recorded behaviours and deployment state. They do not establish complete conformance of all 51 forms, all 200 requirements or the 111 acceptance specifications, nor operating acceptance of real clinical services.

## Findings that determine priority

| Priority | Finding and evidence | Implementation consequence |
|---|---|---|
| Before clinical activation | Clinical tasks are persisted and have owners, but the deployed daily job delivers invitations and reconciles reporting/safety/action exceptions. It does not run the full clinical critical-result, due-care, abandoned-handover and patient-contact scheduling contract. See main.py deliver_jobs, clinical/service.py task, and vercel.platform.json | Deliver restart-safe scheduling, retries, dead letters, accepted fallback ownership and real neutral delivery receipts under adopted response windows. A daily cron is insufficient evidence of urgent clinical response |
| Before wider enrolment | Strong staff MFA/session checks exist; the production authentication routes do not supply the suite's verified recovery, complete acting/delegation and offboarding-with-work-transfer flows | Finish recovery and lifecycle controls before patient/family and broader staff onboarding |
| Before service/country activation | Clinical activation checks facility identity, statutory status, scope and policy references. The full versioned country/operator package, processing-location/retention evidence, reviewer decisions and restricted country/service activation dossier remain incomplete | Add package/evidence resolution and independent scoped activation/restriction controls; preserve historical policy versions. Software cannot supply the missing real approvals |
| Before document-dependent use | storage.py fails closed without configured scanning. A successfully qualified scanner-to-private-object-to-authorised-view path is not established by the release evidence; clinical attachments are also unfinished | Complete actual scanner/quarantine/private upload/retrieval, correction/retention and audited current-authority checks. Reuse private storage rather than accept unscanned files |
| Before pilot/expansion | Restore/keys/files/open-obligation reconciliation, adopted load/capacity, independent privacy/security assessment and observed user accessibility/task performance remain unqualified | Build and execute controlled recovery, capacity and manual UI/accessibility evidence. Preserve the no-Playwright-installation constraint |
| Before institutional scale | Multiple reporting lists have fixed limits; some actor-specific filtering happens after a bounded query. People lookup also has a bounded candidate set. A user's actionable work can become difficult to discover at scale | Apply relevant ownership/scope predicates before limits, use stable cursor/search controls, and show truncation/count freshness. Qualify the global reporting write lane and snapshot work at actual load |
| Next core capability work | Programme, procedure and note workflows are real, but generic programme fields/narratives are not complete labour/birth, immunisation, anaesthesia, nursing and exception workflows. StayAction currently covers transfer/discharge, not every special disposition | Complete structured specialty and exception paths against PRD-015 through 021 and 024, not merely add menu entries |
| Programme completeness | Patient self-service, approved education/policy publication, funded entitlement programmes, claims/refunds/settlement, qualified partner interfaces and governed assistant tools remain missing or partial | Give each a concrete phase with end-to-end acceptance and actual dependency evidence |
| Full-scope acceptance | The cloud runtime does not provide facility-local care during WAN loss; country/custody cells and both existing-EMR adoption routes are not fully qualified | Maintain explicit architecture and compatibility obligations now. Retain offline care as core; defer its facility-local deployment while continuing compatible engineering and retaining its acceptance dependency |

The source anchors for these findings are [authentication and daily jobs](../../services/api/src/lw_care_api/platform/main.py), [clinical activation and permissions](../../services/api/src/lw_care_api/platform/clinical/router.py), [task ownership](../../services/api/src/lw_care_api/platform/clinical/service.py), [specialty input contracts](../../services/api/src/lw_care_api/platform/clinical/contracts.py), [private storage and scanning](../../services/api/src/lw_care_api/platform/storage.py), [bounded reporting queries](../../services/api/src/lw_care_api/platform/reporting/router.py) and [the deployed cron configuration](../../vercel.platform.json).

These are identified scope/control gaps and evidence limitations. No new exploit, record loss or clinical harm was demonstrated by this review.

## Recommended phase sequence

### Phase 4A - Shared production controls and activation readiness

Canonical coverage: LWH-EP-02/10; PRD-001 and cross-cutting care obligations; SPEC-003/011/015/016/021; GOV-002/003/004/006/008; ENG-003/005/006; OPS-005/007.

Deliver verified account/MFA recovery and accepted work transfer on staff departure, expiry or revocation; durable scheduled jobs with an outbox consumer, retries, delivery receipts, dead-letter recovery and audit; real scanning/quarantine/private document access; country/operator/service policy and activation evidence; versioned key recovery/rotation procedures; separate staging/test/live configuration; operational telemetry and staffed incident routes. Establish a requirement-to-code/test/evidence register for the 200 requirements and 111 acceptance specifications.

Exit evidence: recovery cannot merge charts or restore revoked professional authority; scheduler restart/retry cannot lose or duplicate obligations; actual failed notification leads to an owned alternative; wrong-subject/revoked document access is denied; a clean isolated restore recovers database, files, keys and open clinical/stock/finance obligations; incomplete/expired/conflicting activation packages block the affected scope. Execute manual keyboard/screen-reader/device journeys with available tools and no Playwright installation. Response windows and load/RPO/RTO values come from actual operating owners.

### Phase 4B - Complete institutional lifecycle and approved information

Canonical coverage: LWH-EP-03/04; PRD-001 through 008 and 010; SPEC-005/007/008/014; OPS-001 through 004.

Deliver effective-dated hierarchy change and duplicate/site closure stewardship; affiliation findings/responses/corrective work, renewals, notices, restriction, appeal and reinstatement; propagation to publication/routing while preserving care custody. Extend quality assignments, expected calendar opening, source/template reconciliation, returned findings and role-specific leadership defaults. Complete searchable/paginated worklists and governed recomputation of successor snapshots without rewriting published history. Add approved education/policy authoring, qualified review, applicability, publication, correction/withdrawal and distribution receipts. General references and clinical content retain their own approval/licensing boundaries.

Exit evidence: a zone transfer preserves prior returns; expired affiliation cannot silently stay current; appeal/reinstatement retains decisions and notices; all source import rows reconcile; corrections produce reviewed successor evidence and mark affected prior exports; patient-facing policy only publishes a current approved version and withdrawn content is not presented as current. Execute relevant UAT-002/004 through 014 with actual observations.

Phase 4B and Phase 5 can overlap after their required shared controls land. Real hierarchy, affiliation criteria, templates and disclosure decisions remain adoption inputs, not invented fixtures.

### Phase 5 - Complete the clinical workflows for all four facility types

Canonical coverage: LWH-EP-05/06; PRD-015 through 021 and 024; SPEC-018/019; clinical content dependencies from SPEC-021.

Use coherent end-to-end clinical releases: ambulatory/emergency and responsible-team capacity; hospital/nursing/shift handover and leave/self-discharge/death variants; maternal/newborn/labour/birth and child growth/immunisation; diagnostic correction and clinical response; medicines reconciliation, substitutions, returns/reservations/witnessed adjustments and explicit dose/infusion checking interfaces; procedures/anaesthesia/recovery, component/implant traceability and recall. Add complete patient instructions, department worklists, actual service rosters and coverage. Preserve signed history and existing concurrency controls.

Exit evidence: each of the four facility types completes an authorised register-to-disposition journey including a declined handover, amended result, staff absence and an unresolved follow-up that remains owned. Qualify UAT-018 through 026 and relevant stock/medication/team cases. Automated clinical calculations, thresholds and schedules enable only after their actual licensed/applicable package is adopted; manual documented care remains available within approved scope. Partner interfaces qualify in Phase 7; their prerequisites may be developed alongside the relevant department slice.

### Phase 6 - My LW Health Care and family authority

Canonical coverage: LWH-EP-07; PRD-001/012/015/023; SPEC-001/003/012; GOV-004.

Deliver public personal enrolment/recovery and reviewed links to facility patient identities; explicit subject switching; verified dependant/caregiver scope, expiry/revocation and age/confidentiality changes; Today/Get help/My health/Care/Family flows; readable plans, medicines, appointments, permitted released results, timeline, access history and correction requests; neutral controllable reminders and self-reports. Provide a truthful conversation/help channel with automation and human status clearly identified. AI is not required for the core portal; governed assistant capabilities follow Phase 9.

Exit evidence: wrong subject, revoked proxy and sensitive records remain isolated across direct APIs, exports, drafts, reminders and conversation. Switching family profiles cannot carry prior subject data forward. A patient can request care, see actual ownership/next step and review permitted history without repeated registration. Execute UAT-003/015/016 and relevant sharing/continuity cases using actual UI observations.

### Phase 7 - Connected care, partner interfaces and both EMR adoption routes

Canonical coverage: LWH-EP-07/10; PRD-009/011/012 and external portions of 004/005/019; SPEC-005/012/020; ENG-007.

Deliver time-bounded service readiness, suitable matching and verified local contacts; receiving acknowledgement/acceptance/receipt/outcome with retained sender responsibility; remote asynchronous/video consultation with recovery and actual covered staffing; controlled source-attributed exchange and correction/revocation receipts. Qualify selected real LIS/PACS/DICOM/device/document/FHIR or explicitly mapped non-FHIR adapters. Route A retains an existing EMR and exchanges approved data. Route B supplies migration staging, raw-source preservation, per-item quarantine, counts/meaningful clinical reconciliation, fenced cutover and rollback that preserves new care.

Exit evidence: a selected actual partner passes correct/wrong identity, duplicate, amended/out-of-order data, unavailable endpoint and failed-contact cases with semantic receipts. A call failure preserves the care episode. A real source-system rehearsal accounts for identities, signed history, active medicines/results/tasks, stock and financial state. UAT-007/017/027/028/033 are qualified for the applicable scope. No partner, dispatch coverage or standard conformance is claimed without the actual counterpart evidence.

### Phase 8 - Complete care finance and sponsored programmes

Canonical coverage: LWH-EP-08; PRD-013/022; COM-001/003.

Extend the existing tariffs/invoices/cash ledger with payer responsibility splits, actual provider payment intents/callbacks/receipts/allocation, partial payments and reconciliation; claims/acknowledgement/adjudication/remittance/rejection/appeal; independent maker-checker refunds/reversals/write-offs; funded programme eligibility, restricted funds, atomic reservation/release/settlement and privacy-controlled statements; qualified optional accounting export. Preserve currency/scale/source/version and balanced append-only effects.

Exit evidence: concurrent reservations cannot overspend; duplicate callbacks cannot double post; timeouts remain unconfirmed; refunds and adjustments need independent approval; claim approval and payment remain distinct; delivered care reconciles to charges, payer allocations and actual receipts. Execute UAT-029/030 and relevant accounting-independence checks. Requires real contracted provider/payer/programme terms and approved prices; urgent care priority remains independent of balance. This work can overlap later patient/partner releases once the relevant fulfilment contracts are stable.

### Phase 9 - Governed assistants and bounded automation

Canonical coverage: LWH-EP-09; PRD-014 plus assistant portions of 007/023/024; SPEC-013; GOV-007.

Deliver registered use cases, approved sources and source-linked deterministic summaries, strict subject/purpose-scoped retrieval, typed tool allowlists and independent authorisation, versioned drafts and correction invalidation, human review/signing, approved provider processing scope, cost/timeout controls, evaluation and use-case rollback. Start with lower-consequence documentation/report preparation; activate each clinical use case only after its own evidence.

Exit evidence: source negation, stale/contradictory facts, malicious retrieved text, wrong subject, forged citation and attempted tool/authority expansion fail safely. Every cited number reconciles to deterministic source data. AI-off and the free provider being unavailable preserve the underlying care and reporting workflows. Execute UAT-034 and use-case-specific reviewed evaluations. A working free OpenRouter probe is infrastructure evidence, not delivery or approval of these assistant capabilities; never substitute a paid model silently.

### Phase 10 - Integrated qualification and controlled activation/expansion

Canonical coverage: LWH-EP-10; ENG-003/004/005/006/007; SPEC-015/016/021; GOV-008; OPS-005/006/007.

Select actual country/operator/facility cohorts; resolve real policy/custody, staff/privileges/readiness, licensed content, contracts/funding and support inputs. Qualify the release's full enabled scope using the requirement/test register, 111 specified acceptance cases, representative user/device accessibility, independent security/privacy/clinical/finance review, adopted-load/capacity and database/files/keys restoration. Record actual staff training/competence, incident and reconciliation drills, scoped authorised decisions and rollback/exit procedures. Expand only on observed fulfilment and reviewed exceptions.

Exit evidence: all applicable required cases have actual release-specific results, reviewers and dispositions; unexecuted cases remain explicit. No critical clinical/privacy/financial integrity issue is waived by an ordinary green build. Cloud engineering qualification can proceed while offline installation is deferred. **Full facility-core acceptance still depends on the deferred offline capability and its outage/reconnect qualification.** Software deployment, institutional adoption and clinical activation remain distinct decisions.

### Core offline care lane - Facility-local deployment deferred

Canonical coverage: LWH-EP-05/06/10; LWH-DEC-112; SPEC-017; OPS-006; UAT-028/031/032/036.

The project lead defers deployments outside the existing cloud stack. Offline care remains core; cloud-compatible foundations and deployment scripts may proceed, while installation and hosting of the facility-local runtime remain deferred. Do not remove this from the core backlog or represent a browser cache as equivalent. Full delivery still requires the complete local API/database/files/identity/policy/department/printing/job stack, single writer with authority epochs and fenced failover, valid bounded credentials, durable outbox/inbox and per-item semantic reconciliation, accepted conflicts, local backup/restore and mixed-version packages. Execute all enabled clinical/stock/billing workflows during an adopted WAN partition, restart and recovery. The suite's 72-hour example is a proposed qualification target, not an adopted service promise.

Preserve node/custodian/source versions, durable event identities and portable packaging in cloud changes now. Those compatibility precautions do not constitute installation of an offline runtime.

### Optional extension - Full accounting, procurement, HR and payroll

Canonical coverage: LWH-EP-11; PRD-025. Implement only under separately agreed scope, with its own employment/payroll/accounting rules and segregation. Clinical rosters, care billing and clinical stock remain core and independent of this extension.

## First implementation batch after this review

| Order | Concrete batch | Required result before calling the batch complete |
|---|---|---|
| 4A.1 | Requirement/evidence and activation registry | Exact IDs, implemented/partial/missing findings, source/tests/evidence, accountable owners and adopted package gates; archive unchanged |
| 4A.2 | Verified recovery, delegation and offboarding | Staff recovery works without clinical identity merge; current authority is preserved/revoked correctly and outstanding work has an accepted owner |
| 4A.3 | Durable job and clinical obligation delivery | Restart-safe task/deadline processing, actual adopted coverage, neutral provider receipts, failed-contact ownership and dead-letter replay with one domain effect |
| 4A.4 | Scanner and private evidence/clinical attachments | Real scan/quarantine, private persistence and current-authority retrieval with wrong-subject/revocation and failure evidence |
| 4A.5 | Restore, operational observability and accessible existing workflows | Isolated database/files/key restore with source/open-care/ledger/stock reconciliation; adopted load evidence; observed role/device accessibility; release/containment runbooks |
| 4B.1 | Standards lifecycle plus institutional usability | Renewal/notice/appeal/correction/custody and complete searchable work discovery with retained historical scope |
| 4B.2 | Approved information and reporting completion | Governed policy/education lifecycle, actual template mapping and corrections through independent successor snapshot release |

Phase 4A controls are not a reason to halt independent specifications, UI design or synthetic development in later phases. Dependent production enabling waits for the actual required control/adoption evidence. Per-feature releases retain the established process: meaningful checks, exact source, additive/reconciled migrations, staged compatible deployment, live verification and an updated suite-wide progress record.

## Decisions and inputs to obtain while engineering continues

Actual country/facility selection and intended services; clinical/privacy/records/information/finance/service owners and deputies; validated Region/Zone roster; mandated templates and affiliation renewal/review rules; disclosure assessment and clinical content; adopted coverage and tested contacts; processing/retention/key recovery and measured load/RPO/RTO; real EMR/department/payment/payer counterpart specifications and agreements; operating support/funding. Emmanuel Patrick's Directorate administrator nomination does not itself supply the separate clinical, privacy, finance or independent-review authority.

These inputs govern adoption, interface qualification and effort estimates. Calendar dates, prices, staffing capacity, partner availability, clinical thresholds and approvals have not been invented. The roadmap is ordered by dependency and exit evidence; reliable effort/calendar estimates follow these concrete decisions and requirement-level sizing.
