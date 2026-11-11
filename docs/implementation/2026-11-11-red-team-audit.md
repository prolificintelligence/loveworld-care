# Red-team engineering audit and production-readiness roadmap — 11 November 2026

Audited repository HEAD `addd1ad917536f740445be3b40bad06846d337d3`; live runtime `6de5ddb87b5428df371e6159cd1264afa7a52e24`. This audit reconciles the [10 November comprehensive audit](2026-11-10-comprehensive-audit-and-production-readiness.md) with subsequent delivered work. It changes documentation only. The [current release inventory](current-release.json) remains authoritative and unchanged. [Sanitised evidence](2026-11-11-red-team-evidence.json), [15 ranked findings](2026-11-11-red-team-findings.csv), [25-PRD assessment](2026-11-11-red-team-capability-assessment.csv), [roadmap](2026-11-11-red-team-roadmap.csv) and [copy-ready handoff](2026-11-11-red-team-new-session-prompt.md).

## Verdict

**Continue engineering; the platform is not ready for unrestricted clinical operation or complete product acceptance.** A scoped Director-first pilot remains a future actual-owner decision after its applicable gates close. This audit grants no operating approval. The most significant immediate technical finding is a locally reproduced application login-budget gap; the largest overall readiness gap remains the absence of a real operating institution and executed acceptance.

| Dimension | Current state | What the evidence permits |
|---|---|---|
| Code delivery | **Deployed; substantial; core scope partial** | Persistent institutional and cloud-care workflows exist on the current Vercel/Neon stack. Scope completion does not follow from deployment. |
| Engineering evidence | **Bounded successes; new availability concern confirmed** | Exact-runtime CI, fresh source/HTTP checks, selected negative tests and retained isolated Neon/capacity/recovery proofs. Their populations and limits remain explicit. |
| Operating adoption | **Incomplete** | One account, no actual facility or observed Director loop, no populated activation or clinical coverage packages. |
| Full-suite acceptance | **Incomplete: 200 requirements /111 cases NOT_RUN** | No engineering test total, route count or synthetic approval changes formal acceptance. |

There is no defensible single percentage-complete figure. The 25-PRD assessment remains **22 Partial /1 Not delivered (sponsorship) /1 Infrastructure only (governed assistance) /1 Optional/deferred (ERP)**. The full-offline clinical requirement remains core even though local/additional hosting is deferred.

## Fresh observations and test boundaries

Aggregate observation began `2026-11-11T18:54:08.158333+00:00`; additional provider/role/service metadata began `2026-11-11T18:56:33.087464+00:00`. No patient, chart, staff contact, payment contents or decrypted environment values were read.

| Observed item | Result |
|---|---|
| API | `dpl_BRBXrzAxXVboSZS3dRNLk1iSmHkJ`, READY, current source metadata matches runtime |
| Web | `dpl_FVisAWdnT2SemRxRvRpSQw8raKGU`, READY, current source metadata matches runtime |
| Neon | **Schema 9 /102 base tables /53 protected histories**; no audit migration |
| Institutional identity | **One account** with one PLATFORM_ADMIN and one REGISTRY_STEWARD grant; these are not two independent people |
| Operating population | Zero observed units/operators/facilities/criteria/applications/evidence/inspections/decisions; zero clinical sites/records/events and reporting definitions/obligations/returns/snapshots; zero institutional case/finding/response/decision/journal records |
| Activation and staffing | Zero policy packages, site packages and clinical coverage rows |
| Assurance and cleanup | 22 assurance records; no retained `lwh_link_verify_...` schemas |
| Scanner/protection | No production scanner-host environment entry; SSO unchanged; zero temporary probe tokens on both projects |

Fresh checks passed: **72 API /33 web-public source hashes**, both origins' health/readiness and signed-out boundaries/invalid login checks, **all 12 pages**, canonical register integrity and all **78 controlled-document hashes**, native mapping and recording preservation. Current runtime [CI 43018352401](https://github.com/prolificintelligence/loveworld-care/actions/runs/43018352401) was rechecked successful: **289 Python /11 client /4 PWA**, plus build/typecheck/secret/register checks. Its six PostgreSQL-only skips remain disclosed in release evidence; this audit did not rerun the full suite or those Neon races.

Fresh local checks: **7 passed /1 existing deprecation warning**. Six guard regressions covered failed-login accounting/redaction, notice response windows, institutional current authority before replay, expiry without silent extension, reporting scope/revocation replay and representative personal authority/revocation. The seventh is the new audit reproduction: its passing result confirms a gap, not a successful mitigation. No packages were installed to silence the TestClient/httpx warning.

The latest release retains two pinned isolated Neon scenarios, six nonempty history DELETE refusals, unchanged 21 production aggregates and cleanup. The interrupted first proof remains explicitly retained as INTERRUPTED_NO_PASS. Earlier actual-Vercel capacity and Neon/R2 recovery evidence remains historical execution. None is relabelled as a fresh audit drill or human acceptance.

This is an adversarial engineering review of selected source, traceability and release evidence across the full product scope. It is not external independent penetration testing, a current vulnerability/licence certification of every dependency, a new clause-by-clause certification of the 78-document suite or a safety/privacy/legal approval. Locked dependency versions and frozen CI inputs were inspected; no unsupported CVE claim is made.

## Milestones achieved

| Delivered increment | Current engineering value | Remaining qualification |
|---|---|---|
| Cloud foundation and native LW Care | Persistent MFA/current scoped authority; registry/standards; encrypted chart/encounter/diagnostic/medicine/ward and cash-ledger foundations | Actual operation, specialist/exception scope, independent clinical/finance qualification |
| Director reporting/intelligence/intervention | Versioned obligations/returns and forms, manual/CSV/native capture, independent verification, permitted snapshots and accepted accountable actions | Actual adopted forms/calendar/disclosure and witnessed return-to-reviewed-outcome loop |
| Operating controls and recovery | Reviewed activation contracts, MFA recovery, accepted handovers, durable jobs, encrypted archives, isolated restoration/reconciliation | Staffed coverage, monitored cadence, independent copy/key custody, adopted RPO/RTO and supported resumption |
| Institutional lifecycle and publication | Reviewed hierarchy/site changes, renewal/noncompliance/appeal increments, notice acknowledgement/delivery evidence and retained publication | Actual policy adoption and complete canonical notice/service/appeal/expiry/exception semantics |
| Personal/family and PWA | Verified subject/representative authority, independently reviewed releases, accountable human requests and same-origin installable patient access | Full remote/referral continuity, device/accessibility/low-bandwidth UAT; full offline clinical runtime remains undelivered |
| Phase A reporting integrity | Ticket 001 historical snapshot/list/export defect fixed; period/source index and narrower extraction locks for 002; schema 9 | Sustained representative correction/contention/provider qualification and adopted targets remain open |
| Release controls and crosswalk | Exact-CI/source/same-build API-first promotion, expected-parent checks, revoked probe access; complete canonical inventory and CI drift checks | Full sandbox, dependency/licence review and paired newer-data-preserving rollback; complete semantic acceptance |
| Latest Director-first safeguards | Initial SCREENING/evidence review, retained correction/withdrawal, accepted teams, exact corrective plans, bounded tagged capture and initial negative-criterion source links/retractions | Broader Director-first capture and state contracts, actual roster/policy adoption and formal tests |

The latest source association retains an actual original negative inspection observation against an existing finding. It supplies context and creates no finding, current proof, plan completion, response, resolution or recognition. Original authorship and retraction history remain retained. This is a bounded implemented extension, not complete canonical finding conversion.

## Ranked red-team findings

Severity below distinguishes **technical risk** from a **critical operating/acceptance gate**. A critical readiness gate is not a newly demonstrated remote exploit. All 15 findings have evidence classes, owner-role requirements and concrete exit evidence in the [findings register](2026-11-11-red-team-findings.csv).

### RT-001 — High: rotating login identities evade any shared application work budget

The reviewed [login limiter](../../services/api/src/lw_care_api/platform/main.py#L422) hashes the supplied key; [login](../../services/api/src/lw_care_api/platform/main.py#L502) supplies only the normalised email. [Password verification](../../services/api/src/lw_care_api/platform/main.py#L519) still runs for unknown accounts using the expensive constant-work fallback. A fixed identity receives eight attempts per window; changing identity starts another budget and inserts another persistent limiter row. No client/global admission budget appears in this reviewed path. No limiter pruning was found in the reviewed application sources.

Local reproduction from the same TestClient: **eight 401 responses, then 429; two new emails then returned 401/401**, leaving **three limiter rows and zero accounts**. The reproduction source and receipt are embedded in the evidence so another session can reconstruct it. It made **zero production requests**. Authentication/MFA was not bypassed, availability degradation was not measured and provider WAF/edge protection was not verified. The confirmed conclusion is narrower: the application does not itself bound aggregate verification work or key growth across rotating identities.

**Next engineering priority:** trusted-client plus aggregate admission control, bounded key retention/growth and explicit saturation behavior, preserving account budgets/MFA/redaction. Qualify proxy identity rather than trusting an arbitrary forwarded header; test identity rotation, spoofing, concurrent requests, state growth and provider/control-store failures within the existing stack. Associate this work with tickets **010/002/019**. This audit reports the issue and does not deploy a fix.

### RT-002/003 — Critical readiness gates: no actual operating loop; no formal acceptance

Fresh aggregates show the implementation has not yet demonstrated the required real loop: **registered facility → affiliation → return → independent verification → permitted leadership release → accepted intervention/outcome review**. Real appointments, deputies, approved facilities/criteria, Director forms/calendar/disclosure, activation authority and funded support remain actual-owner inputs. One administrator holding two roles cannot demonstrate independence. All **200 requirements /111 specified cases remain NOT_RUN**. These gates require attributable real decisions and witnessed case results, not more synthetic approvals.

### RT-004/005/006 — High service/response risks and a critical recovery gate

Files remain excluded: the mandatory [scanner guard](../../services/api/src/lw_care_api/platform/storage.py#L49) is fail closed and no production scanner-host entry was observed. Required evidence cannot be waived because scanning is unavailable. A configuration entry or synthetic CLEAN metadata would still not qualify an engine.

Retained nonempty recovery/newer-data-preservation engineering is valuable, but no monitored backup cadence, independent copy/key custody, adopted RPO/RTO or representative staffed resumption is established. The prior operator production rehearsal had no clinical file population. **22 assurance records are not 22 successful operating drills.** Likewise, the [daily cron](../../vercel.platform.json) and worker CLI do not establish minute-level clinical response; no clinical coverage records were observed. Keep critical-result/urgent-response claims excluded until actual supported service commitments and human fallback are qualified.

### RT-007/008 — High: canonical scope and full offline care remain incomplete

Fresh conformance covers **51 forms /355 fields /75 screens /30 state families /82 interfaces**, with **315 actual API routes /71 indexed models**. Field results remain **21 partial proofs /298 explicit gaps /36 candidates**, all 75 screen qualifications open and 2 partial/28 open state families. A partial field proof or page link is not field/screen acceptance. Initial SCREENING, accepted team/plan gates, capture and source links have been delivered; do not call them missing or rebuild them without a new concern. Notice/service/appeal/expiry and broader Director-first semantics still need specific reconciliation against the existing implementation.

The [PWA worker](../../apps/platform-web/public/my-health-sw.js) provides connection guidance and caches no charts/drafts. It does not provide full local clinical API/DB/files/auth, department jobs, semantic sync or staffed outage resumption. **Offline care remains core while additional/local hosting is deferred.** Full readiness cannot close under that unresolved constraint. A later actual scope/hosting decision is needed; this audit adds no host and silently removes no requirement.

### RT-009/010 — High: receiving continuity and financial core remain incomplete

The [referral transition](../../services/api/src/lw_care_api/platform/clinical/service.py#L1780) permits CLOSE after TRANSFERRED without a separate receiving-outcome contract. Named acceptance and actual handover are present; full receiving receipt/outcome and decline/unreachable responsibility remain open under **011**. This is a source-confirmed existing backlog gap, not a newly proven harmful clinical event.

Cash billing and an immutable balanced ledger do not complete payer claims/remittance, electronic settlement, controlled independent refunds or contracted sponsorship entitlement/reservation/reconciliation. Sponsorship remains **not delivered** under PRD-013; core finance/sponsorship is distinct from optional ERP. Complete these flows under actual financial/service contracts before making full-scope claims.

### RT-011/012/013/015 — High: independent review, sustained capacity, release resumption and human UAT

Selected access/current-authority/replay tests passed; that does not complete independent security/privacy, keys/rights/retention/custody/exit or incident-operation review. Accountable owner decisions and independent assessments remain open. This session's new availability finding illustrates why passing implementation tests cannot substitute for adversarial review.

Earlier actual-cloud evidence measured explicit **5,000 selected records /20,000 signed events** and truthful overflow refusal. It did not qualify simultaneous maximum-volume facilities or sustained corrections/contention. Local pooled ASGI/Neon proof is not Vercel duration/memory/cold-start evidence. Global low-volume governance locks and per-request master reconciliation still require representative contention evaluation. No performance target is invented here.

Exact-source staged promotion and revoked probe access reduce release risk. They do not establish a completely isolated provider/service sandbox, least-privilege proof role, dependency/licence/legacy-surface disposition or a qualified schema-9-compatible rollback preserving concurrent newer care/finance/source history. Expected-parent checks are not provider-side atomic compare-and-swap against another privileged operator. Six PostgreSQL-only tests are skipped in normal SQLite CI; latest release Neon evidence covers two selected scenarios, not a new full rerun of every older race. Repeatable PostgreSQL release gates should close that evidence gap safely.

All 12 pages responding and client/PWA tests passing do not establish keyboard/screen-reader/device/low-bandwidth usability, safe subject switching or interrupted-action behavior with actual operators. Execute and retain manual UAT; **do not install Playwright**.

### RT-014 — Medium: provider readiness is not governed assistance or counterpart integration

Free OpenRouter readiness uses fixed public text; it is infrastructure, not an adopted assistant with governed sources/tools/memory/data routing or injection/AI-off evaluation. Actual LIS/PACS/analyser, exchange, settlement and migration counterparts follow selected-facility registration/approval and documented decisions. Native LW Care needs no second EMR. Preserve that sequence and the separation of optional ERP from core care finance/stock/sponsorship.

## Roadmap and production entry criteria

| Phase | Work | Required exit evidence |
|---|---|---|
| **R0 — next engineering increment** | Fix the reproduced login admission/state-growth gap; preserve MFA, current authority and file exclusion | Trusted client/global budgets and safe saturation under rotation/spoofing/concurrency; exact CI, isolated Neon, same-build existing-stack release evidence |
| **R1 — Director-first conformance** | Reconcile bounded notice/service/appeal/expiry and broader capture gaps against existing code | Explicit field/state/permission/persistence/negative-case proof; actual policy inputs where needed; no repeated rebuilding of delivered slices |
| **R2 — reliability/security/release** | Sustained representative capacity; monitored recovery/custody/resumption; independent review; PG release gates; sandbox/dependency/licence/paired rollback | Actual adopted targets and attributable custody/support; provider measurements, new-data preservation and witnessed supported resumption |
| **R3 — actual Director pilot gate** | Real officers/deputies/facility/criteria/forms/calendar/disclosure/service authority and funded ownership; witnessed Director loop | Applicable R0–R2 gates closed, legitimate required evidence, actual-role/manual device UAT and actual scoped operating decision; no approval inferred |
| **R4 — remaining core and selected counterparts** | Receiving outcomes, payer/sponsorship, clinical/personal/remote exceptions and governed assistance; selected interfaces after facility approval | Complete responsibility/exception/reconciliation paths and applicable independent clinical/finance/privacy acceptance |
| **R5 — full offline and complete acceptance** | Resolve core-offline hosting/runtime deferral and execute the complete applicable suite | Outage/sync/fencing/auth/printing/resumption qualification, requirement/case/result traceability and actual acceptance decisions |

These phases use **evidence gates, not invented dates or staff assignments**. Actual institutional preparation should run alongside engineering; R2 reliability work can run with R1. There is no authorised clinical/pilot launch date. Keep tickets **002/003/004/007/009/010/013/017/019/020** and the other unfulfilled scope tickets open for their stated evidence. **001's engineering defect is fixed** and should reopen only on a new regression. The current 20-ticket overlay remains [the release backlog](2026-11-11-initial-source-readiness-backlog.csv); the audit findings supplement it rather than replacing or renumbering it.

## Session recommendation

**Finish the audit here; begin the next implementation increment in a fresh session using the handoff.** This is a workflow recommendation, not a technical requirement or a claim that this session cannot continue. The next task should be narrow and adversarially tested, and this conversation already carries many release cycles. The repository and pinned evidence provide a cleaner source of truth for new implementation than accumulated conversation context.

Start the new session with **RT-001 under 010/002/019**, then return to bounded **014** notice/service/appeal/expiry/capture work. Revalidate actual source/edge behavior before choosing the mitigation; do not assume an arbitrary proxy header is trustworthy. Do not rebuild delivered screening/team/plan/capture/source features or begin unrelated broad feature batches. The [copy-ready prompt](2026-11-11-red-team-new-session-prompt.md) contains the exact starting evidence, constraints and release procedure.

## Preservation and audit limits

No runtime was changed, redeployed or migrated; no backup, invitation, authenticated production business fixture, notification/jobs dispatch or synthetic production approval was created. No Playwright, dependency, deferred host or provider recreation was added. Technical denial/rate/session metadata can grow during signed-out checks; business-count comparisons are aggregate observations rather than full database equality. All 78 original controlled hashes/native mapping and recording `4fd2bbb9fedb1b6ab890f6b79488ba53f4bd266acab2a980a7f7f5dfc9aac5bf` were preserved. Original documents and formal statuses were not rewritten. The recording remains untracked/unstaged.
