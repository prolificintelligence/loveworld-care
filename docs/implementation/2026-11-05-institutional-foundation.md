# Institutional foundation — implementation and release evidence

Date: 5 November 2026. This file records the initial implementation evidence. The subsequent cloud release is **DEPLOYED AND VERIFIED**, as detailed in the [release record](2026-11-05-cloud-release.md).

The user selected foundations and facility onboarding first, confirmed existing data is test/demo data, and explicitly changed the target to live Vercel/Neon deployment with real integrations. Full platform scope remains the LWH suite. This increment does not satisfy the entire suite or establish clinical production readiness.

## What changed

`apps/platform-web` supplies the institutional sign-in, authenticator enrolment, facility registry, application dossier, organisation administration, standards, access/revocation, audit and public directory screens. All operational views call the authoritative API. They do not manufacture totals, records, successful dependency responses or professional authority. Public-source organisation research has its own provenance and adoption status.

`services/api/src/lw_care_api/platform` implements PostgreSQL-backed accounts, opaque sessions, scoped/effective grants, organisations/operators, facilities, criteria, applications, inspection evidence, independent recommendations/decisions, revisions, audit, operation receipts and outbox. Production rejects SQLite, missing encryption keys and invalid application origins. SQLite is used only by the isolated automated tests. Browser credentials are secure HttpOnly cookies, with origin checks; authenticator counters and revocations persist.

Facility ownership, identity verification, statutory evidence, affiliation, publication, capability and readiness are separate. Creation does not imply affiliation or available care. Public queries allow-list fields and omit private contacts/evidence. Expired affiliation cannot appear in directory results. Final Directorate decisions require a separately authorised, independent central decider. Signed inspection/decision/evidence history has PostgreSQL append-only triggers in the explicit migration.

Mutations use scoped idempotency receipts, expected versions, PostgreSQL advisory/row locks and atomic state/history/audit/outbox transactions. Replayed private receipts recheck current grants. Evidence uploads require a configured real scanner, actual private S3/R2 storage, bounded content and checksums. Missing scanning/storage returns an unavailable operation rather than accepting unsafe or imaginary evidence. Resend invitations are durably queued with encrypted tokens and stored provider acceptance receipts; mailbox delivery is not inferred.

`api/platform.py`, `vercel.platform.json`, `requirements.platform.txt` and `scripts/platform_cloud_release.py` prepare an isolated institutional production release. The API source bundle includes only the institutional package and shared connection helper, excluding legacy seeded runtime modules. Runtime dependencies are pinned. CI discovers the new app and backend tests. The release command never prints credential values or provider response bodies.

## Canonical mapping and limits

| Contract | Implemented mechanics | Remaining work before claiming complete coverage |
|---|---|---|
| LWH-PRD-001; SPEC-003; SCR-001/002/003 | Real invitation/enrolment, MFA, persistent session/grant verification, effective scopes and revocation | Account recovery, broader personal/clinical identities, accepted task handover, hierarchy transfers and facility-local identity |
| LWH-PRD-002; FRM-001.F001…F008; API-001; QRY-001/002; SCR-004/005/006 | Owner/site separation, four site types, ownership labels, independent status axes, versioned verification, controlled directory projection | Reviewed duplicate merges, full edit/closure propagation, population suitability and adopted readiness/service activation |
| LWH-PRD-003; FRM-007/008; API-007/008; SCR-007/008/009 | Criteria snapshots, private evidence handling, independent inspector/reviewer, central reasoned decision and separate publication | Corrections, complete renewal/restriction/appeal workflows, assessor qualification and adopted institutional criteria |
| LWH-SPEC-009/010/011 | Version/state/permission checks, durable receipts/history/outbox and provider invitation acceptance | Full event envelope/sequence, downstream consumers, controlled offline capture and replay qualification |
| LWH-EVT-002/003/005 | Existing canonical meanings retained: facility verified, application submitted, decision recorded | Additional implementation events are named extensions, not renumbered canonical IDs |
| LWH-ARC-001; SPEC-017 | Institutional cloud boundary explicitly separated from future facility clinical write authority | Complete local clinical runtime, offline departments, sync/conflict/recovery and site-loss qualification |

The typed facility request uses server-derived actor/node metadata and explicit domain fields. `site_name`, `operator_org_id`, `ownership_category`, `jurisdiction_profile`, `address`, `services`, contacts and private evidence map to the FRM-001 field families. The supplied capture-schema wrapper and the runtime command DTO are distinct; full schema-driven draft/unknown capture remains unimplemented. The decision route is a consequential resource-specific command with expected version and explicit intent. It does not treat form capture as approval.

## Tests actually executed

Repository baseline commit: `6de23be49a7a1fa693dcd04b8d3db8775247249e`; changes are uncommitted workspace files.

| Check | Result | Boundary |
|---|---|---|
| Entire backend regression suite | **68 passed** in 67.29 seconds | Isolated test environments; one upstream Starlette/httpx deprecation warning |
| Institutional tests after final event/provenance changes | **12 passed** in 49.29 seconds | Real isolated SQLite databases, not production PostgreSQL/provider proof |
| Platform TypeScript check | **Passed** | Compiler/static types |
| Platform Next.js production build | **Passed** | `/`, `/activate`, `/directory`; no live API or browser journey certified |
| Targeted Ruff and whitespace checks | **Passed** | Institutional code, release tooling and new tests |
| Original controlled-document hashes | **78 match** | Document integrity, not implementation acceptance |

Initial institutional source-tree SHA-256: `c88b083408a3adf640236e93270413c9f229d650811c0cbabb91d4bb0c442cfb`.

Initial frontend source-tree SHA-256: `d5889839453b2b19661f7dc4127adbf40a8ef3a493cb9265e13fda7a0217c79e`.

Tests cover restart/replica-visible persistence, session/grant revocation, MFA replay, enrolment token reuse, failed-login throttling, sensitive validation-error redaction, wrong-zone access, administrative/clinical separation, operation-key conflicts, current-authority checks on receipt replay, stale versions, independent review/decision, publication gating and public-field minimisation. The institutional chain uses explicitly synthetic, isolated evidence fixtures; it does not claim an R2 upload, malware scan or live institutional approval.

The suite's 111 supplied implementation acceptance cases remain **NOT_RUN**. PostgreSQL-specific concurrency/trigger tests, browser/accessibility/device tests, real email/storage/scanner receipts, backup/restore and live end-to-end qualification have not run.

## Cloud access at the initial implementation review

The access failures in this section were subsequently resolved using the supplied credentials; see the release record for the successful migration, deployment, provider checks and invitation receipt.

Vercel account access initially succeeded and returned the existing LoveWorld projects. Subsequent approved shell calls failed DNS resolution or connection checks for Vercel, Neon and Resend. No new production project, migration or deployment is asserted. The new release's configuration phase has not been applied. No administrator invitation has been sent.

Vercel and Neon integrations were discovered as available but unconnected and offered as an alternative cloud route. Connection has not been confirmed. The administrator nominated by the user is Emmanuel Patrick, `epatrick@prolificintelligence.co`; the bootstrap command is ready to create and send the real invitation after the cloud release and verified email configuration succeed.

Actual adopted affiliation criteria, complete Directorate organisation authority, a reachable scanner and country/facility clinical activation packages remain operating dependencies. The [organisation research report](../CHRIST_EMBASSY_ORGANISATION_RESEARCH.md) records eight public-source findings and their limits. These are not seeded authorities or a complete roster.

## Migration, release and rollback

1. Restore working cloud access or confirm the Vercel/Neon connections. Run `scripts/platform_cloud_release.py inspect`; verify project scope and actual verified sender domain.
2. Run `configure` to prepare gitignored `.env.platform.local` and encrypted production settings. No credentials belong in source control. Configure the real private scanner before evidence uploads can be accepted.
3. Run `migrate` against the intended Neon database. It creates only the separate `health_platform` schema and does not seed facilities, clinicians, criteria or pricing. Verify the PostgreSQL constraints, append-only triggers, backup/restore and concurrency before release acceptance.
4. Deploy API and web source with `deploy --target api` and `deploy --target web`; poll each exact deployment identifier and exercise real health/readiness/authentication.
5. Bootstrap the nominated administrator using `lw_care_api.platform.cli bootstrap` with explicit email, name and access expiry. Inspect provider receipt; confirm enrolment, MFA and real browser sessions. Do not report the invitation delivered solely from queue/provider acceptance.
6. Rehearse registration/review/publication with actual authorised staff and adopted criteria before accepting the milestone. Continue the complete clinical/reporting/finance/AI/local-runtime scope rather than treating this increment as a scope reduction.

Rollback restores the previous Vercel routing/version. Preserve the additive schema, source evidence and retained history; do not drop tables or erase records. The legacy Care deployments were not replaced by this workspace work.
