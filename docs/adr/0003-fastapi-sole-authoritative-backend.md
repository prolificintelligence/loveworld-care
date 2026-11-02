# ADR-0003: FastAPI `/v1` is the sole authoritative backend

- **Status:** Accepted
- **Date:** 2026-11-01
- **Spec refs:** §12.1–12.4, §14.1, §25.3

## Context

Two backends existed:

1. `apps/patient-web/src/app/api/v1/state/route.ts` wrote directly to Neon from a Next.js route. It had no authentication, no roles and no idempotency, and it exposed `SIGN_ENCOUNTER` and `TOGGLE_KILL_SWITCH` as plain actions.
2. `services/api` (FastAPI) carried the real domain model. However, it resolved the caller from client-supplied `X-Actor-Id` / `X-Actor-Roles` headers, so any caller could impersonate a clinician.

It also booted with hard-coded default secrets while defaulting `environment=production`.

## Decision

1. FastAPI `/v1` is the only service that reads or writes the clinical, finance, identity and governance schemas. The Next.js state route is deleted in Phase 1, together with the role-switcher UI.
2. Caller identity comes **only** from a verified bearer token. The token is EdDSA (Ed25519) signed and carries `iss`, `aud`, `exp`, `nbf`, `iat`, `jti`, `sid`, `sub`, `roles`, `mfa` and an optional `org`. Client-supplied identity headers are ignored.
3. Clinician credential state (licence, status, expiry) is resolved server-side from the roster registry, never from token claims or headers.
4. Settings fail closed. When `LW_ENVIRONMENT=production`, the app refuses to start if any secret still equals a shipped default, the signing seed is missing, or CORS allows `*` or `localhost`.
5. Uvicorn uses the factory (`lw_care_api.main:create_app --factory`). There is no import-time app construction.
6. A dev-only `POST /v1/auth/dev-token` exists for local work and tests. It is not mounted in production. The production patient login (phone OTP or email magic link) and staff login (SSO + TOTP) will issue the same token format.

## Consequences

- Identity is now verified on every route. Existing tests that relied on header impersonation are migrated to tokens.
- The OpenAPI document becomes the single contract that `packages/api-contracts` is generated from (ADR-0004).
