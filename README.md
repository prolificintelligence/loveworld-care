# LW Health Intelligence Platform

Monorepo for the Directorate's institutional health platform and its LW Care capability. The institutional runtime provides persistent identity, scoped administration, facility onboarding and standards/directory workflows. The `/care` workspace extends it with a persistent, encrypted cloud EMR, clinical permissions, encounter/document/order/medicine/ward/specialty workflows, controlled sharing and care billing. The `/directorate` workspace adds governed returns, independent verification, protected safety review, disclosure-controlled snapshots and accountable actions. `/operations` provides verified recovery review, activation evidence, accepted clinical duty/handover and durable delivery controls; `/recover` provides account recovery. Overall scope and remaining qualification are assessed in the [project progress report](docs/implementation/2026-11-05-platform-progress.md).

The production frontend is `apps/platform-web`; its authoritative backend is `services/api/src/lw_care_api/platform` with Vercel entrypoint `api/platform.py`. Production configuration uses encrypted Vercel environment settings and Neon schema `health_platform`. See [institutional release evidence](docs/implementation/2026-11-05-cloud-release.md), [EMR release evidence](docs/implementation/2026-11-05-emr-release.md), [Directorate release evidence](docs/implementation/2026-11-07-directorate-release.md), [reporting authority and disclosure](docs/adr/0009-directorate-reporting-disclosure-and-review.md), [clinical authority and custody](docs/adr/0008-cloud-emr-authority-and-record-custody.md) and [organisation research](docs/CHRIST_EMBASSY_ORGANISATION_RESEARCH.md). Offline care remains core scope. Deployments outside the current cloud stack, including facility-local installations, are deferred; this cloud EMR requires a reachable cloud authority. Phase 4A controls are tracked in [the controls release record](docs/implementation/2026-11-08-control-release.md) and [the cloud recovery release](docs/implementation/2026-11-08-cloud-recovery-release.md). The [Phase 4B release](docs/implementation/2026-11-08-institutional-publication-release.md) adds reviewed hierarchy/site changes, affiliation lifecycle and approved publication in `/governance`, with current public information in `/learn`.

## Strict `D:\` Drive Toolchain Isolation

Before running any `pnpm`, `uv`, `pytest`, or `turbo` commands in a new terminal session, activate the `D:\` drive isolation script so zero caches or packages touch `C:\`:

```powershell
. .\scripts\env-d-drive.ps1
```

## Production runtime

```text
apps/platform-web/                     Identity, facility, care and Directorate workspaces
api/platform.py                        Vercel entrypoint
services/api/src/lw_care_api/platform/  Authoritative identity and institutional service
  clinical/                            Encrypted cloud EMR and clinical custody
  reporting/                           Obligations, verification, disclosure, safety and actions
  control/                             Recovery, activation evidence, jobs and accepted handovers
  institutional/                       Reviewed hierarchy, affiliation lifecycle and publication
scripts/                               Cloud release, packaging and real PostgreSQL verification
docs/implementation/                   Exact release evidence and overall suite progress
```

The other application/package directories retain earlier development work. Production release packaging selects the institutional runtime, clinical, reporting and control modules, and platform-web. The progress report describes the actual delivered scope and operating dependencies.
