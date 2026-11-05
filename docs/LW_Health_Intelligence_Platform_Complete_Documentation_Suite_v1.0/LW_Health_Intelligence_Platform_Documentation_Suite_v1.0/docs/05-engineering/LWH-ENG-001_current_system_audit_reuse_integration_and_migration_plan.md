---
document_id: "LWH-ENG-001"
title: "Existing-system audit, reuse and integration plan"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Engineering lead and existing Care maintainers"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-ARC-001", "LWH-SPEC-017", "LWH-ENG-007"]
source_refs: ["PROJECT-002", "PROJECT-003"]
directive_refs: []
---

# Existing-system audit, reuse and integration plan

## Audit purpose and evidence status

Retain useful LW Care development and connect it to the broader platform through verified reuse decisions. Historical user-supplied surfaces include patient entries at loveworld-care.vercel.app and loveworld-care-patient.vercel.app; clinician, command, sponsor and API deployments under the corresponding loveworld-care-* domains. They are integration candidates, not architecture boundaries. This documentation task did not inspect current repositories or verify backend/runtime claims; historical interface observations are not current deployment evidence.

## Required inventory

| Area | Evidence to collect | Decision/result |
|---|---|---|
| Source/deployment | Repository, branch/commit, build, environment, owner and dependency inventory | Trace each live surface to exact source |
| Routes/screens | Patient/clinician/command/sponsor entry paths, auth gates, fixtures and shared components | Canonical routes and workspace reuse map |
| Identity/permissions | Account/subject/family/professional models, sessions, RBAC/object/field checks | Preserve compatible identities; close insecure gaps |
| Clinical workflow | Intake, notes, orders/results, referrals, signatures and tasks | Verified capabilities versus scaffolds/demo behaviour |
| Database/files | Actual schema, migrations, real/synthetic data, custody, backups and objects | Safe migration/integration and retention plan |
| APIs/integrations | Runtime endpoints, persistence, provider receipts, video/messages/payment | Actual end-to-end proof and error behaviour |
| Finance | Ledger, entitlement, balance, payout and reconciliation controls | Preserve historical truth and identify missing invariants |
| Intelligence | Tools, prompts, data scopes, source/model versions, evaluations | Governed reuse; no unverified safety claims |
| Operations/security | Secrets, observability, CI/CD, access, incidents and restore | Remediation and release prerequisites |
| Local runtime | Existing deployability on facility LAN, dependencies and offline behaviour | Reuse versus extraction/rebuild decision |

## Audit method

Read source and trace one synthetic end-to-end task through UI, authoritative API, database, jobs and audit. Test negative permissions and dependency failure. Inventory mocks/fixtures explicitly; determine whether each environment contains real records before moving/deleting anything. Do not assume all data is synthetic because one screen says demo. Evidence records exact commit/configuration and observed limitations.

## Reuse decision categories

REUSE_AS_IS where behaviour/tests satisfy the new contract; ADAPT where bounded changes preserve data/identity; EXTRACT_SHARED where duplicated services become a canonical component; REPLACE where authority/clinical/finance invariants cannot be safely met; RETIRE_ROUTE after compatibility redirects/export/custody are addressed. Record requirement IDs, rationale, migration/rollback and owner for every decision.

## New direction mapping

Existing patient experience maps to My LW Health Care; clinician work to LW Care Clinical Workspace; command work to LW Health Command plus distinct Leadership/Coordination/Facility views; sponsor work to LW Health Programmes. The facility EMR and local runtime are explicit expanded scope, not assumed features of an existing triage page. Preserve account links where valid, choose canonical patient entry/redirects and avoid duplicated login or competing clinical truth.

## Deliverables and acceptance

Produce source/deployment inventory, capability evidence matrix, data/fixture map, security/control findings, integration/reuse ADRs and an incremental migration backlog linked to the suite. Audit completion requires evidence for each claimed reusable feature and a disposition for unknowns. Actual repository access, live credentials and production mutations are separate implementation work; this plan does not claim they were performed.
