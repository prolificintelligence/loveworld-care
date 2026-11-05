---
document_id: "LWH-SPEC-019"
title: "Clinical terminology, medicines and specialty data contracts"
version: "1.0.0"
issued: "2026-11-05"
timezone: "Africa/Lagos"
platform: "LW Health Intelligence Platform"
prepared_by: "Prolific Intelligence"
project_lead: "Pastor Emmanuel Patrick"
owner_role: "Clinical terminology and medication-safety leads"
document_status: "authored_design_baseline"
institutional_policy_status: "proposed_pending_authorised_adoption"
implementation_status: "not_verified_by_this_document"
scope: "core"
depends_on: ["LWH-STD-001", "LWH-SPEC-006", "LWH-GOV-002"]
source_refs: ["LWH-SRC-018", "LWH-SRC-019", "LWH-SRC-020", "LWH-SRC-021", "LWH-SRC-039", "LWH-SRC-040"]
directive_refs: []
---

# Clinical terminology, medicines and specialty data contracts

## Terminology service

Every coded fact carries system, code, display, version, mapping/provenance and clinical verification status where applicable. Store original local coding alongside approved mappings. Retired or unmapped codes remain interpretable and enter stewardship; do not silently replace them with a similar term. Pin packages and record their exact licence/edition/applicability. A display string alone is not an interoperable clinical code.

| Domain | Reference approach | Required local adaptation |
|---|---|---|
| Conditions/mortality | Applicable ICD classification for reporting; clinical terminology where licensed | Country/programme adoption, case definitions, confirmed/suspected and cause-of-death authority |
| Detailed clinical concepts | SNOMED CT where licensed/applicable or approved local vocabulary | Edition/territory rights, extensions, mapping review and version |
| Tests/observations | LOINC where suitable, preserving local order/test catalogue | Exact analyte/property/system/method mapping; no guessed equivalence |
| Units | UCUM-compatible coded units where applicable | Dimension/precision and permitted conversion; original units retained |
| Medicines | Country formulary/product catalogue with ingredient/form/strength/route | Local regulatory/product codes, substitutions, availability and clinical safety content |
| Images | DICOM identifiers/metadata and authorised study references | Patient/accession mapping, archive conformance and privacy |

## Observation and allergy semantics

Observation has code, typed value or explicit absent reason, unit, actual effective time, method, source and status. Composite values use defined components rather than an ambiguous free-text number. Reference ranges/critical thresholds depend on laboratory method, age/context and adopted policy. Conversions use approved deterministic mappings with dimensional checks and preserve source precision; AI cannot infer missing units.

Allergy/intolerance distinguishes unknown, not-assessed, none-known and known. Known records retain agent, reaction, severity/criticality where known, certainty, source and status. The absence of rows is not a negative finding. Problem lists distinguish tentative assessment, confirmed diagnosis, historical/resolved condition and entered-in-error. Patient-reported facts remain attributed until reviewed.

## Medication data and calculations

Prescribed, patient-reported, dispensed and administered medicines are separate records. Dose, strength/concentration, volume, frequency/timing, duration, quantity and route are distinct fields. Use exact decimal/unit representation and approved rounding. Paediatric weight-based, infusion and other calculation functions require current source measurements, unit conversions, formula/version, limits, intended-use review and prescriber confirmation. No calculator/limit is enabled with a guessed formula or stale required input. Store the calculation inputs/output/review where used.

Interactions, contraindications, high-alert checks, controlled-drug rules and substitutions are versioned clinical/regulatory packages with licensing and human authority. Unavailable checking never produces a reassuring successful result. Clinicians/pharmacists can follow the adopted manual workflow and document the appropriate decision; the platform does not independently prescribe.

## Maternal/newborn/child and programme records

Pregnancy dating retains source and uncertainty. Maternal episodes and each infant chart have distinct identities/permissions. Birth outcomes, maternal/newborn reviews and immunisations record actual events and responsible staff. Growth/vaccine recommendations use an adopted schedule/reference version and required age/measurement context; no globally assumed schedule. Chronic programmes define goals, baseline/follow-up measures and meaningful missingness rather than an unsupported universal health score.

## Source and licence control

WHO/HL7/terminology sources support curation but do not establish local clinical authority. LOINC is available under its stated licence; SNOMED CT rights depend on applicable licensing arrangements; WHO material can have noncommercial/share-alike and adaptation terms. Record actual permissions before embedding/reproducing content in commercial services. This suite creates project field/process contracts and does not reproduce complete protected clinical instruments or claim endorsement.
