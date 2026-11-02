# ADR-0005: SponsorCare read-model isolation (k ≥ 5)

- **Status:** Accepted
- **Date:** 2026-11-01
- **Spec refs:** §10.5, §13.1, §16.2, AT-06, AT-14

## Decision

1. Sponsor routes accept only `aud=lwc:sponsor` tokens, plus `aud=lwc:command` tokens holding `FINANCE_CONTROLLER`.
2. A sponsor token MUST carry `org` = the sponsor's `sponsor_id`. A sponsor can read only agreements whose pool `sponsor_id` equals `org`. Requests for other agreements return the same 403 as a missing agreement, so agreement existence is not revealed.
3. Sponsor responses come only from aggregate ledger and analytics projections. Counts below `sponsor_small_cohort_min_k` are suppressed. At the database level, the sponsor role has `SELECT` only on the `analytics` schema views, with no grant on `care_clinical`.
4. Sponsor routes never return patient identifiers, intake text, diagnoses or notes. Contract tests assert this.

## Consequences

- The previous unauthenticated `/v1/sponsor/pools/{id}/report` is closed.
