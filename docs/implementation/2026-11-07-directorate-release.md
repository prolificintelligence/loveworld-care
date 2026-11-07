# Directorate reporting release - 7 November 2026

Status: **DEPLOYED AND VERIFIED** for this Directorate increment. Full platform acceptance remains outstanding.

## Exact release evidence

| Evidence | Actual result |
|---|---|
| Directorate workspace | [Live Directorate](https://lw-health-intelligence.vercel.app/directorate) |
| Existing EMR | [Live Care workspace](https://lw-health-intelligence.vercel.app/care), retained |
| API readiness | [Live API](https://lw-health-intelligence-api.vercel.app/v1/ready): schema 3, reporting READY |
| Source | [Runtime commit 173d60ad](https://github.com/prolificintelligence/loveworld-care/commit/173d60adce9eda255fb8dbef1c35fde14f3a59ff) |
| Exact CI | [Run 42421116592](https://github.com/prolificintelligence/loveworld-care/actions/runs/42421116592): Python, web and secrets scan successful |
| Executed CI tests | **116 passed**, one upstream deprecation warning, 35.72 seconds; Python job 128549537398 |
| API deployment | dpl_Hepau3i4VbiKTR9WLcUUnBw2LbCg, READY |
| Frontend deployment | dpl_3ozH2sGGEXPvRTM5dRCvHFWZPtzB, READY |
| Deployed file evidence | SHA-1 matched the tested local source for **29 API files** (including nested metric catalogue) and **13 frontend files** |
| Migration | Compatible API deployed and verified healthy on schema 2 with reporting gated 503; additive migration 3 applied; frontend then deployed |
| Reporting PostgreSQL proof | One duplicate effect; one winner in review race; serial release/correction with invalidation; protected history rejects mutation; revoked cached receipt denied; restart persistence passed |
| Clinical PostgreSQL regression after migration 3 | Same-key note replay, exclusive bed race, stock issue race and direct signed-note/history mutation protections all passed; zero production fixtures |
| Production protections | 28 history tables have immutable UPDATE/DELETE triggers; signed clinical record trigger covers both UPDATE and DELETE |
| Institutional PostgreSQL regression | Schema 3; duplicate/replay conflict and immutable history checks passed in disposable namespace |
| Original suite | All 78 manifest SHA-256 hashes retained; 200 requirements and 111 specified acceptance cases unchanged |

The public API and frontend's same-origin proxy both returned 200 for /v1/health and /v1/ready, with Cache-Control: no-store. Unauthenticated /v1/auth/me, /v1/clinical/sites, /v1/reporting/context, /v1/reporting/safety-cases and /v1/reporting/snapshots returned 401 with no-store. Frontend /, /care, /directorate, /activate and /directory returned 200 with the expected platform title. `scripts/verify_reporting_cloud.py` records these assertions and verifies actual uploaded source-file UIDs.

The live-site checks cover deployment, readiness and access boundaries; the 24 new integration checks ran against persisted local databases and the concurrency/restart proof ran against actual Neon in a generated namespace. No synthetic identities or clinical/reporting transactions were inserted into the production namespace for live UI testing.

The authorised increment covers versioned reporting obligations and returns, controlled imports, actual EMR contact extraction, independent quality review, disclosure-controlled leadership snapshots, protected safety review and accountable actions. It extends the existing institutional service and cloud EMR. Offline installation remains deferred. No Playwright or browser software was installed.

Implementation and migration decisions are in [ADR-0009](../adr/0009-directorate-reporting-disclosure-and-review.md). The [overall progress report](2026-11-05-platform-progress.md) maps the delivered runtime and remaining work to all 25 PRDs and 21 specifications. This increment does not establish complete platform or clinical acceptance.

## Executed checks before publication

- Existing backend regression: 92 passed, one upstream Starlette/httpx deprecation warning.
- New reporting integration checks: 24 passed, one upstream Starlette/httpx deprecation warning; 116 local tests passed across the existing and new suites.
- Real Neon disposable-schema proof: same-key concurrent definition/draft writes produce one effect; competing independent reviews produce one review; release/correction is serial and invalidates earlier evidence; direct protected history mutation is rejected; revoked cached receipt is denied; records persist across an application restart. Generated namespace removed, zero production fixtures.
- TypeScript and production frontend build passed; /directorate and /care were generated.
- Exact isolated Vercel API artifact imports and verifies real Neon readiness plus unauthenticated denial. Nested metric catalogue included; legacy seeded runtime excluded.
- Original controlled suite: 78 SHA-256 hashes verified; 200 requirements and 111 specified acceptance cases retained.

At 2026-11-07T22:40:39Z, production definitions, obligations, returns, disclosure policies, cohorts, snapshots, event categories, duty windows, safety cases and actions all had zero rows. Clinical sites, privileges, records/events, beds, lots/movements and ledger entries were also zero at post-migration inspection. These are actual unconfigured/empty stores, not zero clinical incidence. Production access-denial audits record the live checks. Test namespaces were removed after their isolated proofs; the production namespace and existing identity/provider data were preserved.

## Operating dependencies

The deployed installation contains no fabricated metric adoption, disclosure policy, reporting return, safety category, duty acceptance, case or action. Authorised officers must adopt actual definitions/templates, period obligations, disclosure rules and risk assessment, category/receipt rules and accepted coverage, and nominate current scoped staff. Existing Directorate administration alone does not open private reporting/case/clinical access.

Disclosure rules cover primary, complementary and overlapping/difference suppression for supported fixed cohorts. They do not certify universal anonymity or causal conclusions. Only the adopted completed-encounter extractor is automatic; other sources remain governed manual declarations. Daily exception reconciliation records owned overdue work and separate acknowledgements; it does not perform emergency dispatch, agency filing or external notification.

Browser/accessibility interaction checks, actual institutional UAT, independent privacy/security assessment, load and backup/restore qualification remain unexecuted. The suite's acceptance specifications remain separate from executed engineering tests.

## Contract extension

Native reporting commands are under /v1/reporting. They use authenticated purpose/scope, strict typed contracts, Idempotency-Key, expected versions, correlation identifiers and retained encrypted receipts. Versioned evidence follows LWH-EVT-007/008/009/010/011/012/013 where applicable; implementation-only events use LWH-EXT-REPORTING-001. These native contracts do not rename archived suite routes or IDs.

Migration 3 is additive. The API supports schema 2 during rollout and gates reporting until 3. Rollback pauses reporting with LWH_REPORTING_ENABLED=false and retains the schema-3-compatible API and evidence. Existing keys, accounts, other schemas and signed clinical history are preserved.
