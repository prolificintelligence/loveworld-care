# Implementation audit and recommended next phases

Assessment: 9 November 2026, Africa/Lagos. Repository HEAD: `331fe1c9d8f8f0dc3c0b09bce73d42a6671c7bcb`. Latest frontend runtime change: `c500275e8ba2a0ee6a5a21535fd6849f6707cc9e`.

## Assessment

The platform has a substantial deployed institutional, clinical and Directorate implementation, with real persistence, scoped authority, protected history and executed recovery evidence. It is not yet a fully accepted operational implementation of the documentation suite. The next major capability phase remains **Phase 6: My LW Health Care and family authority**, preceded or accompanied by a focused closure batch for remaining Phase 4A/4B/5 readiness and reliability gaps.

The most immediate dependency is actual adoption and activation. The current production metadata still contains no facilities, adopted affiliation criteria, clinical sites, clinical records or operating policy packages. This is evidence of an unpopulated operating configuration, not evidence that the corresponding software is absent. Deployment readiness must not be treated as approval to operate clinical services.

## Method and evidence boundary

Reviewed the documentation index, controlled-suite integrity, existing 25-PRD/21-specification matrix, 200-entry evidence register, Phase 5 and login release records, relevant patient/family and offline contracts, current route/module inventory and targeted source paths for queues, authority, resource projections, storage, scheduling, authentication, finance and integrations. This is a targeted implementation and evidence audit, not a complete line-by-line security review, penetration test, clinical validation or observed browser/accessibility UAT.

Fresh checks executed during this audit:

- All **78 controlled document hashes** match the manifest; the authored suite remains unchanged.
- Current HEAD [CI run 42529436960](https://github.com/prolificintelligence/loveworld-care/actions/runs/42529436960) is successful for Python, web and secret scanning. The latest runtime release records **182 Python tests and eight client tests**, type checking and production builds. No broad test suite was rerun for this audit.
- Read-only cloud/Neon observations started at **2026-11-09T05:06:50.459659+00:00**. Both public frontend and API origins returned HTTP 200/readiness READY, schema 7, advanced clinical/reporting/controls READY and no-store responses. Signed-out `/v1/auth/me` returned the expected HTTP 401.
- Neon reports schema 7, **48 protected history tables** and **13 assurance observations**. Facilities, criteria, clinical sites/records/stock/ledger, operating policy packages and all 18 institutional tables remain empty. Only aggregate metadata was inspected; no patient record contents, credentials or session tokens were read.
- The requirement evidence register contains **43 PARTIAL_ENGINEERING_EVIDENCE** entries and **157 REQUIRES_REQUIREMENT_LEVEL_REVIEW** entries. All 200 baseline verification statuses remain NOT_RUN. These counts measure traceability maturity; 157 does not mean 157 features are unimplemented. The 111 authored acceptance specifications remain unexecuted baseline records.

Historical evidence reviewed, not rerun today: Phase 5 actual Neon concurrency/immutability/restart checks, private-object recovery with nonempty synthetic clinical/file populations, retained schema-5/schema-6 restoration after schema 7, and the schema-7 production archive/restore. The latter recovered 91 tables / 107 rows / zero files and nine encrypted fields; the small production population does not qualify representative clinical load or recovery targets.

The latest recorded deployments are API `dpl_CGBAJc4hxkKWYUgvfq2G5Cz4r9dU` and frontend `dpl_7dFRAaYWcxdtmoBPGtKPWAyMmH3h`. The [login release](2026-11-08-login-connectivity-fix.md) records matching **52 API / 19 frontend** source hashes and actual login POST checks through both origins. Deployment inventories and hashes were not fetched again in this audit; today's health checks are a separate current observation.

## Material gaps, in priority order

| Priority / finding | Evidence and consequence | Recommended closure and acceptance evidence |
|---|---|---|
| **Before clinical activation: real operating adoption** | Current aggregate counts are zero for facilities, criteria, clinical sites and operating packages. Existing code requires scoped activation and independent professional privileges. Administrative appointment alone does not establish clinical authority. | Nominate the actual jurisdiction/operator/facility cohort, accountable clinical governor, verified staff, adopted criteria/content and service policies. Exercise registration → affiliation → activation → professional privilege → actual permitted service access, retaining independent decisions and denial of incomplete/expired scope. Do not seed fictional approvals. |
| **Before urgent clinical operation: escalation coverage** | `vercel.platform.json:5` configures daily jobs. Durable jobs, retries and a continuous worker implementation exist, but additional persistent hosting is deferred. Daily/manual processing cannot establish timely response to urgent results or unattended handovers. | Adopt response windows and staffed primary/fallback ownership. Qualify scheduling/delivery on the authorised stack against those windows; where it cannot meet them, retain the operating restriction and deferred hosting dependency. Exercise restart, duplicate delivery, provider outage, failed contact and personally accepted fallback. |
| **Before document-dependent use: scanning and attachments** | `platform/storage.py:32` requires a ClamAV host and rejects uploads when scanning is unavailable. The last release records the scanner as unconfigured; live scanner configuration was not re-read in this audit. Private archive/file recovery evidence does not demonstrate a working upload scanner. | Qualify the actual scan → quarantine/accept → private object → current-authority view/correction path. Preserve the existing rejection behaviour. Scanner hosting beyond the current stack remains deferred; do not claim attachment-dependent workflows operational until qualified. |
| **Before larger enrolment: queue completeness** | `reporting/router.py:562` caps safety-case candidates at 200, then filters some by actor. Actions also filter protected cases after a 200-row limit (`:622`). Quality/exceptions lack continuation for their capped lists. Eligible work can be absent from the returned page even while it exists. | Move all applicable actor/scope predicates before limits, add stable pagination/search and explicit continuation, and update the UI. Test more than 200 mixed-authority records, earliest/overdue work, tied sort values and privilege changes across pages. This is a code-confirmed discoverability risk; no production loss or disclosure was demonstrated. |
| **Before workforce scale: recipient discovery** | `reporting/router.py:185` limits joined candidate grant rows to 1,000 before scope filtering/grouping. Clinical staff selectors cap results at 200 (`clinical/router.py:665,683`) without continuation. Valid recipients can become undiscoverable. | Add scoped server-side search and stable pagination, deduplicate accounts before limits, and prove eligible recipients remain discoverable beyond the cap without revealing unrelated staff. Current submission-time authority checks must remain. |
| **Before multi-facility scale: projection availability and cost** | `clinical/flow_index.py:ready` checks all clinical records without a facility predicate; `clinical/advanced.py:20` and resource/worklist routes invoke it. One mismatched record can block advanced commands or boards in otherwise independent facilities. The query also creates a load concern as source volume grows. | Measure the current path on representative data. Design facility-scoped readiness/repair where isolation is valid, retain global reconciliation and source-version protections, and test two facilities with one deliberately stale projection. Do not weaken safety gates merely to make readiness green. This audit did not measure a performance failure. |
| **Before claiming clinical completion: specialist and exception qualification** | Phase 5 adds actual manual nursing, labour/birth, immunisation, reconciliation, stock, anaesthesia and traceability workflows. Licensed calculations, adopted thresholds/schedules, full specialist templates, statutory/controlled-drug variants and external device conformance remain outstanding. | Map enabled services to their exact applicable requirements and protocols. Qualify each of the four facility types through register-to-disposition journeys with staff absence, declined transfer, amended results, adverse outcomes and unresolved owned follow-up. Enable algorithms only against approved applicable packages. |
| **Before broad rollout: recovery and operating assurance** | Actual encrypted restores are established. Automatic backup cadence, independent copies/key custody, rotation/retirement, full provider/configuration recovery, adopted RPO/RTO and representative-load service resumption remain unqualified. | Record actual targets and accountable operators; implement supported scheduling and independent custody arrangements; rehearse an appropriately sized database/files/keys/configuration recovery with open work/stock/finance reconciliation and reviewed service resumption. Preserve retained archives and the independent recovery key. |
| **Before closing requirements: acceptance traceability and observed usability** | 43 requirements have bounded partial engineering links; 157 still need requirement-level review. Formal baseline cases remain NOT_RUN. HTTP 200 and a build do not demonstrate clinician task success, keyboard/screen-reader use, low-bandwidth behaviour or full security/privacy conformance. | Create a versioned execution register separate from the authored baseline, with applicability, exact release/configuration, observed result, evidence, reviewer and unresolved exceptions. Execute actual user/device journeys and independent reviews. No Playwright installation is required for manual qualification. |
| **Near-term reliability: sign-in observability** | The user confirmed recovery before the frontend correction. Deadlines and guidance are now tested and deployed; invalid-account POST probes cover both origins. The original connection-timeout cause remains unestablished. | Add privacy-safe latency/error observations, incident correlation and supported-device/network checks. Exercise successful sign-in/session restoration/revocation in controlled qualification. Preserve MFA and avoid replaying credentials or treating signed-out HTTP 401 as an outage. |
| **Near-term reporting: evidence currency** | The overall matrix still labels Phase 5 as the latest release and cites an earlier runtime commit, while a later login release and deployment exist. Several older reports retain historical next-phase language. | Maintain a single current release inventory linking commit, migration, deployment IDs, CI and operating qualification; label historical documents clearly. This audit pins the current HEAD and latest recorded runtime without rewriting historical evidence. |

## Coverage against the suite

The existing detailed [25-PRD / 21-specification matrix](2026-11-05-platform-progress.md) remains the scope inventory. Its categories are still **21 Partial, two Not delivered, one Infrastructure only and one Deferred/optional**; there is no defensible aggregate percentage-complete claim.

| Area | Delivered increment | Principal remaining scope |
|---|---|---|
| PRD-001–003: identity, registry, affiliation | MFA/recovery, scoped grants, reviewed hierarchy/site changes, registration, affiliation lifecycle, notices and publication | Actual roster/criteria/activation, complete delegation and departure variants, reminders, scanned evidence and operating acceptance |
| PRD-004–008: Directorate | Reporting/verification, privacy-controlled snapshots, safety review, owned actions and handovers | Queue completeness, wider mappings/extractors/template adoption, portfolio/resources, timely escalation and disclosure/UAT qualification |
| PRD-009–012: network, education, integration and continuity | Accepted clinical referral, approved content lifecycle and portal receipts, identity links and revocable native sharing | Time-bounded service readiness, community planning, remote care, patient preferences, actual counterpart exchange and both existing-EMR adoption routes |
| PRD-015–021/024: clinical care | Broad cloud EMR plus Phase 5 teamwork, structured specialty and resource controls | Complete service-specific protocols/variants, attachments, device/department interfaces, qualified calculations, operating acceptance and offline care |
| PRD-022: care finance | Tariffs, fulfilment-linked invoices, cash receipts and balanced immutable ledger | Payer splits, claims/remittance, electronic settlement, independently controlled refunds/reversals and reconciliation |
| PRD-023: patient/family | **Not delivered in the production platform** | Verified personal identity links, caregiver/dependant authority, subject isolation, own-record views, requests, plans/results, sharing, corrections and preferences |
| PRD-013: sponsored programmes | **Not delivered in the production platform** | Contracted eligibility, restricted allocations/reservations, verified funding, settlement and privacy-controlled statements |
| PRD-014: governed assistance | Infrastructure/provider readiness only | Scoped tools, approved references, draft provenance, human decisions, approved data routing and evaluated use cases |
| PRD-025: optional ERP | Separately scoped/deferred | Accounting, procurement, HR and payroll; these must not block core clinical stock, staffing or care billing |

Older/demo workspace modules are not counted as deployed capability. Current production authority is `services/api/src/lw_care_api/platform` and `apps/platform-web`; the existence of a module elsewhere in the monorepo is insufficient delivery evidence.

## Recommended sequence and exit criteria

### Immediate closure batch: carryover from 4A/4B/5

1. Fix queue and recipient completeness with scope-before-limit queries and stable pagination.
2. Qualify and narrow projection failure scope where appropriate; measure representative worklist/resource latency and concurrency.
3. Establish the current release/requirement execution inventory and privacy-safe sign-in/delivery/queue monitoring.
4. Run an observed clinical journey for each facility type against the enabled scope. Record blockers rather than infer acceptance from green CI.
5. In parallel, obtain actual operator/country/facility/staff/content adoption and confirm which attachment/escalation services can be operated within the authorised stack.

Exit: actionable records remain discoverable beyond current limits; a deliberately stale facility projection is contained according to an approved design; each enabled journey has attributable evidence and exceptions; the real activation dependencies are explicit. This is a focused readiness batch, not a claim that every historical phase must be fully closed before any Phase 6 development can begin.

### Phase 6: My LW Health Care and family authority

Build in this order:

1. **6A — Identity and authority:** verified personal enrolment/recovery, reviewed links to facility patient identities, explicit self/subject context, verified caregiver/dependant scope, expiry/revocation and confidentiality changes. A relationship label or ministry membership must not grant chart access.
2. **6B — Readable care:** Today, My health and Family views; permitted plans, medicines, appointments, released results, provenance, access history and correction requests. Define the patient-release rules before exposing clinical source records.
3. **6C — Requests and continuity:** care requests with actual receiving ownership/status, sharing/revocation, neutral notification preferences, attributed self-reports and clearly identified human/automated support. Delayed acknowledgement must remain owned; no implied clinician review.

Exit: wrong-subject, revoked-proxy and sensitive-record isolation hold across direct API, UI, downloads, drafts and notifications; switching family subjects clears prior data; an actual request has an accepted owner and truthful next step. Observe keyboard/low-bandwidth journeys. AI is not a dependency for this release.

### Phase 7: connected care and both existing-EMR routes

Complete network readiness and receiving acknowledgement/outcome, remote-care interruption recovery, and selected actual LIS/PACS/device/FHIR or explicitly mapped interfaces. Route A preserves an existing EMR and exchanges approved data. Route B provides source-preserving migration staging/quarantine, semantic reconciliation, fenced cutover and rollback that preserves new care.

Exit: a real counterpart passes wrong identity, duplicate, amended/out-of-order data and endpoint-failure cases with semantic receipts; a migration rehearsal reconciles identities, signed history, open care, medicines, stock and finance. Actual counterparts and mappings are dependencies, not placeholders.

### Phase 8: care finance and sponsored programmes

Extend the existing ledger with payer allocation, claims/adjudication/remittance, actual payment intents/callbacks/settlement, independent refunds/reversals and funded entitlements/reservations. Require real contractual and pricing inputs.

Exit: no overspending or duplicate effects under concurrent reservations/retries; timeout remains unconfirmed; fulfilment, claims, payments and ledger reconcile; approvals and actual settlement remain distinct. Clinical priority must remain independent of balance.

### Phase 9: governed assistance

Build scoped assistance over approved sources with source-linked drafts, human approval, permission-aware memory/tools, approved clinical-data routing and use-case evaluations. Retain the explicitly free-model constraint; the core service continues when AI is unavailable.

Exit: wrong-subject access and unsupported clinical instructions are rejected; drafts cannot silently become prescriptions, diagnoses, signed notes or policy; provenance and human decisions are auditable.

### Phase 10: integrated acceptance and controlled expansion

Complete the applicable formal acceptance cases with actual reviewers, representative load/recovery, security/privacy/clinical/finance review, user accessibility, staff readiness and controlled activation/exit evidence. Start this qualification work now for delivered slices; Phase 10 consolidates it rather than postponing all validation until the end.

## Offline care and deferred deployment

Offline care remains core under SPEC-017. It is different from installing its facility-local runtime. The deployed cloud implementation still requires WAN connectivity and has not delivered full local care during WAN loss.

Continue cloud-compatible work on authority epochs, signed bounded reference/identity packages, semantic receipts, conflict reconciliation, portable deployment scripts and recovery contracts. Facility-local installation and additional persistent worker/scanner hosts remain deferred under the user's current-stack constraint. Full offline acceptance still needs the actual local API/database/files/authentication/department/printing/jobs stack, fenced failover and outage/reconnect drills. Patient-approved cached information in Phase 6 is a separate, narrower capability.

## Immediate recommendation

Proceed with the focused readiness batch and **Phase 6A identity/caregiver authority** as the next implementation tranche. Continue adoption and clinical qualification alongside development, retain deferred hosting/offline dependencies explicitly, and use observed acceptance evidence to govern service activation and expansion.
