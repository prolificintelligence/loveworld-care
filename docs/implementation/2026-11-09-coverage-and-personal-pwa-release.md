# Directorate reporting coverage and personal PWA release

Date: 9 November 2026. Status: **deployed and technically verified** for this increment. Institutional, clinical and device acceptance remain incomplete.

## Current user interaction

The user selected an installable patient experience on the current deployment. [My LW Health Care](https://lw-health-intelligence.vercel.app/my-health) now has its own manifest, care icon, name, standalone launch and browser installation guidance. It remains part of the same cloud frontend and uses the existing API and account service. This is separate app presentation and server-enforced personal permissions, not a separate web origin or separate clinical database. Staff still uses `/care` and `/patient-access`; the Directorate uses `/directorate`.

Patients verify their account and self/caregiver permission, select the subject, read recipient-specific reviewed care and send requests to a personally accepted receiving team. Staff accepts and responds, and records clinical work in the native EMR. Remote interaction currently means asynchronous human messages. Clinical staff handles referrals and actual receiving acceptance in the EMR; arrangements can be communicated through human responses or reviewed summaries. A dedicated patient referral tracker and live video/audio consultation remain separate work. See the [interaction guide](personal-family-care-interaction-guide.md).

The service worker is restricted to personal navigations. It ignores API/staff/cross-origin/non-GET requests, stores no charts or drafts in Cache Storage and queues no submissions. A lost navigation displays public connection guidance with no-store. Protected care and submissions require connectivity. This is distinct from full facility WAN-offline care and its deferred local installation. Installation is offered through actual browser events or platform controls; it is not reported complete merely because the prompt was accepted. [ADR-0016](../adr/0016-personal-pwa-on-shared-cloud-and-reporting-coverage.md) records the boundaries and source references.

## Directorate priority delivered

The Overview in [Directorate reporting](https://lw-health-intelligence.vercel.app/directorate) now obtains authoritative SQL totals across **all current permitted configured obligations**, independent of UI page limits. It distinguishes missing, draft, submitted, returned for correction, verified, current receipt, late receipt and overdue submission. The officer can select the exact frozen period or explicitly view all configured periods. Empty denominators are **not established**, rather than 100% or zero clinical incidence.

Current source-reporting/programme authority is checked before aggregation. Overlapping grants do not duplicate obligations; revoked/out-of-scope users cannot acquire counts. Executive-only and administrator-only accounts cannot use this source operational route. No patient identifiers, source narratives or clinical metric values are returned. Released leadership clinical intelligence still uses the existing independent verification, disclosure and snapshot process. Counts describe unit-period obligations, not distinct facilities, disease burden or complete institutional adoption.

## Executed qualification

- [CI](https://github.com/prolificintelligence/loveworld-care/actions/runs/42659587015) on `b54b05400616b0700c4a0754642de4282af3396b` passed **200 Python tests, eight API-client tests and four PWA tests**, type checking, production builds and secret scanning. These test totals do not mean the 200 canonical requirements have been formally accepted.
- Three new coverage integration tests exercise more than 200 obligations, current receipt versus returned correction/draft states, exact periods, overlapping grants, missing denominators, current scope/revocation and denied leadership/admin access.
- Actual Neon SQL qualification used 420 synthetic obligations in a disposable schema: 210 within one facility scope, 420 with a global grant, no duplicated rows from overlapping assignments, correct status/deadline totals and an unestablished empty denominator. No production reporting records were seeded; cleanup completed.
- Four Node worker/manifest tests check real PNG sizes, offline network-failure handling, exclusion of API/staff/cross-origin/POST requests and unchanged online responses. The worker runs in a controlled test context; these tests are not an observed browser/device installation.
- Live source hashes matched **61 API files and 29 frontend/public files**. Actual compiled bundles contain installation/registration and reporting-coverage controls. The manifest, worker and three PNG icons returned HTTP 200 with matching byte hashes; the worker exposes `Service-Worker-Allowed: /my-health` and `Cache-Control: no-store`. The manifest MIME type is `application/manifest+json` and its name/scope/start URL match the intended app.
- Both origins returned readiness 200/schema 8 and protected personal/coverage routes returned signed-out 401/no-store. Eleven workspace pages returned 200. Reserved-invalid-account login POST checks were denied with no session creation. No successful-user live clinical action, device installation or accessibility UAT is inferred.
- All **78 controlled document hashes** match. The original 200 requirement verification statuses and 111 authored acceptance cases remain baseline `NOT_RUN`; partial engineering evidence is recorded separately.

## Deployment and rollback

API: `dpl_3ZzHDwss4PBjzvXkfyo7wA1nur1p`. Frontend: `dpl_8jbzeeXbpDC9NJfUrXX5xUVXVTPL`. Both are READY. Schema remains **8** with no new tables or migration. This change adopts no reporting templates/criteria, clinical facts, receiving coverage, fees or equipment connections. No additional host, browser installation, paid model or provider configuration was introduced.

The preceding compatible schema-8 API/frontend deployments are `dpl_65nkkkvE576Q4tkzQ7pZpreSSA37` and `dpl_5k5bBZuExSYLXEfrj2fTzPo9GCoM`. A rollback would restore the previous frontend before the previous API, retaining the schema/history. An already installed public worker contains no protected cache and continues network-first personal navigation. No rollback/device rehearsal is claimed. Prior actual schema-8 recovery remains recorded in [Phase 6 evidence](2026-11-09-phase6-evidence.json); it was not repeated for this code/assets-only change.

## Remaining work and sequence

The [Director-first plan](2026-11-09-director-vision-alignment.md) remains governing: reconcile actual institutional templates and Region → Zone responsibilities; complete reporting sources/mappings, independent verification, released leadership dashboards and owned interventions; observe actual officer and leadership journeys and controlled facility rollout. The new coverage view is a bounded administrative increment, not complete reporting or adopted global coverage.

The native EMR remains the available clinical system; a second EMR is not required. Imaging/LIS/PACS/device connections follow facility registration, approval and adopted service readiness. Wider patient referral tracking, approved remote consultation, companion/routines, external reminders, actual policy adoption and observed device/clinical acceptance remain open. No installability test is a clinical operating approval.

The [current inventory](current-release.json) and [versioned release evidence](2026-11-09-coverage-and-personal-pwa-evidence.json) retain exact deployment and qualification observations.
