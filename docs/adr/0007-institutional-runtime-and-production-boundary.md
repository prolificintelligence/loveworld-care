# ADR-0007: Institutional runtime and production boundary

Date: 2026-11-05. Implementation in progress; live deployment and qualification are not yet evidenced.

The new LWH suite supersedes the Care-led product framing. The existing Care runtime uses process-local clinical, session, finance and audit structures and advertises an email magic-link delivery that does not contact an email provider. The new institutional workflows must not inherit those behaviours.

The institutional runtime lives in `services/api/src/lw_care_api/platform`, using PostgreSQL schema `health_platform`. The existing API entrypoint selects it only with `LWH_RUNTIME=institutional`; the legacy `/v1` runtime remains separate. A dedicated Vercel API project and Next.js workspace are the intended deployment units. This is an increment towards the full platform, not an assertion that all 25 PRDs are implemented.

The API has no demo bootstrap endpoint, client-supplied role authority, in-memory operational repository or successful fallback when PostgreSQL/provider access fails. Production requires a real PostgreSQL connection, separately provisioned encryption key, exact HTTPS application origin, authority-node identifier and job authentication secret. Migrations are explicit release operations, not application-startup seed operations. No example clinicians, facilities, protocol approvals, prices or criteria are inserted.

Opaque sessions and grants are resolved from storage on each request, including idempotent receipt replays. Browser sessions use secure, HttpOnly, SameSite cookies and origin checks. Passwords use salted PBKDF2 with 600,000 rounds; staff enrolment requires a time-based authenticator, encrypted at rest with AES-GCM, with persisted counter checks to reject replay. Account/grant revocation survives process replacement. Clinical access is outside the institutional runtime and cannot be obtained through administrative seniority.

Facility and application mutations commit versioned state, retained revisions, audit and outbox atomically. PostgreSQL row/advisory locks and uniqueness guard concurrent updates and idempotency. Evidence is private, bounded, checksum-verified and accepted only after a real ClamAV scan. File storage and database commits are separate resources; orphan-object reconciliation still needs qualification. Final affiliation is a central, independent decision after inspection/recommendation; directory publication is separate. Readiness is never inferred from affiliation.

Invitations are transactional outbox work delivered through Resend with an idempotency key and stored provider receipt. “Queued” and “provider accepted” are distinct; delivery to the recipient's mailbox is not claimed without evidence. The initial administrator nominated by the user is Emmanuel Patrick, epatrick@prolificintelligence.co. No invitation has been sent merely by recording that nomination.

The global Region → Zone roster remains an authority input. Public church-source research is retained with source and confidence, never silently promoted into adopted Directorate scope. Country/clinical activation, comprehensive EMR, facility-local offline operation, full reporting/intelligence, existing-EMR migration and optional enterprise modules retain their suite scope. They are not supplied by this institutional increment.

Rollback removes routing to the new runtime and restores the prior Vercel deployment. Retain the new schema, object evidence and event history for custody and forward migration; rollback must not drop those records or restore competing writers. Initial migration is additive in a separate schema; actual Neon installation, concurrent-process proofs and backup/restore remain release gates until executed.
