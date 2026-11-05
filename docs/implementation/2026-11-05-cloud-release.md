# Cloud release — 5 November 2026

The project lead authorised the GitHub push, additive Neon migration, Vercel frontend/API deployment, Upstash and free OpenRouter configuration using credential files under `D:/Projects/secrets`. Credential values are excluded from source, Git URLs and logs. The corrected email credential is `lw-health-resend.md`.

## Verified before deployment

- GitHub repository: `prolificintelligence/loveworld-care`; token has push permission. The remote main branch matched the local baseline before changes were committed.
- Neon: `health_platform` schema installed, version 1. Existing schemas and their data retained; zero demo records seeded.
- Live PostgreSQL verification passed in an isolated, subsequently removed namespace: simultaneous duplicate operations produced one effect; different content with the same key returned 409; the installed append-only trigger rejected mutation. Six history tables are protected.
- Upstash: authenticated PING succeeded; the platform's separate `lwh:platform:ai-disabled` control was initialised with SET NX. Existing care controls were not overwritten.
- OpenRouter: `nvidia/nemotron-3.5-lightning:free` returned a real readiness completion with reported cost 0. A prior Gemma free-model probe returned 429. Requests enforce maximum prompt/completion price zero, with no paid fallback. The deployed integration exposes fixed public readiness probes only; clinical data routing is outside this release.
- Resend: the replacement key is a valid send-only key. Domain listing returns `restricted_api_key`; sender validation is deferred to the real send, and delivery is not claimed from queueing alone.
- Local regression: 14 institutional tests passed after the integration changes. Earlier full backend regression: 68 passed. TypeScript validation passed. Production frontend build is checked before upload.

## Deployment configuration

Projects: `lw-health-intelligence` (Next.js frontend) and `lw-health-intelligence-api` (FastAPI). Runtime secrets are encrypted in their production settings. The API source bundle contains the institutional runtime and shared connection code, excluding the legacy seeded Care runtime. Runtime dependency versions are pinned in `requirements.platform.txt`.

The Vercel account is on Hobby. Its cron permits daily execution; invitations attempt delivery immediately and retain failures for authenticated/manual retry and daily catch-up. This is not qualification of high-frequency clinical scheduling. The [Vercel cron restrictions](https://vercel.com/docs/cron-jobs/usage-and-pricing) and [OpenRouter maximum-price routing](https://openrouter.ai/docs/guides/routing/provider-selection) informed the configuration.

Intended public origins are `https://lw-health-intelligence.vercel.app` and `https://lw-health-intelligence-api.vercel.app`. A URL in configuration is not deployment evidence. Final deployment identifiers, health/readiness results and administrator invitation receipt are recorded below only after verification.

## Release result

Pending GitHub push, production deployment and external HTTP verification.

## Remaining platform work

This release concerns the institutional increment described in ADR-0007. Comprehensive clinical EMR, full facility-local offline care, reporting/intelligence, finance, clinical AI and other documented modules remain implementation/qualification work. Actual criteria, adopted organisation authority, scanner connectivity and country/facility operating packages remain explicit dependencies. No claim of whole-platform or clinical production acceptance is made.
