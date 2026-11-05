---
document_id: "LWH-DOC-001"
title: "Documentation control, terminology and traceability"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Documentation and product lead"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-DOC-000"]
source_refs: []
directive_refs: []
---

# Documentation control, terminology and traceability

## Normative use

MUST denotes a build or operating requirement for the stated scope. SHOULD requires an explained exception. MAY denotes an option. CONFIRMED_PRODUCT_DECISION records the user's direction; SOURCE_SUPPORTED identifies a reference-supported design area; PROPOSED_POLICY records a concrete candidate local rule; ACTIVATION_DEPENDENCY records a decision/evidence item required before live use. Only a signed adoption record establishes an approved policy.

## Identity and references

Document IDs remain LWH-DOC/STR/DIR/BRD/ARC/STD/GOV/PRD/SPEC/ENG/OPS/COM. Requirement IDs are `<document-id>-Rnnn`; local acceptance cases are `<document-id>-ATnnn`. Forms use LWH-FRM-nnn, fields append `.Fnnn`, screens use LWH-SCR-nnn, journeys LWH-JRN-nnn, metrics LWH-MET-nnn, commands LWH-API-nnn, events LWH-EVT-nnn, states LWH-STM-nnn and country parameters LWH-CFG-nnn. Existing DHS-REQ and LWC references retain their original meanings; new requirements supersede only the explicitly documented scope.

Every implementation ticket includes requirement IDs, owner, actor/subject/facility, inputs, outputs, permissions, authoritative node, state guards, failure behaviour, offline behaviour, metric impact and acceptance evidence. Source-supported fields name the source register entry and adaptation scope. Cross-references in Markdown use IDs; manifest.json resolves IDs to paths. Source references are separate from implementation dependencies.

## Canonical glossary

| Term | Definition and boundary |
|---|---|
| Account / actor | Authenticated person or service taking an action; distinct from a patient or payer |
| Patient / subject | Person receiving care, including a dependant with no login |
| Facility / organisation | Facility is a service-delivery site; organisation is an owning, operating or reporting entity |
| Region / zone | Ministry reporting units; geography and legal jurisdiction are separate attributes |
| Affiliation / licence | Network recognition versus statutory/professional authority; neither implies the other |
| Readiness | Time-bounded evidence that a particular service can be delivered |
| Return / event | Period-specific reporting declaration versus occurrence requiring review |
| Encounter / episode | Bounded clinical interaction versus longitudinal care responsibility spanning interactions |
| Anonymous / coded | Anonymous information has no reasonably usable identifying link; protected coded records retain controlled linkage |
| Signed / verified | Signed identifies attestation; verified records the specified check, neither guarantees medical truth |
| Locally committed / synchronised | Durable at the authoritative facility node versus acknowledged by the receiving platform node |

## Control and review

Each file carries owner, status, version, scope, source and dependency metadata. Roles rather than invented individuals are assigned until Directorate nominations exist. Reviewers record exact version, decisions, exceptions and adoption scope. The document lifecycle is AUTHORED → DOMAIN_REVIEW → BASELINED → IMPLEMENTATION_LINKED → VALIDATED → SUPERSEDED. Policy adoption is a separate axis.

An author updates the canonical owner first, then references elsewhere. A changed field meaning receives a schema version and migration mapping; reused labels must not conceal incompatible definitions. Delete neither adverse decisions nor signed historical records to make the current state appear clean. Manifest and traceability are regenerated after changes. Conflicting clinical facts remain visible until an authorised reconciliation.

## Evidence and agent handoff

Keep source citation, adaptation, policy approval, test execution and operational readiness distinct. Demonstration fixtures, screenshots and a successful build are different evidence classes. A final ticket reports changed components, tests actually run, operational dependencies, risks and rollback. Production secrets and identifiable records are excluded from document examples. Examples use synthetic identifiers and contain no dosing instructions.

## Dependency semantics

`depends_on` records the normative reading/reference graph; mutual references are possible and are read once per task context. It is not a topological build scheduler. The ordered implementation dependencies are the LWH-EP epic graph in LWH-ENG-002. An agent must not recursively generate duplicate documents to satisfy a reference cycle.
