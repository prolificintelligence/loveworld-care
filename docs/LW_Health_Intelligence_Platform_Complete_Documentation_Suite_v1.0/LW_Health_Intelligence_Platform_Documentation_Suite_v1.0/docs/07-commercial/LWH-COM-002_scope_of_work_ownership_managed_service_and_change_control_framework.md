---
document_id: "LWH-COM-002"
title: "Scope of work, ownership, managed service and change control"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Directorate sponsor and Prolific Intelligence delivery lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-DOC-000", "LWH-ENG-002", "LWH-ENG-004", "LWH-COM-001"]
source_refs: ["PROJECT-003"]
directive_refs: []
---

# Scope of work, ownership, managed service and change control

## Statement-of-work purpose

Use this framework to agree a build/operate engagement for LW Health Intelligence Platform. The product direction is confirmed; contracting entities, prices, dates, IP/licence terms and responsibilities require written agreement. Existing Care work is audited for reuse rather than assumed discarded or already compliant.

## Deliverables and acceptance schedule

| Work package | Concrete deliverable | Acceptance basis |
|---|---|---|
| Foundation/audit | Verified source/deployment/data inventory, hierarchy, reuse ADRs and baseline contracts | ENG-001; named owners and explicit unknowns |
| Institutional core | Registry, standards/inspection/central decision, reporting/events/verification, leadership/action/education/referral workflows | Director mandate UAT and approved policy/definitions |
| Clinical core | Comprehensive EMR across enabled clinic/inpatient/maternal-child/diagnostic/procedural services, patient/clinician experience and care finance | Core clinical PRDs and integrated UAT |
| Local continuity | Facility runtime, department adapters, strong local auth, full WAN-offline workflows and safe sync | SPEC-017 qualification, restore and reconciliation |
| Adoption/integration | Existing-EMR integration or migration, training, country/facility activation evidence and support readiness | ENG-007; OPS-007; scoped release decision |
| Managed operations | Monitoring, support, maintenance, backup/restore, incident/reconciliation and controlled updates | Agreed SLO/support/custody schedule |
| Optional enterprise | Accounting/procurement/HR/payroll only when contracted | Independent module acceptance; core care unaffected |

Milestones attach payment/acceptance to evidenced outputs, not screen count. The full confirmed first-implementation clinical scope remains explicit even if milestones deliver increments. Estimates follow audit and agreed team/scope/country/site assumptions. No deadline or funding receipt is claimed here.

## Responsibility demarcation

Directorate: institutional mandate, hierarchy/criteria/reporting adoption, central affiliation decisions, core funding and nominated governance. Clinical operator/facilities: professional authority, care decisions, actual staff/equipment/readiness, local operations and clinical content adoption. Privacy/records owners: processing authority, custody, sharing/retention and jurisdiction review. Prolific Intelligence: agreed technical/product delivery, integration, maintenance and evidence within contract. Third-party providers: their actual service/interface/licence commitments. Technical delivery does not automatically make Prolific Intelligence the clinical operator.

## Ownership and licence schedule

Explicitly agree ministry product/brand rights, customer data/custody, bespoke deliverables, Prolific pre-existing platform/tooling/IP, third-party/open-source components, source access/escrow if applicable, deployment rights, maintenance and exit portability. Do not infer ownership transfer or unrestricted patient-data use from payment. Data is not model-training material without a separately approved purpose. Check source instrument/terminology commercial-use terms before embedding content.

## Managed service schedule

Specify central and site responsibilities, staffed support hours/response, measured SLOs, facility hardware/UPS/LAN, backup/RPO/RTO, local credential/certificate/packages, vendor dependencies, security maintenance, incident notices, reconciliation, capacity growth, source updates and recurring fees. Distinguish cloud, site, clinical and external-provider failures. No unsupported unlimited free support/care promise or zero-loss site-disaster claim.

## Change, acceptance and exit

A change request names affected IDs, reason, source/policy, benefit, scope/cost/time, migration, offline compatibility, training, tests and rollback. Authorised parties decide and version the baseline. Coordinate policy/domain reviews through a single gate evidence pack where practical rather than dozens of disconnected approvals. Disputed acceptance uses objective evidence and an agreed cure/review process. Exit includes usable records/source mappings, open care obligations, keys/access transition, retention/deletion, code/licence handover and support continuity under signed terms.
