# Phase 6 personal care release and Director-first sequence

Date: 9 November 2026. Status: **deployed and technically verified** for this increment. Full clinical/institutional acceptance remains incomplete.

## Delivered workflows

- [My LW Health Care](https://lw-health-intelligence.vercel.app/my-health): public personal account enrolment through private email and existing password/MFA activation; no staff grants from enrolment. Existing accounts are not reset by repeated registration. Provider acceptance remains separate from queued delivery; no live signup email was sent by the release checks.
- Independently reviewed self/representative links to confirmed facility patient identities, explicit READ/REQUEST/SHARE permissions, expiry/reassessment, one active self link per facility patient, subject isolation and immediate future-access revocation. Representatives cannot delegate onward. Demographic version changes require renewed identity review.
- Human-reviewed patient-readable plans, verified medicines, appointments, reviewed results and timeline summaries, bound to the actual source version and separately released to each recipient. Restricted sources are withheld. Corrections, signed amendments and entered-in-error markers suppress obsolete summaries; raw staff notes are not automatically disclosed.
- Requests with actual named primary/fallback recipients, personally accepted service coverage, update targets, truthful pending acceptance, attributed human/patient messages, replies, accepted handover and closure. The named current fallback may accept after an owner loses eligibility. Revoking portal access preserves accepted care work. Inactive-owner exceptions are included in operating assurance.
- In-app follow-up preferences and subject-specific access history. No external health notifications, clinical AI companion or facility WAN-offline operation is claimed by this increment.
- [Staff patient-access workspace](https://lw-health-intelligence.vercel.app/patient-access): independent identity review, bounded grants/revocation, source release/withdrawal, service coverage acceptance and assigned request inbox. API authority remains independent of the interface.

Design: [ADR-0015](../adr/0015-personal-subject-authority-and-reviewed-disclosure.md). Native contracts extend `/v1/personal`; canonical suite forms/IDs retain their original meaning. LWH-FRM-022 identity, relationship, authority, evidence, actions and valid-period concepts are mapped explicitly by the reviewed grant workflow.

## Executed qualification

[Final CI](https://github.com/prolificintelligence/loveworld-care/actions/runs/42655187421) passed **197 Python tests, eight client tests, type checks, production builds and secret scanning**. Nine personal integration tests exercise real durable synthetic databases: password/MFA activation, independent review, wrong-subject denial, representative isolation, revocation and idempotency, source amendments/confidentiality, owned handover, service availability, preferences, fallback takeover and permission-history integrity during recovery. These are engineering results, not observed clinician/browser/accessibility UAT.

Actual Neon qualification in a disposable schema passed concurrent duplicate request submission with one committed receipt, independent linking and reviewed release, raw-source withholding, revoked replay denial, retained accepted work and rejection of direct history deletion. No test patients were inserted into production. Temporary test schemas were removed.

All **78 controlled documentation hashes** match. The 200 authored requirement verification statuses and 111 acceptance specifications remain baseline `NOT_RUN`. Bounded partial engineering links are updated separately in the requirement register.

## Deployment and migration

API runtime `04fba3864f67e31e000b3a259d8d7142e5f917f3`: `dpl_65nkkkvE576Q4tkzQ7pZpreSSA37`. Frontend source `b66d779d4e394c4ac5bd93f9c6b459cb3426710b`: `dpl_5k5bBZuExSYLXEfrj2fTzPo9GCoM`. Its 22 web source files are unchanged in the final runtime tree. Both deployments are READY. **60 API and 22 frontend source hashes** match; actual personal/staff built JavaScript bundles contain their deployed controls. Both origins enforce signed-out HTTP 401/no-store on protected personal routes. Readiness is 200/schema 8; eleven workspace pages returned 200. Reserved-invalid login POST probes are denied without sessions; no successful-user live UAT is inferred.

The compatible API was first verified healthy on schema 7 with personal routes gated 503. Additive migration **8** then installed ten personal tables: **101 total tables and 53 protected history tables**. No production clinical records were seeded or existing clinical records rewritten. Existing keys, accounts and protected clinical/reporting history were retained.

## Recovery evidence and limits

Before migration, archive `83dc1ab6-64e8-4026-9a3a-04c22a21ffbe` restored **91 tables / 208 rows / zero files**, verifying 14 encrypted fields and 48 protected history tables with isolated cleanup.

After migration, archive `d17cf40d-e42a-45b2-8609-0d17a435046c` restored **101 tables / 212 rows / 0 files**, verifying **17 encrypted fields and 53 protected history tables**. Integrity checks reported no exceptions; restored data remained isolated and unactivated, and cleanup completed. The first schema-8 rehearsal correctly stopped at a verifier that still expected 48 protected tables. The count check was corrected to 53; the failed assurance observation remains retained and the same archive subsequently passed. A separate populated personal-history test proves that changed permission projections are rejected by lineage verification.

These small production archives contain no operational clinical population or files. They do not qualify representative clinical load, attachment scanning, adopted RPO/RTO, independent custody/cadence or full service resumption. Retained schema-5/6/7 archive shapes remain supported; the schema-7 rehearsal used the new reader before migration.

## Rollback and operating prerequisites

Retain schema 8 and its history; do not alias the old schema-7-only API onto schema 8 or drop personal records. Prefer a corrective compatible release. Receiving services can be paused to stop new requests while current staff continue processing accepted work. Do not globally disable access when open accepted responsibilities require the staff workspace. No rollback rehearsal is claimed here.

Production still requires actual registered/verified facilities, central affiliation/recognition decisions where applicable, adopted activation/release/representative policies, verified records/care professionals and personally accepted receiving coverage. This increment does not invent age/legal rules, clinical instructions, operating approvals or emergency dispatch. Wider companion/routines, external neutral reminders, restricted-source release, observed accessibility and full exception qualification remain partial. Offline care remains core; local installation/additional persistent hosting remain deferred.

## Director-first alignment and next work

The [Director vision review](2026-11-09-director-vision-alignment.md) supersedes the earlier prospective integration-first sequence. **The native EMR is the platform's clinical system; a second EMR is not a prerequisite.** Directorate registration/reporting/oversight is the primary product outcome under DHS-REQ-001/005/006/007/016/017, while comprehensive EMR is confirmed core scope under DEC-105. DEC-107 permits existing-EMR coexistence/migration per facility.

Next: reconcile actual institutional templates and Region → Zone accountabilities; complete facility returns, independent verification, leadership dashboards and owned interventions; qualify additional native-EMR mappings without double counting; observe actual Directorate journeys and controlled facility rollout. Imaging/LIS/PACS/device connections follow facility registration and approval, adopted service activation and actual selected counterpart. No equipment connection or external EMR is a platform-wide prerequisite.

The [current inventory](current-release.json) and [versioned evidence](2026-11-09-phase6-evidence.json) record deployment, recovery, live observations and scope boundaries.
