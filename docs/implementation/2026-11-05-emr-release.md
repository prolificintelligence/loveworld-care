# Cloud EMR release — 5 November 2026

This record concerns the EMR extension to the live institutional service. The project lead authorised implementation, testing, the additive Neon migration, GitHub push and Vercel frontend/API deployment. Offline installation is deferred. No Playwright or browser software was installed for this release.

## Release evidence

The final verified deployment identifiers, source commit, database results and external HTTP checks are recorded here after release verification. Broader project status is assessed in [the progress report against all 25 PRDs](2026-11-05-platform-progress.md).

The initial complete backend regression passed **89 tests**. The frontend passed TypeScript checking and the production Next.js build, including `/care`. Subsequent targeted clinical checks cover final changes and additional procedure/transfusion and identity review journeys; final executed results are recorded below. A deprecation warning originates in the upstream Starlette/httpx test client.

## Scope and custody

The implementation is `services/api/src/lw_care_api/platform/clinical` and `apps/platform-web/src/app/care`. Migration 2 adds clinical storage and database protection without seeding sample care or deleting other schemas. API and frontend remain the existing `lw-health-intelligence-api` and `lw-health-intelligence` Vercel projects. The legacy process-local Care repositories are excluded from the production API artifact.

The user-facing clinical workspace is `/care`. Accounts, facility activation and independent professional privileges are actual stored authority. Initial Directorate administration does not itself grant chart access. Existing secrets, account credentials, the encryption key, provider settings and authority node are preserved; this release does not issue fabricated professional permissions or facility approvals.

The release does not claim complete acceptance of all clinical PRDs. Specialty content/algorithms, interfaces, patient self-service, remaining finance controls, operating activation and offline qualification are identified in the progress report. Clinical records are not sent to the free model integration.

## Migration and rollback

Run `scripts/platform_cloud_release.py migrate` with the authorised, ignored runtime configuration. It creates only missing tables/indexes/triggers in `health_platform` and records schema version 2. Production source data and older schemas are retained. `scripts/verify_clinical_postgres.py` uses a random `lwh_emr_verify_<uuid>` namespace and removes only that verified namespace after its synthetic checks; no synthetic patients are inserted in the production schema.

Rollback restores the previous frontend/API deployments while retaining the additive schema and all clinical, audit, ledger and event history. Do not drop clinical data, reuse conflicting authority epochs, change the encryption key, or restore a competing writer as a rollback. Clinical signing events have server-attested authenticated author intent, hash lineage and Ed25519 signatures; no jurisdiction-specific qualified-signature certification is inferred.
