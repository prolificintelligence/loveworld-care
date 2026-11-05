---
document_id: "LWH-ENG-005"
title: "Environments, CI/CD, release and rollback"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Release engineering and platform leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-ENG-001", "LWH-ENG-003", "LWH-ENG-004", "LWH-ENG-006", "LWH-SPEC-017"]
source_refs: []
directive_refs: []
---

# Environments, CI/CD, release and rollback

## Environment contract

Separate developer, automated test, demonstration, staging, qualified pilot and live environments with distinct identities, data, secrets, storage and provider endpoints. Demonstrations use synthetic fixtures and visible mode. Production cannot fall back to demo responses or role flags. Country/facility scope and clinical enabling are configuration evidence, not merely a URL name.

## Build and assurance pipeline

Validate source/dependency/licence inventory and secrets; lint/type/build as appropriate to the audited stack; validate schemas/contracts and migrations; run meaningful domain/permission/concurrency/integration tests; execute relevant UI/accessibility and fault/continuity suites; produce signed/checksummed release artefacts and evidence. Clinical/model/content updates have their own version/review/evaluation pipeline. No framework/vendor choice is assumed verified before ENG-001 audit.

## Data and schema migration

Use reviewed forward migrations with backups, dry runs, reconciliation and compatibility strategy. Preserve signed/addendum records, identity crosswalks, grants, audit, stock and ledger history. Support approved mixed versions of local nodes during a rollout; incompatible messages are quarantined with recovery instructions rather than silently dropped. Expand/contract changes avoid making disconnected nodes corrupt current data. A changed field meaning requires explicit mapping/version.

## Deployment and local packages

Release packages include code, schema, configuration, forms, terminology/content, trust material and compatibility manifest. Verify provenance/hash, resource capacity and required approvals. Stage one qualified facility/cohort before expansion. Local nodes install atomically with current data backup and rollback; certificate/key/role packages have planned lifecycle. Clinical service activation and software deployment are separate commands and authorities.

## Rollback and containment

Feature flags can restrict a failing capability while preserving core/manual care. Code rollback must remain compatible with already committed data. Never restore an older database over new clinical/financial events as a routine rollback. Preserve/export/replay and reconcile actual post-cutover work under the approved plan. Fence competing authority nodes and retain original epoch/source history. An AI/model rollback does not remove clinician-signed work.

## Release evidence and operations handoff

Record exact source/configuration/content/model versions, tests executed, migrations, backup/restore, known limitations, rollback triggers, contacts, staffed support and required approvals. Monitor local health and central receipt separately. After deployment, reconcile representative clinical/reporting/finance transactions and open obligations before declaring success. No actual deployment or production migration is performed by this documentation suite.
