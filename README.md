# LW Health Intelligence Platform

Monorepo for the Directorate's institutional health platform and its LW Care capability. The current institutional increment provides persistent identity, scoped administration, facility onboarding and standards/directory workflows. Full clinical, offline, reporting and finance scope is tracked against the documentation suite and remains in progress.

The institutional frontend is `apps/platform-web`; its authoritative backend is `services/api/src/lw_care_api/platform` with Vercel entrypoint `api/platform.py`. Production configuration uses encrypted Vercel environment settings and Neon schema `health_platform`. See [implementation evidence](docs/implementation/2026-11-05-institutional-foundation.md), [cloud release procedure](docs/implementation/2026-11-05-cloud-release.md) and [organisation research](docs/CHRIST_EMBASSY_ORGANISATION_RESEARCH.md).

## Strict `D:\` Drive Toolchain Isolation

Before running any `pnpm`, `uv`, `pytest`, or `turbo` commands in a new terminal session, activate the `D:\` drive isolation script so zero caches or packages touch `C:\`:

```powershell
. .\scripts\env-d-drive.ps1
```

## Monorepo Architecture

```text
loveworld-care/
  apps/
    patient-web/         # Port 3000: Patient PWA (DoctorNow, Health Navigator, CareContinuity)
    clinician-web/       # Port 3001: Clinician PWA (Queue, LiveKit RTC, Ed25519 Signing, Addenda)
    command-web/         # Port 3002: Care Command (Executive Economics, Governance Kill-Switch, Ops, Finance)
    sponsor-web/         # Port 3003: SponsorCare & Institutional Workspace (Pools, Espees/Paystack, k>=5 Reports)
  services/
    api/                 # FastAPI /v1 Modular Monolith (Identity, Care, Finance Ledger, Webhooks)
    protocol-runtime/    # Deterministic Three-Valued (TRUE | FALSE | UNKNOWN) AST Protocol Engine
    model-gateway/       # Policy-Limited Multi-Provider AI Router (Gemini, MedGemma, Anthropic) + Kill Switch
    worker/              # Durable Transactional Outbox Consumer, Daily Close Reconciler & PHI-Free Messaging
  packages/
    domain-types/        # Authoritative State Machines, Transitions, MoneyMinor & Unit Economics
    authorization/       # RBAC + ABAC (Assignment, Purpose, Credential Expiry, Break-Glass, k>=5)
    audit/               # Tamper-Evident Hash-Chained Audit & PHI Telemetry Redaction
    fhir-adapters/       # HL7 FHIR R4 Resource Mappers & Signed Referral Bundle Exporter
    api-contracts/       # Typed /v1 DTOs & API Client SDK
    design-system/       # Accessible WCAG 2.2 AA React Primitives, Offline Emergency Banner & Session Lock
  tests/
    adversarial/         # Automated Test Suite covering AT-01 through AT-16 (§20.2)
```
