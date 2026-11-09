# Scoped discovery and clinical projection readiness

Date: 9 November 2026. Status: implemented; deployment evidence is recorded separately.

The November audit found permission checks after capped Directorate queries, recipient limits applied to joined grants, and a global clinical projection check in facility-specific operations. These could hide eligible work or make an unrelated facility unavailable.

## Decisions

- Apply scope, actor and protected-case restrictions in SQL before paging. Safety cases, actions, quality, exceptions and retained return history use ordered keyset pages with an ID tie-breaker and an explicit continuation. Each request resolves current authority again. A cursor is a navigation position, never an authorisation token.
- Page eligible accounts, not joined grants. Reporting recipients require current overlapping assignments derived from the actual hierarchy, without depending on the capped scope picker. Clinical staff search aggregates current privilege capabilities/services only after selecting the account page. Invited candidates visible to a governor acquire no chart authority from being listed. Existing command-time authority checks remain authoritative.
- Lists are live views, not frozen snapshots. After edits, handovers, due-date changes or changes of authority, refresh the list from its beginning. Keyset continuation prevents gaps caused by tied sort values in an unchanged result set; it does not promise a historical snapshot while the underlying work changes.
- A facility command/board checks source records belonging to that facility **or projections claiming that facility**. An incorrectly assigned projection blocks both affected facilities. An unrelated stale record does not block another facility. Global readiness/reconciliation still reports any inconsistency; version, source, status and kind checks remain enforced. The existing operator rebuild repairs projections from source records; it does not modify clinical facts.
- Browser pagination responses are discarded after context/session changes. Recipient searches reset their continuation when the search changes. Return history is cleared when selecting a different source.
- Authentication emits bounded JSON observations for fixed authentication routes, status, elapsed time and generated correlation ID. Observations omit account identifiers, IP addresses, query strings, headers, credentials, bodies and exception messages. This supports incident diagnosis; it does not establish the cause of the earlier timeout or prove supported-device/network acceptance.

## Validation and limits

Regression cases use isolated synthetic databases for more than 400 mixed-authority cases/actions, 1,200 recipient grants, 220 staff with duplicate privilege rows, 206 source versions/quality records and 205 exceptions. Two activated synthetic facilities exercise source/index corruption, misassigned projections, unaffected chart/worklist access and repair. Separate Neon qualification checks SQL semantics and a bounded 2,500-record projection observation in a disposable schema. The release report records actual results, not this design decision.

No schema migration, policy adoption, clinical activation, additional hosting or offline installation is part of this change. Timely urgent escalation, actual scanner availability, jurisdictional adoption, representative load targets and observed clinician/device acceptance remain separate operating dependencies. Phase 6 patient/caregiver identity and release permissions are the next capability work; staff role grants do not confer personal chart access.
