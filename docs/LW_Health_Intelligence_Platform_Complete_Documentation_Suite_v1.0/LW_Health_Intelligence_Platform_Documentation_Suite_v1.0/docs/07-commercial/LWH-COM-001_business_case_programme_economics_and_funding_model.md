---
document_id: "LWH-COM-001"
title: "Business case, funding and programme economics"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Directorate finance and programme sponsor"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-PRD-013", "LWH-PRD-022", "LWH-PRD-025", "LWH-SPEC-007"]
source_refs: ["PROJECT-003"]
directive_refs: []
---

# Business case, funding and programme economics

## Leading funding proposal

The Directorate funds the core platform as the institutional health operating/intelligence infrastructure. Care delivery and optional services generate revenue under approved terms. This is the confirmed leading proposal; no budget amount, price, contract, signed funding commitment or revenue forecast is established by this document. The core cannot depend on an uncontracted future care margin to meet its initial clinical/reporting obligations.

## Cost and responsibility model

| Cost pool | Include | Allocation/approval |
|---|---|---|
| Initial platform delivery | Audit, product/design, institutional services, comprehensive EMR/local runtime, integration, security/assurance, testing and documentation | Directorate capital/project schedule with milestone evidence |
| Core recurring service | Hosting/storage/backups, support, monitoring, patching, source/terminology/content maintenance, identity and disaster recovery | Agreed managed-service/core operating budget |
| Directorate operations | Registry/standards, inspections, reporting review, coordination, training, privacy/clinical governance and programme management | Actual ministry/operator staffing and workload |
| Facility deployment | Local compute/storage/LAN/UPS, printing/devices, licences, installation, restore media and site support | Explicit site schedule; owner/funder named before activation |
| Clinical care | Staff preparation/consultation/documentation/results/handover, diagnostics/medicines and coordination | Actual service/provider contracts and care cost model |
| Integration/migration | Source access, mappings, interface work, dry runs, cutover and reconciliation | Facility route-specific scoped cost |
| Intelligence | Per-use inference/retrieval/evaluation and human correction/maintenance | Bounded approved use-case budget; AI-off available |
| Optional enterprise | Accounting/procurement/HR/payroll configuration, licences, local rules and support | Separate entitlement/service schedule |

Optional procurement is distinct from the real project need to purchase infrastructure/services; clinical stock and patient billing are core. Cost attribution must include standby/urgent reserve, asynchronous results, failed-contact work and rural/low-volume readiness rather than only billable video minutes.

## Unit economics and ledgers

`care_contribution = recognised_service_revenue - clinical_delivery_cost - processing_cost - communications_and_AI - variable_support - attributable_quality_refund_cost`.

`programme_contribution = recognised_programme_fee + attributable_care_contribution - coordination - included_review - other_variable_programme_cost`. Included consultations are not counted again as full incremental revenue.

`core_monthly_requirement = central_fixed_cost + approved_site_runtime_support + programme_governance_cost + free_companion_cost + reserve - contracted_core_funding`. Show cash funding, recognised revenue, restricted programme balances and payable liabilities separately. A sponsor deposit is not automatically earned revenue. Managed technical fees and provider costs appear once in their relevant cost pool.

`expansion_gap_services = ceil(unfunded_approved_expansion_cost / positive_care_contribution_per_service)`. This is a sensitivity tool, not permission to offer unsafe volume. If contribution is zero/negative, increasing the same service volume cannot fund the gap.

## Illustrative sensitivity only

All values below are hypothetical currency-neutral units, not market prices, recommended tariffs or a forecast. Assume an approved expansion gap of 30,000 units beyond funded core operations.

| Contribution per completed qualifying service | Services needed |
|---:|---:|
| 20 | 1,500 |
| 30 | 1,000 |
| 40 | 750 |

Capacity must independently support the volume: `clinical_minutes = encounters * total_minutes_per_encounter + results + followup + handover`; `staffed_minutes = clinical_minutes / adopted_productive_utilisation`. Include breaks, uncertainty and urgent reserve. Price/cost scenarios are reviewed against actual clinical workload, access and affordability, not only gross revenue.

## Revenue and patient-access design

Care revenue can include approved consultations, facility services, continuity programmes and payer/sponsor contracts. Optional services can include enterprise modules, additional managed integration/support and approved institutional services. No fee amount or affiliation charge is assumed approved. Standards decisions remain independent of commercial payment. Clinical urgency and essential emergency guidance are independent of entitlement balance; users see clear prices, coverage, pending payer decisions and support options before chargeable commitments.

## Financial control and pilot evidence

Adopt price books, recognition/cost policy, tax/payer rules, limits, refunds, cancellation, write-off, provider pay and independent approvals per country/operator. Use balanced append-only ledgers and actual provider/cash/remittance evidence. Reconcile every service/benefit/charge/receipt/claim/posting. Offline allowances are allocated to a single spending authority. Never advertise custodial escrow/insurance arrangements without applicable assessment and terms.

Pilot evidence includes actual workload/cost per workflow, local deployment/support burden, free-companion cost, payment/claim failures, reconciliation age, unused benefits, refunds and patient affordability/access. Finance reviews the core funded runway and optional/care contribution separately. Expansion decisions require committed funding and verified operating capacity; no universal profitability claim is made.
