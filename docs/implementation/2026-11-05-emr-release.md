# Cloud EMR release — 5 November 2026

This record concerns the EMR extension to the live institutional service. The project lead authorised implementation, testing, the additive Neon migration, GitHub push and Vercel frontend/API deployment. Offline installation is deferred. No Playwright or browser software was installed for this release.

## Release evidence

Status: **DEPLOYED AND VERIFIED** for the documented cloud EMR increment. Broader project status is assessed in [the progress report against all 25 PRDs and 21 shared specifications](2026-11-05-platform-progress.md).

| Evidence | Actual verified result |
|---|---|
| Clinical workspace | [https://lw-health-intelligence.vercel.app/care](https://lw-health-intelligence.vercel.app/care) |
| API | [https://lw-health-intelligence-api.vercel.app/v1/ready](https://lw-health-intelligence-api.vercel.app/v1/ready) |
| Repository | [prolificintelligence/loveworld-care](https://github.com/prolificintelligence/loveworld-care), branch `main` |
| Runtime source commit | `112e69dad39faabec8372c6c7eaf1145721623ca` |
| Initial EMR implementation commit | `fc25ef265b922228dd293e58976866760a075723` |
| Exact runtime CI | [Run 42097960851](https://github.com/prolificintelligence/loveworld-care/actions/runs/42097960851): Python, web and secrets scan all successful |
| CI test log | **92 passed**, 1 upstream deprecation warning, 22.05 seconds; Python job `127492879813` |
| Targeted local EMR regression | **22 passed**; final entered-in-error correction check also passed after the last amendment |
| Frontend validation | TypeScript passed; production Next.js build passed; `/care` included |
| API deployment | `dpl_BPDsbNWPBPA5EB5YfybuwZjiKrdX`, READY |
| Frontend deployment | `dpl_J6mDcmKqJjr9qRnXg7s7WHygxwtn`, READY |
| Actual source hashes | Vercel source-file UIDs match local SHA-1 for `clinical/service.py`, `clinical/router.py`, `clinical/continuity.py` and `src/app/care/page.tsx` |
| Neon | Additive schema version **2** installed; zero sample care records seeded |
| Actual PostgreSQL concurrency | Concurrent same-key notes: one effect and identical receipts; exclusive bed race: one admission and one 409; stock race: one issue and one 412, remaining quantity 1 |
| Database protection | Direct UPDATE of clinical event history and direct mutation of a signed note both rejected |
| Institutional regression on Neon | Existing idempotency conflict and append-only checks passed after migration 2; ten history tables have immutable triggers |
| Exact isolated API artifact | Import, HTTP health, real database readiness and unauthenticated denial checks passed; legacy seeded runtime excluded |
| Controlled suite integrity | All **78** manifest hashes matched; **200** requirements and **111** specified acceptance cases retained |

Production domain counts were read after migration: zero clinical sites, clinical privileges, clinical records/events, configured clinical beds, stock lots/movements and care ledger entries. These are empty actual stores, not populated demo projections. The verification namespaces were removed after their synthetic checks. Existing institutional accounts, provider settings and all other database schemas were preserved.

The following checks were executed against both the public API origin and the frontend's same-origin API proxy:

| Route | HTTP and semantic result |
|---|---|
| `/v1/health` | 200, running; `Cache-Control: no-store` |
| `/v1/ready` | 200, actual database schema version 2; `no-store` |
| `/v1/auth/me` without credentials | 401; `no-store` |
| `/v1/clinical/sites` without credentials | 401; `no-store` |
| Frontend `/`, `/care`, `/activate`, `/directory` | 200 and expected platform title |

The successful 92-test CI run covers the exact runtime commit, including entered-in-error restrictions on future execution, retained-source correction, independent transfusion witnessing, reviewed identity links, sharing revocation and cached-download denial, and balanced/idempotent cash receipts. The only warning originates in the upstream Starlette/httpx test client. Temporary database test fixtures do not establish clinical operating approval.

## Scope and custody

The implementation is `services/api/src/lw_care_api/platform/clinical` and `apps/platform-web/src/app/care`. Migration 2 adds clinical storage and database protection without seeding sample care or deleting other schemas. API and frontend remain the existing `lw-health-intelligence-api` and `lw-health-intelligence` Vercel projects. The legacy process-local Care repositories are excluded from the production API artifact.

The user-facing clinical workspace is `/care`. Accounts, facility activation and independent professional privileges are actual stored authority. Initial Directorate administration does not itself grant chart access. Existing secrets, account credentials, the encryption key, provider settings and authority node are preserved; this release does not issue fabricated professional permissions or facility approvals.

The release does not claim complete acceptance of all clinical PRDs. Specialty content/algorithms, interfaces, patient self-service, remaining finance controls, operating activation and offline qualification are identified in the progress report. Clinical records are not sent to the free model integration.

Clinical activation still requires a nominated authorised clinical governor, a verified actual facility and adopted operating evidence. Staff must activate their invited MFA accounts before a separate governor issues professional/service privileges. No standing chart permission was added to Emmanuel Patrick's Directorate account merely to populate the EMR. Browser interaction/accessibility tests, actual facility clinical UAT, clinical safety acceptance and backup/restore exercises remain unexecuted; no browser-test software was installed at the user's instruction.

## Migration and rollback

Run `scripts/platform_cloud_release.py migrate` with the authorised, ignored runtime configuration. It creates only missing tables/indexes/triggers in `health_platform` and records schema version 2. Production source data and older schemas are retained. `scripts/verify_clinical_postgres.py` uses a random `lwh_emr_verify_<uuid>` namespace and removes only that verified namespace after its synthetic checks; no synthetic patients are inserted in the production schema.

Rollback restores the previous frontend/API deployments while retaining the additive schema and all clinical, audit, ledger and event history. Do not drop clinical data, reuse conflicting authority epochs, change the encryption key, or restore a competing writer as a rollback. Clinical signing events have server-attested authenticated author intent, hash lineage and Ed25519 signatures; no jurisdiction-specific qualified-signature certification is inferred.
