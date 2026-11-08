# Phase 4A cloud controls release

Date: 8 November 2026, Africa/Lagos. Release verification is in progress; this record will be completed with the actual commit, CI result, migration and deployment evidence. This is a bounded cloud increment, not completion of all Phase 4A or full-suite acceptance.

## Scope and implementation

The new [operations workspace](https://lw-health-intelligence.vercel.app/operations) provides actual scoped recovery review, policy package adoption, accepted duty coverage, clinical overdue alerts, durable job outcomes, staff restriction and personally accepted clinical handovers. [Account recovery](https://lw-health-intelligence.vercel.app/recover) uses the existing account identity, real password/TOTP verification and independent proof. Tokens remain in a removed URL fragment; browser storage is not used for recovery credentials. The care activation form references the independently reviewed package.

Backend components are `platform/control/{contracts,tables,service,recovery,jobs,offboarding,router,worker}.py`; authoritative routes are `/v1/auth/recovery*` and `/v1/operations/*`. Current roles and scope are checked before receipt replay. List predicates precede pagination; sensitive ciphertext, hashes, factor keys and job payloads are excluded from worklists. The existing role-administration workflow supports the added identity/privacy/finance reviewer roles without automatically appointing anyone.

Migration 4 adds the control tables, indexed clinical obligations and nine append-only history protections. Due tasks are indexed in the same transaction as their source change; bounded backfill supports existing tasks. Fenced leases, bounded retries, restart persistence, provider reconciliation and version-specific routing preserve one domain effect. Daily and manually authenticated processing run on the current Vercel stack. Recovery also attempts its durable email job after commit. Actual provider acceptance, delivery/read status and clinical completion remain distinct.

New clinical activations require current independently reviewed country/operator/service evidence. Existing historical activation is preserved; linked withdrawal/expiry blocks new writes. Staff restriction revokes access without erasing signed work; accepted clinical transfer checks source version, subject and current qualification. Other institutional/protected/finance duties still require their own workflow review. See [ADR-0010](../adr/0010-cloud-controls-recovery-and-deferred-hosting.md).

## Verification and release evidence

Local control integration: **20 passed**, 113.24 seconds. Exact isolated API packaging/import/health/database readiness/authentication checks passed. Actual Neon proof passed in a disposable schema: concurrent recovery-code generation returned one set and identical receipts; concurrent recovery requests created one challenge/job; competing workers obtained one lease; backup-code consumption occurred once; reset revoked old sessions and preserved identity/grants; history mutation was rejected; and job state survived application restart. The disposable namespace was removed. A concurrent first-use rate-limit insert race found during verification was corrected using a keyed PostgreSQL transaction lock before lookup/insert, and the Neon proof then passed.

Final exact-commit CI, uploaded source hashes, cloud migration and deployment identifiers are pending below. No synthetic domain data or policy approvals were seeded in the production schema. No real recovery message was sent merely to exercise a release test. No Playwright or additional service host was installed. Provider delivery, manual accessibility and facility UAT remain unexecuted release acceptance work.

## Rollout and containment

Deploy the compatible API while Neon is still at schema 3; operations remain unavailable until migration. Apply additive migration 4, then deploy the frontend. Verify readiness, unauthenticated denials, no-store responses, actual uploaded source hashes and protected history. Retain the previous runtime and all data encryption/configuration keys. `LWH_CONTROLS_ENABLED=false` pauses the new operating API/processing; use an API compatible with retained schema 4 for rollback. Credential resets, restrictions and immutable history are not undone by binary rollback.

## Operating boundaries and next sequence

Deployments remain within existing cloud services. A continuously running worker and malware scanner require additional hosting and are deferred. Unscanned evidence remains blocked. Daily/manual processing is not a qualified urgent clinical escalation service. Provider acceptance is implemented using the real Resend integration, but a release test does not claim delivered/read recovery or clinical notices. Actual clinical/privacy/identity/technical/finance reviewers, policy adoption, coverage, training, response windows, service readiness and facility acceptance remain institutional inputs.

Offline care is core scope and differs from installing its local runtime. No local runtime is deployed here; cloud writes still require WAN access. The prepared `scripts/run_platform_worker.ps1` runs one bounded tick by default; `-Continuous` requires an explicitly provisioned future host. Full offline care, scanner service, continuous processing, database/files/keys restore qualification, load/accessibility/security/UAT and other incomplete Phase 4A controls remain explicit work.

Next, continue the cloud-compatible Phase 4A controls and Phase 4B institutional lifecycle/approved information, followed by clinical completion, patient/family, partner interfaces/migration, finance/sponsors, governed assistance and integrated qualification. The [suite-wide review](2026-11-08-implementation-review-and-next-phases.md), [200-requirement phase register](2026-11-08-next-phase-requirements.csv) and [overall progress matrix](2026-11-05-platform-progress.md) retain the complete scope. Optional ERP remains separately scoped.
