# Directorate reporting release - 7 November 2026

Status: verification in progress. This record will be updated with exact source, CI and live deployment evidence after release.

The authorised increment covers versioned reporting obligations and returns, controlled imports, actual EMR contact extraction, independent quality review, disclosure-controlled leadership snapshots, protected safety review and accountable actions. It extends the existing institutional service and cloud EMR. Offline installation remains deferred. No Playwright or browser software was installed.

Implementation and migration decisions are in [ADR-0009](../adr/0009-directorate-reporting-disclosure-and-review.md). The [overall progress report](2026-11-05-platform-progress.md) maps the delivered runtime and remaining work to all 25 PRDs and 21 specifications. This increment does not establish complete platform or clinical acceptance.

## Executed checks before publication

- Existing backend regression: 92 passed, one upstream Starlette/httpx deprecation warning.
- New reporting integration checks: 24 passed, one upstream Starlette/httpx deprecation warning; 116 local tests passed across the existing and new suites.
- Real Neon disposable-schema proof: same-key concurrent definition/draft writes produce one effect; competing independent reviews produce one review; release/correction is serial and invalidates earlier evidence; direct protected history mutation is rejected; revoked cached receipt is denied; records persist across an application restart. Generated namespace removed, zero production fixtures.
- TypeScript and production frontend build passed; /directorate and /care were generated.
- Exact isolated Vercel API artifact imports and verifies real Neon readiness plus unauthenticated denial. Nested metric catalogue included; legacy seeded runtime excluded.
- Original controlled suite: 78 SHA-256 hashes verified; 200 requirements and 111 specified acceptance cases retained.

## Operating dependencies

The deployed installation contains no fabricated metric adoption, disclosure policy, reporting return, safety category, duty acceptance, case or action. Authorised officers must adopt actual definitions/templates, period obligations, disclosure rules and risk assessment, category/receipt rules and accepted coverage, and nominate current scoped staff. Existing Directorate administration alone does not open private reporting/case/clinical access.

Disclosure rules cover primary, complementary and overlapping/difference suppression for supported fixed cohorts. They do not certify universal anonymity or causal conclusions. Only the adopted completed-encounter extractor is automatic; other sources remain governed manual declarations. Daily exception reconciliation records owned overdue work and separate acknowledgements; it does not perform emergency dispatch, agency filing or external notification.

Browser/accessibility interaction checks, actual institutional UAT, independent privacy/security assessment, load and backup/restore qualification remain unexecuted. The suite's acceptance specifications remain separate from executed engineering tests.

## Contract extension

Native reporting commands are under /v1/reporting. They use authenticated purpose/scope, strict typed contracts, Idempotency-Key, expected versions, correlation identifiers and retained encrypted receipts. Versioned evidence follows LWH-EVT-007/008/009/010/011/012/013 where applicable; implementation-only events use LWH-EXT-REPORTING-001. These native contracts do not rename archived suite routes or IDs.

Migration 3 is additive. The API supports schema 2 during rollout and gates reporting until 3. Rollback pauses reporting with LWH_REPORTING_ENABLED=false and retains the schema-3-compatible API and evidence. Existing keys, accounts, other schemas and signed clinical history are preserved.
