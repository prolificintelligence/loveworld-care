# Cloud release — 5 November 2026

Status: **DEPLOYED AND VERIFIED** for the institutional increment. The project lead authorised the GitHub push, additive Neon migration, Vercel frontend/API deployment, Upstash and free OpenRouter configuration using credential files under `D:/Projects/secrets`. Credential values are excluded from source, Git URLs and logs. The corrected email credential is `lw-health-resend.md`.

## Verified before deployment

- GitHub repository: `prolificintelligence/loveworld-care`; token has push permission. The remote main branch matched the local baseline before changes were committed.
- Neon: `health_platform` schema installed, version 1. Existing schemas and their data retained; zero demo records seeded.
- Live PostgreSQL verification passed in an isolated, subsequently removed namespace: simultaneous duplicate operations produced one effect; different content with the same key returned 409; the installed append-only trigger rejected mutation. Six history tables are protected.
- Upstash: authenticated PING succeeded; the platform's separate `lwh:platform:ai-disabled` control was initialised with SET NX. Existing care controls were not overwritten.
- OpenRouter: `nvidia/nemotron-3.5-lightning:free` returned a real readiness completion with reported cost 0. A prior Gemma free-model probe returned 429. Requests enforce maximum prompt/completion price zero, with no paid fallback. The deployed integration exposes fixed public readiness probes only; clinical data routing is outside this release.
- Resend: the replacement key is a valid send-only key. Domain listing returns `restricted_api_key`; sender validation is deferred to the real send, and delivery is not claimed from queueing alone.
- Local regression after release fixes: **70 passed**. TypeScript and Ruff passed. The exact isolated API artifact passed health, real database readiness and unauthenticated denial checks. The standalone frontend artifact installed from its frozen lockfile and passed its production build.

## Deployment configuration

Projects: `lw-health-intelligence` (Next.js frontend) and `lw-health-intelligence-api` (FastAPI). Runtime secrets are encrypted in their production settings. The API source bundle contains the institutional runtime and shared connection code, excluding the legacy seeded Care runtime. Runtime dependency versions are pinned in `requirements.platform.txt`.

The Vercel account is on Hobby. Its cron permits daily execution; invitations attempt delivery immediately and retain failures for authenticated/manual retry and daily catch-up. This is not qualification of high-frequency clinical scheduling. The [Vercel cron restrictions](https://vercel.com/docs/cron-jobs/usage-and-pricing) and [OpenRouter maximum-price routing](https://openrouter.ai/docs/guides/routing/provider-selection) informed the configuration.

Verified public origins are `https://lw-health-intelligence.vercel.app` and `https://lw-health-intelligence-api.vercel.app`. Actual deployment identifiers, external HTTP results and the invitation receipt are recorded below.

## Release result

| Evidence | Verified result |
|---|---|
| Repository | [prolificintelligence/loveworld-care](https://github.com/prolificintelligence/loveworld-care), branch `main` |
| Runtime source commit | `ec9155dccc7c799cca9099f328b2be0620f12d12` |
| GitHub checks for runtime source | Python: success; web: success; secrets-scan: success |
| Frontend deployment | `dpl_eExYQ3BV1DvccphUsMn98XsppsJL`, READY |
| Final API deployment | `dpl_C81SNFh2neP9CBZgvJ4GGA5xtXuM`, READY |
| Frontend `/`, `/activate`, `/directory` | HTTP 200; expected platform title |
| API `/v1/health` | HTTP 200, RUNNING |
| API `/v1/ready` | HTTP 200, schema version 1 |
| API `/v1/auth/me` without credentials | HTTP 401, AUTH_REQUIRED |
| Frontend proxy `/v1/health`, `/v1/ready` | HTTP 200, actual backend JSON |
| Frontend proxy `/v1/auth/me` without credentials | HTTP 401 |
| Deployed provider source | Hash matches the committed `platform/integrations.py` |
| Real backend model component | PROVIDER_COMPLETED; `nvidia/nemotron-3.5-lightning:free`; cost 0; no patient data transmitted |
| Model receipt | `gen-1793886752-8NZ00qWvqegwmblkDUg8` |
| Administrator | Emmanuel Patrick, `epatrick@prolificintelligence.co`; PLATFORM_ADMIN and REGISTRY_STEWARD |
| Administrator invitation | Resend accepted 1; retry pending 0; expires 24 hours after issue |
| Invitation send receipt | `01a1abf5-8d30-7b21-822a-4e01de61754e`, accepted at `2026-11-05T13:45:58.941947+00:00` |

The administrator's initial grants expire after 90 days. The recipient must use the emailed link to set a password and enrol an authenticator. No password, authenticator secret or invitation token was printed, committed or placed in this evidence file. The administrator account was created from the user's explicit nomination; no fabricated facility or clinical records were seeded.

The final free-model probe returns the usable reply `READY`, with reasoning disabled and output bounded to 512 tokens. Earlier small token budgets exhausted the reasoning allowance before returning usable text. The corrected component completed through the real Upstash control and OpenRouter connection, at reported cost zero. Clinical data routing is outside this integration check. Provider acceptance of the invitation is verified; mailbox delivery and recipient enrolment are not inferred.

Initial deployment faults were corrected before acceptance: an eager package import depended on excluded legacy configuration; shared-parent TypeScript settings did not survive the original frontend upload layout; Turbo omitted the API-origin setting in CI. Imports are now lazy, the frontend deployment is self-contained with its verified pnpm graph, and build environment variables are explicitly declared. Existing lint findings were corrected and legacy database writes now propagate failures. Full regression was rerun after those changes.

## Remaining platform work

This release concerns the institutional increment described in ADR-0007. Comprehensive clinical EMR, full facility-local offline care, reporting/intelligence, finance, clinical AI and other documented modules remain implementation/qualification work. Actual criteria, adopted organisation authority, scanner connectivity and country/facility operating packages remain explicit dependencies. No claim of whole-platform or clinical production acceptance is made.
