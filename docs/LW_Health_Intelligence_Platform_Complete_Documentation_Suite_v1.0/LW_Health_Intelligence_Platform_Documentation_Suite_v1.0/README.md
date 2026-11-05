# LW Health Intelligence Platform — Documentation Suite

Version 1.0.0 · 5 November 2026 · Prepared by Prolific Intelligence for Pastor Emmanuel Patrick and the Health Services Directorate.

This is the authored Director-first product, engineering, governance and operating baseline. **LW Care is the care-delivery capability within LW Health Intelligence Platform. My LW Health Care is the working patient application name.** The ministry reporting spine is Region → Zone with optional lower levels; final affiliation decisions are central Directorate decisions.

The first implementation scope includes comprehensive EMR across community/primary care, inpatient hospitals, maternal/child facilities and specialist/diagnostic centres; facilities can retain/integrate an existing EMR or migrate. All enabled core clinical work continues locally during WAN loss and reconciles later. Full accounting, procurement, HR and payroll are optional. The leading funding proposal is Directorate funding for the core, with revenue from care and optional services. Pilot countries remain unselected.

## Contents and status

| Asset | Coverage |
|---|---|
| Controlled authored Markdown documents | 78, including 25 PRDs and 21 shared specifications |
| Director traceability | 20 recording-derived requirements with preserved confidence/status |
| Forms and fields | 51 forms; 355 tagged fields; 52 shared/form JSON Schemas |
| Operational contracts | 75 screens; 20 end-to-end journeys; 74 entities; 45 measures; 30 state families |
| Interfaces | 52 capture routes; 15 consequential command schemas; 15 query families; 35 events |
| Assurance | 200 granular PRD requirements; 75 PRD examples and 36 integrated UAT cases; all implementation cases NOT_RUN |
| Research | 51 official external reference entries plus primary project sources |
| Supporting files | Machine manifest, field/source/requirement/acceptance/traceability registries, capture OpenAPI, schemas, validator and checksums |

These are substantive authored documents, not the earlier outline. Institutional policy proposals and country/clinical/financial adoption dependencies remain explicitly labelled. The suite does not claim the platform has been implemented, clinical protocols approved, integrations qualified or tests executed. No dose/clinical threshold, actual budget, named ministry roster or pilot country is invented.

## Reading routes

| Reader | Recommended route |
|---|---|
| Director / executive sponsor | LWH-STR-001 → LWH-DIR-001 → LWH-BRD-001 → LWH-GOV-001 → LWH-PRD-007/008 → LWH-COM-001 → LWH-ENG-004 |
| Product/design | LWH-DOC-000/001 → module PRDs → LWH-SPEC-001/002/006/009 |
| Clinical/standards leadership | LWH-GOV-002/004/005/008 → LWH-PRD-003/015…024 → LWH-SPEC-018/019 → LWH-OPS-003/006/007 |
| Engineering / implementation agents | AGENTS.md → LWH-ARC-001 → LWH-ENG-001/002 → LWH-SPEC-003/004/006/009/010/011/017 → affected PRDs |
| Data / Directorate intelligence | LWH-PRD-004…008 → LWH-SPEC-007/008/014 → LWH-OPS-002 |
| Finance / programme owners | LWH-COM-001…003 → LWH-PRD-013/022/025 → finance/entitlement state and ledger contracts |
| Privacy/security/QA | LWH-GOV-002…008 → LWH-SPEC-003/012…017/021 → LWH-ENG-003/004 → VALIDATION_REPORT.md |

## File index

Paths and links below are relative to the unpacked suite. Open this README after extracting the archive to follow them. Document IDs remain stable for agent search and cross-reference; manifest.json provides exact paths, metadata and checksums.

### 00-control

| Document | Title | Owner |
|---|---|---|
| [LWH-DIR-001](docs/00-control/LWH-DIR-001_directive_validation_source_dossier_and_decision_register.md) | Director directive dossier, confirmed decisions and unresolved inputs | Directorate business analyst |
| [LWH-DOC-000](docs/00-control/LWH-DOC-000_documentation_master_blueprint.md) | Documentation master and product baseline | Programme product owner |
| [LWH-DOC-001](docs/00-control/LWH-DOC-001_documentation_control_terminology_and_traceability_handbook.md) | Documentation control, terminology and traceability | Documentation and product lead |

### 01-programme

| Document | Title | Owner |
|---|---|---|
| [LWH-ARC-001](docs/01-programme/LWH-ARC-001_system_context_capability_architecture_and_integration_strategy.md) | Platform architecture, system context and integration strategy | Platform architect |
| [LWH-BRD-001](docs/01-programme/LWH-BRD-001_business_requirements_and_institutional_service_model.md) | Business requirements and institutional service model | Directorate product owner |
| [LWH-STR-001](docs/01-programme/LWH-STR-001_programme_charter_and_executive_outcome_framework.md) | Programme charter and executive outcome framework | Directorate programme sponsor |

### 02-prds

| Document | Title | Owner |
|---|---|---|
| [LWH-PRD-001](docs/02-prds/LWH-PRD-001_organisation_identity_roles_and_delegated_administration.md) | Organisation identity, roles and delegated administration | Identity and Directorate operations lead |
| [LWH-PRD-002](docs/02-prds/LWH-PRD-002_facility_registry_service_directory_and_discovery.md) | Facility registry, service directory and discovery | Network registry lead |
| [LWH-PRD-003](docs/02-prds/LWH-PRD-003_affiliation_standards_inspection_renewal_and_noncompliance.md) | Affiliation, inspection, renewal and noncompliance | Directorate standards lead |
| [LWH-PRD-004](docs/02-prds/LWH-PRD-004_periodic_facility_and_zone_health_reporting.md) | Periodic facility, zone and regional health reporting | Health information lead |
| [LWH-PRD-005](docs/02-prds/LWH-PRD-005_health_event_notification_safety_learning_and_review.md) | Health events, safety reporting and review | Clinical quality and health information leads |
| [LWH-PRD-006](docs/02-prds/LWH-PRD-006_data_validation_verification_and_stewardship.md) | Data validation, verification and stewardship | Health information stewardship lead |
| [LWH-PRD-007](docs/02-prds/LWH-PRD-007_leadership_dashboards_and_institutional_intelligence.md) | Leadership dashboards and institutional intelligence | Directorate intelligence owner |
| [LWH-PRD-008](docs/02-prds/LWH-PRD-008_interventions_decisions_and_accountable_action_tracking.md) | Interventions, decisions and accountable action | Directorate programme operations lead |
| [LWH-PRD-009](docs/02-prds/LWH-PRD-009_community_clinics_network_readiness_and_referral_coordination.md) | Community clinics, readiness and referral coordination | Network clinical operations lead |
| [LWH-PRD-010](docs/02-prds/LWH-PRD-010_health_education_approved_policy_and_rights_communication.md) | Health education, approved policy and rights communication | Clinical editorial and Directorate policy lead |
| [LWH-PRD-011](docs/02-prds/LWH-PRD-011_loveworld_care_workspace_and_service_integration.md) | LW Care service integration and remote care | Clinical service product owner |
| [LWH-PRD-012](docs/02-prds/LWH-PRD-012_patient_identity_record_continuity_and_controlled_exchange.md) | Patient identity, record continuity and controlled exchange | Clinical information and privacy leads |
| [LWH-PRD-013](docs/02-prds/LWH-PRD-013_sponsor_programmes_institutional_funding_and_programme_impact.md) | Sponsored programmes, entitlements and funding | Programme finance and care access leads |
| [LWH-PRD-014](docs/02-prds/LWH-PRD-014_governed_intelligence_assistants_and_workflow_automation.md) | Governed assistants and workflow automation | AI product and clinical governance leads |
| [LWH-PRD-015](docs/02-prds/LWH-PRD-015_patient_administration_and_longitudinal_clinical_chart.md) | Patient administration and longitudinal clinical chart | Facility clinical information lead |
| [LWH-PRD-016](docs/02-prds/LWH-PRD-016_ambulatory_emergency_triage_and_encounter_workflows.md) | Ambulatory, emergency triage and encounter workflows | Facility clinical operations lead |
| [LWH-PRD-017](docs/02-prds/LWH-PRD-017_inpatient_admission_nursing_transfer_and_discharge.md) | Inpatient admission, nursing, transfer and discharge | Hospital clinical and nursing directors |
| [LWH-PRD-018](docs/02-prds/LWH-PRD-018_maternal_newborn_child_and_continuing_care_programmes.md) | Maternal, newborn, child and continuing care programmes | Maternal/child and continuing-care clinical leads |
| [LWH-PRD-019](docs/02-prds/LWH-PRD-019_clinical_orders_laboratory_imaging_and_results.md) | Clinical orders, laboratory, imaging and results | Diagnostic services and clinical information leads |
| [LWH-PRD-020](docs/02-prds/LWH-PRD-020_medicines_prescribing_dispensing_administration_and_clinical_stock.md) | Medicines, prescribing, dispensing, administration and stock | Medication safety, pharmacy and nursing leads |
| [LWH-PRD-021](docs/02-prds/LWH-PRD-021_procedures_surgery_anaesthesia_and_transfusion.md) | Procedures, surgery, anaesthesia and transfusion | Facility procedural services and clinical safety leads |
| [LWH-PRD-022](docs/02-prds/LWH-PRD-022_patient_billing_payments_claims_and_care_financial_workflows.md) | Patient billing, payments, claims and care finance | Facility and programme finance lead |
| [LWH-PRD-023](docs/02-prds/LWH-PRD-023_my_lw_health_care_patient_and_family_experience.md) | My LW Health Care: patient and family experience | Patient experience and clinical service owners |
| [LWH-PRD-024](docs/02-prds/LWH-PRD-024_lw_care_clinician_workspace_and_companion.md) | LW Care clinician workspace and companion | Clinical workforce and service owners |
| [LWH-PRD-025](docs/02-prds/LWH-PRD-025_optional_accounting_procurement_hr_and_payroll_modules.md) | Optional accounting, procurement, HR and payroll | Enterprise service and facility finance owners |

### 03-specifications

| Document | Title | Owner |
|---|---|---|
| [LWH-SPEC-001](docs/03-specifications/LWH-SPEC-001_information_architecture_design_system_and_role_specific_screens.md) | Information architecture, design system and screen behaviour | Product design and accessibility lead |
| [LWH-SPEC-002](docs/03-specifications/LWH-SPEC-002_user_journeys_and_service_blueprints.md) | End-to-end user journeys and service blueprints | Service design and operations lead |
| [LWH-SPEC-003](docs/03-specifications/LWH-SPEC-003_identity_authorisation_and_delegation_matrix.md) | Identity, authorisation and delegation matrix | Security and privacy architects |
| [LWH-SPEC-004](docs/03-specifications/LWH-SPEC-004_canonical_domain_model_data_dictionary_and_lineage.md) | Canonical domain model, data dictionary and lineage | Data and clinical information architects |
| [LWH-SPEC-005](docs/03-specifications/LWH-SPEC-005_facility_master_data_geography_and_service_readiness_contracts.md) | Facility master data, geography and service readiness | Network master-data lead |
| [LWH-SPEC-006](docs/03-specifications/LWH-SPEC-006_form_catalogue_field_dictionary_and_executable_schemas.md) | Form catalogue, field dictionary and executable capture schemas | Clinical information, standards and reporting leads |
| [LWH-SPEC-007](docs/03-specifications/LWH-SPEC-007_indicator_catalogue_and_reporting_measurement_framework.md) | Indicator catalogue and measurement framework | Health information and clinical measurement leads |
| [LWH-SPEC-008](docs/03-specifications/LWH-SPEC-008_reporting_data_quality_and_reconciliation_specification.md) | Reporting, data quality and reconciliation rules | Health information systems lead |
| [LWH-SPEC-009](docs/03-specifications/LWH-SPEC-009_workflow_state_transition_and_business_rule_catalogue.md) | State transitions and business-rule catalogue | Domain architecture and operations leads |
| [LWH-SPEC-010](docs/03-specifications/LWH-SPEC-010_api_command_query_and_error_contracts.md) | API commands, queries and error contracts | API and domain architecture lead |
| [LWH-SPEC-011](docs/03-specifications/LWH-SPEC-011_events_notifications_durable_jobs_and_integration_contracts.md) | Events, notifications, durable jobs and integrations | Workflow and integration architecture lead |
| [LWH-SPEC-012](docs/03-specifications/LWH-SPEC-012_interoperability_and_patient_record_exchange_specification.md) | Interoperability and controlled patient-record exchange | Clinical interoperability and records leads |
| [LWH-SPEC-013](docs/03-specifications/LWH-SPEC-013_intelligence_runtime_tools_memory_and_evaluation.md) | Intelligence runtime, tools, memory and evaluation | AI engineering and clinical governance leads |
| [LWH-SPEC-014](docs/03-specifications/LWH-SPEC-014_analytics_disclosure_control_and_leadership_view_contracts.md) | Analytics, disclosure and leadership view contracts | Analytics and privacy leads |
| [LWH-SPEC-015](docs/03-specifications/LWH-SPEC-015_nonfunctional_reliability_and_service_quality_specification.md) | Reliability, performance and service-quality specification | Platform reliability and service operations leads |
| [LWH-SPEC-016](docs/03-specifications/LWH-SPEC-016_security_architecture_and_threat_model.md) | Security architecture and threat model | Security architect and privacy owner |
| [LWH-SPEC-017](docs/03-specifications/LWH-SPEC-017_facility_local_runtime_offline_operations_and_synchronisation.md) | Facility local runtime, full offline care and synchronisation | Facility runtime architect and clinical operator |
| [LWH-SPEC-018](docs/03-specifications/LWH-SPEC-018_clinical_record_orders_and_team_workflow_contracts.md) | Clinical record, order and team workflow contracts | Clinical information architect |
| [LWH-SPEC-019](docs/03-specifications/LWH-SPEC-019_clinical_terminology_medicines_and_specialty_data_contracts.md) | Clinical terminology, medicines and specialty data contracts | Clinical terminology and medication-safety leads |
| [LWH-SPEC-020](docs/03-specifications/LWH-SPEC-020_laboratory_imaging_devices_and_document_interfaces.md) | Laboratory, imaging, device and document interfaces | Departmental integration lead |
| [LWH-SPEC-021](docs/03-specifications/LWH-SPEC-021_global_jurisdiction_activation_and_policy_configuration.md) | Global jurisdiction activation and policy configuration | Country activation and platform policy leads |

### 04-governance

| Document | Title | Owner |
|---|---|---|
| [LWH-GOV-001](docs/04-governance/LWH-GOV-001_operating_model_organisation_hierarchy_and_decision_rights.md) | Operating model, ministry hierarchy and decision rights | Directorate operations lead |
| [LWH-GOV-002](docs/04-governance/LWH-GOV-002_clinical_scope_intended_use_and_safety_governance.md) | Clinical intended use, scope and safety governance | Authorised clinical governance lead |
| [LWH-GOV-003](docs/04-governance/LWH-GOV-003_privacy_lawful_processing_and_jurisdictional_data_governance.md) | Privacy, processing purposes and jurisdictional governance | Privacy officer and accountable data custodians |
| [LWH-GOV-004](docs/04-governance/LWH-GOV-004_records_consent_sharing_retention_and_correction_policy.md) | Records, consent, sharing, retention and correction policy | Clinical records custodian and privacy lead |
| [LWH-GOV-005](docs/04-governance/LWH-GOV-005_affiliation_standards_inspections_and_institutional_compliance_policy.md) | Affiliation, inspection and institutional standards policy | Directorate authorised standards body |
| [LWH-GOV-006](docs/04-governance/LWH-GOV-006_risk_incidents_escalation_and_complaints_governance.md) | Risk, incidents, escalation and complaints governance | Clinical quality and service incident owners |
| [LWH-GOV-007](docs/04-governance/LWH-GOV-007_ai_knowledge_and_automation_governance_policy.md) | AI, knowledge and automation governance | Clinical AI governance and security leads |
| [LWH-GOV-008](docs/04-governance/LWH-GOV-008_country_activation_facility_privileging_and_local_authority.md) | Country activation, facility privileges and local authority | Directorate country activation owner |
| [LWH-STD-001](docs/04-governance/LWH-STD-001_source_standards_adaptation_and_local_policy_register.md) | Source standards, adaptation and policy register | Clinical standards, data and security source owners |

### 05-engineering

| Document | Title | Owner |
|---|---|---|
| [LWH-ENG-001](docs/05-engineering/LWH-ENG-001_current_system_audit_reuse_integration_and_migration_plan.md) | Existing-system audit, reuse and integration plan | Engineering lead and existing Care maintainers |
| [LWH-ENG-002](docs/05-engineering/LWH-ENG-002_delivery_roadmap_epics_dependencies_and_build_contracts.md) | Delivery roadmap, epics and implementation contracts | Engineering delivery and product leads |
| [LWH-ENG-003](docs/05-engineering/LWH-ENG-003_quality_strategy_verification_and_test_specifications.md) | Quality strategy and verification specifications | QA lead with clinical, privacy and finance reviewers |
| [LWH-ENG-004](docs/05-engineering/LWH-ENG-004_role_based_uat_mandate_demonstration_and_acceptance_pack.md) | Role-based UAT, Director demonstration and acceptance pack | Programme acceptance and clinical QA leads |
| [LWH-ENG-005](docs/05-engineering/LWH-ENG-005_environments_ci_cd_release_and_rollback_specification.md) | Environments, CI/CD, release and rollback | Release engineering and platform leads |
| [LWH-ENG-006](docs/05-engineering/LWH-ENG-006_observability_reconciliation_and_release_evidence_specification.md) | Observability, reconciliation and release evidence | Platform observability and clinical operations leads |
| [LWH-ENG-007](docs/05-engineering/LWH-ENG-007_legacy_emr_integration_migration_and_cutover.md) | Existing EMR integration, migration and cutover | Migration lead, records custodian and facility clinical director |

### 06-operations

| Document | Title | Owner |
|---|---|---|
| [LWH-OPS-001](docs/06-operations/LWH-OPS-001_facility_network_onboarding_and_directory_stewardship_sop.md) | Facility/network onboarding and directory stewardship | Network registry lead |
| [LWH-OPS-002](docs/06-operations/LWH-OPS-002_facility_reporting_zone_coordination_and_data_quality_sop.md) | Facility reporting, regional/zonal coordination and data quality | Health information lead |
| [LWH-OPS-003](docs/06-operations/LWH-OPS-003_inspection_affiliation_renewal_and_noncompliance_casework_sop.md) | Inspection, affiliation, renewal and noncompliance casework | Directorate standards secretariat |
| [LWH-OPS-004](docs/06-operations/LWH-OPS-004_clinic_referral_education_and_intervention_fulfilment_sop.md) | Clinic, referral, education and intervention fulfilment | Regional/zonal health operations and clinical network leads |
| [LWH-OPS-005](docs/06-operations/LWH-OPS-005_platform_support_continuity_recovery_and_service_runbooks.md) | Platform support, incidents, recovery and continuity | Platform service and incident leads |
| [LWH-OPS-006](docs/06-operations/LWH-OPS-006_facility_clinical_operations_offline_care_and_sync_reconciliation.md) | Facility clinical operation, downtime and synchronisation | Facility clinical director and local technical lead |
| [LWH-OPS-007](docs/06-operations/LWH-OPS-007_emr_adoption_training_and_facility_activation.md) | EMR adoption, role training and facility activation | Facility implementation and clinical training leads |

### 07-commercial

| Document | Title | Owner |
|---|---|---|
| [LWH-COM-001](docs/07-commercial/LWH-COM-001_business_case_programme_economics_and_funding_model.md) | Business case, funding and programme economics | Directorate finance and programme sponsor |
| [LWH-COM-002](docs/07-commercial/LWH-COM-002_scope_of_work_ownership_managed_service_and_change_control_framework.md) | Scope of work, ownership, managed service and change control | Directorate sponsor and Prolific Intelligence delivery lead |
| [LWH-COM-003](docs/07-commercial/LWH-COM-003_partner_data_sharing_procurement_and_service_agreement_templates.md) | Participation, service and data agreement templates | Directorate legal/commercial and privacy owners |

## First implementation actions

1. Nominate actual Directorate, clinical, records/privacy, information, finance and facility owners; reconcile the official hierarchy and existing templates.
2. Audit the current Care repositories/deployments/data and decide verified reuse/integration.
3. Implement shared identity/data/permission/state/local-runtime foundations and the complete institutional vertical slice.
4. Implement the full clinical scope and both facility adoption routes using the canonical contracts.
5. Select countries/facilities, adopt applicable packages and qualify actual staffing, privacy/clinical/finance, local infrastructure, integration, training and support before live activation.

Use the supplied requirement/acceptance registries to generate scoped implementation tickets. Source pages/metadata were researched; exact clinical instruments, local law and licensed content are reviewed at their stated adoption depth. See LWH-STD-001 for source boundaries and rights.
