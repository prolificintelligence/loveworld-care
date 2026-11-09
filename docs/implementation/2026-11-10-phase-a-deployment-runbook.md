# Phase A reporting source accounting deployment

Scope: LWH-AUD-20261109-001 and the engineering increment for 002. Preserve the Director-first sequence and all constraints in the comprehensive audit. This runbook grants no operating authority.

## Qualification and promotion

1. Activate `scripts/env-d-drive.ps1`. Use existing dependencies; do not install Playwright. Record repository status, commit, provider deployment IDs and aggregate-only production counts before mutation.
2. Run native reporting regressions, source fingerprint/archive compatibility checks, the broader Python checks, client/PWA tests and frontend typecheck/build. Record failed checks as well as corrected results. Run `scripts/verify_phase_a_postgres.py`: it creates and removes its own isolated Neon schema, retaining no synthetic production records. Its timings are local ASGI plus real Neon I/O, not Vercel capacity acceptance.
3. Commit and push explicit intended paths, excluding `docs/New Recording 20.m4a`. Require successful CI for that exact runtime commit before deployment. The production roots remain `api/platform.py` / `services/api/src/lw_care_api/platform` and `apps/platform-web`.
4. Run `scripts/platform_cloud_release.py migrate`. Schema 9 adds `reporting_source_index` and its period/target indexes. The helper rebuilds derived clinical/source projections from encrypted existing records in bounded pages. It creates no facilities, staff, clinical events, returns or approvals. Missing/stale source projection entries block current use; do not bypass readiness.
5. Deploy API and web with `scripts/platform_cloud_release.py deploy --target api` / `--target web`. Poll the returned deployment IDs to a terminal state. Do not recreate providers or change production secret configuration. The schema-8 runtime's readiness endpoint does not support schema 9, so the migration-to-new-API interval can report unavailable readiness; do not mistake that interval for successful promotion.
6. Run `scripts/verify_reporting_cloud.py` with both new deployment IDs. Verify exact packaged source hashes, schema-9 health/readiness through both origins, signed-out boundaries, invalid sign-in rejection and frontend pages. Check the changed Directorate bundle and retained PWA assets. Recheck aggregate production counts and the recording hash. Publish exact release evidence and the next handoff separately from runtime code.

## Data-preserving recovery boundary

The additive table is a rebuildable projection; clinical events and reporting histories remain authoritative. Reconcile it with `reporting.source_index.rebuild` after source/version discrepancies. Retained snapshots remain historical and ineligible for current use when accounting is unavailable. Never restore an old database over new clinical/finance events to reverse this release.

The old schema-8 runtime is **not a qualified rollback artifact for schema 9**: its readiness and archive guards do not recognise the new version. Prefer a forward correction on schema 9, preserving all new events and receipts. Any reverse promotion needs a separately qualified compatibility build and a data-preserving rehearsal; do not drop history, remove schema markers or reset the database as an improvised rollback. Exact-artifact staging/promotion and rollback qualification remain ticket 019 acceptance work.

## Acceptance boundaries

- 001: engineering closure requires retained view/list/CSV figures, unavailable/stale current-use status, blocked uncheckable new releases, and active disclosure/scope/integrity enforcement.
- 002: period/dependency/event accounting and extraction lock scoping are an engineering increment. Metadata completeness checks still inspect facility-wide index coverage. Representative Vercel memory/duration, larger event histories, sustained contention/load and adopted latency targets remain open; raising caps is not acceptance.
- Actual independent officers, facility affiliation, adopted forms/calendar/disclosure, leadership review and accepted intervention/outcome evidence are operating inputs. Synthetic qualification is not Director adoption.
- Scanner, backup/custody, canonical conformance, staging/rollback, independent security, real device/accessibility and the 200 requirements /111 specified cases retain their separate gates. Offline clinical care remains core and its facility-local deployment remains deferred.
