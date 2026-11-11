# LW Health Intelligence Platform

Latest assessment: [11 November red-team audit, milestones and production-readiness roadmap](docs/implementation/2026-11-11-red-team-audit.md). A locally reproduced login admission/state-growth gap is the next engineering priority; operating adoption and full-suite acceptance remain incomplete. See the [ranked findings](docs/implementation/2026-11-11-red-team-findings.csv), [current 20-ticket overlay](docs/implementation/2026-11-11-initial-source-readiness-backlog.csv), [next-session handoff](docs/implementation/NEXT_SESSION_HANDOFF.md) and [copy-ready continuation prompt](docs/implementation/2026-11-11-red-team-new-session-prompt.md).

Latest delivered increment: [exact initial inspection lineage](docs/implementation/2026-11-11-initial-source-release.md) and [current readiness overlay](docs/implementation/2026-11-11-initial-source-readiness-backlog.csv). Independent source confirmation and retained retraction preserve original observations without advancing corrective work. Notice/service/appeal reconciliation and operating acceptance remain open.

Native reporting: [qualified source mappings and officer workflow](docs/implementation/native-reporting-source-guide.md), with signed provenance and explicit coverage/freshness. [Current release evidence](docs/implementation/current-release.json) records the live cloud increment.

Reporting officers: [template review and adoption](https://lw-health-intelligence.vercel.app/reporting-templates). Director review: [researched working forms and proposed calendar](docs/implementation/reporting-forms/README.md). These proposed forms use retained review/adoption; deployment does not represent institutional approval.

Current production entry points: [Directorate reporting](https://lw-health-intelligence.vercel.app/directorate), [My LW Health Care PWA](https://lw-health-intelligence.vercel.app/my-health), [LW Care staff EMR](https://lw-health-intelligence.vercel.app/care) and [patient access/receiving teams](https://lw-health-intelligence.vercel.app/patient-access). These share the current platform API; personal and professional permissions remain independently enforced. See the [current release](docs/implementation/current-release.json), [interaction guide](docs/implementation/personal-family-care-interaction-guide.md) and [Director-first sequence](docs/implementation/2026-11-09-director-vision-alignment.md).

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

The [Phase 5 clinical release](docs/implementation/2026-11-08-phase5-clinical-release.md) adds actual capacity/shift/teamwork, nursing receipt and special dispositions, maternal/child facts, medicine/stock stewardship, procedure monitoring/trace/recall and patient instructions in `/care`. Clinical activation and current professional authority remain required. Phase 6 personal/family access is recorded in the current release inventory; the comprehensive audit now governs the readiness and implementation sequence.
