---
document_id: "LWH-ENG-007"
title: "Existing EMR integration, migration and cutover"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Migration lead, records custodian and facility clinical director"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-ENG-001", "LWH-SPEC-012", "LWH-SPEC-017", "LWH-SPEC-020", "LWH-GOV-004"]
source_refs: []
directive_refs: []
---

# Existing EMR integration, migration and cutover

## Facility-by-facility route selection

Route A retains the existing EMR and exchanges approved institutional reporting and scoped clinical summaries/orders/results according to capability. Route B migrates to the LW facility EMR. Hybrid departmental adapters are allowed with explicit data/write authority. Assess service fit, licences/contracts, data custody, technical interfaces, local continuity, support and staff readiness before selecting. Participation in institutional reporting does not require native EMR adoption.

## Discovery and mapping

Inventory real/synthetic records, patient/external IDs, signed notes/addenda, episodes/encounters, active medicines, allergies, results/orders, referrals/pending tasks, ADT/beds, maternal/infant links, stock lots/movements, invoices/receipts/claims/benefits, grants/consents and audit. Record source schema/status/code/unit/time semantics and retention. Obtain legitimate source access/purpose and safe working environment. Preserve original signatures/attestation with verified/unknown validity; an importer must not impersonate the historical clinician.

## Route A: integration qualification

Create partner capability/profile, data agreement, identifiers and reviewed mappings. Test direct/bulk/API feeds with per-row outcomes. Define authoritative indicator and clinical source so an extract plus manual return is not added twice. Validate minimal/partial/corrected data, wrong patient, unavailable adapter, retries, offline store-forward and amendment propagation. Clinical records remain in source custody; scoped copies preserve provenance and access authority.

## Route B: migration rehearsal

Extract immutable source snapshots/checksums, transform through versioned mappings and load into isolated staging. Quarantine unresolved identity/unit/status conflicts. Reconcile record counts, links, signed/addendum histories, active clinical tasks, orders/results, medication intent/actual events, stock balances and financial ledger groups. Clinical/custody/finance owners sample meaningful cases, not just row totals. Train actual staff with the target workflow and test local WAN-offline operation and restore.

## Cutover procedure

Agree downtime/manual care, communications, actual roster and stop/go evidence. Freeze/fence the relevant source writer, take a final delta and backup, apply/reconcile, assign the new authority epoch and verify identity/credentials/departments/open-care tasks. Activate the qualified facility scope, monitor real transactions and maintain accountable support. Avoid independent clinical dual writes; read-only shadow comparison is acceptable with controlled purpose.

## Rollback and exit

Trigger rollback/containment on defined integrity/safety failures. Preserve all actual post-cutover clinical/financial work; do not overwrite it with an older backup. Export/replay/reconcile under the chosen authority and accepted custody. If returning to the old EMR, it must receive and validate new work before resuming authority. Old node epochs remain fenced. Supplier exit delivers usable records, source/code/version mappings, audit/consent and outstanding responsibilities, with contractually defined retention/deletion.

## Acceptance evidence

Record mapping versions, data authority, full input/output accounting, sampled clinical/financial correctness, unresolved exceptions, interface tests, user competence, local continuity, restore and approved cutover decision. No migration is claimed executed by this suite. Unknown existing systems are assessed through this procedure instead of guessed compatible.
