---
document_id: "LWH-PRD-025"
title: "Optional accounting, procurement, HR and payroll"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Enterprise service and facility finance owners"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "optional-enterprise"
depends_on: ["LWH-BRD-001", "LWH-SPEC-001", "LWH-SPEC-003", "LWH-SPEC-004", "LWH-SPEC-006", "LWH-SPEC-009", "LWH-COM-001", "LWH-SPEC-021"]
source_refs: ["PROJECT-003"]
directive_refs: []
---

# Optional accounting, procurement, HR and payroll

## Purpose and service result

Provide optional enterprise administration without making it a prerequisite for care, clinical stock, clinical staffing or patient billing. Separate entitlement, data access and financial/local-law configuration apply to each module.

**Primary users:** Accountants, procurement staff, HR/payroll teams, approvers and technical integration stewards. **Accountable product/operating owner:** Enterprise service and facility finance owners. The module is complete only when its downstream responsibility is accepted or its stated final result has evidence. Navigation, loading/empty/stale/error/denied/conflict behaviour and accessibility follow LWH-SPEC-001; entity, form and state definitions are canonical in LWH-SPEC-004/006/009.

## Functional requirements

| Reference | Requirement | Required behaviour | Verification |
|---|---|---|---|
| LWH-PRD-025-R001 | Independent modules | MUST independently enable accounting, procurement, HR and payroll by contracted facility/organisation. | Disabling ERP leaves core clinical and care-finance functions usable. |
| LWH-PRD-025-R002 | Accounting | MUST support chart of accounts, journals, AP/AR, cash/bank reconciliation, budgets, periods and controlled close. | Every posting group balances per currency and retains source linkage. |
| LWH-PRD-025-R003 | Clinical posting interface | MUST consume care-finance journals idempotently with acknowledgement and difference reports. | Accounting failure cannot block care billing or duplicate revenue. |
| LWH-PRD-025-R004 | Procurement | MUST support requisition, approvals, supplier/quotation, purchase order, receiving and invoice matching. | Procurement receipt creates an authorised stock movement rather than rewriting clinical dispensing history. |
| LWH-PRD-025-R005 | HR | MUST support employment records, contracts, assignments, leave and attendance under scoped access. | An HR job title alone cannot grant clinical privileges. |
| LWH-PRD-025-R006 | Payroll | MUST version country/employer pay rules, approved inputs, calculation, review, payment file and posting. | No invented universal tax/pension deductions are activated. |
| LWH-PRD-025-R007 | Segregation | MUST separate supplier/employee maintenance, approval, payment and review with reasoned exceptions. | A user cannot silently create and pay a beneficiary under incompatible duties. |
| LWH-PRD-025-R008 | Privacy and integration | MUST keep salary/employment information separate from patient charts and executive health aggregates. | An exported clinical report contains no payroll details. |

## Screen contracts

| Screen | Purpose | Visible content / inputs | Primary actions | Failure and recovery |
|---|---|---|---|---|
| LWH-SCR-073 | Enterprise module administration | Contracted modules, scope, country configuration and readiness | Enable qualified module, set approvers or suspend | Missing country/payroll rules prevent payroll activation only |
| LWH-SCR-074 | Finance and procurement workbench | Journals, periods, invoices, requisitions, orders and receiving exceptions | Post, reconcile, approve, receive or close | Unbalanced/duplicate/unapproved actions are blocked with retained source |
| LWH-SCR-075 | People and payroll workbench | Employment, leave, attendance, pay-run inputs, deductions and approvals | Prepare, review, approve or export payment instructions | Payroll lock/conflict preserves the last approved run and requires review |

Every screen displays the active facility/subject or administrative scope. Destructive or consequential actions require the applicable role and server-side state guard; hiding a control is insufficient. Dates show the relevant local time zone. Reuse previously verified information with a freshness check instead of repeating onboarding.

## End-to-end journey

An organisation contracts and activates the relevant optional module, imports approved master data and configures local rules. Operational users prepare transactions, independent approvers authorise and finance reconciles actual receipts/payments. Clinical events post through idempotent interfaces. Payroll uses approved jurisdiction/employer rules and preserves each reviewed run and payment result.

## Operational responsibilities and exceptions

Enterprise owners adopt financial/procurement/HR/payroll policy and jurisdiction rules; technical stewards reconcile interfaces; facility clinical leads retain independent clinical staffing and privilege authority. Pricing/support and data custody are separately contracted. Any vendor ERP adapter is tested against these functional contracts rather than assumed correct.

## Offline and integration behaviour

Core care continues independently. Optional ERP local operation is a separately qualified deployment option with single-writer and reconciliation rules. Bank settlement, supplier acceptance and statutory submission remain pending until actual confirmation; payroll rules cannot be guessed during disconnection.

## Acceptance cases

| Reference | Scenario | Exercise | Expected result |
|---|---|---|---|
| LWH-PRD-025-AT001 | ERP disabled | Run complete care and clinical stock/billing with optional modules disabled. | Core work remains fully usable. |
| LWH-PRD-025-AT002 | Journal replay | Replay a care invoice posting and its acknowledgement. | One balanced journal is recognised with source reconciliation. |
| LWH-PRD-025-AT003 | Payroll rules absent | Attempt a payroll run without an adopted country package. | No guessed deductions/payments occur; other modules continue. |

These cases are specifications, not executed tests. LWH-ENG-003/004 add cross-module, permission, concurrency and operational evidence. Release requires the exact deployed configuration, staff readiness and relevant country/facility approval.

## Measures and build handoff

Track optional-module adoption, posting differences, unmatched receipts, approval exceptions and pay-run accuracy against approved rules. Definitions, coverage and exclusions are controlled in LWH-SPEC-007. The feature ticket references the requirement IDs above, canonical data/forms/states/APIs, owner, authority node, error recovery, telemetry and acceptance evidence. Module-specific defects must be resolved rather than hidden by an aggregate task-success score.
