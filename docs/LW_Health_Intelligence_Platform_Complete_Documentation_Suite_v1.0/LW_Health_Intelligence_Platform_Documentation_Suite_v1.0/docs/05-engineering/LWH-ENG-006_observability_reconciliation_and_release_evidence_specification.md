---
document_id: "LWH-ENG-006"
title: "Observability, reconciliation and release evidence"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Platform observability and clinical operations leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-SPEC-007", "LWH-SPEC-011", "LWH-SPEC-015", "LWH-OPS-005"]
source_refs: []
directive_refs: []
---

# Observability, reconciliation and release evidence

## Observability layers

Monitor infrastructure/service health, domain workflow integrity, data freshness/reconciliation and human operational fulfilment separately. Central availability cannot prove a facility is providing care; a disconnected facility can remain locally operational. A completed HTTP call cannot prove clinical acknowledgement, external settlement or referral acceptance.

## Signals and owners

| Layer | Required signals | Owner |
|---|---|---|
| Facility infrastructure | Local API/database/storage, LAN/UPS, backups, certificate/key/package validity, clock | Local technical/platform team |
| Central services | Latency/error/capacity, jobs/integrations, storage and authority availability | Platform on-call |
| Clinical workflow | Unclaimed/overdue care, unreviewed critical results, missed handover, stale order/admin conflict | Duty clinical leads |
| Network/standards | Stale readiness, declined/unreceived referrals, overdue evidence/renewals | Network/standards |
| Reporting/analytics | Missing/partial/late units, verification age, correction runs, coverage/freshness | Information owner |
| Sync | Outbox age/size, per-item outcomes, missing dependencies, conflicting hashes/epochs | Sync/data stewards |
| Finance/stock | Unbalanced/unmatched groups, duplicate keys, outstanding reservations, provider/payer differences | Finance/pharmacy |
| AI | Unsupported facts, correction burden, tool denials, drift, latency/cost and fallback | AI/clinical governance |

## Telemetry and audit

Use correlation/causation IDs across UI/API/jobs/receipts. General logs/metrics contain minimum operational identifiers and no patient narrative, credentials, payment secrets or raw documents. Protected audit separately records actor, resource/subject, purpose, authority/policy/version, action, outcome and before/after references under retention/access controls. Access to audit is itself scoped and logged. Tamper evidence is tested; absolute immutability is not claimed.

## Alerts and escalation

Every alert identifies severity, owner, actual impact, runbook, acknowledgement and fallback. Deduplicate noisy alerts without suppressing unresolved clinical responsibility. Cover unowned urgent work, critical result review, storage/backup failure, grant/package expiry, abnormal access and ledger/stock integrity. Actual service response commitments use adopted staffing; no empty on-call contact qualifies. Alert delivery is not incident closure.

## Reconciliation and evidence packs

Daily/periodic reconciliation accounts for origin events, domain revisions, outbox/inbox receipts, clinical tasks, reports/snapshots, stock movements, benefit allocations, provider receipts and optional GL postings. Preserve counts and explained differences. Release packs include code/configuration/content/model versions, requirement/test results actually executed, hazard/defect dispositions, access/disclosure review, outage/restore evidence, actual roster/readiness, funding and approvals. Operational reviewers sign the facts they examined, not an unexplained green dashboard.

## Acceptance

Inject failed dependencies, delayed critical tasks, corrupted sync identity, missing backup and duplicate finance event. Verify the right owner receives actionable information without protected leakage. Restore a release in isolation, reconcile source/domain/output totals and recover open care obligations. Record limits honestly, including site-loss exposure during a WAN partition.
