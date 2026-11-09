# Readiness closure release

Date: 9 November 2026. Deployed runtime: `f525920ea1888394e2e2c5a2e1c01c208551c375`.

Release status: **deployed and technically verified** on the existing cloud stack. Operational/clinical acceptance remains incomplete. The [current release inventory](current-release.json) pins runtime, CI, deployments and observations.

## Delivered change

This is the first implementation batch from the [9 November audit](2026-11-09-implementation-audit-and-next-phases.md), addressing discovery and availability before larger enrolment. It does not implement Phase 6 patient/family access or close operational acceptance of Phases 4A/4B/5.

- Safety-case and protected-action authority is applied before SQL limits. Quality, exceptions, safety cases, actions and retained return history now expose stable continuation with an ID tie-breaker. Current permissions are checked on every page. Invalid, oversized, wrong-type and database-incompatible cursors return a controlled validation error.
- Reporting recipients use actual overlapping assignments across Region, Zone and Facility scopes without depending on a capped scope-picker response. Eligible accounts are paged before their grants are grouped. Staff selectors support scoped name search, continuation and deduplicated privileges. Clinical commands still independently validate the selected recipient's authority.
- The Directorate and care workspaces expose search and continuation controls. Search changes invalidate the previous continuation; session/context changes discard late responses. Selecting a different return clears the prior history.
- Clinical worklist, resource and advanced-workflow readiness checks isolate failures to the source facility and any facility incorrectly claimed by its projection. Unrelated facilities remain accessible. Global readiness still detects inconsistencies. Source versions, privileges, treating relationships and immutable clinical history remain enforced.
- Fixed authentication routes emit status, elapsed time and generated correlation identifiers. Account identifiers, IP addresses, query strings, request/response bodies, credentials and exception details are excluded. No monitoring SLA or cause of the previous login outage is inferred.

Design and tradeoffs: [ADR-0014](../adr/0014-scoped-discovery-and-clinical-projection-readiness.md).

## Executed evidence

Local qualification passed the existing **36 reporting/Phase 5 tests**, **six new readiness regressions**, TypeScript checking and **eight client tests**. The final hardened-cursor revision passed [full CI](https://github.com/prolificintelligence/loveworld-care/actions/runs/42568511736): **188 Python tests, eight client tests, type checking, production builds and the secrets scan**. New tests cover:

1. More than 400 mixed-authority safety cases/actions, tied sort values, full traversal, malformed cursors and revocation between pages.
2. 1,200 recipient grant rows across 240 accounts, deduplication, discovery beyond the old cap, unrelated-scope exclusion and literal wildcard search.
3. Two activated synthetic clinical facilities, stale/misassigned projections, continued access to the unaffected facility and recovery from source.
4. 220 staff accounts with duplicate privilege rows, stable traversal and targeted search.
5. Authentication observation fields and exclusion of submitted query-string secrets.
6. 206 quality records, 205 exceptions and 206 retained source versions with complete continuation.

The Neon verifier uses a uniquely named disposable schema, not live clinical tables. It exercises 450 mixed-authority cases (230 eligible), 1,100 recipient grant rows and 2,500 clinical source/projection records. Its single readiness timing includes this environment's connection/network cost; it is neither a service-level target nor representative mixed-workload certification. Cleanup is verified in the recorded result.

All **78 controlled document hashes** still match the original manifest. The 200 canonical requirement records and 111 authored acceptance specifications are unchanged. Engineering results do not turn authored `NOT_RUN` cases into observed clinical acceptance.

The final Neon run passed against runtime `f525920ea1888394e2e2c5a2e1c01c208551c375`: 230/230 eligible cases traversed exactly once, late recipient discovery passed, and stale projection isolation retained global failure reporting. The observed 2,500-record facility check took **1243.01 ms** including this connection/network path. All disposable schemas were removed; no production care records were seeded.

Live verification found **54 API and 19 frontend source hashes matching**. Both origins returned readiness 200/schema 7 and enforced authentication/no-store on protected routes. Actual `/care` and `/directorate` built JavaScript bundles contain the new controls. Reserved-invalid-account login POSTs returned 401 in 2.869 seconds directly and 2.847 seconds through the frontend proxy, without creating sessions. This is a connectivity/denial check, not successful-user UAT. Nine public/authentication workspace pages returned HTTP 200.

Production aggregate metadata still shows zero facilities, criteria, clinical sites, clinical records, stock lots, ledger entries, operating packages and safety cases. Actual onboarding and operating adoption are therefore still required. The [execution register](2026-11-09-readiness-execution-register.csv) separates synthetic engineering evidence from remaining observed acceptance.

## Deployment and rollback

API deployment: `dpl_HocsoRxoLyFMFE8rC3a2QLb6WhW1`. Frontend deployment: `dpl_YQcx1AUGPe4AEnyLBmUfH2gm7SAk`. Both are READY and verified at their production origins.

This is a code-only release on the existing Vercel/Neon stack. No migration, destructive data change, credential rotation, email campaign or new hosting is required. Schema 7, existing encryption keys and all signed/history records are preserved.

The previous API and frontend deployment IDs are `dpl_CGBAJc4hxkKWYUgvfq2G5Cz4r9dU` and `dpl_7dFRAaYWcxdtmoBPGtKPWAyMmH3h`. If this release needs rollback, restore their respective production aliases; do not roll back the database or delete retained events. Restoring those binaries also restores their known discovery/global-readiness limitations. No rollback rehearsal is claimed for this release.

## Remaining scope and next sequence

The technical readiness defects above are addressed; the whole readiness phase remains partial. Actual jurisdiction/operator/facility adoption, independently verified staffing, clinical activation and observed clinician/device/accessibility journeys remain outstanding. Daily/manual scheduling does not qualify urgent response windows. Attachment scanning and extra persistent hosting retain their previously recorded dependencies. Full representative-load targets, independent recovery custody/cadence and operating qualification remain open.

Next capability: **Phase 6A verified personal identity and caregiver authority**, followed by **6B readable released care views** and **6C owned requests, sharing and preferences**. A patient/family account must not receive chart access from ministry membership, an administrative appointment or an unverified relationship label. Phases 7 integrations, 8 finance/sponsorship, 9 governed AI and 10 consolidated acceptance retain the audit sequence, with acceptance evidence accumulated throughout.

Offline care remains core. Facility-local installation and additional worker/scanner deployment remain deferred under the current-cloud-stack constraint; this release does not claim WAN-offline clinical operation.
