# ADR-0002: Four independent deployables with per-audience tokens

- **Status:** Accepted
- **Date:** 2026-11-01
- **Spec refs:** §2.1, §10.5, §16.2, §21.6, §25.1

## Context

The earlier implementation shipped one Next.js bundle (`patient-web`). It had a role switcher that exposed the Patient, Clinician, Care Command and SponsorCare workspaces side by side. Clinical-signing and finance UI were delivered to every patient's device. The other three apps were unconnected mockups.

The spec requires distinct navigation per audience (§21.6) and a hard sponsor boundary that never reaches clinical data (§10.5).

## Decision

1. Ship four separately built and deployed apps: `patient-web`, `clinician-web`, `command-web` and `sponsor-web`. Each has its own origin, CSP, service worker scope and bundle. No app imports another app's screens.
2. Every access token carries an `aud` claim. Allowed audiences are `lwc:patient`, `lwc:clinician`, `lwc:command` and `lwc:sponsor`. The API rejects a token on any route whose audience set does not include the token's audience. A patient token on a clinician route is a 401 at the API, not a hidden button.
3. Each audience has an allow-list of roles. A token whose roles fall outside its audience's allow-list is rejected at verification, so a `SPONSOR_ADMIN` role cannot ride in a patient token.
4. Staff audiences (`clinician`, `command`) require `mfa=true` for every mutation. High-risk mutations additionally require a TOTP step-up code.

## Consequences

- The role-switcher UI is removed in Phase 1.
- Shared code lives only in `packages/*`: design tokens, primitives, contracts and policy.
- Each app can be released, rolled back and rate-limited independently.
